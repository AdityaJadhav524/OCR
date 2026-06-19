import os
import sys
import time

_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
sys.path.insert(0, _workspace)

# Mock detect_document_type
import core.extractors.document_router as dr
original_detect = dr.detect_document_type

def mock_detect(*args, **kwargs):
    return ("digital", "mocked_reason >= 30")

dr.detect_document_type = mock_detect

# Now import API
from fastapi.testclient import TestClient
from validation_lab.backend.api import app

client = TestClient(app)

digital_pdf = os.path.join(_workspace, "tests", "pdfs", "YESBANK_SAVINGS_DIGITAL.pdf")

print("--- DIGITAL PDF VIA API (MOCKED TO DIGITAL) ---")
t0 = time.time()
with open(digital_pdf, "rb") as f:
    response = client.post("/api/process", files={"file": ("test.pdf", f, "application/pdf")})
t1 = time.time()

data = response.json()
print(f"Success: {data.get('success')}")
print(f"Document Class: {data.get('document_type')}")
print(f"OCR Used: {data.get('ocr_metrics', {}).get('ocr_used', False)}")
print(f"Processing Time MS: {(t1 - t0) * 1000:.2f}")

ocr_executed = False
for s in data.get("stages", []):
    if "OCR Engine" in s["name"] and s["status"] == "SUCCESS":
        ocr_executed = True
        
print(f"OCR Actually Executed: {ocr_executed}")
