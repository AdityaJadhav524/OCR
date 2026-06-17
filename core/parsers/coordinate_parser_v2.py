"""
Coordinate Parser V2 — Geometry-First, Accounting-First

A row is accepted ONLY by proving it IS a transaction.
Never by proving it is NOT something else.

Proof requirements (all must hold):
  G1. Date token is physically inside date_zone AND matches date regex.
  G2. Balance token is physically inside balance_zone AND is a positive number.
  G3. Exactly one of debit/credit is populated (never both, never neither).
  G4. Amount token is physically inside its declared zone (debit_zone or credit_zone).
  A1. Conservation: |prev_balance + credit - debit - current_balance| < TOLERANCE.

Conservation states (P2):
  PASS     → conservation check passes
  FAIL     → conservation check fails (known prev_balance, math doesn't hold)
  UNSEEDED → prev_balance unknown (page boundary, first row) → ACCEPT anyway

Page-level balance seeding (P3):
  Opening/closing balances extracted per page and used to seed prev_balance
  at the start of each page, eliminating page-boundary rejects.

Keyword blacklists are a secondary last-resort backstop only.
They do not drive acceptance or rejection of rows.
"""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.validators.ledger_truth import annotate_ledger_truth
from core.validators.financial_audit import _parse_float
from core.validators.ocr_signature_detector import detect_ocr_signatures

logger = logging.getLogger("core.parsers.coordinate_parser_v2")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONSERVATION_TOLERANCE = 1.50   # ₹1.50 rounding tolerance per row
MAX_REASONABLE_AMOUNT  = 50_000_000.0  # ₹5 crore per single transaction

# Conservation states (P2)
CONSERVATION_PASS     = "PASS"
CONSERVATION_FAIL     = "FAIL"
CONSERVATION_UNSEEDED = "UNSEEDED"

_DATE_RE = re.compile(
    r'^\s*('
    r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|'
    r'\d{2,4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|'
    r'\d{1,2}[\s\-][A-Za-z]{3,9}[\s\-]\d{2,4}'
    r')\s*$',
    re.IGNORECASE
)

# Prefix variant — used when a PDF token concatenates the date with the narration
# (e.g. "07/02/22UPI-HARPREET SINGH-").  The \D lookahead ensures the date is
# followed by a non-digit character so we don't accidentally clip a 4-digit year
# off a reference number like "20221234".
_DATE_PREFIX_RE = re.compile(
    r'^(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\D',
    re.IGNORECASE
)

# Page-level balance hints: labels that precede opening/closing balance values
_PAGE_BALANCE_RE = re.compile(
    r'\b(opening\s+balance|closing\s+balance|balance\s+b/?f|balance\s+c/?f|'
    r'brought\s+forward|carried?\s+forward|balance\s+b\.?f\.?|balance\s+c\.?f\.?)\b',
    re.IGNORECASE
)

