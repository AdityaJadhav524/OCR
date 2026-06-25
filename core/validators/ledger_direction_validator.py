import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.validators.ledger_direction_validator")

from core.validators.financial_audit import _parse_float

def run_ledger_direction_validator(sorted_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Mathematically validates and corrects OCR spatial debit/credit assignments.
    Requires transactions to be in chronological (ascending) order.
    """
    if not sorted_transactions:
        return {
            "direction_score": 0.0,
            "total_amounts": 0,
            "corrected_amounts": 0,
            "transactions": sorted_transactions
        }
        
    total_amounts = 0
    corrected_amounts = 0
    
    prev_balance = None
    
    # We create a new list of dictionaries so we don't mutate the originals in unpredictable ways,
    # though dictionaries are mutable so we'll just update the dicts safely.
    
    for i, txn in enumerate(sorted_transactions):
        cb = _parse_float(txn.get("balance"))
        c_val = _parse_float(txn.get("credit"))
        d_val = _parse_float(txn.get("debit"))
        
        ocr_direction = None
        amount = None
        if c_val is not None and c_val > 0:
            ocr_direction = "credit"
            amount = c_val
        elif d_val is not None and d_val > 0:
            ocr_direction = "debit"
            amount = d_val
            
        txn["ocr_direction"] = ocr_direction
        txn["ledger_direction"] = ocr_direction
        txn["direction_corrected"] = False
            
        if prev_balance is not None and cb is not None and amount is not None:
            total_amounts += 1
            delta = cb - prev_balance
            
            # Safe Magnitude Matching
            if abs(abs(delta) - amount) <= 1.0:
                ledger_direction = "credit" if delta > 0 else "debit"
                
                if ledger_direction != ocr_direction:
                    txn["ledger_direction"] = ledger_direction
                    txn["direction_corrected"] = True
                    
                    # APPLY THE HEAL: Swap the debit and credit values so downstream validators see the fixed state
                    txn["debit"], txn["credit"] = txn.get("credit"), txn.get("debit")
                    
                    corrected_amounts += 1
                    logger.info(f"Row {i}: Overrode OCR direction {ocr_direction} -> {ledger_direction} (Amount: {amount}, Delta: {delta})")
                    
        prev_balance = cb if cb is not None else prev_balance
        
    direction_score = 100.0
    if total_amounts > 0:
        # Penalize if we had to correct? 
        # Actually, if we mathematically corrected it, the final state is 100% accurate.
        # But for the sake of the engine, the "direction accuracy" might mean how good the OCR was,
        # OR how confident we are in the final direction.
        # Since we healed it, confidence is high, but let's report the OCR's raw accuracy.
        direction_score = round(((total_amounts - corrected_amounts) / total_amounts) * 100.0, 2)
        
    return {
        "direction_score": direction_score,
        "total_amounts": total_amounts,
        "corrected_amounts": corrected_amounts,
        "transactions": sorted_transactions
    }
