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
    pdf_path = None
    if matches:
        pdf_path = Path(matches[-1])
            
    if not pdf_path or not pdf_path.exists():
        print("Could not find BOI PDF")
        return

    print(f"Extracting {pdf_path.name}...")
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, parser_tel = parse_with_coordinates(
        page_tokens,
        pdf_name=pdf_path.name,
        statement_id="audit",
        job_id="audit",
        bank="Bank of India",
        pdf_type="SCANNED"
    )
    
    truth_file = ROOT / "tests" / "truth_corpus" / "boi_scanned.json"
    expected_count = 0
    if truth_file.exists():
        truth = json.loads(truth_file.read_text(encoding="utf-8"))
        expected_count = len(truth.get("transactions", []))
    
    # Baseline (Audit Before Heal)
    txns_baseline = copy.deepcopy(txns)
    sorted_baseline, _ = validate_and_sort_transactions(txns_baseline)
    rb_baseline = run_running_balance_audit(sorted_baseline)
    recon_baseline = run_financial_reconciliation(sorted_baseline)
    dir_baseline = run_ledger_direction_validator(sorted_baseline)
    
    comp_base = 100.0 if not expected_count else (len(txns_baseline) / expected_count) * 100.0
    conf_base = (rb_baseline["continuity_percentage"] * 0.40) + \
                (recon_baseline["reconciliation_percentage"] * 0.35) + \
                (dir_baseline["direction_score"] * 0.15) + \
                (comp_base * 0.10)
                
    print("\n=== PIPELINE 1: AUDIT BEFORE HEAL (Current) ===")
    print(f"Continuity: {rb_baseline['continuity_percentage']}%")
    print(f"Reconciliation: {recon_baseline['reconciliation_percentage']}%")
    print(f"Confidence: {int(round(conf_base))}")
    
    # Test (Heal Before Audit)
    txns_test = copy.deepcopy(txns)
    sorted_test, _ = validate_and_sort_transactions(txns_test)
    dir_test = run_ledger_direction_validator(sorted_test) # Heals in-place
    rb_test = run_running_balance_audit(sorted_test)
    recon_test = run_financial_reconciliation(sorted_test)
    
    comp_test = 100.0 if not expected_count else (len(txns_test) / expected_count) * 100.0
    conf_test = (rb_test["continuity_percentage"] * 0.40) + \
                (recon_test["reconciliation_percentage"] * 0.35) + \
                (dir_test["direction_score"] * 0.15) + \
                (comp_test * 0.10)
                
    print("\n=== PIPELINE 2: HEAL BEFORE AUDIT (Test) ===")
    print(f"Continuity: {rb_test['continuity_percentage']}%")
    print(f"Reconciliation: {recon_test['reconciliation_percentage']}%")
    print(f"Confidence: {int(round(conf_test))}")

if __name__ == "__main__":
    run_experiment()
