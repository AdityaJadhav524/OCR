import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("core.layout.column_detector")

def detect_columns(rows: List[Dict[str, Any]], identity: Dict = None) -> Dict[str, Tuple[float, float]]:
    """
    Scans physical rows to find the table header and calculates exact x-coordinate
    boundaries for Date, Narration, Debit, Credit, and Balance columns.
    Returns a tuple of (zones, detected_headers)
    """
    
    date_kws = ["DATE", "TXN DATE", "VALUE DATE"]
    narration_kws = ["PARTICULARS", "NARRATION", "DESCRIPTION", "DETAILS"]
    debit_kws = ["WITHDRAWAL", "DEBIT", "DR"]
    credit_kws = ["DEPOSIT", "CREDIT", "CR"]
    balance_kws = ["BALANCE", "BAL"]

    if identity and "identity_markers" in identity and "transaction_table_identity" in identity["identity_markers"]:
        # If we have explicit table headers from the template, we could overwrite the heuristics
        # But wait, the LLM output is something like ["Date", "Description", "Debit", "Credit", "Balance"]
        # which may vary wildly. So it's best to augment the keywords rather than strictly replace them
        # if we are doing heuristic search, OR strict search if it's precise.
        # Actually, let's keep the keywords broad for the header *row* detection,
        # but if we know it's a single amount column or similar from parsing_hints, we could adapt.
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
            
            row_has_date = any(kw in text_upper for kw in date_kws)
            row_has_bal = any(kw in text_upper for kw in balance_kws)
            row_has_amt = any(kw in text_upper for kw in debit_kws + credit_kws)
            
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
        
        is_debit = any(kw in text for kw in debit_kws) or 'WITHDRAWAL' in text
        is_credit = any(kw in text for kw in credit_kws) or 'DEPOSIT' in text
        
        if any(kw in text for kw in date_kws):
            cols_found.append({"type": "date", "x0": t["x0"], "xc": xc})
        elif any(kw in text for kw in narration_kws):
            cols_found.append({"type": "narration", "x0": t["x0"], "xc": xc})
        elif is_debit and is_credit:
            cols_found.append({"type": "debit", "x0": t["x0"], "xc": xc})
            cols_found.append({"type": "credit", "x0": xc, "xc": xc})
        elif is_debit:
            cols_found.append({"type": "debit", "x0": t["x0"], "xc": xc})
        elif is_credit:
            cols_found.append({"type": "credit", "x0": t["x0"], "xc": xc})
        elif any(kw in text for kw in balance_kws):
            cols_found.append({"type": "balance", "x0": t["x0"], "xc": xc})
            

    cols_found.sort(key=lambda c: c["x0"])

    # Let multiple columns of the same type overwrite each other (keeps the right-most one, which is usually Post Date)
    # Assign zones using exactly adjacent boundaries to prevent overlap
    for i in range(len(cols_found)):
        col = cols_found[i]
        
        # Calculate start_x (left bound)
        if i == 0:
            start_x = 0.0
        else:
            start_x = col["x0"] - 10
            
        # Calculate end_x (right bound)
        if i < len(cols_found) - 1:
            end_x = cols_found[i+1]["x0"] - 10
        else:
            end_x = 9999.0  # infinite right bound for the last column
            
        zones[f"{col['type']}_zone"] = [start_x, end_x]
        
    logger.info(f"Detected columns dynamically: {zones}")
    return zones, header_row
