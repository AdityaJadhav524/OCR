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
                        break
                    return result
                return None
            time.sleep(1)
    return None

def parse_float_safe(val):
    if not val: return None
    try:
        cleaned = str(val).replace(',', '').strip()
        if cleaned.endswith(('Cr', 'Dr')):
            cleaned = cleaned[:-2].strip()
        return float(cleaned)
    except:
        return None

def distance_to_edge(x, zone):
    if not zone: return 999
    return min(abs(x - zone[0]), abs(x - zone[1]))

def zone_overlap(z1, z2):
    if not z1 or not z2: return 0
    overlap_start = max(z1[0], z2[0])
    overlap_end = min(z1[1], z2[1])
    if overlap_start < overlap_end:
        overlap = overlap_end - overlap_start
        width = z1[1] - z1[0]
        if width > 0:
            return (overlap / width) * 100
    return 0

def run_column_drift_audit():
    print(f"Running Column Drift Audit on {len(pdf_files)} PDFs...\n")

    overall_failures = {
        "ZONE_CREATION": 0,
        "ROW_GROUPING": 0,
        "OCR_DRIFT": 0,
        "UNKNOWN": 0
    }
    
    bank_summaries = []

    for pdf_path in pdf_files:
        pdf_name = os.path.basename(pdf_path)
        pwd = passwords.get(pdf_name, "1170AKSH")
        
        print(f"\n==============================================")
        print(f"Auditing {pdf_name}...")
        passwords_to_try = [pwd, "1170AKSH", "11707454011", None]
        res = run_test(pdf_path, passwords_to_try)
        
        if not res or res.get("status") != "success":
            print(f"  -> Failed to extract.")
            continue
            
        bank = res.get("bank_name", "UNKNOWN")
        transactions = res.get("v2_output", [])
        telemetry = res.get("v2_telemetry", {})
        zones = telemetry.get("zones", {})
        
        cz = zones.get("credit_zone")
        bz = zones.get("balance_zone")
        
        cz_width = cz[1] - cz[0] if cz else 0
        cz_center = cz[0] + cz_width/2 if cz else 0
        bz_width = bz[1] - bz[0] if bz else 0
        bz_center = bz[0] + bz_width/2 if bz else 0
        
        overlap_pct = zone_overlap(cz, bz)
        
        bank_stats = {
            "bank": bank,
            "rows_total": len(transactions),
            "ledger_failures": 0,
            "zone_overlap_percent": round(overlap_pct, 1),
            "avg_credit_width": round(cz_width, 1),
            "avg_balance_width": round(bz_width, 1),
            "suspected_root_cause": "UNKNOWN"
        }
        
        failed_rows = []
        success_rows = []
        
        for i, txn in enumerate(transactions):
            ledger = txn.get("ledger_truth", {})
            raw = txn.get("raw_extraction", {})
            status = ledger.get("ledger_status")
            
            is_fail = status != "PASS"
            if is_fail:
                bank_stats["ledger_failures"] += 1
                
            tokens = txn.get("_source_tokens", [])
            if not tokens: continue
            
            y_min = min((t.get("y0", 0) for t in tokens))
            y_max = max((t.get("y1", 0) for t in tokens))
            
            next_row_dist = 999
            if i + 1 < len(transactions):
                next_tokens = transactions[i+1].get("_source_tokens", [])
                if next_tokens:
                    next_y_min = min((t.get("y0", 0) for t in next_tokens))
                    next_row_dist = next_y_min - y_max
            
            row_merge = next_row_dist < 5.0
            
            cred_val = raw.get("parsed_credit")
            bal_val = raw.get("parsed_balance")
            # If it's a balance as credit failure, the target is the credit val
            target_val = cred_val if cred_val else bal_val
            
            token_x = 0
            token_text = ""
            for t in tokens:
                v = parse_float_safe(t.get("text"))
                if v and v == target_val:
                    token_x = t.get("x0", 0)
                    token_text = t.get("text", "")
                    break
                    
            if not token_text:
                continue
                
            dist_c = distance_to_edge(token_x, cz)
            dist_b = distance_to_edge(token_x, bz)
            
            assigned_to = "credit" if cred_val else "balance"
            
            record = {
                "bank": bank,
                "row": i,
                "expected_balance": ledger.get("expected_balance"),
                "parsed_credit": raw.get("parsed_credit"),
                "parsed_balance": raw.get("parsed_balance"),
                "token_text": token_text,
                "assigned_to": assigned_to,
                "credit_zone": cz,
                "balance_zone": bz,
                "credit_zone_width": round(cz_width, 1),
                "balance_zone_width": round(bz_width, 1),
                "credit_zone_center": round(cz_center, 1),
                "balance_zone_center": round(bz_center, 1),
                "token_x": token_x,
                "token_distance_from_balance_center": round(abs(token_x - bz_center), 1) if bz_center else 999,
                "candidate_columns": [
                    {"column": "credit", "distance": round(dist_c, 1)},
                    {"column": "balance", "distance": round(dist_b, 1)}
                ],
                "row_id": i,
                "row_y_min": round(y_min, 1),
                "row_y_max": round(y_max, 1),
                "token_count": len(tokens),
                "next_row_distance": round(next_row_dist, 1),
                "suspected_row_merge": row_merge,
                "failure": status
            }
            
            if is_fail:
                failed_rows.append(record)
                
                # Heuristic mapping for heatmap
                if row_merge:
                    overall_failures["ROW_GROUPING"] += 1
                elif overlap_pct > 15:
                    overall_failures["ZONE_CREATION"] += 1
                elif abs(dist_c - dist_b) < 15:
                    overall_failures["ZONE_CREATION"] += 1
                elif token_x > bz_center + 15 or token_x < cz_center - 15:
                    overall_failures["OCR_DRIFT"] += 1
                else:
                    overall_failures["UNKNOWN"] += 1
            else:
                if len(success_rows) < 20:
                    success_rows.append(record)
                    
        # Determine Bank root cause
        if bank_stats["zone_overlap_percent"] > 15:
            bank_stats["suspected_root_cause"] = "ZONE_CREATION"
        elif any(r["suspected_row_merge"] for r in failed_rows):
            bank_stats["suspected_root_cause"] = "ROW_GROUPING"
        elif any(r["token_distance_from_balance_center"] > 50 for r in failed_rows):
            bank_stats["suspected_root_cause"] = "OCR_DRIFT"
            
        bank_summaries.append(bank_stats)
        
        if failed_rows:
            print(f"\n--- 1 FAILED ROW EXAMPLE ({bank}) ---")
            print(json.dumps(failed_rows[0], indent=2))
            
        if success_rows:
            print(f"\n--- 1 SUCCESS ROW EXAMPLE ({bank}) ---")
            print(json.dumps(success_rows[0], indent=2))

    print("\n\n=== BANK SUMMARIES ===")
    print(json.dumps(bank_summaries, indent=2))
        
    print("\n\n=== OVERALL FAILURE HEATMAP ===")
    print(json.dumps(overall_failures, indent=2))

if __name__ == "__main__":
    run_column_drift_audit()
