import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("core.layout.column_detector")

import re

def detect_columns(rows: List[Dict[str, Any]], identity: Dict = None) -> Dict[str, Tuple[float, float]]:
    """
    Scans physical rows to find the table header and calculates exact x-coordinate
    boundaries for Date, Narration, Debit, Credit, and Balance columns.

    Header detection uses a SCORING approach:
    - Every row window is scored by how many distinct column types (date, narration,
      debit, credit, balance) it contains.
    - The highest-scoring window wins.
    - On ties, the later window wins (transaction tables appear after account-summary
      sections that may contain the same keyword combinations).

    Returns a tuple of (zones, detected_headers).
    """

    date_kws      = ["DATE"]
    value_date_kws= ["VALUE DATE", "VALUE DT", "VAL DT", "VAL.DATE", "EFFECTIVE DATE"]
    cheque_kws    = ["CHQ", "CHEQUE", "REF", "REFERENCE", "INSTRUMENT"]
    narration_kws = ["PARTICULARS", "NARRATION", "DESCRIPTION", "DETAILS", "REMARKS"]
    debit_kws     = ["WITHDRAWAL", "WITHDRAWALS", "DEBIT", "DR"]
    credit_kws    = ["DEPOSIT", "DEPOSITS", "CREDIT", "CR"]
    balance_kws   = ["BALANCE", "BAL"]

    def matches_any(text: str, kws: List[str]) -> bool:
        for kw in kws:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                return True
        return False

    # ── Header detection: score every row window, keep the best ──────────────
    best_score      = 0
    best_header_row = []
    best_idx        = -1

    for i, row in enumerate(rows):
        window_rows = rows[i:i+3]

        found_types      = set()
        window_header_end = i

        for j, w_row in enumerate(window_rows):
            text_upper = " ".join([t["text"].upper() for t in w_row.get("tokens", [])])

            if matches_any(text_upper, value_date_kws) and "value_date" not in found_types:
                found_types.add("value_date"); window_header_end = i + j
            if matches_any(text_upper, cheque_kws)    and "cheque"    not in found_types:
                found_types.add("cheque");     window_header_end = i + j
            if matches_any(text_upper, date_kws)      and "date"      not in found_types:
                found_types.add("date");      window_header_end = i + j
            if matches_any(text_upper, balance_kws)   and "balance"   not in found_types:
                found_types.add("balance");   window_header_end = i + j
            if matches_any(text_upper, debit_kws)     and "debit"     not in found_types:
                found_types.add("debit");     window_header_end = i + j
            if matches_any(text_upper, credit_kws)    and "credit"    not in found_types:
                found_types.add("credit");    window_header_end = i + j
            if matches_any(text_upper, narration_kws) and "narration" not in found_types:
                found_types.add("narration"); window_header_end = i + j

        # Minimum qualification: date + balance + at least one of debit/credit
        if "date" not in found_types or "balance" not in found_types:
            continue
        if "debit" not in found_types and "credit" not in found_types:
            continue

        score = len(found_types)
        # Higher score wins; on ties prefer the later occurrence (later in document
        # is more likely to be the actual transaction table header, not a summary section)
        if score > best_score or (score == best_score and i > best_idx):
            best_score = score
            best_idx   = i
            candidate_tokens = []
            for j in range(i, window_header_end + 1):
                candidate_tokens.extend(rows[j].get("tokens", []))
            best_header_row = candidate_tokens

    header_row = best_header_row

    if not header_row:
        logger.warning("Could not detect a clear header row for column analysis.")
        return {}, []

    # ── Column type assignment ────────────────────────────────────────────────
    zones      = {}
    cols_found = []

    for t in header_row:
        text = t["text"].upper().replace(".", "").strip()
        xc   = (t["x0"] + t.get("x1", t["x0"] + 50)) / 2.0

        is_debit  = matches_any(text, debit_kws)
        is_credit = matches_any(text, credit_kws)

        if is_debit and is_credit:
            # Check if it's a balance indicator rather than merged amount columns
            clean_text = text.replace(" ", "").replace("/", "").replace("\\", "").replace("-", "")
            if clean_text in ["DRCR", "CRDR"]:
                continue
            # OCR merged Debit and Credit headers into one token — split at midpoint.
            dr_pos = min([text.find(kw) for kw in debit_kws  if text.find(kw) != -1])
            cr_pos = min([text.find(kw) for kw in credit_kws if text.find(kw) != -1])
            mid    = (t["x0"] + t.get("x1", t["x0"] + 50)) / 2.0
            if dr_pos < cr_pos:
                cols_found.append({"type": "debit",  "x0": t["x0"], "xc": (t["x0"] + mid) / 2.0})
                cols_found.append({"type": "credit", "x0": mid,      "xc": (mid + t.get("x1", t["x0"] + 50)) / 2.0})
            else:
                cols_found.append({"type": "credit", "x0": t["x0"], "xc": (t["x0"] + mid) / 2.0})
                cols_found.append({"type": "debit",  "x0": mid,      "xc": (mid + t.get("x1", t["x0"] + 50)) / 2.0})
        elif matches_any(text, value_date_kws):
            cols_found.append({"type": "value_date", "x0": t["x0"], "xc": xc})
        elif matches_any(text, cheque_kws):
            cols_found.append({"type": "cheque", "x0": t["x0"], "xc": xc})
        elif matches_any(text, date_kws):
            cols_found.append({"type": "date", "x0": t["x0"], "xc": xc})
        elif matches_any(text, narration_kws):
            cols_found.append({"type": "narration", "x0": t["x0"], "xc": xc})
        elif is_debit:
            cols_found.append({"type": "debit",   "x0": t["x0"], "xc": xc})
        elif is_credit:
            cols_found.append({"type": "credit",  "x0": t["x0"], "xc": xc})
        elif matches_any(text, balance_kws):
            cols_found.append({"type": "balance", "x0": t["x0"], "xc": xc})

    cols_found.sort(key=lambda c: c["x0"])

    # Deduplicate: for date/narration keep leftmost; for amounts/balance keep rightmost.
    best_cols = {}
    for c in cols_found:
        t = c["type"]
        if t in ["date", "narration", "value_date", "cheque"]:
            if t not in best_cols or c["x0"] < best_cols[t]["x0"]:
                best_cols[t] = c
        else:
            if t not in best_cols or c["x0"] > best_cols[t]["x0"]:
                best_cols[t] = c

    cols_found = list(best_cols.values())
    cols_found.sort(key=lambda c: c["x0"])

    # ── Zone assignment: midpoint between column centers ───────
    # This provides maximal tolerance for right-aligned amount columns
    # expanding into the empty space to their left.
    right_boundaries = []
    for i in range(len(cols_found)):
        if i < len(cols_found) - 1:
            boundary = (cols_found[i]["xc"] + cols_found[i+1]["xc"]) / 2.0
            right_boundaries.append(boundary)
        else:
            right_boundaries.append(9999.0)

    for i, col in enumerate(cols_found):
        start_x = 0.0 if i == 0 else right_boundaries[i-1]
        end_x   = right_boundaries[i]
        zones[f"{col['type']}_zone"] = [start_x, end_x]

    logger.info(f"Detected columns dynamically: {zones}")
    return zones, header_row
