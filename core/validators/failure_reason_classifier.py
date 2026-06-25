import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("core.validators.failure_reason_classifier")

def classify_ledger_break(break_info: Dict[str, Any]) -> str:
    """
    Categorizes a ledger break into a specific failure reason for targeted engineering fixes.
    
    Expected break_info keys:
    - row_index
    - prev_balance
    - current_balance
    - expected_balance
    - difference
    - credit
    - debit
    """
    diff = abs(break_info.get("difference", 0.0))
    cred = break_info.get("credit", 0.0)
    debt = break_info.get("debit", 0.0)
    
    # 1. Missing Transaction
    # If the difference is extremely large and does not match the current row's amounts,
    # it's highly likely one or more transactions were missed entirely.
    if diff > 10.0 and abs(diff - cred) > 1.0 and abs(diff - debt) > 1.0:
        # It's not a simple direction flip, and it's a large jump.
        return "MISSING_TRANSACTION"
        
    # 2. Direction Error (Debit <-> Credit Flip)
    # If a debit was wrongly parsed as credit (or vice versa), the difference
    # will be exactly twice the amount of the transaction.
    # Expected if credit=100 (should be debit=100): prev + 100
    # Actual: prev - 100
    # Diff: 200 (which is 2 * 100)
    if cred > 0 and abs(diff - (2 * cred)) <= 1.0:
        return "DIRECTION_ERROR"
    if debt > 0 and abs(diff - (2 * debt)) <= 1.0:
        return "DIRECTION_ERROR"
        
    # 3. Amount Extraction Error
    # The OCR read the amount incorrectly (e.g. 500.00 read as 50.00)
    # The difference will be non-zero, but not exactly matching missing or double rules.
    # Usually, if difference is relatively small but not matching the amounts.
    if (cred > 0 or debt > 0) and diff > 1.0:
        return "AMOUNT_EXTRACTION_ERROR"
        
    # 4. Balance Corruption
    # If neither credit nor debit exists (amount missing) OR if the balance itself is clearly wrong
    if cred == 0.0 and debt == 0.0:
        return "BALANCE_CORRUPTION"
        
    return "UNKNOWN_LEDGER_BREAK"
