import os
import sys
import json
import time
import requests
import fitz

pdf_dir = r"C:\Users\adity\Downloads\CA\tests\pdfs"
files_to_run = [
    os.path.join(pdf_dir, "BOI_SAVINGS_SCANNED.pdf"),
    os.path.join(pdf_dir, "HDFC_SAVINGS_SCANNED.pdf")
]

print("=== STARTING BENCHMARKS ===")
job_ids = {}
for f in files_to_run:
    if not os.path.exists(f):
        print(f"Missing {f}")
        continue
    with open(f, "rb") as fobj:
        res = requests.post("http://localhost:8000/api/benchmark/upload", files={"files": fobj})
        job_id = res.json().get("job_id")
        job_ids[f] = job_id
        print(f"Started {os.path.basename(f)} -> {job_id}")

print("\n=== HEADER CONSTRUCTION AUDIT ===")
sys.path.insert(0, os.path.abspath('.'))
from core.extractors.document_router import route_document

def get_tokens_in_y_range(tokens, y_min, y_max):
    return [t for t in tokens if t.get("yc", (t.get("y0",0)+t.get("y1",0))/2) >= y_min and t.get("yc", (t.get("y0",0)+t.get("y1",0))/2) <= y_max]

for f in files_to_run:
    if not os.path.exists(f): continue
    
    tmp_path = f"tmp_page1_{os.path.basename(f)}"
    try:
        doc = fitz.open(f)
        doc.select([0])
        doc.save(tmp_path)
        doc.close()
        
        print(f"\nRunning OCR on {tmp_path} (Page 1)...")
        full_text, pages, telemetry, page_tokens = route_document(tmp_path)
        
        header_y_min = 9999
        header_y_max = 0
        found = False
        
        for t in page_tokens:
            text = t.get("text", "").upper()
            if "DEBIT" in text or "CREDIT" in text or "BALANCE" in text or "AMOUNT" in text:
                header_y_min = min(header_y_min, t.get("y0", 0) - 10)
                header_y_max = max(header_y_max, t.get("y1", 0) + 10)
                found = True
                
        if found:
            raw_header_tokens = get_tokens_in_y_range(page_tokens, header_y_min, header_y_max)
            raw_header_tokens.sort(key=lambda t: t.get("x0", 0))
            
            print(f"\n[{os.path.basename(f)}] RAW OCR TOKENS IN HEADER ZONE:")
            merged_count = 0
            for t in raw_header_tokens:
                text = t.get('text')
                print(f"  - '{text}'  (x0: {round(t.get('x0',0),1)}, x1: {round(t.get('x1',0),1)})")
                if "DEBIT" in text.upper() and "CREDIT" in text.upper():
                    merged_count += 1
            if merged_count > 0:
                print(f"  -> WARNING: Found {merged_count} token(s) that appear to merge multiple columns!")
        else:
            print(f"Could not locate header zone in {os.path.basename(f)}")
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

print("\n=== WAITING FOR BENCHMARK RESULTS ===")
def parse_float_safe(val):
    if not val: return None
    try:
        cleaned = str(val).replace(',', '').strip()
        if cleaned.endswith(('Cr', 'Dr')):
            cleaned = cleaned[:-2].strip()
        return float(cleaned)
    except: return None

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
        if width > 0: return (overlap / width) * 100
    return 0

results = {}
while len(results) < len(job_ids):
    for f, jid in job_ids.items():
        if f in results: continue
        res = requests.get(f"http://localhost:8000/api/benchmark/status/{jid}").json()
        if res.get("status") in ["completed", "error"]:
            if res.get("results"):
                results[f] = res["results"][0]
            else:
                results[f] = {} # error
            print(f"Finished {os.path.basename(f)}")
    time.sleep(2)

print("\n=== FORENSIC FAILURE BREAKDOWN ===")

for f, data in results.items():
    if not data: continue
    bank = data.get("bank_name", os.path.basename(f))
    transactions = data.get("transactions", [])
    telemetry = data.get("telemetry", {})
    zones = telemetry.get("zones", {})
    
    cz = zones.get("credit_zone")
    bz = zones.get("balance_zone")
    cz_center = cz[0] + (cz[1]-cz[0])/2 if cz else 0
    bz_center = bz[0] + (bz[1]-bz[0])/2 if bz else 0
    
    stats = {
        "rows_failed": 0,
        "missing_balance_zone": 0,
        "zone_overlap": 0,
        "row_merge": 0,
        "ocr_drift": 0,
        "unknown": 0
    }
    
    overlap_pct = zone_overlap(cz, bz)
    
    for i, txn in enumerate(transactions):
        ledger = txn.get("ledger_truth", {})
        if ledger.get("ledger_status") == "PASS":
            continue
            
        stats["rows_failed"] += 1
        
        tokens = txn.get("_source_tokens", [])
        y_max = max((t.get("y1", 0) for t in tokens)) if tokens else 0
        
        next_row_dist = 999
        if i + 1 < len(transactions):
            next_tokens = transactions[i+1].get("_source_tokens", [])
            if next_tokens:
                next_y_min = min((t.get("y0", 0) for t in next_tokens))
                next_row_dist = next_y_min - y_max
                
        row_merge = next_row_dist < 5.0
        
        cred_val = txn.get("raw_extraction", {}).get("parsed_credit")
        bal_val = txn.get("raw_extraction", {}).get("parsed_balance")
        target_val = cred_val if cred_val else bal_val
        
        token_x = 0
        if target_val is not None and tokens:
            for t in tokens:
                v = parse_float_safe(t.get("text"))
                if v is not None and abs(v - target_val) < 0.01:
                    token_x = t.get("x0", 0)
                    break
            if not token_x:
                num_tokens = [t for t in tokens if parse_float_safe(t.get("text")) is not None]
                if num_tokens:
                    token_x = max(num_tokens, key=lambda t: t.get("x0", 0)).get("x0", 0)
                    
        dist_c = distance_to_edge(token_x, cz)
        dist_b = distance_to_edge(token_x, bz)
        
        if not bz:
            stats["missing_balance_zone"] += 1
        elif row_merge:
            stats["row_merge"] += 1
        elif overlap_pct > 15 or abs(dist_c - dist_b) < 15:
            stats["zone_overlap"] += 1
        elif token_x > bz_center + 15 or token_x < cz_center - 15:
            stats["ocr_drift"] += 1
        else:
            stats["unknown"] += 1
            
    total_failed = stats["rows_failed"]
    if total_failed > 0:
        percentages = {
            "MISSING_BALANCE_ZONE": round((stats["missing_balance_zone"] / total_failed) * 100, 1),
            "ROW_GROUPING": round((stats["row_merge"] / total_failed) * 100, 1),
            "ZONE_OVERLAP": round((stats["zone_overlap"] / total_failed) * 100, 1),
            "OCR_DRIFT": round((stats["ocr_drift"] / total_failed) * 100, 1),
            "UNKNOWN": round((stats["unknown"] / total_failed) * 100, 1)
        }
        
        out = {
            "bank": bank,
            "rows_failed": total_failed,
            "failure_breakdown": percentages
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"{bank}: 0 failures")
