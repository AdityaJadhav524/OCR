import sys
import glob
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.transaction_order_validator import validate_and_sort_transactions
from core.validators.running_balance_audit import run_running_balance_audit
from core.validators.ledger_direction_validator import run_ledger_direction_validator

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

    sorted_txns, _ = validate_and_sort_transactions(txns)
    
    # Heal
    run_ledger_direction_validator(sorted_txns)
    for t in sorted_txns:
        if t.get("direction_corrected"):
            t["debit"], t["credit"] = t.get("credit"), t.get("debit")
            
    rb_audit = run_running_balance_audit(sorted_txns)
    
    print("\n=== HDFC ORDERING FORENSICS ===")
    
    breaks = rb_audit.get("ledger_breaks", [])
    breaks.sort(key=lambda x: abs(x["difference"]), reverse=True)
    
    for b in breaks[:3]:
        row_idx = b['row_index']
        print(f"\n--- BREAK AROUND ROW {row_idx} ---")
        print(f"Break details: Prev {b['prev_balance']} | Amt +{b['credit']}/-{b['debit']} -> Expected {b['expected_balance']}, Got {b['current_balance']} (Diff: {b['difference']})")
        
        start_idx = max(0, row_idx - 10)
        end_idx = min(len(sorted_txns), row_idx + 10)
        
        for i in range(start_idx, end_idx):
            txn = sorted_txns[i]
            
            # Find the top y coordinate of the source box
            y_coord = None
            if txn.get("_source_bbox"):
                y_coord = round(txn["_source_bbox"][1], 1)
            elif txn.get("_source_tokens"):
                y_coord = round(min(t["y0"] for t in txn["_source_tokens"]), 1)
                
            mark = ">>" if i == row_idx else "  "
            
            out = {
                "row": i,
                "date": txn.get("date"),
                "page": txn.get("page"),
                "y": y_coord,
                "balance": txn.get("balance"),
                "debit": txn.get("debit"),
                "credit": txn.get("credit")
            }
            print(f"{mark} {json.dumps(out)}")

if __name__ == "__main__":
    run_forensics()
