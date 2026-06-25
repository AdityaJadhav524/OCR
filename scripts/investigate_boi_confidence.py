import sys
import os
import json
from pathlib import Path
import glob

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.statement_confidence_engine import generate_statement_confidence

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def run_investigation():
    pattern = str(TEMP_DIR / "*BOI_SAVINGS_SCANNED.pdf")
    matches = glob.glob(pattern)
    pdf_path = None
    if matches:
        pdf_path = Path(matches[-1])
            
    if not pdf_path or not pdf_path.exists():
        print("Could not find BOI_SAVINGS_SCANNED.pdf in temp dir")
        return

    print(f"Investigating {pdf_path.name}...")
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, parser_tel = parse_with_coordinates(
        page_tokens,
        pdf_name=pdf_path.name,
        statement_id="audit",
        job_id="audit",
        bank="Bank of India",
        pdf_type="SCANNED"
    )
    
    # Load truth
    truth_file = ROOT / "tests" / "truth_corpus" / "boi_scanned.json"
    expected = 0
    if truth_file.exists():
        truth = json.loads(truth_file.read_text(encoding="utf-8"))
        expected = len(truth.get("transactions", []))
        
    conf = generate_statement_confidence(txns, expected_transaction_count=expected)
    
    print("\n--- BOI CONFIDENCE SUMMARY ---")
    print(f"Confidence:     {conf['confidence']} ({conf['status']})")
    print(f"Continuity:     {conf['continuity']}%")
    print(f"Reconciliation: {conf['reconciliation']}%")
    print(f"Direction:      {conf['direction']}% (Healed: {conf['details'].get('corrected_directions', 0)})")
    print(f"Completeness:   {conf['transaction_completeness']}%")
    
    print("\n--- TOP 20 LEDGER BREAKS ---")
    breaks = conf["details"].get("ledger_breaks", [])
    for idx, b in enumerate(breaks[:20]):
        print(f"Row {b['row_index']}: Prev Balance: {b['prev_balance']}, "
              f"Credit: {b['credit']}, Debit: {b['debit']} -> "
              f"Expected: {b['expected_balance']}, Got: {b['current_balance']}, Diff: {b['difference']}")

if __name__ == "__main__":
    run_investigation()
