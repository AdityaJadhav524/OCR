import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.validators.financial_reconciliation")

from core.validators.financial_audit import _parse_float

def run_financial_reconciliation(sorted_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates Statement-Level Reconciliation:
    Opening + sum(Credits) - sum(Debits) = Closing
    
    Assumes transactions are chronologically sorted (ascending).
    """
    if not sorted_transactions:
        return {
            "reconciliation_percentage": 0.0,
            "difference": 0.0,
            "derived_opening_balance": None,
            "derived_closing_balance": None,
            "total_credits": 0.0,
            "total_debits": 0.0,
            "is_reconciled": False
        }
        
    # Compute totals
    total_credits = 0.0
    total_debits = 0.0
    
    for txn in sorted_transactions:
        c = _parse_float(txn.get("credit")) or 0.0
        d = _parse_float(txn.get("debit")) or 0.0
        total_credits += c
        total_debits += d
        
    # The true chronological opening balance relies on reversing the math of the first transaction.
    # However, OCR dropouts can cause the first or last row to lose its balance field.
    # We must scan for the first and last USABLE balance anchors.
    
    first_balanced_txn = None
    first_balanced_index = -1
    for idx, txn in enumerate(sorted_transactions):
        if _parse_float(txn.get("balance")) is not None:
            first_balanced_txn = txn
            first_balanced_index = idx
            break
            
    last_balanced_txn = None
    last_balanced_index = -1
    for idx, txn in reversed(list(enumerate(sorted_transactions))):
        if _parse_float(txn.get("balance")) is not None:
            last_balanced_txn = txn
            last_balanced_index = idx
            break
            
    derived_opening_balance = None
    if first_balanced_txn is not None:
        first_balance = _parse_float(first_balanced_txn.get("balance"))
        first_credit = _parse_float(first_balanced_txn.get("credit")) or 0.0
        first_debit = _parse_float(first_balanced_txn.get("debit")) or 0.0
        
        # We trace back the math to find what the balance was BEFORE this transaction occurred
        derived_opening_balance = first_balance - first_credit + first_debit
        
    derived_closing_balance = None
    if last_balanced_txn is not None:
        derived_closing_balance = _parse_float(last_balanced_txn.get("balance"))
    
    difference = None
    is_reconciled = False
    reconciliation_percentage = 0.0
    
    if derived_opening_balance is not None and derived_closing_balance is not None:
        expected_closing = derived_opening_balance + total_credits - total_debits
        difference = expected_closing - derived_closing_balance
        
        if abs(difference) <= 1.0:
            is_reconciled = True
            reconciliation_percentage = 100.0
        else:
            is_reconciled = False
            # Scale the reconciliation score based on how close the difference is to the total volume
            volume = total_credits + total_debits
            if volume > 0:
                error_ratio = abs(difference) / volume
                reconciliation_percentage = max(0.0, 100.0 - (error_ratio * 100.0))
            else:
                reconciliation_percentage = 0.0
                
    return {
        "reconciliation_percentage": round(reconciliation_percentage, 2),
        "difference": round(difference, 2) if difference is not None else None,
        "derived_opening_balance": derived_opening_balance,
        "derived_closing_balance": derived_closing_balance,
        "total_credits": round(total_credits, 2),
        "total_debits": round(total_debits, 2),
        "is_reconciled": is_reconciled,
        "opening_balance_source_row": first_balanced_index if first_balanced_index != -1 else None,
        "closing_balance_source_row": last_balanced_index if last_balanced_index != -1 else None,
        "opening_balance_recovered": first_balanced_index > 0,
        "closing_balance_recovered": last_balanced_index != -1 and last_balanced_index < len(sorted_transactions) - 1
    }
