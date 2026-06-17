import requests
import time
import json
import os

PDF_PATH = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"

print("1. Hitting /api/benchmark/upload")
with open(PDF_PATH, "rb") as f:
    res = requests.post("http://127.0.0.1:8000/api/benchmark/upload", files={"files": ("test.pdf", f, "application/pdf")})

data = res.json()
print("Upload Response:", data)
job_id = data.get("job_id")
print("job_id:", job_id)

if not job_id:
    exit(1)

print("\n2. Polling /api/benchmark/status/{job_id}")
while True:
    status_res = requests.get(f"http://127.0.0.1:8000/api/benchmark/status/{job_id}")
    status_data = status_res.json()
    status = status_data.get("status")
    print(f"Status: {status} | Files processed: {len(status_data.get('results', []))}")
    
    if status in ("completed", "error"):
        print("\n--- FINAL STATUS PAYLOAD ---")
        # Print keys to keep it short if results are huge
        print("Keys:", status_data.keys())
        print("status:", status_data.get("status"))
        print("error:", status_data.get("error"))
        results = status_data.get("results", [])
        print(f"results array length: {len(results)}")
        
        if len(results) > 0:
            first_result = results[0]
            print(f"first result keys: {first_result.keys()}")
            print(f"first result status: {first_result.get('status')}")
            
            # Print whether it has result inside
            result_obj = first_result.get('result', {})
            if isinstance(result_obj, dict):
                print(f"first result.result keys: {result_obj.keys()}")
            else:
                print(f"first result.result: {type(result_obj)}")
        else:
            print("results array is empty!")
            
        print("\n--- DOES FRONTEND LOSE IT? ---")
        print("Check if the frontend expects `statusData.statements` but the backend returns `statusData.results`.")
        break
        
    time.sleep(2)
