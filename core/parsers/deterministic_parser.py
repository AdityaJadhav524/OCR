"""
deterministic_parser.py  —  Balance-Reconciliation Column Solver
================================================================
Architecture
------------
Phase 1  Extract rows as  {date, narration, numbers:[float,...]}
         No debit/credit labels. Just the numbers.

Phase 2  For every candidate "balance column index" b:
           For each consecutive row pair (i, i+1):
             delta = balance[i+1] - balance[i]
             Search the non-balance numbers in row i+1 for one ≈ |delta|
             delta > 0  →  credit;   delta < 0  →  debit
           score = fraction of pairs that reconciled
         Pick the b with the highest score.

Phase 3  Recovery Engine
         Locates missing OCR rows, re-parses them using the known
         balance column, and merges them if confidence >= 0.9.

Phase 4  Hard-fail if debit_total == 0 AND credit_total == 0.
"""

import re
import logging
import hashlib
from typing import List, Dict, Optional, Tuple, Any

from core.extractors.pdf_extractor import DATE_RE

logger = logging.getLogger("ledgerai.deterministic_parser")

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
_TOLERANCE    = 2.0    # max allowed gap between delta and best matching amount
_ROUNDING_GAP = 0.05   # deltas smaller than this are genuine rounding artifacts
_AMOUNT_RE  = re.compile(r'[\d,]+\.\d{2}')   # decimal amounts only

# Seed balance source score ranking
_SEED_SCORES = {
    "opening": 100,
    "previous": 95,
    "brought_forward": 95,
    "balance_as_on_in_range": 80,
    "balance_as_on_out_of_range": 0,
}

# Date patterns in seed balance lines (e.g. "Balance as on 17-04-2026")
_SEED_DATE_RE = re.compile(
    r'(\d{1,2}[-/\.](\d{1,2}|[A-Za-z]{3})[-/\.]\d{2,4})'
)

# Statement period extraction (e.g. "01/01/2026 to 31/03/2026" or "From 01-01-2026 To 31-03-2026")
_STMT_PERIOD_RE = re.compile(
    r'(?:from|between)?\s*'
    r'(\d{1,2}[-/\.](\d{1,2}|[A-Za-z]{3})[-/\.]\d{2,4})'
    r'\s*(?:to|and|-)\s*'
    r'(\d{1,2}[-/\.](\d{1,2}|[A-Za-z]{3})[-/\.]\d{2,4})',
    re.IGNORECASE,
)

_SKIP_RE = re.compile(
    r'(grand.?total|opening.?balance|closing.?balance'
    r'|total.?debit|total.?credit|registered.?office'
    r'|statement.?period|account.?no|customer\.?\s*$'
    r'|page\s+\d+\s+of\s+\d+)',
    re.IGNORECASE,
)

_FOOTER_PATTERNS = [
    r"computer generated statement",
    r"does not require a signature",
    r"end of statement",
    r"^\*{3,}",
    r"^=+$"
]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _all_amounts(text: str) -> List[float]:
    """All decimal numbers in the line, left-to-right, sanity-capped."""
    result = []
    for raw in _AMOUNT_RE.findall(text):
        try:
            v = float(raw.replace(',', ''))
            if v <= 1_00_00_000:
                result.append(v)
        except ValueError:
            pass
    return result


def _is_footer_line(line: str) -> bool:
    line_lower = line.lower().strip()
    for pattern in _FOOTER_PATTERNS:
        if re.search(pattern, line_lower):
            return True
    return False


def _parse_seed_date(date_str: str) -> Optional[Any]:
    """Parse a date string from various formats into a datetime.date object."""
    import datetime
    date_str = date_str.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
                "%d-%m-%y", "%d/%m/%y", "%d.%m.%y",
                "%d-%b-%Y", "%d/%b/%Y"):
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None


def _extract_statement_period(full_text: str):
    """Extract the statement start/end dates from header text.
    Returns (start_date, end_date) as datetime.date objects, or (None, None).
    """
    import datetime
    for m in _STMT_PERIOD_RE.finditer(full_text):
        start = _parse_seed_date(m.group(1))
        end   = _parse_seed_date(m.group(3))
        if start and end and start <= end:
            return start, end
    return None, None


