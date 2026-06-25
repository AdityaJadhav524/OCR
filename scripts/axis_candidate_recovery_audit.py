import sys
import os
import json
import glob
from pathlib import Path
import copy

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.statement_confidence_engine import validate_and_sort_transactions
from core.validators.running_balance_audit import run_running_balance_audit
from core.extractors.candidate_generator import generate_balance_candidates
from core.validators.financial_audit import _parse_float

CORPUS_DIR  = ROOT / "tests" / "truth_corpus"
TEMP_DIR    = ROOT / "validation_lab" / "backend" / "temp"

def find_latest_temp_file(corpus_file: str):
    pattern = str(TEMP_DIR / f"*{corpus_file}")
    matches = glob.glob(pattern)
    if not matches:
        exact = TEMP_DIR / corpus_file
        if exact.exists(): return exact
        return None
    return Path(sorted(matches, key=os.path.getmtime)[-1])

def run_axis_candidate_recovery_audit():
    pdf_name = "axis.pdf"
    pdf_path = find_latest_temp_file(pdf_name)
    if not pdf_path:
        print(f"Error: {pdf_name} not found.")
        return
        
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, _ = parse_with_coordinates(
        page_tokens,
        pdf_name=pdf_name,
        statement_id="audit",
        job_id="audit",
        bank="AXIS BANK",
        pdf_type="DIGITAL"
    )
    
    # Generate all possible candidates for all transactions
    txns = generate_balance_candidates(txns)
    
    # Sort them
    sorted_txns, _ = validate_and_sort_transactions(txns)
    
    # Run a baseline continuity audit using the primary (default) balance
    baseline_audit = run_running_balance_audit(sorted_txns)
    
    total_breaks = len(baseline_audit["ledger_breaks"])
    fixable_breaks = 0
    
    results = []
    
    for brk in baseline_audit["ledger_breaks"]:
        idx = brk["row_index"]
        txn = sorted_txns[idx]
        
        # The expected balance for this row, given the previous row's balance + credits - debits
        expected_balance = brk["expected_balance"]
        
        # See if any candidate matches the expected balance
        cands = txn.get("balance_candidates", [])
        
        fixed = False
        matching_cand = None
        
        for c in cands:
            val = c.get("value")
            if abs(val - expected_balance) <= 1.0:
                fixed = True
                matching_cand = val
                break
                
        if fixed:
            fixable_breaks += 1
            
        # Log this break
        res = {
            "row": idx,
            "selected_balance": txn.get("balance"),
            "expected_balance": expected_balance,
            "candidates": [c.get("value") for c in cands],
            "would_continuity_be_fixed": fixed,
            "matching_candidate": matching_cand
        }
        results.append(res)
        
    print(json.dumps(results, indent=2))
    print("\nSUMMARY:")
    print(f"Total breaks: {total_breaks}")
    print(f"Fixed if choosing alternate candidate: {fixable_breaks}")
    print(f"Not fixable: {total_breaks - fixable_breaks}")

if __name__ == "__main__":
    run_axis_candidate_recovery_audit()
