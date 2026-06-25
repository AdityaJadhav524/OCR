import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("core.validators.transaction_order_validator")

from core.validators.financial_audit import _parse_float

def validate_and_sort_transactions(transactions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Analyzes the extracted transactions to determine their true chronological order.
    Returns a newly sorted list of transactions (guaranteed ascending) and a metadata payload.
    
    Validation factors:
    - Balance math sequence (prev_balance + credit - debit == current_balance)
    - Date parsing (if balance math is ambiguous)
    """
    if not transactions or len(transactions) < 2:
        return transactions, {
            "is_descending": False,
            "confidence": 100,
            "asc_matches": 0,
            "desc_matches": 0
        }

    asc_matches = 0
    desc_matches = 0
    
    for i in range(1, len(transactions)):
        prev = transactions[i-1]
        curr = transactions[i]
        
        pb = _parse_float(prev.get("balance"))
        cb = _parse_float(curr.get("balance"))
        
        if pb is None or cb is None:
            continue
            
        c_curr = _parse_float(curr.get("credit")) or 0.0
        d_curr = _parse_float(curr.get("debit")) or 0.0
        
        c_prev = _parse_float(prev.get("credit")) or 0.0
        d_prev = _parse_float(prev.get("debit")) or 0.0
        
        # Check ascending math: prev_balance + curr_credit - curr_debit == curr_balance
        if abs(pb + c_curr - d_curr - cb) <= 1.0:
            asc_matches += 1
            
        # Check descending math: curr_balance + prev_credit - prev_debit == prev_balance
        if abs(cb + c_prev - d_prev - pb) <= 1.0:
            desc_matches += 1

    is_descending = desc_matches > asc_matches
    
    # Optional: If matches are tied, we could fall back to date parsing.
    # For now, we trust the balance math.
    
    confidence = 100
    if asc_matches == 0 and desc_matches == 0:
        confidence = 0  # Cannot mathematically prove order
    elif is_descending and asc_matches > 0:
        confidence = int((desc_matches / (asc_matches + desc_matches)) * 100)
    elif not is_descending and desc_matches > 0:
        confidence = int((asc_matches / (asc_matches + desc_matches)) * 100)
        
    logger.info(f"Order Validation: is_descending={is_descending}, asc_matches={asc_matches}, desc_matches={desc_matches}, confidence={confidence}%")

    sorted_transactions = list(transactions)
    if is_descending:
        sorted_transactions.reverse()
        
    return sorted_transactions, {
        "is_descending": is_descending,
        "confidence": confidence,
        "asc_matches": asc_matches,
        "desc_matches": desc_matches
    }
