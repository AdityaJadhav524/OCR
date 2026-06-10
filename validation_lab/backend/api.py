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
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# â”€â”€ Add core/ and ocr_core/ to sys.path â”€â”€
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _WORKSPACE_ROOT)
if os.path.join(_WORKSPACE_ROOT, "core") not in sys.path:
    sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "core"))
if os.path.join(_WORKSPACE_ROOT, "ocr_core") not in sys.path:
    sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "ocr_core"))

# Imports from core
from core.extractors.document_router import detect_document_type, _extract_digital, _extract_scanned
from core.detection.bank_detector import classify_document_llm
from core.parsers.statement_parser import parse_with_llm
from core.parsers.validation import extract_json_from_response, normalize_date
from pipeline import run_pipeline  # ocr_core/ is on sys.path (no __init__.py → not a package)

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


@app.post("/api/process")
async def process_document(file: UploadFile = File(...), password: Optional[str] = Form(None)):
    """
    Runs the full pipeline, but captures every intermediate artifact and timing.
    """
    file_path = os.path.join(TEMP_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    stages = []
    
    def log_stage(name, status, result, time_taken_ms, error=None, extra_data=None):
        stage_info = {
            "name": name,
            "status": status,
            "time_ms": time_taken_ms,
            "result": result,
            "error": error,
            "extra_data": extra_data
        }
        stages.append(stage_info)
        return stage_info

    try:
        # STAGE 1: PDF Detection
        t0 = time.time()
        doc_type = detect_document_type(file_path)
        t1 = time.time()
        log_stage("PDF Classification", "SUCCESS", doc_type, int((t1 - t0) * 1000))

        # STAGE 2: Text Extraction (Digital or Scanned)
        full_text = ""
        pages = []
        extra_data = {}

        if doc_type == "digital":
            t0 = time.time()
            full_text, pages = _extract_digital(file_path, password=password)
            t1 = time.time()
            log_stage("PDF Text Extraction", "SUCCESS", f"Extracted {len(pages)} pages", int((t1 - t0) * 1000), extra_data={"full_text": full_text, "pages": pages})
        else:
            # For scanned, we run the OCR pipeline to capture the OCR layout tree separately
            t0 = time.time()
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            doc = run_pipeline(file_bytes=file_bytes, filename=file.filename)
            t1 = time.time()
            
            # Serialize the Layout Tree for the UI
            ocr_output = {
                "total_pages": len(doc.pages) if doc and hasattr(doc, "pages") else 0,
                "lines_preview": []
            }
            if doc and hasattr(doc, "pages"):
                for p in doc.pages:
                    for l in p.lines:
                        ocr_output["lines_preview"].append({"page": p.page_number, "text": l.text})

            log_stage("OCR Engine", "SUCCESS", f"Extracted {ocr_output['total_pages']} pages", int((t1 - t0) * 1000), extra_data={"ocr_tree": ocr_output})

            # STAGE 3: Adapter
            from core.adapters.ocr_adapter import document_to_text
            t0 = time.time()
            full_text, pages = document_to_text(doc)
            t1 = time.time()
            log_stage("OCR Adapter", "SUCCESS", f"Converted to {len(pages)} text pages", int((t1 - t0) * 1000), extra_data={"full_text": full_text})

        # STAGE 4: Bank Detection
        t0 = time.time()
        identity_json = classify_document_llm(pages)
        t1 = time.time()
        log_stage("Bank Detection", "SUCCESS", identity_json.get("institution_name", "UNKNOWN"), int((t1 - t0) * 1000), extra_data={"identity_json": identity_json})

        # STAGE 5: LLM Extraction
        t0 = time.time()
        raw_response = parse_with_llm(full_text, identity_json)
        t1 = time.time()
        log_stage("Transaction Extraction (LLM)", "SUCCESS", f"Received {(len(raw_response))} chars from LLM", int((t1 - t0) * 1000), extra_data={"raw_response": raw_response})

        # STAGE 6: Normalization
        t0 = time.time()
        transactions = extract_json_from_response(raw_response)
        normalized = []
        for txn in transactions:
            txn["date"] = normalize_date(txn.get("date"))
            if "details" in txn and "narration" not in txn:
                txn["narration"] = txn.pop("details")
            normalized.append(txn)
        t1 = time.time()
        log_stage("Normalization", "SUCCESS", f"Normalized {len(normalized)} transactions", int((t1 - t0) * 1000), extra_data={"transactions": normalized})

        return JSONResponse(content={
            "success": True,
            "file_path": file_path,
            "stages": stages,
            "final_transactions": normalized
        })

    except Exception as e:
        logger.exception("Pipeline error")
        log_stage("Pipeline Error", "ERROR", str(e), 0, error=str(e))
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "stages": stages
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
