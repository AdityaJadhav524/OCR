import requests
import time
import json
import os

BASE_URL = "http://127.0.0.1:8000"
PDF_PATH = os.path.abspath("validation_lab/backend/temp/JOB_20260618_121804_8C99_BOI_SAVINGS_DIGITAL.pdf")

def main():
    print(f"Uploading {PDF_PATH}...")
    with open(PDF_PATH, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/api/benchmark/upload",
            files={"files": f}
        )
    resp.raise_for_status()
    job_id = resp.json().get("job_id")
    print(f"Job ID: {job_id}")

    # Send password immediately
    print("Sending password...")
    resp = requests.post(
        f"{BASE_URL}/api/benchmark/password",
        json={"job_id": job_id, "password": "1170AKSH"}
    )
    resp.raise_for_status()

    # Wait for completion

    # Wait for completion
    time.sleep(2)
    while True:
        resp = requests.get(f"{BASE_URL}/api/benchmark/status/{job_id}")
        data = resp.json()
        print(f"Status: {data.get('status')} | Stage: {data.get('stage')}")
        if data.get("status") in ["completed", "failed"]:
            break
        time.sleep(1)

    print("\n--- FINAL RESULT ---")
    trackers = data.get("trackers", [])
    if trackers:
        t = trackers[0]
        # Find telemetry
        rows_accepted = 0
        abort_reason = None
        zones_created = False
        protected_tokens = 0
        header_row = None
        
        # In the tracker log
        for log in t.get("logs", []):
            state = log.get("state")
            details = log.get("details", {})
            if state == "PROTECTED_HEADER":
                protected_tokens = len(details.get("protected_tokens", []))
                header_row = details.get("protected_row")
            elif state == "PARSED":
                rows_accepted = details.get("accepted_rows", 0)
                if rows_accepted == 0:
                    abort_reason = details.get("abort_reason")
        
        output = {
            "selected_header_row": header_row,
            "protected_tokens": protected_tokens,
            "zones_created": True if rows_accepted > 0 else False,
            "rows_detected": rows_accepted,
            "rows_accepted": rows_accepted,
            "abort_reason": abort_reason
        }
        print(json.dumps(output, indent=2))
        
        # Also let's print the actual result from the API live_result
        print(f"API Live Result: {json.dumps(data.get('live_result'), indent=2)}")

if __name__ == "__main__":
    main()
