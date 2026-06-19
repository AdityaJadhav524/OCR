"""
Validation Lab Backend API
Exposes the core parsing engine step-by-step to the React frontend.
"""

import re
import asyncio
import logging
import os
import sys
import time
import json
import uuid
import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# -- Add core/ and ocr_core/ to sys.path --
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _WORKSPACE_ROOT)
if os.path.join(_WORKSPACE_ROOT, "core") not in sys.path:
    sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "core"))
if os.path.join(_WORKSPACE_ROOT, "ocr_core") not in sys.path:
    sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "ocr_core"))

# Imports from core
from core.extractors.document_router import detect_document_type, _extract_digital, _extract_scanned, check_pdf_security
from core.detection.bank_detector import classify_document_llm
from core.parsers.statement_parser import parse_with_llm
from core.parsers.validation import extract_json_from_response, normalize_date
from pipeline import run_pipeline
from core.telemetry.lifecycle_tracker import LifecycleTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validation_lab.api")

app = FastAPI(title="Validation Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_CACHE = {}

@app.on_event("startup")
async def startup_diagnostics():
    logger.info("=== Validation Lab Startup Diagnostics ===")
    logger.info(f"Python executable: {sys.executable}")
    
    try:
        import paddleocr
        logger.info("PaddleOCR available = True")
    except ImportError:
        logger.info("PaddleOCR available = False")
        
    try:
        import fitz
        logger.info("PyMuPDF available = True")
    except ImportError:
        logger.info("PyMuPDF available = False")
        
    try:
        import cv2
        logger.info("OpenCV available = True")
    except ImportError:
        logger.info("OpenCV available = False")
    logger.info("==========================================")


# Temporary directory for uploads
TEMP_DIR = os.path.join(_WORKSPACE_ROOT, "validation_lab", "backend", "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

class DebugStageRequest(BaseModel):
    file_path: str
    stage: str

class RetryRequest(BaseModel):
    session_id: str

def log_stage(session_id, name, status, result, time_taken_ms, error=None, extra_data=None):
    stage_info = {
        "name": name,
        "status": status,
        "time_ms": time_taken_ms,
        "result": result,
        "error": error,
        "extra_data": extra_data
    }
    if session_id in SESSION_CACHE:
        SESSION_CACHE[session_id]["stages"].append(stage_info)
        SESSION_CACHE[session_id]["last_updated"] = datetime.datetime.now().isoformat()
    return stage_info

def _build_response_from_cache(session_id, error_msg=None, final_txns=[]):
    session = SESSION_CACHE.get(session_id, {})
    stages = session.get("stages", [])
    
    document_type = None
    security_state = "normal"
    
    security_stage = next((s for s in stages if s["name"] == "PDF Security Check"), None)
    if security_stage:
        is_enc = security_stage.get("extra_data", {}).get("is_encrypted", False)
        status = security_stage["status"]
        if status == "PASSWORD_REQUIRED":
            security_state = "encrypted"
        elif is_enc and status in ("UNLOCKED", "PASS"):
            security_state = "unlocked"
    
    classification_stage = next((s for s in stages if s["name"] == "PDF Classification"), None)
    if classification_stage:
        document_type = classification_stage["result"]
        
    ocr_text = ""
    for s in stages:
        ext = s.get("extra_data") or {}
        if s["name"] == "OCR Adapter" or s["name"] == "PDF Text Extraction":
            ocr_text = ext.get("full_text", "")
            
    ocr_words = len(ocr_text.split()) if ocr_text else 0
    ocr_lines = len(ocr_text.split("\n")) if ocr_text else 0
    
    ocr_stage = next((s for s in stages if "OCR Engine" in s["name"] or "PDF Text Extraction" in s["name"]), None)
    ocr_status = ocr_stage["status"] if ocr_stage else "PENDING"
    ocr_pages = 0
    merge_stats = session.get("ocr_metrics", {})
    if ocr_stage and ocr_stage.get("extra_data"):
        ext = ocr_stage["extra_data"]
        ocr_pages = len(ext.get("pages", [])) or ext.get("ocr_tree", {}).get("total_pages", 0)
        
    bank_stage = next((s for s in stages if s["name"] == "Bank Detection"), None)
    txn_stage = next((s for s in stages if s["name"] == "Transaction Extraction (LLM)"), None)

    bank_ext = bank_stage.get("extra_data") or {} if bank_stage else {}
    txn_ext = txn_stage.get("extra_data") or {} if txn_stage else {}

    error_code = None
    if error_msg:
        err_lower = error_msg.lower()
        if "api key not valid" in err_lower or "api_key_invalid" in err_lower:
            error_code = "INVALID_API_KEY"
        elif "missing api key" in err_lower or "not found" in err_lower and "gemini" in err_lower:
            error_code = "MISSING_API_KEY"
        elif "429" in err_lower or "quota" in err_lower or "resource_exhausted" in err_lower:
            error_code = "GEMINI_429"
        elif "503" in err_lower or "overloaded" in err_lower:
            error_code = "GEMINI_503"
        elif "timeout" in err_lower:
            error_code = "READ_TIMEOUT"
        elif "session_not_found" in err_lower:
            error_code = "SESSION_NOT_FOUND"

    from core.extractors.pdf_extractor import DATE_RE
    date_matches = len(DATE_RE.findall(ocr_text)) if ocr_text else 0
    txn_rows = len([l for l in (ocr_text or "").split('\n') if DATE_RE.search(l[:30])])

    # Compute audit summary dynamically
    audit_sum = {
        "total_transactions": len(final_txns),
        "full_agreement": 0,
        "partial_agreement": 0,
        "conflict": 0,
        "unseeded": 0,
        "recovery_candidate": 0,
        "suspicious_fields_count": 0,
        "rejected_rows": session.get("ocr_metrics", {}).get("v2_rejected_rows", 0),
        "contaminated_rows": sum(s.get("extra_data", {}).get("contaminated_rows", 0) for s in stages if s["name"] == "Transaction Parsing (V2)")
    }
    
    suspicious_summary = {
        "MULTIPLE_DOTS": 0,
        "PUNCTUATION_CORRUPTION": 0,
        "DATE_NARRATION_MERGE": 0,
        "COLUMN_BOUNDARY_SUSPECT": 0,
        "NUMERIC_SHAPE_ANOMALY": 0,
        "POWER_OF_TEN_DRIFT": 0,
        "SMALL_DIGIT_SUBSTITUTION": 0,
        "PRIMARY_BALANCE_ANOMALY": 0,
        "DOWNSTREAM_CHAIN_EFFECT": 0
    }
    
    for txn in final_txns:
        st = txn.get("agreement_state")
        if st == "FULL_AGREEMENT": audit_sum["full_agreement"] += 1
        elif st == "PARTIAL_AGREEMENT": audit_sum["partial_agreement"] += 1
        elif st == "CONFLICT": audit_sum["conflict"] += 1
        elif st == "UNSEEDED": audit_sum["unseeded"] += 1
        elif st == "RECOVERY_CANDIDATE": audit_sum["recovery_candidate"] += 1
        if txn.get("suspicious_fields"):
            audit_sum["suspicious_fields_count"] += 1
            for k, field_data in txn["suspicious_fields"].items():
                reason = field_data.get("reason")
                if reason in suspicious_summary:
                    suspicious_summary[reason] += 1
                else:
                    suspicious_summary[reason] = 1

    return JSONResponse(status_code=500 if error_msg else 200, content={
        "success": not error_msg,
        "session_id": session_id,
        "document_type": document_type,
        "security_state": security_state,
        "stages": stages,
        "final_transactions": final_txns,
        "reject_ledger": session.get("ocr_metrics", {}).get("reject_log", []),
        "audit_summary": audit_sum,
        "suspicious_summary": suspicious_summary,
        "error": error_msg,
        "error_code": error_code,
        "ocr_status": ocr_status,
        "ocr_pages": ocr_pages,
        "ocr_words": ocr_words,
        "ocr_lines": ocr_lines,
        "ocr_text_preview": ocr_text[:1000] if ocr_text else "",
        "ocr_metrics": {
            **session.get("ocr_metrics", {}),
            **merge_stats,
            "date_matches": date_matches,
            "txn_rows": txn_rows
        },
        "bank_detection": bank_ext.get("identity_json", {}) if bank_stage and bank_stage["status"] == "SUCCESS" else {},
        "transaction_extraction": {"raw": txn_ext.get("raw_response", "")} if txn_stage and txn_stage["status"] == "SUCCESS" else {},
        "real_benchmark": session.get("real_benchmark", None)
    })

def do_bank_detection(session_id):
    session = SESSION_CACHE[session_id]

    logger.info("[do_bank_detection] entered, pid=%s", os.getpid())

    if session.get("bank_detection"):
        logger.info("[do_bank_detection] returning cached result: %s",
                    session["bank_detection"].get("institution_name", "UNKNOWN"))
        log_stage(session_id, "Bank Detection", "SUCCESS",
                  session["bank_detection"].get("institution_name", "UNKNOWN"), 0,
                  extra_data={"identity_json": session["bank_detection"]})
        return True, None

    pages = session.get("pages", [])
    logger.info("[do_bank_detection] calling classify_document_llm on %d pages", len(pages))

    t0 = time.time()
    try:
        identity_json = classify_document_llm(pages)
        t1 = time.time()
        session["bank_detection"] = identity_json
        logger.info("[do_bank_detection] detected: %s  (%.0f ms)",
                    identity_json.get("institution_name", "UNKNOWN"), (t1 - t0) * 1000)
        log_stage(session_id, "Bank Detection", "SUCCESS",
                  identity_json.get("institution_name", "UNKNOWN"),
                  int((t1 - t0) * 1000), extra_data={"identity_json": identity_json})
        return True, None
    except Exception as e:
        logger.exception("Bank Detection error")
        log_stage(session_id, "Bank Detection", "ERROR", str(e),
                  int((time.time() - t0) * 1000), error=str(e))
        return False, str(e)

def do_extraction(session_id):
    session = SESSION_CACHE[session_id]
    if session.get("transactions"):
        log_stage(session_id, "Transaction Extraction (LLM)", "SUCCESS", f"Used {len(session['transactions'])} cached transactions", 0, extra_data={"raw_response": session.get("llm_raw_output", "[]")})
        return True, None

    full_text = session.get("ocr_text", "")
    identity_json = session.get("bank_detection", {})
    document_type = session.get("document_type", "digital")
    t0 = time.time()
    
    from core.parsers.statement_parser import TransactionExtractionFailure, parse_with_llm
    from core.parsers.deterministic_parser import parse_deterministic_transactions
    from core.parsers.credit_card_parser import parse_credit_card_transactions
    
    # 1. Deterministic Extraction (Fast Path)
    # Applied to ALL documents since the parser uses Bank Agnostic balance math
    transactions = []
    parser_used = "none"
    
    try:
        tokens = session.get("tokens", [])
        if tokens:
            from core.layout.structural_token_protection import protect_table_header_tokens
            tokens = protect_table_header_tokens(tokens, session)
            from core.detection.header_suppression import suppress_headers_and_footers
            tokens = suppress_headers_and_footers(tokens)
            
        if identity_json.get("document_family") == "CREDIT_CARD":
            transactions, telemetry = parse_credit_card_transactions(tokens)
            parser_used = "credit_card"
        else:
            if tokens:
                from core.parsers.coordinate_parser_v2 import parse_with_coordinates
                transactions, telemetry = parse_with_coordinates(
                    tokens,
                    bank=identity_json.get("institution_name", "Unknown")
                )
                parser_used = "coordinate_v2"
                
                # Fallback to V1 if V2 extracted 0 transactions
                if not transactions:
                    transactions, telemetry = parse_deterministic_transactions(full_text)
                    parser_used = "deterministic"
            else:
                transactions, telemetry = parse_deterministic_transactions(full_text)
                parser_used = "deterministic"
            
        if transactions:
            session["llm_result"] = {
                "raw_response": "[]", # No LLM used
                "prompt_text": "",
                "provider": "deterministic",
                "model": "deterministic",
                "transactions": transactions
            }
            session["llm_raw_output"] = "[]"
            ocr_metrics = session.setdefault("ocr_metrics", {})
            ocr_metrics["parser_used"] = parser_used
            ocr_metrics.update(telemetry)
            
            t1 = time.time()
            log_stage(session_id, "Transaction Parsing (V2)", "COMPLETED", f"Extracted {len(transactions)} transactions", int(time.time()*1000) - t0, extra_data={"parser_used": parser_used, **telemetry, "contaminated_rows": telemetry.get("contaminated_rows", 0)})
            return True, None
    except Exception as e:
        logger.warning(f"Deterministic parser failed: {e}")

    # 2. Deterministic extraction returned nothing — hard fail with debug dump
    #    NO LLM fallback. The balance solver is the primary and only engine.
    msg = (
        f"DETERMINISTIC_EXTRACTION_FAILURE: "
        f"Balance solver found 0 transactions in {len(full_text.splitlines())} OCR lines. "
        f"Check dumps/{session_id}_ocr.txt for the raw text."
    )
    logger.warning(msg)

    dump_dir = os.path.join(_WORKSPACE_ROOT, "validation_lab", "backend", "dumps")
    os.makedirs(dump_dir, exist_ok=True)
    with open(os.path.join(dump_dir, f"{session_id}_ocr.txt"), "w", encoding="utf-8") as f:
        f.write(full_text)

    session["llm_result"] = {
        "raw_response": "[]",
        "prompt_text":  "",
        "provider":     "deterministic",
        "model":        "deterministic",
        "transactions": [],
    }
    session["llm_raw_output"] = "[]"
    session.setdefault("ocr_metrics", {})["parser_used"] = "deterministic_failed"

    log_stage(session_id, "Transaction Extraction (Deterministic)", "ERROR",
              msg, int((time.time() - t0) * 1000), error=msg)
    return False, msg

def do_validation(session_id):
    session = SESSION_CACHE[session_id]
    llm_result = session.get("llm_result", {})
    if "transactions" in llm_result:
        transactions = llm_result["transactions"]
    else:
        raw_response = session.get("llm_raw_output", "")
        transactions = extract_json_from_response(raw_response)
        
    t0 = time.time()
    try:
        normalized = []
        for txn in transactions:
            txn["date"] = normalize_date(txn.get("date"))
            if "details" in txn and "narration" not in txn:
                txn["narration"] = txn.pop("details")
            normalized.append(txn)
        t1 = time.time()
        session["transactions"] = normalized
        
        bank_detected = bool(session.get("bank_detection", {}).get("institution_name"))
        if bank_detected and len(normalized) == 0:
            ocr_text = session.get("ocr_text", "")
            ocr_lines = len(ocr_text.splitlines()) if ocr_text else 0
            pages = len(session.get("pages", []))
            
            if pages > 0 and ocr_lines > 20:
                msg = "EXTRACTION_SUSPECT: Bank statement detected successfully, >0 pages, >20 lines, but 0 transactions extracted."
                logger.warning(msg)
                
                # Save to disk
                dump_dir = os.path.join(_WORKSPACE_ROOT, "validation_lab", "backend", "dumps")
                os.makedirs(dump_dir, exist_ok=True)
                
                with open(os.path.join(dump_dir, f"{session_id}_ocr.txt"), "w", encoding="utf-8") as f:
                    f.write(ocr_text)
                    
                prompt = session.get("llm_result", {}).get("prompt_text", "")
                with open(os.path.join(dump_dir, f"{session_id}_prompt.txt"), "w", encoding="utf-8") as f:
                    f.write(prompt)
                    
                raw_response = session.get("llm_raw_output", "")
                with open(os.path.join(dump_dir, f"{session_id}_llm_raw.txt"), "w", encoding="utf-8") as f:
                    f.write(raw_response)
                    
                log_stage(session_id, "Normalization", "SUCCESS", msg, int((t1 - t0) * 1000), extra_data={"transactions": normalized})
            else:
                msg = "WARNING: Bank statement detected successfully, but 0 transactions extracted."
                logger.warning(msg)
                log_stage(session_id, "Normalization", "SUCCESS", msg, int((t1 - t0) * 1000), extra_data={"transactions": normalized})
        else:
            log_stage(session_id, "Normalization", "SUCCESS", f"Normalized {len(normalized)} transactions", int((t1 - t0) * 1000), extra_data={"transactions": normalized})
            
        return True, normalized, None
    except Exception as e:
        logger.exception("Normalization error")
        log_stage(session_id, "Normalization", "ERROR", str(e), int((t1 - t0) * 1000), error=str(e))
        log_stage(session_id, "Normalization", "ERROR", str(e), int((t1 - t0) * 1000), error=str(e))
        return False, [], str(e)

@app.post("/api/process")
async def process_document(file: UploadFile = File(...), password: Optional[str] = Form(None), session_id: Optional[str] = Form(None)):
    """
    Unified endpoint for processing a document.
    """
    logger.info("=== INCOMING UPLOAD REQUEST: session_id=%s has_password=%s ===",
                session_id, password is not None)

    if session_id and session_id in SESSION_CACHE:
        logger.info("[process_document] existing session: ocr=%s bank=%s txns=%s",
                    bool(SESSION_CACHE[session_id].get('ocr_text')),
                    bool(SESSION_CACHE[session_id].get('bank_detection')),
                    bool(SESSION_CACHE[session_id].get('transactions')))
        # Clear stages on re-upload (e.g. password retry)
        SESSION_CACHE[session_id]["stages"] = []
        SESSION_CACHE[session_id]["last_updated"] = datetime.datetime.now().isoformat()
    else:
        session_id = f"SESSION_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
        logger.info("[process_document] new session: %s", session_id)
        SESSION_CACHE[session_id] = {
            "created_at": datetime.datetime.now().isoformat(),
            "last_updated": datetime.datetime.now().isoformat(),
            "retry_count": 0,
            "ocr_execution_count": 0,
            "document_type": None,
            "security_state": "normal",
            "ocr_text": "",
            "pages": [],
            "ocr_metrics": {},
            "bank_detection": {},
            "llm_raw_output": "",
            "transactions": [],
            "validation": {},
            "stages": []
        }

    file_path = os.path.join(TEMP_DIR, f"{session_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # STAGE 0: Security Check
    t0 = time.time()
    security = check_pdf_security(file_path, password)
    t1 = time.time()
    log_stage(session_id, "PDF Security Check", security["status"], f"Encrypted: {security['is_encrypted']}", int((t1 - t0) * 1000), extra_data={"is_encrypted": security["is_encrypted"]})
    
    if security["status"] == "PASSWORD_REQUIRED":
        return JSONResponse(status_code=200, content={
            "success": False,
            "error_code": "PASSWORD_REQUIRED",
            "needs_password": True,
            "filename": file.filename,
            "session_id": session_id
        })
    elif security["status"] == "INVALID_PASSWORD":
        return JSONResponse(status_code=401, content={
            "success": False,
            "error_code": "INVALID_PASSWORD",
            "error": "Incorrect PDF password",
            "needs_password": True,
            "filename": file.filename,
            "session_id": session_id
        })

    # STAGE 1 & 2 & 3: PDF Detection and OCR
    if SESSION_CACHE[session_id].get("ocr_text"):
        log_stage(session_id, "PDF Text Extraction", "SUCCESS", "Used cached OCR results", 0, extra_data={"full_text": SESSION_CACHE[session_id]["ocr_text"], "pages": SESSION_CACHE[session_id].get("pages", [])})
    else:
        try:
            t0 = time.time()
            doc_type, doc_reason = detect_document_type(file_path, password)
            SESSION_CACHE[session_id]["document_type"] = doc_type
            t1 = time.time()
            log_stage(session_id, "PDF Classification", "SUCCESS", doc_type, int((t1 - t0) * 1000), extra_data={"pdf_type": doc_type, "reason": doc_reason})
    
            full_text = ""
            pages = []
            
            SESSION_CACHE[session_id]["ocr_execution_count"] += 1
    
            if doc_type == "digital":
                t0 = time.time()
                full_text, pages, merge_stats, page_tokens = _extract_digital(file_path, password=password)
                t1 = time.time()
                log_stage(session_id, "PDF Text Extraction", "SUCCESS", f"Extracted {len(pages)} pages", int((t1 - t0) * 1000), extra_data={"full_text": full_text, "pages": pages, "merge_stats": merge_stats})
                SESSION_CACHE[session_id]["ocr_metrics"].update(merge_stats)
            else:
                t0 = time.time()
                full_text, pages, merge_stats, page_tokens = _extract_scanned(file_path, password=password)
                t1 = time.time()
                SESSION_CACHE[session_id]["ocr_metrics"].update(merge_stats)
                
                ocr_output = {
                    "total_pages": len(pages),
                    "lines_preview": [{"page": i + 1, "text": line} for i, p in enumerate(pages) for line in p.split('\n')[:10] if line.strip()]
                }
                log_stage(session_id, "OCR Engine (Subprocess)", "SUCCESS", f"Extracted {len(pages)} pages", int((t1 - t0) * 1000), extra_data={"ocr_tree": ocr_output})
                log_stage(session_id, "OCR Adapter", "SUCCESS", f"Converted to {len(pages)} text pages", 0, extra_data={"full_text": full_text})
                
            SESSION_CACHE[session_id]["ocr_text"] = full_text
            SESSION_CACHE[session_id]["pages"] = pages
            SESSION_CACHE[session_id]["tokens"] = page_tokens

            # ==========================================
            # REAL BENCHMARK INJECTION
            # ==========================================
            if page_tokens:
                try:
                    from core.layout.row_detector import detect_rows
                    from core.layout.column_detector import detect_columns
                    from core.parsers.coordinate_parser_v2 import parse_with_coordinates
                    from core.parsers.deterministic_parser import parse_deterministic_transactions
                    from core.validators.financial_audit import run_financial_audit
                    from core.validators.confidence_scorer import score_statement

                    # V1 Benchmark
                    v1_rows, _ = parse_deterministic_transactions(full_text)
                    v1_audit = run_financial_audit(v1_rows)
                    v1_score = score_statement(v1_rows)

                    from core.detection.bank_detector import classify_document_llm
                    identity = classify_document_llm(pages)

                    # V2 Benchmark — pass raw tokens, let V2 do its own detection
                    v2_txns, v2_tel = parse_with_coordinates(
                        page_tokens, 
                        bank=identity.get("institution_name"), 
                        identity=identity
                    )
                    v2_audit = run_financial_audit(v2_txns)
                    v2_score = score_statement(v2_txns)

                    SESSION_CACHE[session_id]["real_benchmark"] = {
                        "token_count": len(page_tokens),
                        "v1_count": len(v1_rows),
                        "v2_count": len(v2_txns),
                        "diff_rows": abs(len(v1_rows) - len(v2_txns)),
                        "v1_output": v1_rows,
                        "v1_score": v1_score.get("statement_score", 0),
                        "v2_output": v2_txns,
                        "v2_score": v2_score.get("statement_score", 0),
                        "v2_telemetry": v2_tel,
                        "audit_result": v2_audit
                    }
                except Exception as b_exc:
                    logger.error(f"Benchmark injection failed: {b_exc}")
            else:
                logger.warning("No tokens available for V2 benchmark. Is this a scanned PDF?")
            # ==========================================
        except Exception as e:
            logger.exception("OCR Pipeline error")
            log_stage(session_id, "OCR Engine", "ERROR", str(e), 0, error=str(e))
            return _build_response_from_cache(session_id, error_msg=str(e))

    # STAGE 4: Bank Detection
    ok, err = do_bank_detection(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)

    # STAGE 5: LLM Extraction
    ok, err = do_extraction(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)

    # STAGE 6: Normalization
    ok, normalized, err = do_validation(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)

    return _build_response_from_cache(session_id, final_txns=normalized)

def truncate_stages_before_retry(session_id, stage_names_to_keep):
    session = SESSION_CACHE[session_id]
    session["retry_count"] += 1
    new_stages = []
    for s in session["stages"]:
        if s["name"] in stage_names_to_keep:
            new_stages.append(s)
    session["stages"] = new_stages

@app.post("/api/retry-bank-detection")
async def retry_bank_detection(req: RetryRequest):
    session_id = req.session_id
    if session_id not in SESSION_CACHE:
        return JSONResponse(status_code=200, content={"success": False, "error_code": "SESSION_NOT_FOUND"})
    session = SESSION_CACHE[session_id]
    if "ocr_text" not in session or "pages" not in session:
        return JSONResponse(status_code=200, content={"success": False, "error_code": "CACHE_INCOMPLETE"})

    truncate_stages_before_retry(session_id, ["PDF Security Check", "PDF Classification", "PDF Text Extraction", "OCR Engine (Subprocess)", "OCR Adapter"])

    ok, err = do_bank_detection(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)
    ok, err = do_extraction(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)
    ok, normalized, err = do_validation(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)

    return _build_response_from_cache(session_id, final_txns=normalized)

@app.post("/api/retry-extraction")
async def retry_extraction(req: RetryRequest):
    session_id = req.session_id
    if session_id not in SESSION_CACHE:
        return JSONResponse(status_code=200, content={"success": False, "error_code": "SESSION_NOT_FOUND"})
    session = SESSION_CACHE[session_id]
    if "ocr_text" not in session or "bank_detection" not in session:
        return JSONResponse(status_code=200, content={"success": False, "error_code": "CACHE_INCOMPLETE"})

    truncate_stages_before_retry(session_id, ["PDF Security Check", "PDF Classification", "PDF Text Extraction", "OCR Engine (Subprocess)", "OCR Adapter", "Bank Detection"])

    ok, err = do_extraction(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)
    ok, normalized, err = do_validation(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)

    return _build_response_from_cache(session_id, final_txns=normalized)

@app.post("/api/retry-validation")
async def retry_validation(req: RetryRequest):
    session_id = req.session_id
    if session_id not in SESSION_CACHE:
        return JSONResponse(status_code=200, content={"success": False, "error_code": "SESSION_NOT_FOUND"})
    session = SESSION_CACHE[session_id]
    if "llm_raw_output" not in session:
        return JSONResponse(status_code=200, content={"success": False, "error_code": "CACHE_INCOMPLETE"})

    truncate_stages_before_retry(session_id, ["PDF Security Check", "PDF Classification", "PDF Text Extraction", "OCR Engine (Subprocess)", "OCR Adapter", "Bank Detection", "Transaction Extraction (LLM)"])

    ok, normalized, err = do_validation(session_id)
    if not ok: return _build_response_from_cache(session_id, error_msg=err)

    return _build_response_from_cache(session_id, final_txns=normalized)

@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    if session_id not in SESSION_CACHE:
        return JSONResponse(status_code=200, content={"success": False, "error_code": "SESSION_NOT_FOUND"})
    
    session = SESSION_CACHE[session_id]
    res = _build_response_from_cache(session_id, final_txns=session.get("transactions", []))
    body = json.loads(res.body)
    return JSONResponse(status_code=200, content={
        "success": True,
        "session_id": session_id,
        "full_result": body,
        "metadata": {
            "retry_count": session.get("retry_count"),
            "ocr_execution_count": session.get("ocr_execution_count")
        }
    })

@app.get("/api/session/{session_id}/ocr")
async def get_session_ocr(session_id: str):
    if session_id not in SESSION_CACHE:
        return JSONResponse(status_code=404, content={"success": False, "error": "Session not found"})
    session = SESSION_CACHE[session_id]
    return JSONResponse(status_code=200, content={
        "success": True,
        "session_id": session_id,
        "ocr_text": session.get("ocr_text", "")
    })

@app.get("/api/session/{session_id}/prompt")
async def get_session_prompt(session_id: str):
    if session_id not in SESSION_CACHE:
        return JSONResponse(status_code=404, content={"success": False, "error": "Session not found"})
    session = SESSION_CACHE[session_id]
    llm_result = session.get("llm_result", {})
    return JSONResponse(status_code=200, content={
        "success": True,
        "session_id": session_id,
        "prompt": llm_result.get("prompt_text", "")
    })

@app.get("/api/session/{session_id}/llm_raw")
async def get_session_llm_raw(session_id: str):
    if session_id not in SESSION_CACHE:
        return JSONResponse(status_code=404, content={"success": False, "error": "Session not found"})
    session = SESSION_CACHE[session_id]
    llm_result = session.get("llm_result", {})
    return JSONResponse(status_code=200, content={
        "success": True,
        "session_id": session_id,
        "raw_response": llm_result.get("raw_response", session.get("llm_raw_output", ""))
    })

@app.post("/api/debug-stage")
async def debug_stage(request: DebugStageRequest):
    """
    Rerun a specific stage isolated.
    """
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        if request.stage == "classification":
            doc_type = detect_document_type(request.file_path)
            return {"result": doc_type}
        else:
            raise HTTPException(status_code=400, detail=f"Stage {request.stage} debug not fully implemented yet.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/cache")
async def debug_cache():
    return JSONResponse(content=SESSION_CACHE)

@app.get("/api/debug/parser_flow/{session_id}")
async def debug_parser_flow(session_id: str):
    session = SESSION_CACHE.get(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    # Run deterministic parser again to get fresh output
    from core.parsers.deterministic_parser import parse_deterministic_transactions
    full_text = session.get("ocr_text", "")
    try:
        det_output, _ = parse_deterministic_transactions(full_text)
    except:
        det_output = []
        
    # Get normalization input
    llm_result = session.get("llm_result", {})
    if "transactions" in llm_result:
        norm_input = llm_result["transactions"]
    else:
        norm_input = []
        
    # Get normalization output
    norm_output = session.get("transactions", [])
    
    return JSONResponse(content={
        "deterministic_parser_output": det_output[:5],
        "normalization_input": norm_input[:5],
        "normalization_output": norm_output[:5],
        "session_cache_object": {k: v[:5] if isinstance(v, list) else v for k, v in session.items() if k not in ["ocr_text", "pages"]},
    })


@app.get("/api/debug/run_v2/{session_id}")
async def debug_run_v2(session_id: str):
    """
    Re-run coordinate_parser_v2 on the cached tokens for the given session.
    Returns fresh telemetry including full P1 reject log (debit, credit, balance,
    prev_balance, conservation_state per reject).
    Use this to get updated telemetry after parser code changes without re-uploading.
    """
    session = SESSION_CACHE.get(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    tokens = session.get("tokens")
    if not tokens:
        return JSONResponse(status_code=400, content={"error": "No tokens in session cache"})

    try:
        from core.parsers.coordinate_parser_v2 import parse_with_coordinates
        from core.parsers.deterministic_parser import parse_deterministic_transactions
        from core.validators.financial_audit import run_financial_audit

        v2_txns, v2_tel = parse_with_coordinates(tokens)
        v2_audit = run_financial_audit(v2_txns)

        full_text = session.get("ocr_text", "")
        v1_rows, _ = parse_deterministic_transactions(full_text)

        return JSONResponse(content={
            "session_id":   session_id,
            "token_count":  len(tokens),
            "v1_count":     len(v1_rows),
            "v2_count":     len(v2_txns),
            "diff":         abs(len(v1_rows) - len(v2_txns)),
            "v2_telemetry": v2_tel,
            "v2_output":    v2_txns,
            "audit":        v2_audit,
        })
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"error": str(e), "traceback": traceback.format_exc()})

# ── BENCHMARK BACKGROUND WORKER ──────────────────────────────────────────────────

BENCHMARK_JOBS = {}

from fastapi import BackgroundTasks

async def run_benchmark_job(job_id: str, file_paths: List[str], password: str = None, original_filenames: List[str] = None):
    try:
        from core.adapters.ocr_subprocess import extract_via_subprocess
        from core.parsers.coordinate_parser_v2 import parse_with_coordinates
        from core.validators.ledger_truth import annotate_ledger_truth
        from core.detection.header_suppression import suppress_headers_and_footers
        
        import uuid
        for idx, file_path in enumerate(file_paths):
            t0_job = time.time()
            BENCHMARK_JOBS[job_id]["current_idx"] = idx
            BENCHMARK_JOBS[job_id]["status"] = "processing"
            BENCHMARK_JOBS[job_id]["stage"] = "Starting"
            
            # Extract PDF name and generate statement_id
            base_name = os.path.basename(file_path)
            prefix = f"{job_id}_"
            pdf_name = original_filenames[idx] if original_filenames and idx < len(original_filenames) else (base_name[len(prefix):] if base_name.startswith(prefix) else base_name)
            statement_id = str(uuid.uuid4())
            logger.info(f"Processing file {idx + 1}/{len(file_paths)}: {pdf_name} (statement_id: {statement_id})")
            
            bank_name = "Unknown"
            doc_class = "UNKNOWN"
            parser_used_name = "Unknown"
            doc_family = "BANK_STATEMENT"

            def update_live_state(stage_name):
                BENCHMARK_JOBS[job_id]["stage"] = stage_name
                BENCHMARK_JOBS[job_id]["live_result"] = {
                    "pdf_name": pdf_name,
                    "bank_name": bank_name,
                    "document_class": doc_class,
                    "parser_used": parser_used_name,
                    "status": "processing"
                }
            
            tracker = BENCHMARK_JOBS[job_id]["trackers"][idx]
            tracker.log_state("QUEUED")
            if password:
                tracker.stamp("password_received_at")
            
            try:
                t_file_start = time.time()
                update_live_state("Detecting Document Class")
                # Detect document class (digital vs scanned)
                try:
                    tracker.stamp("engine_start")
                    doc_type, _ = detect_document_type(file_path, password=password)
                    doc_class = doc_type.upper()
                    tracker.stamp("classification_at")
                    tracker.log_state("CLASSIFIED")
                except ValueError as ve:
                    if "PASSWORD" in str(ve):
                        tracker.stamp("password_detected_at")
                        tracker.stamp("password_validated_at") # For invalid it throws different or same? Wait, 'needs_pass' doesn't mean invalid. It just means required.
                        tracker.stamp("engine_end")
                        tracker.stamp("engine_result", "PASSWORD_REQUIRED")
                        tracker.stamp("engine", "PyMuPDF")
                        tracker.log_state("PASSWORD_REQUIRED")
                        tracker.stamp("backend_state_available_at")
                        raise ve
                    doc_class = "UNKNOWN"
                except Exception:
                    doc_class = "UNKNOWN"

                tracker.stamp("engine", "PyMuPDF" if doc_class == "DIGITAL" else "PaddleOCR")
                update_live_state(f"Extracting Text ({doc_class})")
                tracker.stamp("extraction_started_at")
                tracker.log_state("EXTRACTING")
                # 1. Extract (uses route_document to avoid OCR on digital PDFs)
                from core.extractors.document_router import route_document
                full_text, pages, telemetry, page_tokens = route_document(file_path, password=password)
                if password:
                    tracker.stamp("password_validated_at")
                tracker.stamp("extraction_finished_at")
                tracker.stamp("engine_end")
                tracker.stamp("engine_result", "SUCCESS")
                
                update_live_state("Detecting Bank")
                # 1.1 Bank Detection
                from core.detection.bank_detector import classify_document_llm
                from core.parsers.credit_card_parser import parse_credit_card_transactions
                identity = classify_document_llm(pages)
                bank_name = identity.get("institution_name", "Unknown")
                doc_family = identity.get("document_family", "BANK_STATEMENT")
                
                update_live_state("Suppressing Headers")
                # 1.5 Header Suppression (P1)
                from core.layout.structural_token_protection import protect_table_header_tokens
                # Telemetry dictionary for extraction
                suppression_telemetry = {}
                page_tokens = protect_table_header_tokens(page_tokens, suppression_telemetry)
                
                # Merge into tracker if needed
                if "protection_events" in suppression_telemetry:
                    for ev in suppression_telemetry["protection_events"]:
                        tracker.log_state("PROTECTED_HEADER", details=ev)
                        
                from core.detection.header_suppression import suppress_headers_and_footers
                page_tokens = suppress_headers_and_footers(page_tokens)
                
                update_live_state("Parsing Transactions")
                tracker.stamp("parser_started_at")
                tracker.log_state("PARSING")
                # 2. Extract
                if doc_family == "CREDIT_CARD":
                    txns, tel = parse_credit_card_transactions(page_tokens)
                    parser_used_name = "credit_card_parser"
                else:
                    pdf_type = "SCANNED" if "SCANNED" in base_name.upper() else "DIGITAL"
                    txns, tel = parse_with_coordinates(
                        page_tokens, 
                        pdf_name=pdf_name, 
                        statement_id=statement_id, 
                        job_id=job_id, 
                        bank=bank_name,
                        pdf_type=pdf_type
                    )
                    parser_used_name = "coordinate_parser_v2"
                tracker.stamp("parser_finished_at")
                update_live_state("Validating")
                tracker.log_state("VALIDATING")
                # 3. Validation
                doc_family = identity.get("family", "BANK_STATEMENT") if "identity" in locals() and identity else "BANK_STATEMENT"
                final_txns = annotate_ledger_truth(txns, document_family=doc_family, full_text=full_text)
                tracker.stamp("validation_completed_at")

                BENCHMARK_JOBS[job_id]["stage"] = "Finalizing Results"
                # Enriched metadata
                rows_detected_val = tel.get("rows_detected", len(txns) + tel.get("rejected_rows", len(tel.get("reject_log", []))))
                rejected_txns_count = tel.get("rejected_rows", len(tel.get("reject_log", [])))
                token_count_val = len(page_tokens) if page_tokens else 0
                processing_time_ms_val = int((time.time() - t0_job) * 1000)
                
                reject_log = tel.get("reject_log", [])
                if reject_log:
                    from collections import Counter
                    counts = Counter([r.get("reject_reason", "unknown") for r in reject_log])
                    logger.info(f"REJECT REASON COUNTS FOR {pdf_name}: {dict(counts)}")
                
                # Compute aggregates similar to the frozen architecture
                primary_anomalies = []
                downstream_effects = []
                ocr_format_counts = {}
                
                for txn in final_txns:
                    for field, sig in txn.get("suspicious_fields", {}).items():
                        reason = sig.get("reason", "")
                        if reason in ("POWER_OF_TEN_DRIFT", "SMALL_DIGIT_SUBSTITUTION", "PRIMARY_BALANCE_ANOMALY"):
                            primary_anomalies.append({
                                "anomaly_id": sig.get("anomaly_id", "—"),
                                "date": txn.get("date"),
                                "difference": sig.get("diff"),
                                "detector": reason,
                                "affected_rows": sig.get("affected_rows", [])
                            })
                        elif reason == "DOWNSTREAM_CHAIN_EFFECT":
                            downstream_effects.append({
                                "date": txn.get("date"),
                                "root_row": sig.get("root_row"),
                                "diff": sig.get("diff")
                            })
                        elif reason in ("MULTIPLE_DOTS", "PUNCTUATION_CORRUPTION",
                                        "DATE_NARRATION_MERGE", "COLUMN_BOUNDARY_SUSPECT",
                                        "NUMERIC_SHAPE_ANOMALY"):
                            ocr_format_counts[reason] = ocr_format_counts.get(reason, 0) + 1
                
                BENCHMARK_JOBS[job_id]["results"].append({
                    "statement_id": statement_id,
                    "pdf_name": pdf_name,
                    "bank": bank_name,
                    "bank_name": bank_name,
                    "document_class": doc_class,
                    "parser_used": parser_used_name,
                    "ocr_used": doc_class != "DIGITAL",
                    "token_count": token_count_val,
                    "rows_detected": rows_detected_val,
                    "accepted_transactions": len(final_txns),
                    "rejected_transactions": rejected_txns_count,
                    "processing_time_ms": processing_time_ms_val,
                    "pages": len(pages) if "pages" in locals() else 0,
                    "summary": {
                        "transactions": len(final_txns),
                        "primary_anomalies": len(primary_anomalies),
                        "downstream_effects": len(downstream_effects),
                        "format_issues": sum(ocr_format_counts.values()),
                        "rejected_rows": tel.get("rejected_rows", len(tel.get("reject_log", []))),
                        "contaminated_rows": tel.get("contaminated_rows", 0),
                        "contamination_summary": tel.get("contamination_summary", {})
                    },
                    "status": "success",
                    "transactions": final_txns,
                    "telemetry": tel,
                    "ocr_metrics": telemetry,
                    "error_code": None,
                    "primary_anomalies": primary_anomalies,
                    "downstream_effects": downstream_effects,
                    "ocr_format_counts": ocr_format_counts
                })
                
            except Exception as e:
                err_msg = str(e)
                # Password detection fallback in batch
                if "PyCryptodome" in err_msg or "password" in err_msg.lower() or "encrypted" in err_msg.lower() or "PASSWORD_REQUIRED" in err_msg:
                    logger.info(f"Password required for {file_path} - skipping.")
                    BENCHMARK_JOBS[job_id]["results"].append({
                        "statement_id": statement_id,
                        "pdf_name": pdf_name,
                        "status": "password_required",
                        "error_code": "PASSWORD_REQUIRED"
                    })
                else:
                    logger.exception(f"Error processing {file_path}")
                    BENCHMARK_JOBS[job_id]["results"].append({
                        "statement_id": statement_id,
                        "pdf_name": pdf_name,
                        "bank": bank_name,
                        "status": "error",
                        "error": err_msg
                    })
                
            tracker.stamp("completed_at")
            if "PASSWORD" not in str(err_msg if 'err_msg' in locals() else ""):
                tracker.log_state("COMPLETED")
                tracker.stamp("backend_state_available_at")
                
            try:
                out_dir = os.path.join(_WORKSPACE_ROOT, "tests", "audit_reports", "timelines")
                tracker.dump(out_dir)
            except Exception as e:
                logger.error(f"Failed to dump timeline: {e}")
                
        BENCHMARK_JOBS[job_id]["status"] = "completed"
        
    except Exception as e:
        logger.exception("Benchmark job crashed")
        BENCHMARK_JOBS[job_id]["status"] = "error"
        BENCHMARK_JOBS[job_id]["error"] = str(e)

@app.post("/api/benchmark/upload")
async def benchmark_upload(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...),
    password: Optional[str] = Form(None)
):
    job_id = f"JOB_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
    file_paths = []
    original_filenames = []
    
    os.makedirs(os.path.join(os.path.dirname(__file__), "temp"), exist_ok=True)
    for f in files:
        temp_path = os.path.join(os.path.dirname(__file__), "temp", f"{job_id}_{f.filename}")
        with open(temp_path, "wb") as buffer:
            buffer.write(await f.read())
        file_paths.append(temp_path)
        original_filenames.append(f.filename)
        
    trackers = []
    for f in original_filenames:
        t = LifecycleTracker(job_id, f)
        t.stamp("uploaded_at")
        trackers.append(t)
        
    BENCHMARK_JOBS[job_id] = {
        "status": "pending",
        "stage": "Pending",
        "total_files": len(files),
        "current_idx": 0,
        "results": [],
        "file_names": [f.filename for f in files],
        "trackers": trackers
    }
    
    background_tasks.add_task(run_benchmark_job, job_id, file_paths, password, original_filenames)
    return {"job_id": job_id, "total_files": len(files)}

@app.get("/api/benchmark/status/{job_id}")
async def benchmark_status(job_id: str):
    if job_id not in BENCHMARK_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job_info = BENCHMARK_JOBS[job_id]
    
    for tracker in job_info.get("trackers", []):
        if job_info["status"] == "completed" or any(r.get("status") == "password_required" for r in job_info.get("results", [])):
            if tracker.timestamps.get("frontend_polled_at") is None:
                tracker.stamp("frontend_polled_at")
                try:
                    out_dir = os.path.join(_WORKSPACE_ROOT, "tests", "audit_reports", "timelines")
                    tracker.dump(out_dir)
                except: pass
                
    return job_info

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
