import sys
import os
import json
import glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.statement_confidence_engine import (
    validate_and_sort_transactions,
    run_running_balance_audit,
    run_ledger_direction_validator
)
from core.extractors.candidate_generator import generate_balance_candidates
from core.validators.balance_sanity_validator import run_balance_sanity_validator

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

def run_candidate_regression_audit():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    
    for tf in truth_files:
        truth = json.loads(tf.read_text(encoding="utf-8"))
        pdf_name = truth.get("corpus_file", "")
        bank = truth.get("bank", "Unknown")
        
        if not pdf_name: continue
        
        # We only care about banks that regressed or had issues
        if bank not in ["YES BANK", "HDFC BANK"]:
            continue
            
        pdf_path = find_latest_temp_file(pdf_name)
        if not pdf_path: continue
        
        try:
            doc_type, _ = detect_document_type(str(pdf_path))
        except ValueError as e:
            if "PASSWORD_REQUIRED" in str(e): continue
            raise
            
        full_text, pages, tel, page_tokens = route_document(str(pdf_path))
        identity = classify_document_llm(pages)
        detected_pdf_type = "SCANNED" if doc_type == "scanned" else "DIGITAL"
        
        txns, parser_tel = parse_with_coordinates(
            page_tokens,
            pdf_name=pdf_name,
            statement_id="audit",
            job_id="audit",
            bank=bank,
            pdf_type=detected_pdf_type,
            identity=identity
        )
        
        # Phase 1: Legacy Engine Execution (Layers 1-2 only)
        # Deep copy the txns so we don't mutate the originals during sorting
        import copy
        legacy_txns = copy.deepcopy(txns)
        sorted_legacy, _ = validate_and_sort_transactions(legacy_txns)
        
        # Phase 2: New Engine Execution (Layers 1-4)
        new_txns = copy.deepcopy(txns)
        sorted_new, _ = validate_and_sort_transactions(new_txns)
        
        generate_balance_candidates(sorted_new)
        
        run_balance_sanity_validator(sorted_new)
        
        print(f"\n{'='*50}")
        print(f"REGRESSION AUDIT: {bank}")
        print(f"{'='*50}")
        
        regressions = 0
        for i, (old_txn, new_txn) in enumerate(zip(sorted_legacy, sorted_new)):
            old_bal = old_txn.get("balance")
            new_bal = new_txn.get("balance")
            
            if old_bal != new_bal:
                regressions += 1
                cands = new_txn.get("balance_candidates", [])
                
                print(f"\nRow {i}:")
                print(f"  Old Balance : {old_bal}")
                print(f"  New Balance : {new_bal}")
                print(f"  Raw Text    : {new_txn.get('raw_balance_text')}")
                print(f"  All Cands   : {[c.get('value') for c in cands]}")
                print(f"  Selected Ev : {new_txn.get('_selected_candidate_evidence', [])}")
                
        if regressions == 0:
            print(f"  No balance regressions detected.")
        else:
            print(f"\n  Total Regressions: {regressions}")

if __name__ == "__main__":
    run_candidate_regression_audit()
