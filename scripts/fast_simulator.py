import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.validators.statement_confidence_engine import validate_and_sort_transactions
from core.validators.running_balance_audit import run_running_balance_audit
from core.ordering.page_sequence_repair import run_page_sequence_repair

def simulate_fast():
    truth_file = ROOT / "tests" / "truth_corpus" / "hdfc_scanned.json"
    truth = json.loads(truth_file.read_text(encoding="utf-8"))
    
    # We will use the truth transactions, which ALREADY have balances.
    txns = truth.get("transactions", [])
    if not txns: return
    
    print(f"Loaded {len(txns)} transactions from truth corpus.")
    
    # Let's shuffle the pages by setting their 'page' randomly if they aren't already out of order?
    # Wait! The truth corpus is ALREADY in the correct chronological order!
    # Because it was manually transcribed in correct order!
    # Let's see if it has 'page' info.
    pages = set(t.get("page", 0) for t in txns)
    print(f"Pages in truth: {pages}")
    
    # Let's see what continuity the Truth corpus gets BEFORE any sorting.
    baseline_audit = run_running_balance_audit(txns)
    print(f"Baseline (Truth) Continuity: {baseline_audit['continuity_percentage']}%")

if __name__ == "__main__":
    simulate_fast()
