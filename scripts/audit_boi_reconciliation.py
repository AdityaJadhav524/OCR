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
from core.validators.ledger_direction_validator import run_ledger_direction_validator
from core.validators.financial_audit import _parse_float

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def run_audit():
    pattern = str(TEMP_DIR / "*BOI_SAVINGS_SCANNED.pdf")
    matches = glob.glob(pattern)
    pdf_path = Path(matches[-1]) if matches else None
    if not pdf_path or not pdf_path.exists(): 
        print("PDF not found")
        return

    print(f"Extracting {pdf_path.name}...\n")
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, parser_tel = parse_with_coordinates(page_tokens, pdf_name=pdf_path.name, statement_id="audit", job_id="audit", bank="Bank of India", pdf_type="SCANNED")
    
    # Run the exact production pipeline (Heal Before Audit)
    sorted_test, _ = validate_and_sort_transactions(txns)
    run_ledger_direction_validator(sorted_test) 
    for t in sorted_test:
        if t.get("direction_corrected"):
            t["debit"], t["credit"] = t.get("credit"), t.get("debit")
            
    # Audit Reconciliation Mathematics
    if not sorted_test:
        print("No transactions found.")
        return
        
    first_txn = sorted_test[0]
    last_txn = sorted_test[-1]
    
    first_balance = _parse_float(first_txn.get("balance"))
    first_credit = _parse_float(first_txn.get("credit")) or 0.0
    first_debit = _parse_float(first_txn.get("debit")) or 0.0
    
    closing_balance = _parse_float(last_txn.get("balance"))
    
    derived_opening_balance = None
    if first_balance is not None:
        derived_opening_balance = first_balance - first_credit + first_debit
        
    total_credits = sum(_parse_float(t.get("credit")) or 0.0 for t in sorted_test)
    total_debits = sum(_parse_float(t.get("debit")) or 0.0 for t in sorted_test)
    
    expected_closing = None
    difference = None
    if derived_opening_balance is not None:
        expected_closing = derived_opening_balance + total_credits - total_debits
        if closing_balance is not None:
            difference = expected_closing - closing_balance

    print("=== RECONCILIATION ROOT CAUSE AUDIT ===")
    print(f"Derived Opening Balance:  {derived_opening_balance}")
    print(f"Total Credits Extracted:  +{total_credits}")
    print(f"Total Debits Extracted:   -{total_debits}")
    print(f"Expected Closing Balance: {expected_closing}")
    print(f"Actual Closing Balance:   {closing_balance}")
    print(f"Mathematical Difference:  {difference}")
    
    print("\n=== FIRST TRANSACTION ===")
    print(json.dumps(first_txn, indent=2))
    
    print("\n=== LAST TRANSACTION ===")
    print(json.dumps(last_txn, indent=2))
    
    print("\n=== TOP 5 BALANCE JUMPS (Continuity Breaks) ===")
    from core.validators.running_balance_audit import run_running_balance_audit
    rb_test = run_running_balance_audit(sorted_test)
    breaks = rb_test.get("ledger_breaks", [])
    
    # Sort by absolute difference
    breaks.sort(key=lambda x: abs(x["difference"]), reverse=True)
    for b in breaks[:5]:
        print(f"Row {b['row_index']}: Prev Balance {b['prev_balance']} | Amt +{b['credit']}/-{b['debit']} -> Expected {b['expected_balance']}, Got {b['current_balance']} (Diff: {b['difference']})")

if __name__ == "__main__":
    run_audit()
