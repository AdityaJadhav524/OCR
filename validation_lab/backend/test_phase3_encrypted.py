import requests
import time
import os
import fitz  # PyMuPDF

PDF_PATH = r"z:\CA\debug\test_enc.pdf"
PASSWORD = "password123"

# Create a dummy encrypted PDF
doc = fitz.open()
page = doc.new_page()
# Write some text so it has "content" (maybe detected as digital, but if we render to image it'll be scanned)
# For now, let's just create an empty PDF. fitz detect_document_type uses page.get_text("words").
# If we add no words, it's considered scanned.
doc.save(PDF_PATH, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=PASSWORD, user_pw=PASSWORD)
doc.close()

print("--- GATE 10: Encrypted Scanned PDF ---")
print("1. Uploading without password...")
with open(PDF_PATH, "rb") as f:
    files = {"file": ("test_enc.pdf", f, "application/pdf")}
    res = requests.post("http://127.0.0.1:8000/api/process", files=files)

data = res.json()
print("Process response (no password):", data.get("error_code"))
session_id = data.get("session_id")
print("Session ID:", session_id)

print("\n2. Uploading WITH password (simulating Unlock & Process)...")
with open(PDF_PATH, "rb") as f:
    files = {"file": ("test_enc.pdf", f, "application/pdf")}
    data = {"password": PASSWORD, "session_id": session_id}
    t0 = time.time()
    res = requests.post("http://127.0.0.1:8000/api/process", files=files, data=data)
    t1 = time.time()

data = res.json()
print(f"Process response (with password): success={data.get('success')} error={data.get('error')}")
print(f"Total /api/process time: {t1 - t0:.2f} seconds")

print("\n3. Verifying OCR Count...")
res = requests.get(f"http://127.0.0.1:8000/api/session/{session_id}")
session_info = res.json()
ocr_count = session_info["metadata"]["ocr_execution_count"]
retry_count = session_info["metadata"]["retry_count"]
print(f"OCR Execution Count: {ocr_count} (Expected 1)")
print(f"Retry Count: {retry_count} (Expected 0)")

print("\n4. Triggering Retry Extraction...")
res = requests.post("http://127.0.0.1:8000/api/retry-bank-detection", json={"session_id": session_id})
retry_data = res.json()
print("Retry response:", retry_data.get("success"), retry_data.get("error_code") or retry_data.get("error"))

res = requests.get(f"http://127.0.0.1:8000/api/session/{session_id}")
session_info = res.json()
ocr_count2 = session_info["metadata"]["ocr_execution_count"]
retry_count2 = session_info["metadata"]["retry_count"]
print(f"OCR Execution Count: {ocr_count2} (Expected 1)")
print(f"Retry Count: {retry_count2} (Expected 1)")