def _pick_best_seed(
    candidates: List[Dict],
    stmt_start,
    stmt_end,
) -> Tuple[Optional[float], Dict]:
    """
    Score each seed candidate and pick the highest-scoring valid one.

    Returns (seed_balance, telemetry_dict).
    """
    import datetime
    best_score = -1
    best_value = None
    best_meta  = {}

    for c in candidates:
        score  = c["score"]
        value  = c["value"]
        source = c["source"]
        date   = c.get("date")  # datetime.date or None

        # Date-validate "balance as on" type candidates
        if source == "balance_as_on" and date is not None:
            if stmt_start and stmt_end:
                if date < stmt_start or date > stmt_end:
                    # Out-of-range: reject
                    c["rejected"] = True
                    c["reject_reason"] = f"balance_date {date} outside statement period [{stmt_start}, {stmt_end}]"
                    score = 0
                else:
                    score = _SEED_SCORES["balance_as_on_in_range"]
                    c["rejected"] = False
            else:
                # No statement period known: be conservative, accept with low score
                score = 50
                c["rejected"] = False
        else:
            c["rejected"] = False

        c["final_score"] = score
        if score > best_score:
            best_score = score
            best_value = value
            best_meta  = c

    telemetry = {
        "seed_source":       best_meta.get("source"),
        "seed_date":         str(best_meta.get("date")) if best_meta.get("date") else None,
        "seed_score":        best_meta.get("final_score"),
        "seed_rejected":     best_meta.get("rejected", False),
        "seed_reject_reason": best_meta.get("reject_reason"),
        "seed_candidates":   len(candidates),
    }

    if best_score <= 0:
        return None, telemetry  # All candidates rejected — run seedless

    return best_value, telemetry


def _preprocess_text(full_text: str) -> str:
    """
    Handle OCR output where the entire statement is mashed onto one or a few
    very long lines (common with DocScanner / mobile OCR apps).

    Only splits a long line if at least one of the resulting segments looks
    like a real transaction row (contains a decimal amount). This prevents
    header blobs (account summary, branch info) from being fractured into
    phantom candidate rows that inflate missing_ratio.
    """
    # Fix OCR mangling where commas are misread as periods in numbers (e.g. 728.662.39 -> 728,662.39)
    def _fix_mangled_commas(match):
        parts = match.group(0).split('.')
        return ','.join(parts[:-1]) + '.' + parts[-1]
    
    full_text = re.sub(r'\b\d{1,3}(?:\.\d{3})+\.\d{2}\b', _fix_mangled_commas, full_text)

    out_lines = []
    for line in full_text.splitlines():
        date_matches = list(DATE_RE.finditer(line))
        if len(line) > 200 and len(date_matches) >= 2:
            # Build candidate segments
            segments = []
            prev_end = 0
            for m in date_matches:
                if m.start() > prev_end:
                    head = line[prev_end:m.start()].strip()
                    if head:
                        segments.append(head)
                prev_end = m.start()
            segments.append(line[prev_end:].strip())
            segments = [s for s in segments if s]

            # Only split if at least one segment looks like a transaction row
            # (i.e. it starts with a date AND contains a decimal amount)
            has_txn_segment = any(
                DATE_RE.match(seg) and bool(_AMOUNT_RE.search(seg))
                for seg in segments
            )
            if has_txn_segment:
                out_lines.extend(segments)
            else:
                # Header blob — leave it intact so SKIP_RE can discard it
                out_lines.append(line)
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _extract_summary(full_text: str) -> Dict[str, Any]:
    summary = {
        "summary_found": False,
        "dr_count": None,
        "cr_count": None,
        "total_debit": None,
        "total_credit": None,
        "closing_balance": None
    }
    
    dr_c_match = re.search(r'(dr\s*count|debit\s*count|no\.?\s*of\s*debits)[^\d]*(\d+)', full_text, re.IGNORECASE)
    if dr_c_match:
        summary["dr_count"] = int(dr_c_match.group(2))
        summary["summary_found"] = True
        
    cr_c_match = re.search(r'(cr\s*count|credit\s*count|no\.?\s*of\s*credits)[^\d]*(\d+)', full_text, re.IGNORECASE)
    if cr_c_match:
        summary["cr_count"] = int(cr_c_match.group(2))
        summary["summary_found"] = True
        
    tot_dr_match = re.search(r'total\s+debit[^\d]*([\d,]+\.\d{2})', full_text, re.IGNORECASE)
    if tot_dr_match:
        summary["total_debit"] = float(tot_dr_match.group(1).replace(',', ''))
        summary["summary_found"] = True

    tot_cr_match = re.search(r'total\s+credit[^\d]*([\d,]+\.\d{2})', full_text, re.IGNORECASE)
    if tot_cr_match:
        summary["total_credit"] = float(tot_cr_match.group(1).replace(',', ''))
        summary["summary_found"] = True
        
    return summary


