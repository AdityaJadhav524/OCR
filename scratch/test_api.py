import os
import sys
import time

_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
sys.path.insert(0, _workspace)

from validation_lab.backend.api import SESSION_CACHE, _build_response_from_cache

# Let's mock a request to the API's internal logic.
# Wait, it's easier to just use fastapi TestClient or directly call process_document.
from fastapi.testclient import TestClient
from validation_lab.backend.api import app

client = TestClient(app)

digital_pdf = os.path.join(_workspace, "tests", "pdfs", "YESBANK_SAVINGS_DIGITAL.pdf")

print("--- DIGITAL PDF VIA API ---")
t0 = time.time()
with open(digital_pdf, "rb") as f:
    response = client.post("/api/process", files={"file": ("test.pdf", f, "application/pdf")})
t1 = time.time()

data = response.json()
print(f"Success: {data.get('success')}")
print(f"Document Class: {data.get('document_type')}")
print(f"OCR Used: {data.get('ocr_metrics', {}).get('ocr_used', False)}")
print(f"Processing Time MS: {(t1 - t0) * 1000:.2f}")

# Check stages to see if OCR was used
for s in data.get("stages", []):
    if "OCR Engine" in s["name"] and s["status"] == "SUCCESS":
        print(f"OCR Actually Executed: True")
