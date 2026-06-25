import sys
import os
import json
import glob
import copy
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.transaction_order_validator import validate_and_sort_transactions
from core.validators.running_balance_audit import run_running_balance_audit
from core.validators.financial_reconciliation import run_financial_reconciliation
from core.validators.ledger_direction_validator import run_ledger_direction_validator

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def run_experiment():
    pattern = str(TEMP_DIR / "*BOI_SAVINGS_SCANNED.pdf")
    matches = glob.glob(pattern)
    pdf_path = Path(matches[-1]) if matches else None
    if not pdf_path or not pdf_path.exists(): return

    print(f"Extracting {pdf_path.name}...")
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, parser_tel = parse_with_coordinates(page_tokens, pdf_name=pdf_path.name, statement_id="audit", job_id="audit", bank="Bank of India", pdf_type="SCANNED")
    
    txns_test = copy.deepcopy(txns)
    sorted_test, _ = validate_and_sort_transactions(txns_test)
    dir_test = run_ledger_direction_validator(sorted_test) 
    
    for t in sorted_test:
        if t.get("direction_corrected"):
            t["debit"], t["credit"] = t.get("credit"), t.get("debit")
            
    rb_test = run_running_balance_audit(sorted_test)
    recon_test = run_financial_reconciliation(sorted_test)
    
    print("\n=== PIPELINE 2: HEAL BEFORE AUDIT + APPLY ===")
    print(f"Continuity: {rb_test['continuity_percentage']}%")
    print(f"Reconciliation: {recon_test['reconciliation_percentage']}%")
    print(f"Difference: {recon_test['difference']}")
    
    print("\n--- REMAINING LEDGER BREAKS (The 5%) ---")
    breaks = rb_test.get("ledger_breaks", [])
    for idx, b in enumerate(breaks[:10]):
        print(f"Row {b['row_index']}: Prev Balance: {b['prev_balance']}, "
              f"Credit: {b['credit']}, Debit: {b['debit']} -> "
              f"Expected: {b['expected_balance']}, Got: {b['current_balance']}, Diff: {b['difference']}")

if __name__ == "__main__":
    run_experiment()
