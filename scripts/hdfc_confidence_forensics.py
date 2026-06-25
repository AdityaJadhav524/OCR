import sys
import glob
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.transaction_order_validator import validate_and_sort_transactions
from core.validators.ledger_direction_validator import run_ledger_direction_validator
from core.validators.financial_audit import _parse_float
from core.validators.running_balance_audit import run_running_balance_audit
from core.validators.financial_reconciliation import run_financial_reconciliation

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def run_forensics():
    pattern = str(TEMP_DIR / "*HDFC_SAVINGS_SCANNED.pdf")
    matches = glob.glob(pattern)
    pdf_path = Path(matches[-1]) if matches else None
    if not pdf_path or not pdf_path.exists():
        print("HDFC PDF not found in temp directory.")
        return

    print(f"Extracting {pdf_path.name}...\n")
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, parser_tel = parse_with_coordinates(
        page_tokens, 
        pdf_name=pdf_path.name, 
        statement_id="audit", 
        job_id="audit", 
        bank="HDFC Bank", 
        pdf_type="SCANNED"
    )

    # Apply production pipeline
    sorted_txns, _ = validate_and_sort_transactions(txns)
    dir_audit = run_ledger_direction_validator(sorted_txns)
    for t in sorted_txns:
        if t.get("direction_corrected"):
            t["debit"], t["credit"] = t.get("credit"), t.get("debit")
            
    rb_audit = run_running_balance_audit(sorted_txns)
    recon_audit = run_financial_reconciliation(sorted_txns)
    
    print("\n=== HDFC FORENSICS OVERVIEW ===")
    print(f"Total Transactions: {len(sorted_txns)}")
    print(f"Continuity: {rb_audit['continuity_percentage']}%")
    print(f"Reconciliation: {recon_audit['reconciliation_percentage']}%")
    
    print("\n=== RECONCILIATION DETAILS ===")
    print(json.dumps(recon_audit, indent=2))
    
    print("\n=== TOP 5 CONTINUITY BREAKS ===")
    breaks = rb_audit.get("ledger_breaks", [])
    breaks.sort(key=lambda x: abs(x["difference"]), reverse=True)
    for b in breaks[:5]:
        print(f"Row {b['row_index']}: Prev Balance {b['prev_balance']} | Amt +{b['credit']}/-{b['debit']} -> Expected {b['expected_balance']}, Got {b['current_balance']} (Diff: {b['difference']})")
        
    print("\n=== FIRST TRANSACTION (For Anchor Check) ===")
    if sorted_txns: print(json.dumps(sorted_txns[0], indent=2))

    print("\n=== LAST TRANSACTION (For Anchor Check) ===")
    if sorted_txns: print(json.dumps(sorted_txns[-1], indent=2))

if __name__ == "__main__":
    run_forensics()
