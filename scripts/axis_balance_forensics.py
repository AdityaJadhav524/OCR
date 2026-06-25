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
from core.validators.financial_audit import _parse_float
from core.extractors.candidate_generator import generate_balance_candidates
from core.validators.balance_sanity_validator import run_balance_sanity_validator

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def run_forensics():
    pattern = str(TEMP_DIR / "*axis.pdf")
    matches = glob.glob(pattern)
    pdf_path = Path(matches[-1]) if matches else None
    if not pdf_path or not pdf_path.exists():
        print("AXIS PDF not found in temp directory.")
        return

    print(f"Extracting {pdf_path.name}...\n")
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, parser_tel = parse_with_coordinates(
        page_tokens, 
        pdf_name=pdf_path.name, 
        statement_id="audit", 
        job_id="audit", 
        bank="Axis Bank", 
        pdf_type="DIGITAL"
    )

    txns = generate_balance_candidates(txns)
    txns = run_balance_sanity_validator(txns)

    sorted_txns, _ = validate_and_sort_transactions(txns)
    rb_audit = run_running_balance_audit(sorted_txns)
    
    print("\n=== AXIS FORENSICS OVERVIEW ===")
    print(f"Total Transactions: {len(sorted_txns)}")
    print(f"Continuity: {rb_audit['continuity_percentage']}%")
    
    print("\n=== TOP 5 CONTINUITY BREAKS (Watermark Analysis) ===")
    breaks = rb_audit.get("ledger_breaks", [])
    breaks.sort(key=lambda x: abs(x["difference"]), reverse=True)
    
    for b in breaks[:5]:
        row_idx = b['row_index']
        txn = sorted_txns[row_idx]
        
        # Collect all numeric tokens on the same line
        y_center = txn.get("_source_tokens", [])[0]["yc"] if txn.get("_source_tokens") else None
        page = txn.get("page")
        
        candidates = []
        if y_center and page:
            for t in page_tokens:
                if t["page"] == page and abs(t["yc"] - y_center) < 10:
                    try:
                        # Attempt to parse it as a float to see if it's numeric
                        val_str = t["text"].replace(",", "")
                        if val_str.endswith("CR") or val_str.endswith("DR"):
                            val_str = val_str[:-2]
                        val = float(val_str)
                        candidates.append(val)
                    except:
                        pass
                        
        print(json.dumps({
            "row": row_idx,
            "all_numeric_candidates": candidates,
            "chosen_balance": txn.get("balance"),
            "expected_balance": b["expected_balance"],
            "watermark_detected": any(c for c in candidates if c in [178, 56, 169, 248, 100]) or "178" in txn["raw_extraction"].get("ocr_balance_text", ""),
            "raw_balance_text": txn["raw_extraction"].get("ocr_balance_text")
        }, indent=2))

if __name__ == "__main__":
    run_forensics()
