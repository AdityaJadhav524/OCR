import logging
from typing import List, Dict, Any
import statistics

logger = logging.getLogger("core.validators.balance_sanity_validator")

def run_balance_sanity_validator(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Layer 4: Balance Sanity Validator
    Removes mathematically impossible balance candidates before they can pollute downstream validators.
    Rules:
    - Candidate cannot be 100x larger than the local median.
    - Candidate without 'decimal_present' evidence is heavily penalized if it's an outlier.
    """
    # 1. First pass to find the rough magnitude of the ledger.
    # We look for "safe" balances (those with decimals, not suspect)
    safe_balances = []
    for txn in transactions:
        candidates = txn.get("balance_candidates", [])
        for c in candidates:
            ev = c.get("evidence", [])
            if "decimal_present" in ev and "watermark_pattern_suspect" not in ev:
                safe_balances.append(c["value"])
                
    if not safe_balances:
        # If no safe balances, fallback to all balances
        for txn in transactions:
            for c in txn.get("balance_candidates", []):
                safe_balances.append(c["value"])

    # If still no balances, nothing we can do
    if not safe_balances:
        return transactions

    global_median = statistics.median(safe_balances)
    # We don't want the median to be 0 for math reasons
    if global_median < 1.0:
        global_median = 1.0

    # 2. Prune candidates
    for i, txn in enumerate(transactions):
        candidates = txn.get("balance_candidates", [])
        surviving_candidates = []
        
        for c in candidates:
            val = c["value"]
            ev = c.get("evidence", [])
            
            # Rule 1: Cannot be 100x larger than global median
            if val > global_median * 100:
                continue
                
            # Rule 2: Purely numeric string without decimal that is 10x larger than median
            if "watermark_pattern_suspect" in ev and "decimal_present" not in ev:
                if val > global_median * 10:
                    continue
                    
            surviving_candidates.append(c)
            
        # If we aggressively pruned EVERYTHING, fallback to at least preserving the original parsed balance
        if not surviving_candidates and candidates:
            # Sort by value closest to median
            closest = min(candidates, key=lambda c: abs(c["value"] - global_median))
            surviving_candidates.append(closest)
            
        txn["balance_candidates"] = surviving_candidates
        
        # Select the default balance from the surviving candidates for the legacy pipeline
        if surviving_candidates:
            # Prefer candidates with decimal_present or synthetic decimal shifts over pure integer watermarks
            best_candidate = None
            
            # Priority 1: Has decimal
            for c in surviving_candidates:
                if "decimal_present" in c.get("evidence", []):
                    best_candidate = c
                    break
            
            # Priority 2: Synthetic decimal
            if not best_candidate:
                for c in surviving_candidates:
                    if "synthetic_decimal_shift" in c.get("evidence", []):
                        best_candidate = c
                        break
                        
            # Fallback: Just take the first one
            if not best_candidate:
                best_candidate = surviving_candidates[0]
                
            txn["balance"] = best_candidate["value"]
            txn["_selected_candidate_evidence"] = best_candidate.get("evidence", [])
        else:
            txn["balance"] = None
            
    return transactions
