import requests
import time
import os

PDF_PATH = r"z:\CA\debug\test.pdf"

# Create a dummy PDF if needed
if not os.path.exists(PDF_PATH):
    os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)
    with open(PDF_PATH, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF")

print("--- GATE 1: Initial OCR Runs Once ---")
with open(PDF_PATH, "rb") as f:
    files = {"file": ("test.pdf", f, "application/pdf")}
    print("Uploading file to /api/process...")
    res = requests.post("http://127.0.0.1:8000/api/process", files=files)

data = res.json()
print("Process response:", data.get("success"), data.get("error"))
session_id = data.get("session_id")
print("Session ID:", session_id)

if not session_id:
    print("FAILED to get session ID")
    exit(1)

print("\n--- GET /api/session ---")
res = requests.get(f"http://127.0.0.1:8000/api/session/{session_id}")
session_info = res.json()
ocr_count = session_info["metadata"]["ocr_execution_count"]
retry_count = session_info["metadata"]["retry_count"]
print(f"OCR Execution Count: {ocr_count} (Expected 1)")
print(f"Retry Count: {retry_count} (Expected 0)")

print("\n--- GATE 2 & 3: Retries do not run OCR ---")
print("Triggering /api/retry-bank-detection...")
res = requests.post("http://127.0.0.1:8000/api/retry-bank-detection", json={"session_id": session_id})
retry_data = res.json()
print("Retry response:", retry_data.get("success"), retry_data.get("error_code") or retry_data.get("error"))

res = requests.get(f"http://127.0.0.1:8000/api/session/{session_id}")
session_info = res.json()
ocr_count2 = session_info["metadata"]["ocr_execution_count"]
retry_count2 = session_info["metadata"]["retry_count"]
print(f"OCR Execution Count: {ocr_count2} (Expected 1)")
print(f"Retry Count: {retry_count2} (Expected 1)")

print("\n--- GATE 9: Server Restart Behavior ---")
print("We cannot restart server easily from here, but we can hit retry with bad ID.")
res = requests.post("http://127.0.0.1:8000/api/retry-extraction", json={"session_id": "bad_session"})
print("Bad Session Retry:", res.json())

