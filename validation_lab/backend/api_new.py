"""
Validation Lab Backend API
Exposes the core parsing engine step-by-step to the React frontend.
"""

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
    if ocr_stage and ocr_stage.get("extra_data"):
        ext = ocr_stage["extra_data"]
        ocr_pages = len(ext.get("pages", [])) or ext.get("ocr_tree", {}).get("total_pages", 0)
        
    bank_stage = next((s for s in stages if s["name"] == "Bank Detection"), None)
    txn_stage = next((s for s in stages if s["name"] == "Transaction Extraction (LLM)"), None)

    bank_ext = bank_stage.get("extra_data") or {} if bank_stage else {}
    txn_ext = txn_stage.get("extra_data") or {} if txn_stage else {}

    return JSONResponse(status_code=500 if error_msg else 200, content={
        "success": not error_msg,
        "session_id": session_id,
        "stages": stages,
        "final_transactions": final_txns,
        "error": error_msg,
        "document_type": document_type,
        "security_state": security_state,
        "ocr_status": ocr_status,
        "ocr_pages": ocr_pages,
        "ocr_words": ocr_words,
        "ocr_lines": ocr_lines,
        "ocr_text_preview": ocr_text[:1000] if ocr_text else "",
        "bank_detection": bank_ext.get("identity_json", {}) if bank_stage and bank_stage["status"] == "SUCCESS" else {},
        "transaction_extraction": {"raw": txn_ext.get("raw_response", "")} if txn_stage and txn_stage["status"] == "SUCCESS" else {}
    })

def do_bank_detection(session_id):
    session = SESSION_CACHE[session_id]
    pages = session.get("pages", [])
    t0 = time.time()
    try:
        identity_json = classify_document_llm(pages)
        t1 = time.time()
        session["bank_detection"] = identity_json
        log_stage(session_id, "Bank Detection", "SUCCESS", identity_json.get("institution_name", "UNKNOWN"), int((t1 - t0) * 1000), extra_data={"identity_json": identity_json})
        return True, None
    except Exception as e:
        logger.exception("Bank Detection error")
        log_stage(session_id, "Bank Detection", "ERROR", str(e), int((time.time() - t0) * 1000), error=str(e))
        return False, str(e)

def do_extraction(session_id):
    session = SESSION_CACHE[session_id]
    full_text = session.get("ocr_text", "")
    identity_json = session.get("bank_detection", {})
    t0 = time.time()
    try:
        raw_response = parse_with_llm(full_text, identity_json)
        t1 = time.time()
        session["llm_raw_output"] = raw_response
        log_stage(session_id, "Transaction Extraction (LLM)", "SUCCESS", f"Received {(len(raw_response))} chars from LLM", int((t1 - t0) * 1000), extra_data={"raw_response": raw_response})
        return True, None
    except Exception as e:
        logger.exception("Transaction Extraction error")
        log_stage(session_id, "Transaction Extraction (LLM)", "ERROR", str(e), int((time.time() - t0) * 1000), error=str(e))
        return False, str(e)

def do_validation(session_id):
    session = SESSION_CACHE[session_id]
    raw_response = session.get("llm_raw_output", "")
    t0 = time.time()
    try:
        transactions = extract_json_from_response(raw_response)
        normalized = []
        for txn in transactions:
            txn["date"] = normalize_date(txn.get("date"))
            if "details" in txn and "narration" not in txn:
                txn["narration"] = txn.pop("details")
            normalized.append(txn)
        t1 = time.time()
        session["transactions"] = normalized
        log_stage(session_id, "Normalization", "SUCCESS", f"Normalized {len(normalized)} transactions", int((t1 - t0) * 1000), extra_data={"transactions": normalized})
        return True, normalized, None
    except Exception as e:
        logger.exception("Normalization error")
        log_stage(session_id, "Normalization", "ERROR", str(e), int((time.time() - t0) * 1000), error=str(e))
        return False, [], str(e)

@app.post("/api/process")
async def process_document(file: UploadFile = File(...), password: Optional[str] = Form(None), session_id: Optional[str] = Form(None)):
    """
    Runs the full pipeline, but captures every intermediate artifact and timing.
    """
    if not session_id:
        session_id = f"SESSION_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
        
    if session_id not in SESSION_CACHE:
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
    else:
        # Clear stages on re-upload (e.g. password retry)
        SESSION_CACHE[session_id]["stages"] = []
        SESSION_CACHE[session_id]["last_updated"] = datetime.datetime.now().isoformat()

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
    try:
        t0 = time.time()
        doc_type = detect_document_type(file_path, password)
        SESSION_CACHE[session_id]["document_type"] = doc_type
        t1 = time.time()
        log_stage(session_id, "PDF Classification", "SUCCESS", doc_type, int((t1 - t0) * 1000), extra_data={"pdf_type": doc_type})

        full_text = ""
        pages = []
        
        SESSION_CACHE[session_id]["ocr_execution_count"] += 1

        if doc_type == "digital":
            t0 = time.time()
            full_text, pages = _extract_digital(file_path, password=password)
            t1 = time.time()
            log_stage(session_id, "PDF Text Extraction", "SUCCESS", f"Extracted {len(pages)} pages", int((t1 - t0) * 1000), extra_data={"full_text": full_text, "pages": pages})
        else:
            t0 = time.time()
            full_text, pages = _extract_scanned(file_path, password=password)
            t1 = time.time()
            
            ocr_output = {
                "total_pages": len(pages),
                "lines_preview": [{"page": i + 1, "text": line} for i, p in enumerate(pages) for line in p.split('\n')[:10] if line.strip()]
            }
            log_stage(session_id, "OCR Engine (Subprocess)", "SUCCESS", f"Extracted {len(pages)} pages", int((t1 - t0) * 1000), extra_data={"ocr_tree": ocr_output})
            log_stage(session_id, "OCR Adapter", "SUCCESS", f"Converted to {len(pages)} text pages", 0, extra_data={"full_text": full_text})
            
        SESSION_CACHE[session_id]["ocr_text"] = full_text
        SESSION_CACHE[session_id]["pages"] = pages
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
    if not session.get("ocr_text") or not session.get("pages"):
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
    if not session.get("ocr_text") or not session.get("bank_detection"):
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
    if not session.get("llm_raw_output"):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
