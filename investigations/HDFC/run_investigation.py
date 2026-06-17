import os
import sys
import json

# Add root to sys.path
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _WORKSPACE_ROOT)
if os.path.join(_WORKSPACE_ROOT, "core") not in sys.path:
    sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "core"))

from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth

PDF_PATH = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"
OUT_DIR = r"Z:\CA\investigations\HDFC"

print("1. Running OCR...")
full_text, pages_text, telemetry, tokens = extract_via_subprocess(PDF_PATH)

print(f"   OCR found {len(tokens)} tokens.")

print("2. Running V2 Parser...")
txns, tel = parse_with_coordinates(tokens)

print("3. Running Ledger Audit...")
txns = annotate_ledger_truth(txns)

print("4. Saving Investigation Files...")

def save(filename, data):
    with open(os.path.join(OUT_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

save("raw_output.json", txns)
save("telemetry.json", tel)
save("rejects.json", tel.get("reject_log", []))
save("contamination.json", tel.get("contaminated_rows", 0))

# Create Anomaly Report
anomalies = [t for t in txns if t.get("suspicious_fields")]
with open(os.path.join(OUT_DIR, "anomaly_report.md"), "w", encoding="utf-8") as f:
    f.write("# HDFC Anomaly Report\n\n")
    f.write(f"Total Transactions: {len(txns)}\n")
    f.write(f"Total Rejects: {len(tel.get('reject_log', []))}\n")
    f.write(f"Total Anomalies: {len(anomalies)}\n\n")
    for i, t in enumerate(anomalies):
        f.write(f"### Txn {i+1} - {t['date']}\n")
        f.write(f"Narration: {t.get('narration', '')}\n")
        f.write(f"Debit: {t.get('debit')} | Credit: {t.get('credit')} | Balance: {t.get('balance')}\n")
        f.write("Suspicious Fields:\n")
        for k, v in t.get("suspicious_fields", {}).items():
            f.write(f"- {k}: {v}\n")
        f.write("\n")

print("Done. Files saved to Z:\CA\investigations\HDFC")
