import sys
import os
import json
from pathlib import Path
from dateutil.parser import parse as parse_date

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.ordering.page_sequence_repair import run_page_sequence_repair, score_page_link
from core.validators.running_balance_audit import run_running_balance_audit
from core.extractors.candidate_generator import generate_balance_candidates
from core.validators.balance_sanity_validator import run_balance_sanity_validator
from core.validators.transaction_order_validator import validate_and_sort_transactions
from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
import glob

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def find_latest_temp_file(corpus_file: str):
    pattern = str(TEMP_DIR / f"*{corpus_file}")
    matches = glob.glob(pattern)
    if not matches:
        exact = TEMP_DIR / corpus_file
        if exact.exists(): return exact
        return None
    return Path(sorted(matches, key=os.path.getmtime)[-1])

def test_repair():
    pdf_path = find_latest_temp_file("HDFC_SAVINGS_SCANNED.pdf")
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, _ = parse_with_coordinates(page_tokens, pdf_name="HDFC", bank="HDFC BANK", pdf_type="SCANNED")
    
    txns = generate_balance_candidates(txns)
    txns = run_balance_sanity_validator(txns)
    sorted_txns, _ = validate_and_sort_transactions(txns)
    
    repaired_txns = run_page_sequence_repair(sorted_txns)
    
    rb_audit = run_running_balance_audit(repaired_txns)
    print(f"Repaired Continuity: {rb_audit['continuity_percentage']}%")

if __name__ == "__main__":
    test_repair()