# Secondary backstop: known structural labels that should never be transactions.
# These are last-resort guards only — geometry + accounting should catch them first.
_STRUCTURAL_LABELS = re.compile(
    r'\b(closing|opening|brought\s+forward|carried?\s+forward|balance\s+b/?f|'
    r'balance\s+c/?f|grand\s+total|page\s+total|total\s+debit|total\s+credit|'
    r'statement\s+of\s+account|end\s+of\s+statement)\b',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Geometry proofs
# ---------------------------------------------------------------------------

def _in_zone(x: float, zone: Optional[List[float]]) -> bool:
    """True when x physically lies inside [zone[0], zone[1]]."""
    return zone is not None and zone[0] <= x <= zone[1]


def _prove_date(token: Dict, date_zone: List[float]) -> Optional[str]:
    """
    G1: token must be inside date_zone AND match date pattern.
    Returns the date string on success, None on failure.

    Fallback: some PDFs (e.g. YES Bank) concatenate the date and narration
    into a single OCR token with no separator, e.g.:
        "07/02/22UPI-HARPREET SINGH-"
    In that case, extract just the date prefix.
    This is safe because:
      - Token must already be physically inside date_zone
      - Date must be at position 0 of the token
      - No amount or balance tokens are affected
    """
    if not _in_zone(token["x0"], date_zone):
        return None
    text = token.get("text", "").strip()
    if _DATE_RE.match(text):
        return text
    # Fallback: date prefix in a concatenated date+narration token
    prefix_match = _DATE_PREFIX_RE.match(text)
    if prefix_match:
        logger.debug(
            f"V2 date_prefix extracted {prefix_match.group(1)!r} "
            f"from concatenated token {text[:30]!r}"
        )
        return prefix_match.group(1)
    return None


def _prove_amount(token: Dict, zone: List[float]) -> Optional[float]:
    """
    G4: token must be physically inside its zone.
    Returns parsed float (> 0 and <= MAX_REASONABLE_AMOUNT) on success, else None.
    """
    if not _in_zone(token["x0"], zone):
        return None
        
    text = token.get("text", "")
    # Reject dates bleeding into amount zones
    if '/' in text or '\\' in text:
        return None
        
    # Reject long numeric strings without a decimal point (likely reference numbers)
    if sum(c.isdigit() for c in text) > 8 and '.' not in text:
        return None
        
    val = _parse_float(text)
    if val is None or val <= 0 or val > MAX_REASONABLE_AMOUNT:
        return None
    return val


def _prove_balance(token: Dict, balance_zone: List[float]) -> Optional[float]:
    """
    G2: balance token must be inside balance_zone and be a non-negative number.
    """
    if not _in_zone(token["x0"], balance_zone):
        return None
    val = _parse_float(token.get("text", ""))
    if val is None or val < 0:
        return None
    return val


# ---------------------------------------------------------------------------
# Page-level balance seeding (P3)
# ---------------------------------------------------------------------------

def _extract_page_balance_seeds(rows: List[Dict]) -> Dict[int, float]:
    """
    P3: Scan all rows for opening/closing balance labels.
    Returns {page_number: seed_balance} where seed_balance is the
    closing balance of the previous page (= opening balance of this page).

    Strategy: find rows containing a page-balance label followed by
    a numeric value on the same row. The value is the seed for the
    next page boundary.
    """
    seeds: Dict[int, float] = {}

    for row in rows:
        page = row.get("page", 0)
        tokens = row.get("tokens", [])
        row_text = " ".join(t.get("text", "") for t in tokens)

        # Check if this row contains a page-level balance label
        if not _PAGE_BALANCE_RE.search(row_text):
            continue

        # Find the rightmost numeric token on this row (likely the balance value)
        balance_val: Optional[float] = None
        for tok in reversed(tokens):
            v = _parse_float(tok.get("text", ""))
            if v is not None and v > 0:
                balance_val = v
                break

        if balance_val is None:
            continue

        label_lower = row_text.lower()
        is_closing = any(kw in label_lower for kw in [
            "closing", "carried", "c/f", "c.f", "balance c"
        ])
        is_opening = any(kw in label_lower for kw in [
            "opening", "brought", "b/f", "b.f", "balance b"
        ])

        if is_closing:
            # Closing balance of page N → seed for page N+1
            seeds[page + 1] = balance_val
            logger.debug(f"PageSeed: page {page} closing={balance_val} → seeds page {page+1}")
        elif is_opening:
            # Opening balance of page N → seed for page N
            if page not in seeds:
                seeds[page] = balance_val
                logger.debug(f"PageSeed: page {page} opening={balance_val}")

    return seeds


# ---------------------------------------------------------------------------
# Accounting proof (P1 + P2)
# ---------------------------------------------------------------------------

def _prove_conservation(
    prev_balance: Optional[float],
    credit: float,
    debit: float,
    current_balance: float,
) -> Tuple[str, float]:
    """
    A1: prev_balance + credit - debit ≈ current_balance.

    Returns (state, residual) where state is one of:
        CONSERVATION_PASS     — math checks out
        CONSERVATION_FAIL     — prev_balance known but math fails
        CONSERVATION_UNSEEDED — prev_balance unknown (page boundary)
    """
    if prev_balance is None or current_balance is None:
        return CONSERVATION_UNSEEDED, 0.0

    expected = prev_balance + credit - debit
    residual = abs(expected - current_balance)
    if residual <= CONSERVATION_TOLERANCE:
        return CONSERVATION_PASS, residual
    return CONSERVATION_FAIL, residual


# ---------------------------------------------------------------------------
# Block extraction — Token Ownership Model
# ---------------------------------------------------------------------------

def _extract_block(
    block: List[Dict],
    zones: Dict[str, List[float]],
) -> Optional[Dict]:
    """
    Token Ownership Extraction.

    Every token in the block is claimed by exactly one role:
        DATE | BALANCE | DEBIT | CREDIT | NARRATION

    Narration = ALL tokens NOT claimed by the four structural roles.
    No narration zone clipping — narration is the remainder after structural
    tokens are removed. This guarantees completeness regardless of how
    accurately the narration column boundary was detected.

    Token loss validation:
        total_tokens == claimed_count + narr_count  (must always hold)
    """
    date_zone    = zones.get("date_zone")
    debit_zone   = zones.get("debit_zone")
    credit_zone  = zones.get("credit_zone")
    balance_zone = zones.get("balance_zone")

    # Page number of this block (from the first row's page field)
    page_num = block[0].get("page", 0) if block else 0

    # Collect every non-empty token from the block
    all_tokens: List[Dict] = []
    block_text_parts: List[str] = []
    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")

    for row in block:
        for tok in row.get("tokens", []):
            text = tok.get("text", "").strip()
            if not text:
                continue
            all_tokens.append(tok)
            block_text_parts.append(text.lower())
            
            # Update bounding box
            if tok.get("x0") is not None and tok["x0"] < min_x: min_x = tok["x0"]
            if tok.get("y0") is not None and tok["y0"] < min_y: min_y = tok["y0"]
            if tok.get("x1") is not None and tok["x1"] > max_x: max_x = tok["x1"]
            if tok.get("y1") is not None and tok["y1"] > max_y: max_y = tok["y1"]
            
    source_bbox = [min_x, min_y, max_x, max_y] if min_x != float("inf") else []

    date    = None
    debit   = None
    credit  = None
    balance = None
    ocr_amount = None
    ocr_x = None
    assigned_column = None
    # Raw OCR text strings — captured at claim time, never modified after
    _raw_debit_text   = None
    _raw_credit_text  = None
    _raw_balance_text = None
    claimed: set = set()   # indices into all_tokens

    # --- Pass 1: Claim structural roles in priority order ---
    # Priority: DATE > BALANCE > DEBIT > CREDIT
    # (Balance before amounts avoids mis-claiming balance tokens as credit/debit)
    for idx, tok in enumerate(all_tokens):
        # G1: Date
        if date is None and date_zone:
            d = _prove_date(tok, date_zone)
            if d:
                date = d
                claimed.add(idx)
                continue

        # G2: Balance — FIRST valid balance wins.
        # The real transaction balance is always in the anchor row (first row of block).
        # Footer/header tokens appended to the block come later and must NOT override it.
        # "Last wins" caused SBI page-number tokens ("3 of 4") to replace real balance.
        if balance is None and balance_zone:
            b = _prove_balance(tok, balance_zone)
            if b is not None:
                balance = b
                _raw_balance_text = tok.get("text", "").strip()
                claimed.add(idx)
                continue

        # G4: Debit — FIRST valid debit wins.
        if debit is None and debit_zone:
            v = _prove_amount(tok, debit_zone)
            if v is not None:
                debit = v
                ocr_amount = v
                ocr_x = tok.get("x0")
                assigned_column = "debit"
                _raw_debit_text = tok.get("text", "").strip()
                claimed.add(idx)
                continue

        # G4: Credit — FIRST valid credit wins.
        if credit is None and credit_zone:
            v = _prove_amount(tok, credit_zone)
            if v is not None:
                credit = v
                ocr_amount = v
                ocr_x = tok.get("x0")
                assigned_column = "credit"
                _raw_credit_text = tok.get("text", "").strip()
                claimed.add(idx)
                continue

    # --- Pass 2: All unclaimed tokens → narration (sorted left-to-right) ---
    narration_tokens = sorted(
        (all_tokens[i] for i in range(len(all_tokens)) if i not in claimed),
        key=lambda t: t.get("x0", 0)
    )

    # Drop bare standalone numbers that escaped zone proof (stray amounts)
    narr_words = [
        t["text"].strip() for t in narration_tokens
        if not re.fullmatch(r'[\d,\.]+', t["text"].strip())
    ]
    narration = " ".join(narr_words).strip() or None

    # Token loss accounting (should always be 0)
    narr_count = len(narration_tokens)
    lost = len(all_tokens) - len(claimed) - narr_count
    if lost != 0:
        logger.warning(
            f"V2 token_loss_detected: total={len(all_tokens)} "
            f"claimed={len(claimed)} narr={narr_count} lost={lost}"
        )

    # Generate anchor row text for structural label check
    anchor_tokens = block[0].get("tokens", []) if block else []
    anchor_text = " ".join([t.get("text", "") for t in anchor_tokens]).lower()

    # raw_extraction — write-once, created here, never modified by any downstream layer
    raw_extraction = {
        "ocr_debit_text":   _raw_debit_text,
        "ocr_credit_text":  _raw_credit_text,
        "ocr_balance_text": _raw_balance_text,
        "parsed_debit":     debit,
        "parsed_credit":    credit,
        "parsed_balance":   balance,
    }

    # ── Phase 1A: OCR Signature Detection ────────────────────────────────────
    # Pure token-level checks. No ledger math. Runs before conservation.
    # Finds: PUNCTUATION_CORRUPTION, MULTIPLE_DOTS, DATE_NARRATION_MERGE,
    #        COLUMN_BOUNDARY_SUSPECT, NUMERIC_SHAPE_ANOMALY
    _date_token_text = None
    for tok in all_tokens:
        if _prove_date(tok, date_zone):
            _date_token_text = tok.get("text", "")
            break

    suspicious_fields = detect_ocr_signatures(
        raw_debit_text   = _raw_debit_text,
        raw_credit_text  = _raw_credit_text,
        raw_balance_text = _raw_balance_text,
        date_token_text  = _date_token_text,
        debit_x0         = ocr_x if assigned_column == "debit" else None,
        credit_x0        = ocr_x if assigned_column == "credit" else None,
        zones            = zones,
    )

    return {
        "date":           date,
        "narration":      narration,
        "debit":          debit,
        "credit":         credit,
        "balance":        balance,
        "page":           page_num,
        "raw_extraction": raw_extraction,
        "suspicious_fields": suspicious_fields,
        "ocr_amount":     ocr_amount,
        "ocr_x":          ocr_x,
        "assigned_column": assigned_column,
        "debit_zone":     debit_zone,
        "credit_zone":    credit_zone,
        "_block_text":    " ".join(block_text_parts),
        "_anchor_text":   anchor_text,
        "_token_total":   len(all_tokens),
        "_token_claimed": len(claimed),
        "_token_narr":    narr_count,
        "_source_bbox":   source_bbox,
        "_source_tokens": all_tokens,
    }



# ---------------------------------------------------------------------------
# Positive qualification gate (P1 + P2)
# ---------------------------------------------------------------------------

def _qualifies(txn: Dict, prev_balance: Optional[float], balance_zone_missing: bool = False) -> Tuple[bool, str, str]:
    """
    Run all proofs. Returns (passes, reject_reason, conservation_state).

    G1: valid date present
    G2: balance present
    G3: exactly one of debit/credit > 0
    A1: conservation with previous balance (PASS/FAIL/UNSEEDED)
    Backstop: structural label check

    Conservation rules (P2):
        PASS         → accept (agreement_state = OK)
        UNSEEDED     → accept (agreement_state = UNSEEDED)
        FAIL         → accept WITH CONFLICT flag (agreement_state = CONFLICT)
                       Row is NOT rejected. Evidence is preserved.
                       prev_balance advances from this row's OCR balance so the
                       rest of the statement is not cascade-blocked by a single
                       OCR typo.  Caller must set agreement_state = CONFLICT.

    Hard rejects (missing structural data — nothing to anchor from):
        no_date              → reject
        no_balance           → reject
        no_debit_or_credit   → reject
        both_debit_and_credit→ reject
        structural_label     → reject
    """
    if not txn.get("date"):
        return False, "no_date", CONSERVATION_UNSEEDED

    if txn.get("balance") is None:
        if balance_zone_missing:
            # P9A Provisional Fallback: balance zone never detected, so don't reject row.
            txn["quality"] = "PROVISIONAL"
            # It falls through to UNSEEDED conservation state automatically
        else:
            # Standard Strict Rule: balance column exists, so failure to OCR it is a hard reject
            return False, "no_balance", CONSERVATION_UNSEEDED

    has_debit  = txn.get("debit")  is not None
    has_credit = txn.get("credit") is not None

    # P0.5 Transaction Seed Validator
    # At minimum we need some amount movement to call this a transaction,
    # or a balance to act as an anchor if there are no movements (rare but possible).
    if not has_debit and not has_credit and txn.get("balance") is None:
        return False, "NO_TRANSACTION_SEED", CONSERVATION_UNSEEDED
        
    # P2 Row Contamination Detector
    contamination_keywords = [
        "IFSC", "MICR", "Account No", "Account Number", "Branch", "Branch Code",
        "Currency", "Nomination", "Nominee", "Customer ID", "Cust ID", "Phone",
        "Mobile", "Email", "Address", "Page No", "Statement Period", "Opening Balance",
        "Closing Balance", "Generated On", "Printed On"
    ]
    nar_val = txn.get("narration")
    narration_text = str(nar_val).upper() if nar_val is not None else ""
    contaminants = []
    for kw in contamination_keywords:
        if kw.upper() in narration_text:
            contaminants.append(kw)
            
    if contaminants:
        txn["contamination_detected"] = True
        txn["_contaminants"] = contaminants
            
    # G3: exactly one money movement
    if not has_debit and not has_credit:
        return False, "no_debit_or_credit", CONSERVATION_UNSEEDED
    if has_debit and has_credit:
        return False, "both_debit_and_credit", CONSERVATION_UNSEEDED

    credit = txn.get("credit") or 0.0
    debit  = txn.get("debit")  or 0.0

    # A1: conservation (P2 three-state)
    balance_val = txn.get("balance")
    con_state, residual = _prove_conservation(prev_balance, credit, debit, balance_val)

    if con_state == CONSERVATION_FAIL:
        # Accept with CONFLICT — do NOT reject. The row has a valid date, balance,
        # and amount token; the only issue is the accounting math doesn't close.
        # This is most commonly an OCR balance typo (e.g. 285,201 vs 286,201).
        # Rejecting it would cascade-block every subsequent row because prev_balance
        # would never advance past the bad row.
        #
        # The CONFLICT flag is the contract:
        #   - debit / credit / balance are NOT mutated (raw OCR values preserved)
        #   - agreement_state = CONFLICT is set by the caller
        #   - raw_extraction + _source_tokens carry the full evidence
        #   - prev_balance will be updated to this row's OCR balance (best available anchor)
        return True, f"conservation_conflict(residual={residual:.2f},prev={prev_balance})", con_state

    # PASS or UNSEEDED → continue to backstop
    # Backstop: structural label (last resort)
    # Only check the anchor row (first row) text to prevent appended footers from killing valid transactions.
    if _STRUCTURAL_LABELS.search(txn.get("_anchor_text", txn.get("_block_text", ""))):
        return False, "structural_label", con_state

    return True, "ok", con_state


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_with_coordinates(
    tokens: List[Dict[str, Any]],
    pdf_name: str = "Unknown",
    statement_id: str = "unknown",
    job_id: str = "unknown",
    bank: str = "Unknown",
    pdf_type: str = "Unknown",
    identity: Dict = None
) -> Tuple[List[Dict], Dict]:
    """
    Geometry-first, accounting-first transaction extraction.

    Accepts a row only by proving it IS a transaction — never by
    ruling out what it might not be.

    P2: Conservation uses PASS/FAIL/UNSEEDED — never rejects on UNSEEDED.
    P3: Page-level balance seeds prevent page-boundary losses.
    """
    if not tokens:
        return [], {}

    rows = detect_rows(tokens)
    if not rows:
        return [], {}

    zones, detected_headers = detect_columns(rows, identity=identity)

    if not zones or "date_zone" not in zones:
        logger.warning("V2: No column zones detected — aborting.")
        return [], {"error": "no_column_zones"}

    # Group rows by page to enforce P0.5 page boundary firewall
    page_to_rows = {}
    for r in rows:
        p = r.get("page", 0)
        page_to_rows.setdefault(p, []).append(r)
        
    blocks = []
    for p in sorted(page_to_rows.keys()):
        page_blocks = detect_transaction_blocks(page_to_rows[p], date_x_bounds=zones["date_zone"])
        blocks.extend(page_blocks)
        
    logger.info(f"PDF TYPE: {pdf_type}")
    logger.info(f"OCR TOKENS: {len(tokens)}")
    logger.info(f"COLUMN ZONES: {zones}")
    logger.info(f"ROWS DETECTED: {len(rows)}")
    logger.info(f"BLOCKS DETECTED: {len(blocks)}")

    # P3: Extract page-level balance seeds before processing blocks
    page_seeds = _extract_page_balance_seeds(rows)
    if page_seeds:
        logger.info(f"V2: Page balance seeds found: {page_seeds}")

    accepted:     List[Dict] = []
    rejected_log: List[Dict] = []
    prev_balance: Optional[float] = None
    current_page: int = -1
    evidence_counter: int = 1

    for block_idx, block in enumerate(blocks):
        candidate = _extract_block(block, zones)
        if candidate is None:
            continue
            
        candidate["_evidence_id"] = f"txn_{evidence_counter:05d}"
        candidate["job_id"] = job_id
        candidate["statement_id"] = statement_id
        candidate["pdf_name"] = pdf_name
        candidate["bank"] = bank
        evidence_counter += 1

        block_page = candidate.get("page", 0)

        # P3: On page transition, attempt to seed prev_balance from page_seeds
        if block_page != current_page:
            if block_page in page_seeds and prev_balance is None:
                seed = page_seeds[block_page]
                logger.info(
                    f"V2: Seeding prev_balance={seed} from page_seeds[{block_page}] "
                    f"(was None at page boundary)"
                )
                prev_balance = seed
            elif block_page != current_page and prev_balance is not None:
                # prev_balance carries across page boundaries automatically
                logger.debug(
                    f"V2: Page transition {current_page}→{block_page}, "
                    f"carrying prev_balance={prev_balance}"
                )
            current_page = block_page

        balance_zone_missing = "balance_zone" not in zones
        
        # --- E-Statement Layout Masking Rescue ---
        # If balance_zone is missing, the right-most column (usually credit_zone) extends to 9999.0.
        # This causes it to swallow the true balance tokens. 
        # If BOTH debit and credit are populated, it means the true transaction amount was in one, 
        # and the true balance was swallowed by the other.
        if balance_zone_missing and candidate.get("debit") is not None and candidate.get("credit") is not None:
            cz = zones.get("credit_zone", [0, 0])
            dz = zones.get("debit_zone", [0, 0])
            
            if cz[1] > dz[1]:
                # Credit zone was right-most, it swallowed the balance.
                candidate["balance"] = candidate["credit"]
                candidate["credit"] = None
            else:
                # Debit zone was right-most, it swallowed the balance.
                candidate["balance"] = candidate["debit"]
                candidate["debit"] = None
        ok, reason, con_state = _qualifies(candidate, prev_balance, balance_zone_missing=balance_zone_missing)

        if not ok:
            # P1: Full reject telemetry — no silent rejects
            rejected_log.append({
                "status":             "REJECTED",
                "reject_reason":      reason,
                "conservation_state": con_state,
                "raw_extraction":     candidate.get("raw_extraction"),
                "geometry_truth": {
                    "ocr_x":           candidate.get("ocr_x"),
                    "assigned_column": candidate.get("assigned_column"),
                    "debit_zone":      candidate.get("debit_zone"),
                    "credit_zone":     candidate.get("credit_zone")
                },
                "_evidence_id":       f"rej_{len(rejected_log)+1:05d}",
                "_source_page":       block_page,
                "_source_bbox":       candidate.get("_source_bbox"),
                "_source_tokens":     candidate.get("_source_tokens"),
                
                # Legacy fields for debugging logs
                "block":              block_idx,
                "date":               candidate.get("date"),
                "debit":              candidate.get("debit"),
                "credit":             candidate.get("credit"),
                "balance":            candidate.get("balance"),
                
                "job_id":             job_id,
                "statement_id":       statement_id,
                "pdf_name":           pdf_name,
                "bank":               bank,
                
                "prev_balance":       prev_balance,
                "block_text_snippet": candidate.get("_block_text", "")[:80],
            })
            logger.debug(
                f"V2 REJECT block[{block_idx}] page={block_page} "
                f"date={candidate.get('date')!r} "
                f"dr={candidate.get('debit')} cr={candidate.get('credit')} "
                f"bal={candidate.get('balance')} prev={prev_balance} "
                f"→ {reason} [{con_state}]"
            )
            continue

        # Advance prev_balance from this row's OCR balance.
        # This holds for both PASS and CONFLICT rows — the CONFLICT row's balance
        # is the best available anchor for subsequent rows. Do NOT skip this
        # on CONFLICT: skipping is Option 2, which was explicitly rejected because
        # it would keep prev_balance stuck and cascade-block all downstream rows.
        prev_balance = candidate["balance"]

        # Clean up internal fields before output
        out = {k: v for k, v in candidate.items() if not k.startswith("_")}
        out["extraction_method"]  = "coordinate_v2"
        out["conservation_state"] = con_state
        out["_evidence_id"]       = candidate["_evidence_id"]
        out["_source_page"]       = candidate["page"]
        out["_source_bbox"]       = candidate["_source_bbox"]
        if "_source_tokens" in candidate:
            out["_source_tokens"] = candidate["_source_tokens"]

        # CONFLICT rows: set agreement_state so callers can distinguish them.
        # All three accounting fields (debit, credit, balance) are intentionally
        # left as-is — raw OCR values, never mutated.
        if con_state == CONSERVATION_FAIL:
            out["agreement_state"] = "CONFLICT"
            logger.info(
                f"V2 CONFLICT accepted block[{block_idx}] page={block_page} "
                f"date={candidate.get('date')!r} "
                f"dr={candidate.get('debit')} cr={candidate.get('credit')} "
                f"bal={candidate.get('balance')} prev={prev_balance} "
                f"→ {reason}"
            )

        accepted.append(out)

    # Truth Preservation Engine annotation pass
    accepted = annotate_ledger_truth(accepted)

    telemetry = {
        "v2_extracted_rows":   len(accepted),
        "v2_rejected_rows":    len(rejected_log),
        "zones_detected":      list(zones.keys()),
        "page_seeds":          page_seeds,
        "reject_log":          rejected_log,
        "template_used":       identity.get("id", "Unknown") if identity else "Unknown"
    }

    logger.info(
        f"V2: {len(accepted)} accepted | {len(rejected_log)} rejected "
        f"| zones={list(zones.keys())} | page_seeds={list(page_seeds.keys())}"
    )
    return accepted, telemetry
