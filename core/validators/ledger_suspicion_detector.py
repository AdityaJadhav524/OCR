"""
core/validators/ledger_suspicion_detector.py
────────────────────────────────────────────
Phase 1B: Ledger Suspicion Layer

Runs after conservation math has evaluated the row. Uses context
(prev_balance, expected_balance) to detect single-digit OCR substitutions
that pure formatting checks cannot catch.

Does not mutate transaction values. Appends to `suspicious_fields`.
"""
import math
import logging
from typing import Dict, Optional

logger = logging.getLogger("core.validators.ledger_suspicion_detector")

def _check_power_of_ten_drift(ocr_balance: float, expected_balance: float) -> Optional[Dict]:
    """
    Detects if the difference between OCR balance and expected balance
    is exactly a power of 10.
    
    This is the signature of a single-digit OCR error (e.g. 6 misread as 5).
    286201.63 -> 285201.63 (diff 1000)
    """
    diff = abs(ocr_balance - expected_balance)
    if diff <= 0.001:
        return None
        
    try:
        log = math.log10(diff)
        # Check if the log is very close to an integer (accounting for float drift)
        if abs(log - round(log)) < 0.01:
            magnitude = int(round(log))
            return {
                "reason": "POWER_OF_TEN_DRIFT",
                "severity": "HIGH",
                "diff": round(diff, 2),
                "magnitude": magnitude,
                "detail": f"Difference of {diff} indicates single digit OCR substitution"
            }
    except Exception:
        pass
    
    return None

def _check_small_digit_substitution(ocr_balance: float, expected_balance: float) -> Optional[Dict]:
    """
    Detects small integer differences (e.g. 1, 2, 3, 4, 5, 6, 7, 8, 9)
    that don't hit the power-of-10 rule but are common OCR shape confusions.
    For instance 208208.93 vs 208205.93 (diff 3).
    """
    diff = abs(ocr_balance - expected_balance)
    if 0.5 < diff <= 9.0:
        # Check if it's exactly an integer difference
        if abs(diff - round(diff)) < 0.01:
            return {
                "reason": "SMALL_DIGIT_SUBSTITUTION",
                "severity": "MEDIUM",
                "diff": int(round(diff)),
                "detail": f"Integer difference of {int(round(diff))} suggests minor digit shape confusion"
            }
    return None

def detect_ledger_suspicion(
    ocr_balance: float,
    prev_balance: float,
    debit: float,
    credit: float
) -> Dict:
    """
    Run ledger-aware OCR suspicion checks.
    
    Returns a dict that can be merged into `suspicious_fields`.
    Returns {} if nothing suspicious.
    """
    suspicious = {}
    
    expected_balance = round(prev_balance + credit - debit, 2)
    
    sig = _check_power_of_ten_drift(ocr_balance, expected_balance)
    if sig:
        suspicious["balance"] = sig
        logger.debug(f"Ledger suspicion [POWER_OF_TEN_DRIFT] diff={sig['diff']} mag={sig['magnitude']}")
    else:
        # Fallback to small digit substitution
        sig2 = _check_small_digit_substitution(ocr_balance, expected_balance)
        if sig2:
            suspicious["balance"] = sig2
            logger.debug(f"Ledger suspicion [SMALL_DIGIT_SUBSTITUTION] diff={sig2['diff']}")

    return suspicious