def _get_row_signature(date_str: str, balance: Optional[float], num_len: int, narration: str) -> str:
    norm_narr = re.sub(r'\s+', '', narration)[:50].lower()
    h = hashlib.md5(norm_narr.encode('utf-8')).hexdigest()[:8]
    return f"{date_str}_{balance}_{num_len}_{h}"


# ---------------------------------------------------------------------------
# PHASE 1 — RAW ROW EXTRACTION
# ---------------------------------------------------------------------------

def _extract_raw_rows(lines: List[str], stmt_start=None, stmt_end=None) -> Tuple[List[Dict], Optional[float], int, Dict[str, int], List[Dict], List[Dict]]:
    rows: List[Dict] = []
    block: List[str] = []
    seed_candidates: List[Dict] = []
    candidate_dates = 0
    page_candidate_rows: Dict[str, int] = {}
    current_page = "1"
    all_candidate_rows: List[Dict] = []
    
    last_seen_date = None
    block_class = {}

    def flush():
        if not block:
            return
        raw = " ".join(l.strip() for l in block)
        dm  = DATE_RE.search(raw)
        if not dm:
            block.clear()
            return
        raw_no_dates = DATE_RE.sub(lambda m: " " * len(m.group(0)), raw)
        nums = []
        nums_x = []
        for m in _AMOUNT_RE.finditer(raw_no_dates):
            try:
                v = float(m.group(0).replace(',', ''))
                if v <= 1_00_00_000:
                    nums.append(v)
                    nums_x.append(m.start())
            except ValueError:
                pass
        
        if not nums:
            block.clear()
            block_class.clear()  # Fix 1: always reset state
            return
        narration = raw.replace(dm.group(0), "", 1)
        narration = _AMOUNT_RE.sub("", narration)
        narration = re.sub(r'\s+', ' ', narration).strip()
        
        # Fix 2: Reject rows that were classified as new_transaction but ended up
        # with no narration — this means the classifier fired on a numeric-only line.
        if not narration and block_class.get("line_type") == "new_transaction":
            block.clear()
            block_class.clear()
            return
        
        rows.append({
            "date":      dm.group(0),
            "narration": narration,
            "numbers":   nums,
            "nums_x":    nums_x,
            "page":      current_page,
            "raw_narration": raw,
            "raw_numbers_len": len(nums),
            "source_lines": list(block),
            "row_build_strategy": "single_line" if len(block) == 1 else "multiline_merge",
            "continuation_classification": dict(block_class) if block_class else None
        })
        block.clear()
        block_class.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
            
        if _is_footer_line(stripped):
            flush()
            continue
            
        page_match = re.match(r'^PAGE\s+(\d+)$', stripped)
        if page_match:
            # CRITICAL: flush before advancing the page so rows spanning a
            # page boundary (last row of page N) are not silently discarded.
            flush()
            current_page = page_match.group(1)
            continue
            
        has_date = bool(DATE_RE.search(stripped))
        has_nums = bool(_AMOUNT_RE.search(stripped))

        if re.search(r'\b(opening|prev(ious)?|brought.?forward|b/?f|balance as on)\b', stripped, re.IGNORECASE):
            nums = _all_amounts(stripped)
            if nums:
                if re.search(r'\b(opening)\b', stripped, re.IGNORECASE):
                    source, score = "opening", _SEED_SCORES["opening"]
                elif re.search(r'\b(prev(ious)?|brought.?forward|b/?f)\b', stripped, re.IGNORECASE):
                    source, score = "brought_forward", _SEED_SCORES["brought_forward"]
                else:
                    source, score = "balance_as_on", _SEED_SCORES["balance_as_on_out_of_range"]
                dm = _SEED_DATE_RE.search(stripped)
                seed_date = _parse_seed_date(dm.group(1)) if dm else None
                seed_candidates.append({
                    "source": source,
                    "score":  score,
                    "value":  nums[-1],
                    "date":   seed_date,
                    "line":   stripped,
                })
            flush()
            continue
            
        if _SKIP_RE.search(stripped):
            flush()
            continue

        if has_date:
            last_seen_date = DATE_RE.search(stripped).group(0)

        is_new_txn = False
        reason = None
        if not has_date and block:
            if re.match(r'^(UPI/CR/|UPI/DR/|IMPS/|NEFT/|RTGS/|AEPS/|ATM/|POS/|WDL\s+TFR\s+UP/DR/)', stripped, re.IGNORECASE):
                # Fix 3: require meaningful non-numeric text — prevents numeric-only
                # lines (e.g. "  -  100.00") from being misclassified as new transactions.
                text_only = re.sub(r'[\d,\.\-\s/]', '', stripped)
                if len(text_only) > 3 and re.search(r'\d{6,}', stripped) and re.search(r'\b(UPI|SBIN|YESB|HDFC|UTIB|BKID|MAHB|FDRL|paytm|okaxis|ybl|apl)\b', stripped, re.IGNORECASE):
                    is_new_txn = True
                    reason = "matched_upi_pattern"

        if is_new_txn:
            flush()
            if last_seen_date:
                block.append(f"{last_seen_date} {line}")
            else:
                block.append(line)
            # Fix 1: block_class was already cleared by flush(); set fresh state.
            block_class.update({"line_type": "new_transaction", "reason": reason})
        elif has_date and has_nums:
            flush()
            # Fix 1: reset block_class explicitly when starting any new non-classified block.
            block_class.clear()
            block.append(line)
        elif block:
            block.append(line)

    flush()

    _HEADER_NARR_RE = re.compile(
        r'\b(debit|credit|balance|withdrawal|deposit|particulars|narration'
        r'|description|transaction|cheque|reference|amount)\b',
        re.IGNORECASE,
    )

    def _is_junk_row(row: Dict) -> bool:
        if len(row["numbers"]) > 8:
            return True
        kw_count = len(_HEADER_NARR_RE.findall(row["narration"]))
        if kw_count >= 3:
            return True
        return False

    clean_rows = [r for r in rows if not _is_junk_row(r)]

    # Build candidate counts from the clean parsed rows (not raw OCR line scan).
    # Using clean_rows prevents header/footer fragments from inflating the count.
    page_candidate_rows = {}
    all_candidate_rows = []
    for r in clean_rows:
        pg = r["page"]
        page_candidate_rows[pg] = page_candidate_rows.get(pg, 0) + 1
        all_candidate_rows.append(r)

    return clean_rows, seed_candidates, candidate_dates, page_candidate_rows, all_candidate_rows


