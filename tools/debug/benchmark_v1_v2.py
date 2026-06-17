"""
Phase A Benchmark: V1 vs V2 Disagreement Report
Uses pre-extracted OCR text from dumps/_ocr.txt files.
Runs V1 (text parser) on the text and reports results.
V2 needs coordinate tokens which are not in dumps, so we measure V1 only here
and report the zones V2 detected during live sessions from the api debug artifacts.

For full V1 vs V2 comparison: upload a fresh PDF via the UI and Export JSON.
The real_benchmark block in api.py now correctly captures diff_rows.
"""
import sys, os, json
sys.path.insert(0, "z:/CA")

DUMPS_DIR = "z:/CA/validation_lab/backend/dumps"
DEBUG_ARTIFACT = "z:/CA/validation_lab/backend/dumps/debug_artifact.json"

from core.parsers.deterministic_parser import parse_deterministic_transactions
from core.validators.financial_audit import run_financial_audit


def run_v1_on_dump(ocr_path):
    text = open(ocr_path, encoding="utf-8", errors="ignore").read().strip()
    if not text or len(text) < 100:
        return None
    try:
        txns, tel = parse_deterministic_transactions(text)
        audit = run_financial_audit(txns)
        return {
            "file": os.path.basename(ocr_path),
            "v1_count": len(txns),
            "v1_audit_pass": audit.get("passed", False),
            "v1_issues": audit.get("issues", []),
            "missing_ratio": tel.get("missing_ratio", 0),
            "text_len": len(text)
        }
    except Exception as e:
        return {"file": os.path.basename(ocr_path), "v1_count": 0, "error": str(e)}


def main():
    dumps = sorted(f for f in os.listdir(DUMPS_DIR) if f.endswith("_ocr.txt"))
    print(f"\n{'='*70}")
    print(f"  V1 Baseline Report — {len(dumps)} OCR dump files")
    print(f"{'='*70}\n")

    results = []
    for dump in dumps:
        r = run_v1_on_dump(os.path.join(DUMPS_DIR, dump))
        if r is None:
            continue
        results.append(r)
        audit_flag = "PASS" if r.get("v1_audit_pass") else "FAIL"
        issues = len(r.get("v1_issues", []))
        print(f"  {audit_flag}  txns={r['v1_count']:>3}  issues={issues}  {r['file']}")

    passed = [r for r in results if r.get("v1_audit_pass")]
    failed = [r for r in results if not r.get("v1_audit_pass") and r.get("v1_count", 0) > 0]
    empty  = [r for r in results if r.get("v1_count", 0) == 0]

    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Total dump files : {len(results)}")
    print(f"  Audit PASS       : {len(passed)}")
    print(f"  Audit FAIL       : {len(failed)}")
    print(f"  Zero txns        : {len(empty)}")

    # Load debug_artifact for V2 benchmark data if present
    if os.path.exists(DEBUG_ARTIFACT):
        try:
            data = json.load(open(DEBUG_ARTIFACT, encoding="utf-8"))
            if isinstance(data, list):
                v2_entries = [d for d in data if isinstance(d, dict) and "real_benchmark" in d]
            elif isinstance(data, dict) and "real_benchmark" in data:
                v2_entries = [data]
            else:
                v2_entries = []

            if v2_entries:
                print(f"\n{'='*70}")
                print(f"  V2 LIVE BENCHMARK DATA (from debug_artifact.json)")
                print(f"{'='*70}")
                for entry in v2_entries:
                    rb = entry["real_benchmark"]
                    print(f"  V1={rb.get('v1_count','?')}  V2={rb.get('v2_count','?')}  diff={rb.get('diff_rows','?')}  "
                          f"V1_score={rb.get('v1_score','?')}  V2_score={rb.get('v2_score','?')}  "
                          f"zones={rb.get('v2_telemetry', {}).get('zones_detected', [])}")
        except Exception as e:
            print(f"  Could not read debug_artifact: {e}")

    print(f"\n  NOTE: Upload a statement via the UI and Export JSON to get live V1 vs V2 diff_rows.")
    print(f"  The real_benchmark field in the session now correctly tracks both parsers.\n")


if __name__ == "__main__":
    main()
