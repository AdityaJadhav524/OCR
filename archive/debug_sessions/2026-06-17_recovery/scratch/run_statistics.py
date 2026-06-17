"""
scratch/run_statistics.py
─────────────────────────
Bank Validation Matrix — Parser KPI Dashboard

Runs the full pipeline (OCR Signature + Ledger Suspicion + Dipole Resolution)
over every available test PDF and produces:

  1. Per-bank JSON record
  2. Human-readable anomaly causal chain (primary → affected downstream rows)
  3. Cross-bank KPI table
"""
import os
import glob
import json
from collections import defaultdict
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth


def process_bank(bank_name: str, pdf_path: str) -> dict | None:
    try:
        _, _, _, page_tokens = extract_via_subprocess(pdf_path)
        txns, tel = parse_with_coordinates(page_tokens)
        final_txns = annotate_ledger_truth(txns)
    except Exception as e:
        print(f"  FAILED: {e}")
        return None

    # Aggregate counts
    primary_anomalies = []
    downstream_effects = []
    ocr_format_counts = defaultdict(int)
    conservation_fail = tel.get("rejected_rows", len(tel.get("reject_log", [])))

    for txn in final_txns:
        for field, sig in txn.get("suspicious_fields", {}).items():
            reason = sig.get("reason", "")
            if reason in ("POWER_OF_TEN_DRIFT", "SMALL_DIGIT_SUBSTITUTION", "PRIMARY_BALANCE_ANOMALY"):
                primary_anomalies.append({
                    "anomaly_id": sig.get("anomaly_id", "—"),
                    "date": txn.get("date"),
                    "difference": sig.get("diff"),
                    "detector": reason,
                    "affected_rows": sig.get("affected_rows", [])
                })
            elif reason == "DOWNSTREAM_CHAIN_EFFECT":
                downstream_effects.append({
                    "date": txn.get("date"),
                    "root_row": sig.get("root_row"),
                    "diff": sig.get("diff")
                })
            elif reason in ("MULTIPLE_DOTS", "PUNCTUATION_CORRUPTION",
                            "DATE_NARRATION_MERGE", "COLUMN_BOUNDARY_SUSPECT",
                            "NUMERIC_SHAPE_ANOMALY"):
                ocr_format_counts[reason] += 1

    return {
        "bank": bank_name,
        "transactions": len(final_txns),
        "primary_anomalies": len(primary_anomalies),
        "downstream_effects": len(downstream_effects),
        "ocr_format_issues": sum(ocr_format_counts.values()),
        "multiple_dots": ocr_format_counts.get("MULTIPLE_DOTS", 0),
        "punctuation_corruption": ocr_format_counts.get("PUNCTUATION_CORRUPTION", 0),
        "date_merge": ocr_format_counts.get("DATE_NARRATION_MERGE", 0),
        "conservation_fail": conservation_fail,
        "_primary_detail": primary_anomalies,
        "_downstream_detail": downstream_effects,
    }


def print_causal_chain(record: dict):
    if not record["_primary_detail"] and not record["_downstream_detail"]:
        print("  No anomalies detected.")
        return
    for p in record["_primary_detail"]:
        print(f"  [{p['anomaly_id']}] {p['date']}  diff={p['difference']}  ({p['detector']})")
        for affected in p.get("affected_rows", []):
            print(f"        +-- DOWNSTREAM: {affected}")


def main():
    tests = [
        ("YES", r"Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf"),
    ]
    for bank_dir in sorted(glob.glob(r"Z:\CA\tests\*")):
        if os.path.isdir(bank_dir) and os.path.basename(bank_dir) not in (
            "__pycache__", "artifacts", "debug", "unit", "regression", "integration"
        ):
            pdfs = glob.glob(os.path.join(bank_dir, "*.pdf"))
            if pdfs:
                tests.append((os.path.basename(bank_dir), pdfs[0]))

    print("=" * 70)
    print(" BANK VALIDATION MATRIX — Parser KPI Dashboard")
    print("=" * 70)

    records = []
    for bank_name, pdf_path in tests:
        if not os.path.exists(pdf_path):
            print(f"\n[{bank_name}] SKIPPED — PDF not found: {pdf_path}")
            continue
        print(f"\n[{bank_name}] {os.path.basename(pdf_path)}")
        rec = process_bank(bank_name, pdf_path)
        if rec:
            records.append(rec)
            print_causal_chain(rec)

    print()
    print("=" * 70)
    print(" CROSS-BANK KPI TABLE")
    print("=" * 70)
    h = f"| {'Bank':<6} | {'Txns':>4} | {'Primary':>7} | {'Downstream':>10} | {'OCR Format':>10} | {'Cons.Fail':>9} |"
    print(h)
    print(f"| {'-'*6} | {'-'*4} | {'-'*7} | {'-'*10} | {'-'*10} | {'-'*9} |")
    for r in records:
        print(
            f"| {r['bank']:<6} | {r['transactions']:>4} | "
            f"{r['primary_anomalies']:>7} | {r['downstream_effects']:>10} | "
            f"{r['ocr_format_issues']:>10} | {r['conservation_fail']:>9} |"
        )

    print()
    print("Full JSON records:")
    for r in records:
        out = {k: v for k, v in r.items() if not k.startswith("_")}
        out["primary_anomaly_detail"] = r["_primary_detail"]
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