# ---------------------------------------------------------------------------
# PHASE 2 — BALANCE-DELTA SOLVER
# ---------------------------------------------------------------------------

def _score_balance_col(
    rows: List[Dict],
    b: int,
    seed_balance: Optional[float] = None,
) -> Tuple[float, List[Dict]]:
    txns: List[Dict] = []
    hits = 0
    prev_bal: Optional[float] = seed_balance

    for i, row in enumerate(rows):
        nums = row["numbers"]
        if b >= len(nums):
            continue

        balance  = nums[b]
        non_bal  = [v for j, v in enumerate(nums) if j != b]

        if prev_bal is None:
            prev_bal = balance
            # For first row, we don't have a delta. We just record the OCR amount if there's exactly one.
            ocr_amt = non_bal[0] if len(non_bal) == 1 else None
            ocr_x = -1
            if ocr_amt is not None:
                for idx, val in enumerate(nums):
                    if idx != b and val == ocr_amt:
                        nx = row.get("nums_x", [])
                        if idx < len(nx): ocr_x = nx[idx]
                        break
            
            txns.append({
                "date": row["date"], "narration": row["narration"],
                "debit": None, "credit": None, "balance": balance, "page": row["page"],
                "raw_narration": row["raw_narration"], "raw_numbers_len": row["raw_numbers_len"],
                "ocr_amount": ocr_amt, "ocr_x": ocr_x, "delta_amount": None, "amount_conflict": False,
                "source_lines": row.get("source_lines", []),
                "row_build_strategy": row.get("row_build_strategy", "unknown"),
                "continuation_classification": row.get("continuation_classification")
            })
            continue

        delta     = round(balance - prev_bal, 2)
        abs_delta = abs(delta)
        prev_bal  = balance

        debit  = None
        credit = None

        # Always try to find the matching amount first.
        best, best_diff = None, float('inf')
        for v in non_bal:
            diff = abs(v - abs_delta)
            if diff < best_diff:
                best, best_diff = v, diff

        ocr_amount = best if best is not None else (non_bal[0] if len(non_bal) == 1 else None)
        delta_amount = abs_delta
        amount_conflict = False

        if best is not None and best_diff <= _TOLERANCE:
            # Good match — OCR and math agree, assign the physical amount
            hits += 1
            if delta > 0:
                credit = best
            else:
                debit  = best
        elif abs_delta <= _ROUNDING_GAP:
            # Delta is tiny, no amount matched → genuine rounding artifact
            hits += 1
        else:
            # Conflict: delta and OCR disagree. NEVER null out known printed evidence.
            # Assign the physical OCR amount (use delta direction to determine DR/CR),
            # flag the conflict so the auditor can review both values later.
            amount_conflict = True
            if ocr_amount is not None:
                if delta > 0:
                    credit = ocr_amount
                else:
                    debit = ocr_amount

        ocr_x = -1
        if ocr_amount is not None:
            for idx, val in enumerate(nums):
                if idx != b and val == ocr_amount:
                    nx = row.get("nums_x", [])
                    if idx < len(nx): ocr_x = nx[idx]
                    break

        txns.append({
            "date": row["date"], "narration": row["narration"],
            "debit": debit, "credit": credit, "balance": balance, "page": row["page"],
            "raw_narration": row["raw_narration"], "raw_numbers_len": row["raw_numbers_len"],
            "ocr_amount": ocr_amount, "ocr_x": ocr_x, "delta_amount": delta_amount, "amount_conflict": amount_conflict,
            "source_lines": row.get("source_lines", []),
            "row_build_strategy": row.get("row_build_strategy", "unknown"),
            "continuation_classification": row.get("continuation_classification")
        })

    checks = max(1, len(txns) - 1)
    score  = hits / checks
    return score, txns


