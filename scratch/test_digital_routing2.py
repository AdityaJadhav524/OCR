import os
import sys
import time
import fitz # PyMuPDF

_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
sys.path.insert(0, _workspace)

from core.extractors.document_router import route_document
from validation_lab.backend.api import detect_document_type

pdf_path = os.path.join(_workspace, "scratch", "true_digital2.pdf")
doc = fitz.open()
page = doc.new_page()

# Insert 100 unique words
text = " ".join([f"word{i}" for i in range(100)])
page.insert_text((50, 50), text)
doc.save(pdf_path)
doc.close()

doc_type, doc_reason = detect_document_type(pdf_path)
print(f"API detect_document_type returned: {doc_type} (Reason: {doc_reason})")

t0 = time.time()
full_text, pages, telemetry, page_tokens = route_document(pdf_path)
t1 = time.time()

print("\n--- Digital Routing Verification ---")
print(f"document_class = {telemetry.get('classification')}")
print(f"ocr_used = {telemetry.get('engine') == 'PaddleOCR'}")
print(f"processing_time_ms = {(t1 - t0) * 1000:.2f}")

