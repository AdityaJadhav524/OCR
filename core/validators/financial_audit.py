import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.validators.financial_audit")

import re
from core.cleaners.balance_text_sanitizer import sanitize_balance_text

def _parse_float(val) -> float:
    if val is None:
        return None

    if isinstance(val, (int, float)):
        return float(val)

    text = str(val).strip()
    
    # 1. Apply Document-Specific Sanitization (Watermarks, OCR bleeding)
    text = sanitize_balance_text(text)
    if not text:
        return None

    # Strip everything except digits, comma, period, minus (just in case)
    text = re.sub(r'[^\d.,-]', '', text)

    # Apply OCR comma-as-decimal fix
    # Indian formatting uses 2 decimal places. OCR often reads '.' as ','
    if '.' not in text and ',' in text:
        last_comma_idx = text.rfind(',')
        if len(text) - last_comma_idx - 1 == 2:
            text = text[:last_comma_idx] + '.' + text[last_comma_idx+1:]

    text = text.replace(',', '')

    # If there are multiple periods, assume the last one is the decimal point and others are mangled thousands separators
    if text.count('.') > 1:
        parts = text.rsplit('.', 1)
        text = parts[0].replace('.', '') + '.' + parts[1]
    elif text.count('.') == 1:
        # Check for single-period OCR misreads where a comma was read as a period
        parts = text.split('.')
        if len(parts[1]) == 3 and len(parts[0]) <= 3:
            # "2.000" -> "2000"
            text = text.replace('.', '')
        elif len(parts[1]) == 5 and len(parts[0]) <= 3:
            # "2.00000" -> "2000.00"
            text = parts[0] + parts[1][:3] + '.' + parts[1][3:]

    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return None

    return float(match.group())

def _is_negative(val) -> bool:
    v = _parse_float(val)
    if v is None: return False
    return v < 0