def _solve(
    rows: List[Dict],
    seed_balance: Optional[float] = None,
) -> Tuple[List[Dict], float, int]:
    if not rows:
        return [], 0.0, -1

    max_n   = max(len(r["numbers"]) for r in rows)
    best_score, best_txns, best_b = -1.0, [], -1

    for b in range(max_n):
        score, txns = _score_balance_col(rows, b, seed_balance)
        hint = 0.03 if b == max_n - 1 else 0.0
        total = score * 0.97 + hint * 0.03
        if total > best_score:
            best_score, best_txns, best_b = total, txns, b

    return best_txns, best_score, best_b


# ---------------------------------------------------------------------------
# PHASE 3 — RECOVERY ENGINE
# ---------------------------------------------------------------------------

def _recover_missing_rows(
    all_candidate_rows: List[Dict], 
    txns: List[Dict], 
    best_b: int, 
    seed_bal: Optional[float], 
    telemetry: Dict
) -> List[Dict]:
    missing_ratio = telemetry.get("missing_ratio", 0.0)
    missing_rows_count = telemetry.get("candidate_transaction_rows", 0) - telemetry.get("extracted_transactions", 0)

    telemetry["recovery_attempted"] = False
    telemetry["recovery_succeeded"] = 0
    telemetry["recovery_failed"] = 0

    if missing_rows_count <= 0 or best_b < 0:
        return txns

    if missing_ratio > 0.20 or missing_rows_count > 5:
        return txns

    telemetry["recovery_attempted"] = True

    extracted_sigs = set()
    for t in txns:
        if "raw_numbers_len" in t and "raw_narration" in t:
            sig = _get_row_signature(t["date"], t["balance"], t["raw_numbers_len"], t["raw_narration"])
            extracted_sigs.add(sig)

    missing_raw_rows = []
    for crow in all_candidate_rows:
        if best_b < len(crow["numbers"]):
            candidate_balance = crow["numbers"][best_b]
            sig = _get_row_signature(crow["date"], candidate_balance, crow["raw_numbers_len"], crow["raw_narration"])
            if sig not in extracted_sigs:
                missing_raw_rows.append(crow)

    if not missing_raw_rows:
        return txns

    recovered = []
    for mrow in missing_raw_rows:
        candidate_balance = mrow["numbers"][best_b]
        non_bal = [v for j, v in enumerate(mrow["numbers"]) if j != best_b]
        
        best_confidence = -1.0
        best_recovered_t = None
        best_insert_idx = -1
        
        for i in range(len(txns) + 1):
            prev_bal = txns[i-1]["balance"] if i > 0 else seed_bal
            next_bal = txns[i]["balance"] if i < len(txns) else None
            
            if prev_bal is None:
                continue
                
            delta = round(candidate_balance - prev_bal, 2)
            abs_delta = abs(delta)
            
            delta_match = False
            best_val = None
            for v in non_bal:
                if abs(v - abs_delta) <= _TOLERANCE:
                    delta_match = True
                    best_val = v
                    break
                    
            if not delta_match:
                continue
                
            conf = 0.0
            if delta_match: conf += 0.4
            if len(non_bal) == 1: conf += 0.3
            
            if next_bal is not None:
                next_delta = round(next_bal - candidate_balance, 2)
                next_t = txns[i]
                actual_next_val = next_t["credit"] if next_t["credit"] else next_t["debit"]
                if actual_next_val and abs(abs(next_delta) - actual_next_val) <= _TOLERANCE:
                    conf += 0.2
            elif i == len(txns):
                conf += 0.2
                
            conf += 0.1
            
            if conf > best_confidence:
                best_confidence = conf
                debit = best_val if delta < 0 else None
                credit = best_val if delta > 0 else None
                best_recovered_t = {
                    "date": mrow["date"], "narration": mrow["narration"],
                    "debit": debit, "credit": credit, "balance": candidate_balance, "page": mrow["page"],
                    "raw_numbers_len": mrow["raw_numbers_len"], "raw_narration": mrow["raw_narration"],
                    "recovered": True, "recovery_confidence": best_confidence
                }
                best_insert_idx = i

        if best_confidence >= 0.7 and best_recovered_t:
            recovered.append((best_insert_idx, best_recovered_t, best_confidence))
            telemetry["recovery_succeeded"] += 1
        else:
            telemetry["recovery_failed"] += 1

    recovered.sort(key=lambda x: x[0], reverse=True)
    for idx, t, conf in recovered:
        txns.insert(idx, t)

    return txns


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def parse_deterministic_transactions(full_text: str):
    preprocessed = _preprocess_text(full_text)
    lines = preprocessed.splitlines()

    # Extract statement period BEFORE row extraction so we can validate seed dates
    stmt_start, stmt_end = _extract_statement_period(preprocessed)

    raw_rows, seed_candidates, candidate_dates, page_candidate_rows, all_candidate_rows = _extract_raw_rows(
        lines, stmt_start=stmt_start, stmt_end=stmt_end
    )

    seed_bal, seed_telemetry = _pick_best_seed(seed_candidates, stmt_start, stmt_end)

    if seed_bal is not None:
        logger.info("BalanceSolver: seeded opening balance = %.2f  [source=%s]",
                    seed_bal, seed_telemetry.get("seed_source", "?"))
    else:
        logger.info("BalanceSolver: no valid seed found — running seedless")
        
    global_candidate_rows = sum(page_candidate_rows.values())
    
    telemetry = {
        "header_candidates": ["Balance-Delta Solver (No Headers Used)"],
        "chosen_header": "N/A",
        "zones": {},
        "rows_detected": global_candidate_rows,
        "rows_accepted": 0,
        "rows_rejected": 0,
        "reject_reasons": {},
        "abort_reason": None,
        
        "candidate_transaction_rows": global_candidate_rows,
        "extracted_transactions": 0,
        "missing_ratio": 1.0,
        "rows_with_balance": 0,
        "balance_coverage": 0.0,
        "page_candidate_rows": page_candidate_rows,
        "page_extracted_rows": {},
        "page_extraction_failure": False,
        "summary_found": False,
        "summary_match": True,
        "status": "FAIL",
        "hard_failure": None,
        "recovered_transactions": 0, "recovered_amount_total": 0.0,
        "rejected_rows": 0, "reconciliation_score": 0.0,
        "recovery_attempted": False, "recovery_succeeded": 0, "recovery_failed": 0,
        # Seed balance provenance telemetry
        "statement_start": str(stmt_start) if stmt_start else None,
        "statement_end":   str(stmt_end)   if stmt_end   else None,
        **seed_telemetry,
    }
        
    if not raw_rows:
        logger.warning("Deterministic Parser: no rows extracted.")
        telemetry["hard_failure"] = "NO_ROWS_EXTRACTED"
        return [], telemetry

    txns, score, best_b = _solve(raw_rows, seed_bal)
    bal_col = best_b

    # ---------------------------------------------------------
    # COLUMN MEMORY ENGINE (Second-pass repair)
    # ---------------------------------------------------------
    debit_x_clusters = []
    credit_x_clusters = []
    
    for t in txns:
        ox = t.get("ocr_x", -1)
        if ox >= 0 and not t.get("amount_conflict"):
            if t.get("debit") is not None:
                debit_x_clusters.append(ox)
            elif t.get("credit") is not None:
                credit_x_clusters.append(ox)
                
    def _is_in_cluster(x: int, cluster: List[int], tolerance: int = 15) -> bool:
        if not cluster: return False
        avg = sum(cluster) / len(cluster)
        return abs(x - avg) <= tolerance

    for t in txns:
        if t.get("debit") is None and t.get("credit") is None and t.get("ocr_amount") is not None:
            ox = t.get("ocr_x", -1)
            resolved = False
            if ox >= 0:
                is_debit = _is_in_cluster(ox, debit_x_clusters)
                is_credit = _is_in_cluster(ox, credit_x_clusters)
                
                if is_debit and not is_credit:
                    t["debit"] = t["ocr_amount"]
                    resolved = True
                elif is_credit and not is_debit:
                    t["credit"] = t["ocr_amount"]
                    resolved = True
            
            # Semantic Fallback Engine if layout was inconclusive
            if not resolved:
                narr = t.get("narration", "").lower()
                if re.search(r'\b(dr|debit|ach/dr|upi/dr|sent|paid)\b', narr):
                    t["debit"] = t["ocr_amount"]
                elif re.search(r'\b(cr|credit|ach/cr|upi/cr|received|refund|reversal)\b', narr):
                    t["credit"] = t["ocr_amount"]

    # ---------------------------------------------------------
    # NARRATION PROVENANCE LAYER (Completeness Score)
    # ---------------------------------------------------------
    def _contains_text(line: str) -> bool:
        l = DATE_RE.sub("", line)
        l = _AMOUNT_RE.sub("", l)
        return len(re.sub(r'\s+', '', l)) > 2

    for t in txns:
        c_score = 100
        narr = t.get("narration") or ""
        narr = narr.strip()
        
        if len(narr) < 15 or narr == t["date"]:
            has_text = any(_contains_text(l) for l in t.get("source_lines", []))
            
            if not has_text and (t.get("debit") is not None or t.get("credit") is not None) and t.get("balance") is not None:
                t["narration"] = None
                t["source_description_present"] = False
                t["root_cause"] = "source_statement_blank"
            else:
                c_score -= 40
                t["root_cause"] = "row_reconstruction_loss" if has_text else "ocr_loss"
            
        if t.get("ocr_amount") is None and (t.get("debit") is not None or t.get("credit") is not None):
            c_score -= 20 # amount inferred from balance math
            
        if t.get("balance") is None:
            c_score -= 20 # balance inferred
            
        t["completeness_score"] = c_score
        t["needs_review"] = c_score < 100

    # First row opening balance recovery and diagnostic telemetry
    recovered_count = 0
    recovered_total = 0.0
    if txns and seed_bal is not None and txns[0].get("balance") is not None:
        t = txns[0]
        
        # Diagnostic Telemetry for Bad Opening Balances
        if t.get("amount_conflict") and t.get("ocr_amount") is not None:
            implied_seed = t.get("balance") - t.get("ocr_amount") if t.get("delta_amount", 0) < 0 else t.get("balance") + t.get("ocr_amount")
            # The delta is (curr - prev). For DR, delta < 0, so prev = curr - delta.
            # But we don't know if OCR amount is DR or CR just from ocr_amount (it's absolute).
            # We assume it's DR if the raw delta was negative, CR if positive.
            if getattr(t, "delta_amount", 0) > 0:
                 implied_seed = round(t["balance"] - t["ocr_amount"], 2)
            else:
                 implied_seed = round(t["balance"] + t["ocr_amount"], 2)
                 
            telemetry["seed_diagnostic"] = {
                "extracted_seed": seed_bal,
                "first_balance": t["balance"],
                "ocr_amount": t["ocr_amount"],
                "implied_seed": implied_seed,
                "difference": round(abs(seed_bal - implied_seed), 2)
            }
            
            # If the difference is huge, the conflict is likely a Bad Opening Balance extraction,
            # not a legitimate debit/credit mismatch.
            
        if t.get("debit") is None and t.get("credit") is None:
            delta = round(t.get("balance") - seed_bal, 2)
            if delta < -0.01:
                t["debit"] = abs(delta)
                recovered_count += 1
                recovered_total += abs(delta)
            elif delta > 0.01:
                t["credit"] = delta
                recovered_count += 1
                recovered_total += delta
                
    telemetry["recovered_transactions"] = recovered_count
    telemetry["recovered_amount_total"] = round(recovered_total, 2)

    extracted = len(txns)
    if global_candidate_rows > 0:
        telemetry["missing_ratio"] = round((global_candidate_rows - extracted) / global_candidate_rows, 4)
    else:
        telemetry["missing_ratio"] = 0.0
    telemetry["extracted_transactions"] = extracted

    # Run Recovery Engine
    txns = _recover_missing_rows(all_candidate_rows, txns, bal_col, seed_bal, telemetry)

    # Re-calculate telemetry post-recovery
    extracted = len(txns)
    telemetry["extracted_transactions"] = extracted
    telemetry["rejected_rows"] = len(raw_rows) - extracted
    telemetry["reconciliation_score"] = round(score, 4)

    total_debit  = sum(t["debit"]  or 0.0 for t in txns)
    total_credit = sum(t["credit"] or 0.0 for t in txns)

    if global_candidate_rows > 0:
        telemetry["missing_ratio"] = round((global_candidate_rows - extracted) / global_candidate_rows, 4)
    else:
        telemetry["missing_ratio"] = 0.0
        
    page_extracted_rows = {}
    for t in txns:
        p = t.get("page", "1")
        page_extracted_rows[p] = page_extracted_rows.get(p, 0) + 1
    telemetry["page_extracted_rows"] = page_extracted_rows
    
    for p, count in page_candidate_rows.items():
        if count >= 2 and page_extracted_rows.get(p, 0) == 0:
            telemetry["page_extraction_failure"] = True
            break

    rows_with_balance = sum(1 for t in txns if t.get("date") and t.get("balance") is not None)
    telemetry["rows_with_balance"] = rows_with_balance
    if rows_with_balance > 0:
        telemetry["balance_coverage"] = round(extracted / rows_with_balance, 4)
    else:
        telemetry["balance_coverage"] = 0.0

    summary = _extract_summary(full_text)
    if summary["summary_found"]:
        telemetry["summary_found"] = True
        telemetry["summary_match"] = True
        if summary["dr_count"] is not None and summary["dr_count"] > 0 and total_debit == 0.0:
            telemetry["summary_match"] = False
        if summary["cr_count"] is not None and summary["cr_count"] > 0 and total_credit == 0.0:
            telemetry["summary_match"] = False

    hard_fail = False
    if extracted == 0:
        hard_fail = True
        telemetry["hard_failure"] = "ZERO_EXTRACTED_TRANSACTIONS"
    elif total_debit == 0.0 and total_credit == 0.0:
        hard_fail = True
        telemetry["hard_failure"] = "ZERO_DEBIT_AND_CREDIT"
        
    if hard_fail:
        telemetry["status"] = "FAIL"
        telemetry["abort_reason"] = telemetry["hard_failure"]
        telemetry["rows_accepted"] = 0
        telemetry["rows_rejected"] = len(raw_rows)
        if len(raw_rows) > 0:
            telemetry["reject_reasons"] = {"solver_failed": len(raw_rows)}
        logger.error(f"Deterministic Parser HARD FAILURE: {telemetry['hard_failure']}")
        return [], telemetry

    telemetry["rows_accepted"] = extracted
    telemetry["rows_rejected"] = telemetry["rejected_rows"]
    if telemetry["rejected_rows"] > 0:
        telemetry["reject_reasons"] = {"balance_solver_rejection": telemetry["rejected_rows"]}

    # Warning status
    if (0.05 <= telemetry["missing_ratio"] <= 0.15) or \
       (telemetry["missing_ratio"] > 0.15) or \
       (telemetry["balance_coverage"] < 0.50) or \
       (0.50 <= telemetry["balance_coverage"] < 0.70) or \
       (telemetry["page_extraction_failure"]) or \
       (telemetry["summary_found"] and not telemetry["summary_match"]):
        telemetry["status"] = "WARNING"
    else:
        telemetry["status"] = "PASS"

    logger.info(
        "Deterministic Parser: Extracted %d txns | status=%s | missing_ratio=%.3f | rec_succeeded=%d",
        extracted, telemetry["status"], telemetry["missing_ratio"], telemetry["recovery_succeeded"]
    )

    return txns, telemetry
