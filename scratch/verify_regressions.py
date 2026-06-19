import os
import sys
import time
import json

_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
sys.path.insert(0, _workspace)

from core.extractors.document_router import detect_document_type, _extract_digital, _extract_scanned, check_pdf_security, route_document
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

digital_pdf = os.path.join(_workspace, "tests", "pdfs", "YESBANK_SAVINGS_DIGITAL.pdf")

print("--- DIGITAL PDF ---")
t0 = time.time()
try:
    full_text, pages, telemetry, page_tokens = route_document(digital_pdf)
    t1 = time.time()
    
    doc_class = telemetry.get("classification")
    ocr_used = telemetry.get("engine") == "PaddleOCR"
    processing_time_ms = (t1 - t0) * 1000
    
    print(f"document_class: {doc_class}")
    print(f"ocr_used: {ocr_used}")
    print(f"processing_time_ms: {processing_time_ms:.2f}")
except Exception as e:
    print(f"Error: {e}")
