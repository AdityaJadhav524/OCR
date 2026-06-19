import os
import time
import requests
import json
import glob
from collections import defaultdict

API_URL = "http://localhost:8000/api/benchmark/upload"
STATUS_URL = "http://localhost:8000/api/benchmark/status/{}"

pdf_dir = r"C:\Users\adity\Downloads\CA\tests\pdfs"
pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))

passwords = {
    "BOI_SAVINGS_DIGITAL.pdf": "11707454011",
    "11707454011-JUL-25221947 2.PDF": "1170AKSH",
    "HDFC_SAVINGS_SCANNED.pdf": "1170AKSH",
    "ICICI_CC_SCANNED.pdf": "1170AKSH",
    "JOB_20260618_121804_8C99_BOI_SAVINGS_DIGITAL.pdf": "1170AKSH",
    "JOB_20260618_114324_7DC5_ICICI_CC_SCANNED.pdf": "1170AKSH",
    "JOB_20260618_115001_5E18_HDFC_SAVINGS_SCANNED.pdf": "1170AKSH",
    "BOI_SAVINGS_SCANNED.pdf": "1170AKSH"
}

def run_test(pdf_path, passwords_to_try):
    for pwd in passwords_to_try:
        data = {"password": pwd} if pwd else {}
            
        with open(pdf_path, "rb") as f:
            res = requests.post(API_URL, files={"files": f}, data=data)
            
        if res.status_code != 200:
            continue
            
        job_id = res.json().get("job_id")
        if not job_id:
            continue
            
        while True:
            status_res = requests.get(STATUS_URL.format(job_id)).json()
            if status_res.get("status") in ["completed", "error"]:
                if status_res.get("results"):
                    result = status_res["results"][0]
                    if result.get("error_code") in ["PASSWORD_REQUIRED", "INVALID_PASSWORD"]:
                        break # Try next password
                    return result
                return None
            time.sleep(1)
    return None

# Stats Tracking
bank_stats = defaultdict(lambda: {
    "total_rows": 0,
    "pass_rows": 0,
    "fail_rows": 0,
    "failures": defaultdict(int)
})

print(f"Running Geometry Audit on {len(pdf_files)} PDFs...\n")

for pdf_path in pdf_files:
    pdf_name = os.path.basename(pdf_path)
    # Default to 1170AKSH for tests since it's the standard test password
    pwd = passwords.get(pdf_name, "1170AKSH")
    
    print(f"Auditing {pdf_name}...")
    passwords_to_try = [pwd, "1170AKSH", "11707454011", None]
    res = run_test(pdf_path, passwords_to_try)
    
    if not res or res.get("status") != "success":
        print(f"  -> Failed to extract.")
        continue
        
    bank = res.get("bank_name", "UNKNOWN")
    transactions = res.get("v2_output", [])
    
    stats = bank_stats[bank]
    
    if not transactions:
        # If the file passed extraction but yielded 0 transactions
        stats["total_rows"] += 1
        stats["fail_rows"] += 1
        stats["failures"]["TABLE_DETECTION_FAILURE"] += 1
        continue
    
    for txn in transactions:
        stats["total_rows"] += 1
        
        ledger = txn.get("ledger_truth", {})
        raw = txn.get("raw_extraction", {})
        
        status = ledger.get("ledger_status")
        if status == "PASS":
            stats["pass_rows"] += 1
            continue
            
        stats["fail_rows"] += 1
        
        # Taxonomy resolution
        exp_bal = ledger.get("expected_balance")
        curr_bal = raw.get("parsed_balance")
        cred = raw.get("parsed_credit")
        deb = raw.get("parsed_debit")
        
        # Map generic errors to the requested taxonomy
        error_type = status
        if error_type == "BALANCE_MISMATCH":
            error_type = "COLUMN_ASSIGNMENT_FAILURE"
            
        # Check specific geometries
        if cred is not None and exp_bal is not None and abs(cred - exp_bal) < 0.01 and curr_bal != exp_bal:
            error_type = "BALANCE_AS_CREDIT"
        elif deb is not None and exp_bal is not None and abs(deb - exp_bal) < 0.01 and curr_bal != exp_bal:
            error_type = "BALANCE_AS_DEBIT"
        elif deb is not None and cred is not None:
            error_type = "MULTIPLE_AMOUNTS"
        elif curr_bal is None:
            error_type = "MISSING_BALANCE"
            
        stats["failures"][error_type] += 1

print("\n\n--- GEOMETRY AUDIT RESULTS ---")
print(f"{'Bank':<20} | {'Rows':>5} | {'Accuracy':>8} | {'Top Failure':<25}")
print("-" * 65)

# For clustering
failure_clusters = defaultdict(list)

for bank, stats in bank_stats.items():
    total = stats["total_rows"]
    if total == 0: continue
    
    acc = (stats["pass_rows"] / total) * 100
    
    top_failure = "NONE"
    if stats["failures"]:
        top_failure = max(stats["failures"].items(), key=lambda x: x[1])[0]
        failure_clusters[top_failure].append(bank)
        
    print(f"{bank:<20} | {total:>5} | {acc:>7.1f}% | {top_failure:<25}")

print("\n\n--- FAILURE CLUSTERING ---")
print(json.dumps(failure_clusters, indent=2))
