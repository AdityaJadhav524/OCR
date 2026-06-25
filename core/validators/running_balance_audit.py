import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.validators.running_balance_audit")

from core.validators.financial_audit import _parse_float
from core.validators.failure_reason_classifier import classify_ledger_break

def run_running_balance_audit(sorted_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates the running balance of a chronologically sorted list of transactions.
    Assumes Sprint 0 (transaction_order_validator) has already ordered them ascending.
    """
    if not sorted_transactions:
        return {
            "continuity_percentage": 0.0,
            "total_transitions": 0,
            "valid_transitions": 0,
            "ledger_breaks": []
        }
        
    total_transitions = 0
    valid_transitions = 0
    ledger_breaks = []
    
    prev_balance = None
    
    for i, curr in enumerate(sorted_transactions):
        cb = _parse_float(curr.get("balance"))
        
        # We need both prev and current balance to check a transition
        if cb is None:
            prev_balance = None  # Chain broken by missing balance
            continue
            
        if prev_balance is not None:
            c_curr = _parse_float(curr.get("credit")) or 0.0
            d_curr = _parse_float(curr.get("debit")) or 0.0
            
            expected_balance = prev_balance + c_curr - d_curr
            difference = cb - expected_balance
            
            total_transitions += 1
            if abs(difference) <= 1.0:
                valid_transitions += 1
            else:
                break_info = {
                    "row_index": i,
                    "prev_balance": prev_balance,
                    "current_balance": cb,
                    "expected_balance": expected_balance,
                    "difference": difference,
                    "credit": c_curr,
                    "debit": d_curr
                }
                break_info["reason"] = classify_ledger_break(break_info)
                ledger_breaks.append(break_info)
        
        prev_balance = cb
        
    continuity_percentage = 0.0
    if total_transitions > 0:
        continuity_percentage = round((valid_transitions / total_transitions) * 100.0, 2)
    elif len(sorted_transactions) == 1:
        # A single transaction statement has perfect continuity by definition if we can't transition
        continuity_percentage = 100.0
        
    return {
        "continuity_percentage": continuity_percentage,
        "total_transitions": total_transitions,
        "valid_transitions": valid_transitions,
        "ledger_breaks": ledger_breaks
    }