def run_financial_audit(transactions: List[Dict[str, Any]], expected_transaction_count: int = None, telemetry: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Runs core financial reconciliation checks on the extracted transactions.
    """
    results = {
        "audit_passed": True,
        "running_balance_issues": 0,
        "negative_amounts": 0,
        "impossible_jumps": 0,
        "opening_balance_reconciled": False,
        "transaction_count_match": None,
        "warnings": [],
        "audit_summary": {
            "total_transactions": len(transactions),
            "full_agreement": 0,
            "partial_agreement": 0,
            "conflict": 0,
            "unseeded": 0,
            "rejected_rows": telemetry.get("v2_rejected_rows", 0) if telemetry else 0
        }
    }
    
    # Aggregate agreement states
    for txn in transactions:
        state = txn.get("agreement_state")
        if state == "FULL_AGREEMENT":
            results["audit_summary"]["full_agreement"] += 1
        elif state == "PARTIAL_AGREEMENT":
            results["audit_summary"]["partial_agreement"] += 1
        elif state == "CONFLICT":
            results["audit_summary"]["conflict"] += 1
        elif state == "UNSEEDED":
            results["audit_summary"]["unseeded"] += 1

    if expected_transaction_count is not None:
        if len(transactions) == expected_transaction_count:
            results["transaction_count_match"] = True
        else:
            results["transaction_count_match"] = False
            results["warnings"].append(f"Expected {expected_transaction_count} transactions, but extracted {len(transactions)}.")

    if not transactions:
        results["warnings"].append("No transactions to audit.")
        results["audit_passed"] = False
        return results

    # Determine sort order (Ascending means row 0 is oldest, row N is newest)
    # Most banks are descending or ascending. We can detect by checking which way balance moves.
    asc_matches = 0
    desc_matches = 0
    
    for i in range(1, len(transactions)):
        prev = transactions[i-1]
        curr = transactions[i]
        
        pb = _parse_float(prev.get("balance")) or 0.0
        cb = _parse_float(curr.get("balance")) or 0.0
        
        c_curr = _parse_float(curr.get("credit")) or 0.0
        d_curr = _parse_float(curr.get("debit")) or 0.0
        
        c_prev = _parse_float(prev.get("credit")) or 0.0
        d_prev = _parse_float(prev.get("debit")) or 0.0
        
        # Check ascending math: prev_balance + curr_credit - curr_debit == curr_balance
        if abs(pb + c_curr - d_curr - cb) < 0.01:
            asc_matches += 1
            
        # Check descending math: curr_balance + prev_credit - prev_debit == prev_balance
        if abs(cb + c_prev - d_prev - pb) < 0.01:
            desc_matches += 1

    is_descending = desc_matches > asc_matches

    # ---------------------------------------------------------
    # Audit 1: Negative Amount Detection
    # ---------------------------------------------------------
    for idx, txn in enumerate(transactions):
        if _is_negative(txn.get("debit")) or _is_negative(txn.get("credit")):
            results["negative_amounts"] += 1
            results["warnings"].append(f"Row {idx}: Negative amount detected.")
            txn["_audit_negative"] = True

    # ---------------------------------------------------------
    # Audit 2 & 4: Running Balance Check & Impossible Jumps
    # ---------------------------------------------------------
    net_credits = 0.0
    net_debits = 0.0
    valid_reconciliation = 0

    for i in range(1, len(transactions)):
        if is_descending:
            older_idx, newer_idx = i, i - 1
        else:
            older_idx, newer_idx = i - 1, i
            
        older = transactions[older_idx]
        newer = transactions[newer_idx]
        
        bal_old = _parse_float(older.get("balance")) or 0.0
        bal_new = _parse_float(newer.get("balance")) or 0.0
        cred = _parse_float(newer.get("credit")) or 0.0
        debt = _parse_float(newer.get("debit")) or 0.0
        
        expected_bal = bal_old + cred - debt
        diff = abs(expected_bal - bal_new)
        
        if diff < 0.01:
            valid_reconciliation += 1
            newer["_audit_running_bal"] = True
        else:
            newer["_audit_running_bal"] = False
            results["running_balance_issues"] += 1
            results["warnings"].append(
                f"Row {newer_idx}: Balance breaks (Expected {expected_bal:.2f}, Got {bal_new:.2f})"
            )
            
            # Any unexplained jump > 0.01 is an impossible jump in accounting
            results["impossible_jumps"] += 1
            results["warnings"].append(f"Row {newer_idx}: Impossible balance jump of {diff:.2f}")

    # ---------------------------------------------------------
    # Audit 3: Opening Balance Check (Statement-level)
    # ---------------------------------------------------------
    for txn in transactions:
        net_credits += _parse_float(txn.get("credit")) or 0.0
        net_debits += _parse_float(txn.get("debit")) or 0.0
        
    if is_descending:
        opening_bal_idx = len(transactions) - 1
        closing_bal_idx = 0
    else:
        opening_bal_idx = 0
        closing_bal_idx = len(transactions) - 1
        
    opening_bal = _parse_float(transactions[opening_bal_idx].get("balance")) or 0.0
    # We must offset the opening balance by the very first transaction to get the TRUE opening balance before it occurred
    first_cred = _parse_float(transactions[opening_bal_idx].get("credit")) or 0.0
    first_debt = _parse_float(transactions[opening_bal_idx].get("debit")) or 0.0
    true_opening_bal = opening_bal - first_cred + first_debt
    
    closing_bal = _parse_float(transactions[closing_bal_idx].get("balance")) or 0.0
    
    if abs(true_opening_bal + net_credits - net_debits - closing_bal) < 0.01:
        results["opening_balance_reconciled"] = True
    else:
        results["opening_balance_reconciled"] = False
        results["warnings"].append("Statement-level Opening/Closing balance does not reconcile.")

    # ---------------------------------------------------------
    # Final Outcome
    # ---------------------------------------------------------
    # HARD FAILURE RULE: If we extracted transactions but have ZERO amounts, parser completely failed.
    if len(transactions) > 0 and net_credits == 0.0 and net_debits == 0.0:
        results["audit_passed"] = False
        results["warnings"].append("Extraction Failed: No debit or credit values assigned. Amounts likely detected inside narration field.")
        logger.error("HARD FAILURE: Debit and Credit totals are 0.0 for extracted transactions.")
        return results

    # AMOUNT LEAKAGE DETECTION
    leakage_count = sum(1 for t in transactions if t.get("_amount_leakage_detected"))
    if leakage_count > 0:
        results["audit_passed"] = False
        results["warnings"].append(f"AMOUNT_LEAKAGE_DETECTED: {leakage_count} transactions have floating-point amounts mixed into narration.")
        logger.error("HARD FAILURE: AMOUNT_LEAKAGE_DETECTED in narration strings.")

    if results["running_balance_issues"] > 0 or results["negative_amounts"] > 0 or results["impossible_jumps"] > 0 or results["transaction_count_match"] is False:
        results["audit_passed"] = False
        
    logger.info(f"Financial Audit: Passed={results['audit_passed']}, Issues={results['running_balance_issues']}, Jumps={results['impossible_jumps']}, OpeningReconciled={results['opening_balance_reconciled']}")
    
    return results
