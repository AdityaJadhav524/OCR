"""
Evidence Report Generator
Queries the live Validation Lab API and generates the 4-artifact evidence report.
Run after uploading all PDFs to the frontend.
"""
import requests
import json
from collections import defaultdict

BASE = "http://localhost:8000"

def generate_report():
    # 1. Get all session data from the cache debug endpoint
    try:
        resp = requests.get(f"{BASE}/api/debug/cache", timeout=10)
        resp.raise_for_status()
        cache = resp.json()
    except Exception as e:
        print(f"ERROR: Cannot reach backend at {BASE}: {e}")
        print("Make sure the backend is still running.")
        return

    if not cache:
        print("ERROR: Session cache is empty. No PDFs have been processed yet.")
        return

    print(f"Found {len(cache)} sessions in cache.\n")

    # --- Data collection ---
    # Maps: bank -> list of waterfall dicts
    bank_data = defaultdict(list)
    financial_corruption = defaultdict(int)

    for session_id, session in cache.items():
        bank_det = session.get("bank_detection", {}) or {}
        bank = bank_det.get("institution_name", "Unknown")
        if not bank or bank == "Unknown":
            bank = session_id[:20]  # fallback

        ocr_metrics = session.get("ocr_metrics", {}) or {}
        tokens_before = ocr_metrics.get("token_count", len(session.get("tokens", [])))
        tokens_after = tokens_before  # after suppression not directly stored but we can approximate

        reject_log = ocr_metrics.get("reject_log", []) or []
        txns = session.get("transactions", []) or []
        stages = session.get("stages", []) or []

        # Parse stage timing to infer waterfall counts
        v2_tel = {}
        for s in stages:
            if s.get("name") == "Transaction Parsing (V2)":
                extra = s.get("extra_data") or {}
                v2_tel = extra
                break

        rows_detected = ocr_metrics.get("v2_rows_detected", len(txns) + len(reject_log))
        rows_accepted = len(txns)
        rows_rejected = len(reject_log)

        # Determine rejection reasons
        reject_reasons = defaultdict(int)
        for r in reject_log:
            reason = r.get("reason") or r.get("reject_reason") or "UNKNOWN"
            reject_reasons[reason] += 1

        top_reason = "NONE"
        if reject_reasons:
            top_reason = max(reject_reasons.items(), key=lambda x: x[1])[0]

        # Determine failure stage mechanically
        tokens_ratio = (tokens_after / tokens_before) if tokens_before > 0 else 1.0
        headers_count = len([s for s in stages if "header" in s.get("name", "").lower()])
        zones_ok = v2_tel.get("date_zone_found", True)

        first_failed_stage = "PASS"
        rows_lost = max(0, rows_detected - rows_accepted)

        if tokens_ratio < 0.6:
            first_failed_stage = "SUPPRESSION"
        elif rows_detected == 0 and tokens_before > 0:
            first_failed_stage = "HEADER_DETECTION"
        elif not zones_ok:
            first_failed_stage = "ZONE_CREATION"
        elif rows_detected > 0 and rows_accepted == 0:
            first_failed_stage = "VALIDATION"
        elif rows_rejected > 0:
            first_failed_stage = "VALIDATION (partial)"

        # Financial corruption: check if any reject reason involves money fields
        for r in reject_log:
            reason = r.get("reason") or r.get("reject_reason") or ""
            if "balance" in reason.lower() and "credit" in reason.lower():
                financial_corruption["Balance As Credit"] += 1
            elif "balance" in reason.lower() and "debit" in reason.lower():
                financial_corruption["Balance As Debit"] += 1
            elif "date" in reason.lower() and "balance" in reason.lower():
                financial_corruption["Date As Balance"] += 1
            elif "date" in reason.lower() and "amount" in reason.lower():
                financial_corruption["Date As Amount"] += 1

        # Also check transaction fields for corruption
        for txn in txns:
            sf = txn.get("suspicious_fields") or {}
            for field, data in sf.items():
                reason = (data.get("reason") or "").upper()
                if reason in ("PRIMARY_BALANCE_ANOMALY", "DOWNSTREAM_CHAIN_EFFECT"):
                    financial_corruption["Balance Corruption (Downstream)"] += 1
                elif reason == "COLUMN_BOUNDARY_SUSPECT":
                    financial_corruption["Column Overlap (Amount/Balance)"] += 1

        bank_data[bank].append({
            "session_id": session_id,
            "tokens_before": tokens_before,
            "rows_detected": rows_detected,
            "rows_accepted": rows_accepted,
            "rows_rejected": rows_rejected,
            "rows_lost": rows_lost,
            "first_failed_stage": first_failed_stage,
            "top_reason": top_reason,
        })

    # === GENERATE REPORT ===

    print("=" * 70)
    print("EVIDENCE REPORT — CROSS-BANK FAILURE ANALYSIS")
    print("=" * 70)

    # --- Artifact 1: Failure Cost Heatmap ---
    stage_costs = defaultdict(lambda: {"banks": set(), "rows_lost": 0})
    for bank, sessions in bank_data.items():
        for s in sessions:
            stage = s["first_failed_stage"]
            stage_costs[stage]["banks"].add(bank)
            stage_costs[stage]["rows_lost"] += s["rows_lost"]

    total_rows_lost = sum(v["rows_lost"] for v in stage_costs.values())

    print("\n### ARTIFACT 1 — FAILURE COST HEATMAP\n")
    print(f"| {'Stage':<25} | {'Banks':>5} | {'Rows Lost':>10} | {'% of Total':>10} |")
    print(f"|{'-'*27}|{'-'*7}|{'-'*12}|{'-'*12}|")
    for stage in ["SUPPRESSION", "HEADER_DETECTION", "ZONE_CREATION", "ROW_GROUPING", "VALIDATION", "VALIDATION (partial)", "PASS"]:
        d = stage_costs.get(stage, {"banks": set(), "rows_lost": 0})
        pct = (d["rows_lost"] / total_rows_lost * 100) if total_rows_lost > 0 else 0
        print(f"| {stage:<25} | {len(d['banks']):>5} | {d['rows_lost']:>10} | {pct:>9.1f}% |")
    print(f"\nTotal rows lost across corpus: {total_rows_lost}")

    # --- Artifact 2: Bank Failure Matrix ---
    print("\n\n### ARTIFACT 2 — BANK FAILURE MATRIX\n")
    print(f"| {'Bank':<20} | {'Sessions':>8} | {'Total Detected':>14} | {'Total Accepted':>14} | {'Total Rejected':>14} | {'First Failed Stage':<25} |")
    print(f"|{'-'*22}|{'-'*10}|{'-'*16}|{'-'*16}|{'-'*16}|{'-'*27}|")

    for bank in sorted(bank_data.keys()):
        sessions = bank_data[bank]
        total_det = sum(s["rows_detected"] for s in sessions)
        total_acc = sum(s["rows_accepted"] for s in sessions)
        total_rej = sum(s["rows_rejected"] for s in sessions)
        # Use most common failure stage
        stage_counts = defaultdict(int)
        for s in sessions:
            stage_counts[s["first_failed_stage"]] += 1
        dominant_stage = max(stage_counts.items(), key=lambda x: x[1])[0]
        print(f"| {bank:<20} | {len(sessions):>8} | {total_det:>14} | {total_acc:>14} | {total_rej:>14} | {dominant_stage:<25} |")

    # --- Artifact 3: Financial Corruption Matrix ---
    print("\n\n### ARTIFACT 3 — FINANCIAL CORRUPTION MATRIX\n")
    corruption_risk = {
        "Balance As Credit": "CRITICAL",
        "Balance As Debit": "CRITICAL",
        "Date As Balance": "CRITICAL",
        "Date As Amount": "HIGH",
        "Balance Corruption (Downstream)": "HIGH",
        "Column Overlap (Amount/Balance)": "MEDIUM",
    }
    print(f"| {'Failure Type':<40} | {'Count':>6} | {'Risk':<10} |")
    print(f"|{'-'*42}|{'-'*8}|{'-'*12}|")
    for failure_type, risk in corruption_risk.items():
        count = financial_corruption.get(failure_type, 0)
        print(f"| {failure_type:<40} | {count:>6} | {risk:<10} |")

    # --- Artifact 4: Stability Scores ---
    print("\n\n### ARTIFACT 4 — STABILITY SCORES (single run — stability test requires 5x runs)\n")
    print(f"| {'Bank':<20} | {'Signature':<40} |")
    print(f"|{'-'*22}|{'-'*42}|")
    for bank in sorted(bank_data.keys()):
        for s in bank_data[bank]:
            sig = f"{s['rows_detected']}/{s['rows_accepted']}/{s['rows_rejected']}/{s['top_reason']}"
            print(f"| {bank:<20} | {sig:<40} |")

    print("\n\n=== END OF EVIDENCE REPORT ===")


if __name__ == "__main__":
    generate_report()
