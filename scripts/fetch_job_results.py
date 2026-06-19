import requests
import json

job_ids = [
    "JOB_20260618_164443_C915",
    "JOB_20260618_164448_D30D",
    "JOB_20260618_164650_23BE",
    "JOB_20260618_164851_1E4C"
]

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

overall_failures = {
    "ZONE_CREATION": 0,
    "ROW_GROUPING": 0,
    "OCR_DRIFT": 0,
    "UNKNOWN": 0
}

bank_summaries = []

for job_id in job_ids:
    url = f"http://localhost:8000/api/benchmark/status/{job_id}"
    res = requests.get(url).json()
    if not res.get("results"):
        continue
        
    data = res["results"][0]
    bank = data.get("bank_name", "UNKNOWN")
    transactions = data.get("transactions", [])
    telemetry = data.get("telemetry", {})
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
        target_val = cred_val if cred_val else bal_val
        
        token_x = 0
        token_text = ""
        
        if target_val is not None:
            # We will find the token whose center is closest to where we expect, OR whose value matches
            for t in tokens:
                v = parse_float_safe(t.get("text"))
                if v is not None and abs(v - target_val) < 0.01:
                    token_x = t.get("x0", 0)
                    token_text = t.get("text", "")
                    break
        
        if not token_text:
            # Fallback: maybe paddle split the token? Let's just find the token that's physically rightmost
            # since it's either credit or balance.
            num_tokens = [t for t in tokens if parse_float_safe(t.get("text")) is not None]
            if num_tokens:
                rightmost = max(num_tokens, key=lambda t: t.get("x0", 0))
                token_x = rightmost.get("x0", 0)
                token_text = rightmost.get("text", "")
            else:
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
            "token_x": round(token_x, 1),
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
                
    if bank_stats["zone_overlap_percent"] > 15:
        bank_stats["suspected_root_cause"] = "ZONE_CREATION"
    elif any(r["suspected_row_merge"] for r in failed_rows):
        bank_stats["suspected_root_cause"] = "ROW_GROUPING"
    elif any(r["token_distance_from_balance_center"] > 50 for r in failed_rows):
        bank_stats["suspected_root_cause"] = "OCR_DRIFT"
        
    bank_summaries.append(bank_stats)
    
    print(f"\n==============================================")
    print(f"BANK: {bank}")
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
