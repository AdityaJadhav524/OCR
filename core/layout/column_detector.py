import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("core.layout.column_detector")

import re

def detect_columns(rows: List[Dict[str, Any]], identity: Dict = None) -> Dict[str, Tuple[float, float]]:
    """
    Scans physical rows to find the table header and calculates exact x-coordinate
    boundaries for Date, Narration, Debit, Credit, and Balance columns.
    Returns a tuple of (zones, detected_headers)
    """
    
    date_kws = ["DATE"]
    narration_kws = ["PARTICULARS", "NARRATION", "DESCRIPTION", "DETAILS", "REMARKS"]
    debit_kws = ["WITHDRAWAL", "WITHDRAWALS", "DEBIT", "DR"]
    credit_kws = ["DEPOSIT", "DEPOSITS", "CREDIT", "CR"]
    balance_kws = ["BALANCE", "BAL"]

    def matches_any(text: str, kws: List[str]) -> bool:
        for kw in kws:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                return True
        return False

    if identity and "identity_markers" in identity and "transaction_table_identity" in identity["identity_markers"]:
        pass

    header_row = []
    
    for i, row in enumerate(rows):
        window_rows = rows[i:i+3]
        
        found_date = False
        found_balance = False
        found_amt = False
        
        header_end_idx = i
        
        for j, w_row in enumerate(window_rows):
            text_upper = " ".join([t["text"].upper() for t in w_row.get("tokens", [])])
            
            row_has_date = matches_any(text_upper, date_kws)
            row_has_bal = matches_any(text_upper, balance_kws)
            row_has_amt = matches_any(text_upper, debit_kws + credit_kws)
            
            contributes = False
            if row_has_date and not found_date:
                found_date = True
                contributes = True
            if row_has_bal and not found_balance:
                found_balance = True
                contributes = True
            if row_has_amt and not found_amt:
                found_amt = True
                contributes = True
                
            if contributes or j == 0:
                header_end_idx = max(header_end_idx, i + j)
                
        if found_date and found_balance and found_amt:
            # We found the header block!
            for j in range(i, header_end_idx + 1):
                header_row.extend(rows[j].get("tokens", []))
            break
            
    if not header_row:
        logger.warning("Could not detect a clear header row for column analysis.")
        return {}, []
        
    zones = {}
    
    # Simple matching of token texts to keywords
    cols_found = []
    
    for t in header_row:
        text = t["text"].upper().replace(".", "").strip()
        xc = (t["x0"] + t.get("x1", t["x0"] + 50)) / 2.0
        
        is_debit = matches_any(text, debit_kws)
        is_credit = matches_any(text, credit_kws)
        
        if matches_any(text, date_kws):
            cols_found.append({"type": "date", "x0": t["x0"], "xc": xc})
        elif matches_any(text, narration_kws):
            cols_found.append({"type": "narration", "x0": t["x0"], "xc": xc})
        elif is_debit and is_credit:
            pass
        elif is_debit:
            cols_found.append({"type": "debit", "x0": t["x0"], "xc": xc})
        elif is_credit:
            cols_found.append({"type": "credit", "x0": t["x0"], "xc": xc})
        elif matches_any(text, balance_kws):
            cols_found.append({"type": "balance", "x0": t["x0"], "xc": xc})
            

    cols_found.sort(key=lambda c: c["x0"])

    # Deduplicate columns to prevent dictionary overwrite holes.
    # We want the best candidate for each column type.
    # For date and narration, the leftmost candidate is usually correct.
    # For amounts and balance, the rightmost candidate (closest to the numbers) is usually correct.
    best_cols = {}
    for c in cols_found:
        t = c["type"]
        if t in ["date", "narration"]:
            if t not in best_cols or c["x0"] < best_cols[t]["x0"]:
                best_cols[t] = c
        else:
            if t not in best_cols or c["x0"] > best_cols[t]["x0"]:
                best_cols[t] = c
                
    cols_found = list(best_cols.values())
    cols_found.sort(key=lambda c: c["x0"])

    # Assign zones using midpoints between adjacent column headers
    # This naturally handles left/right/center alignment without hardcoded padding
    for i in range(len(cols_found)):
        col = cols_found[i]
        
        # Calculate start_x (left bound)
        if i == 0:
            start_x = 0.0
        else:
            prev_col = cols_found[i-1]
            start_x = (prev_col["x0"] + col["x0"]) / 2.0
            
        # Calculate end_x (right bound)
        if i < len(cols_found) - 1:
            next_col = cols_found[i+1]
            end_x = (col["x0"] + next_col["x0"]) / 2.0
        else:
            end_x = 9999.0  # infinite right bound for the last column
            
        zones[f"{col['type']}_zone"] = [start_x, end_x]
        
    logger.info(f"Detected columns dynamically: {zones}")
    return zones, header_row
