"""
core/validators/ocr_signature_detector.py
──────────────────────────────────────────
Phase 1A: Pure OCR Signature Detector

Detects known OCR error patterns from raw token text and geometry.

Rules:
  - No ledger math.
  - No prev_balance.
  - No context beyond the raw token text and its x0 coordinate.
  - Pure annotation: adds suspicious_fields to each transaction.
  - Never mutates debit, credit, balance, or raw_extraction.

Called from coordinate_parser_v2._extract_block() after token assignment.
"""
import re
import logging
from typing import Dict, Optional, List

logger = logging.getLogger("core.validators.ocr_signature_detector")

# OCR letter-digit confusions: these characters look like digits to a human
# but are frequently misread by PaddleOCR
_ALPHA_DIGIT_CONFUSIONS = re.compile(
    r'(?<!\w)'          # not preceded by word char (avoid false positives in narration)
    r'[OoIlSsBbGg]'    # O→0, o→0, I→1, l→1, S→5, s→5, B→8, b→6, G→6, g→9
    r'(?=\d)'           # followed by a digit → likely a number with OCR confusion
    r'|'
    r'(?<=\d)'          # OR preceded by a digit
    r'[OoIlSsBbGg]'    # followed by the confusion char
)


# ─────────────────────────────────────────────────────────────────────────────
# Individual detectors
# ─────────────────────────────────────────────────────────────────────────────

def _check_punctuation_corruption(raw_text: str) -> Optional[Dict]:
    """
    PUNCTUATION_CORRUPTION:
    Detects when OCR misread a comma as a period, producing a single decimal
    point with an unusual number of digits after it.

    Examples:
      "2.00000"   → likely "2,000.00"  (5 decimal places — comma eaten the decimal)
      "1.000"     → likely "1,000"     (3 decimal places with no fractional part)
    
    Safe: does NOT flag normal "1000.00" or "2.50" etc.
    Not flagged: values with 1, 2, or 4 decimal digits (normal currency precision).
    """
    text = raw_text.strip().replace(',', '')  # strip already-parsed commas
    
    # Must look like a number
    if not re.fullmatch(r'\d+\.\d+', text):
        return None

    decimal_digits = len(text.split('.')[1])
    
    if decimal_digits == 3:
        # "2.000" — 3 decimal places. In ₹ formatting this is always
        # a thousands separator read as a decimal.
        return {
            "reason": "PUNCTUATION_CORRUPTION",
            "severity": "MEDIUM",
            "raw_text": raw_text,
            "detail": f"3 decimal digits suggests comma->dot misread (e.g. 2,000 -> 2.000)"
        }
    elif decimal_digits == 5:
        # "2.00000" — comma became dot AND the real decimal was also lost.
        return {
            "reason": "PUNCTUATION_CORRUPTION",
            "severity": "MEDIUM",
            "raw_text": raw_text,
            "detail": f"5 decimal digits suggests double punctuation corruption (e.g. 2,000.00 -> 2.00000)"
        }
    
    return None


def _check_multiple_dots(raw_text: str) -> Optional[Dict]:
    """
    MULTIPLE_DOTS:
    Detects numeric tokens containing more than one period.
    Always indicates corrupted punctuation.

    Example: "260.065.93" → should be "260,065.93"
    """
    text = raw_text.strip()
    # Must look broadly numeric (digits, dots, commas)
    if not re.fullmatch(r'[\d.,]+', text):
        return None
    
    dot_count = text.count('.')
    if dot_count > 1:
        return {
            "reason": "MULTIPLE_DOTS",
            "severity": "HIGH",
            "raw_text": raw_text,
            "detail": f"{dot_count} periods in numeric token — commas were read as dots"
        }
    return None


def _check_numeric_shape_anomaly(raw_text: str) -> Optional[Dict]:
    """
    NUMERIC_SHAPE_ANOMALY:
    Detects tokens that are mostly digits but contain alpha characters that
    are visually similar to digits (O→0, l→1, S→5, etc.).

    Examples:
      "1O000" → likely "10000"
      "l000"  → likely "1000"
      "S000"  → likely "5000"
    
    Only fires if the token looks broadly numeric (>50% digits).
    Not applied to narration tokens.
    """
    text = raw_text.strip()
    if not text:
        return None
    
    # Token must be at least 50% digits to be suspicious as a number
    digit_count = sum(c.isdigit() for c in text)
    if len(text) < 2 or digit_count < len(text) * 0.5:
        return None
    
    matches = _ALPHA_DIGIT_CONFUSIONS.findall(text)
    if matches:
        return {
            "reason": "NUMERIC_SHAPE_ANOMALY",
            "severity": "LOW",
            "raw_text": raw_text,
            "detail": f"Possible OCR confusion chars: {matches}"
        }
    return None


def _check_column_boundary_suspect(x0: float, zone_boundary: float, margin_px: float = 15.0) -> Optional[Dict]:
    """
    COLUMN_BOUNDARY_SUSPECT:
    Detects when a token's left edge is within `margin_px` pixels of a column
    zone boundary, making its column ownership ambiguous.

    Used for debit/credit tokens near the debit/credit zone boundary.
    A token at x0=1008 with boundary at 1007 is technically in the debit zone,
    but a 1px difference means the OCR bounding box could be off.

    Args:
        x0           : token x0 coordinate
        zone_boundary: the boundary this token is close to
        margin_px    : threshold in pixels (default 15px)
    """
    distance = abs(x0 - zone_boundary)
    if distance <= margin_px:
        return {
            "reason": "COLUMN_BOUNDARY_SUSPECT",
            "severity": "LOW",
            "x0": x0,
            "boundary": zone_boundary,
            "margin_px": round(distance, 1),
            "detail": f"Token x0={x0:.1f} is only {distance:.1f}px from zone boundary {zone_boundary:.1f}"
        }
    return None


def _check_date_narration_merge(raw_text: str, in_date_zone: bool) -> Optional[Dict]:
    """
    DATE_NARRATION_MERGE:
    Detects when a date and narration have been merged into a single OCR token,
    e.g. "07/02/22UPI-HARPREET SINGH-".

    This is already handled by _DATE_PREFIX_RE in the parser, but flagging it
    here creates an evidence record of the merge so it appears in audit data.
    
    Only fires for tokens already placed in the date zone.
    """
    if not in_date_zone:
        return None
    
    # Date prefix pattern (same as _DATE_PREFIX_RE in coordinate_parser_v2)
    prefix_match = re.match(r'^(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\D', raw_text.strip())
    if prefix_match and len(raw_text.strip()) > len(prefix_match.group(0)) + 3:
        return {
            "reason": "DATE_NARRATION_MERGE",
            "severity": "HIGH",
            "raw_text": raw_text[:60],
            "date_extracted": prefix_match.group(1),
            "detail": "Date and narration merged into single OCR token"
        }
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def detect_ocr_signatures(
    raw_debit_text:   Optional[str],
    raw_credit_text:  Optional[str],
    raw_balance_text: Optional[str],
    date_token_text:  Optional[str],
    debit_x0:         Optional[float],
    credit_x0:        Optional[float],
    zones:            Dict,
) -> Dict:
    """
    Run all pure OCR signature detectors on the raw token values for one transaction.

    Called from coordinate_parser_v2._extract_block() after tokens are assigned.
    Returns a dict of {field_name: detection_result} for any suspicious fields found.
    Returns {} (empty) when everything looks clean.

    Args:
        raw_debit_text   : raw OCR text of the claimed debit token (or None)
        raw_credit_text  : raw OCR text of the claimed credit token (or None)
        raw_balance_text : raw OCR text of the claimed balance token (or None)
        date_token_text  : raw OCR text of the claimed date token (or None)
        debit_x0         : x0 coordinate of debit token (or None)
        credit_x0        : x0 coordinate of credit token (or None)
        zones            : column zone dict from detect_columns()

    Returns:
        Dict of suspicious field annotations, e.g.:
        {
          "balance": {"reason": "MULTIPLE_DOTS", "raw_text": "260.065.93", ...},
          "debit":   {"reason": "PUNCTUATION_CORRUPTION", "raw_text": "2.00000", ...}
        }
    """
    suspicious: Dict = {}

    # ── Balance field checks ──────────────────────────────────────────────────
    if raw_balance_text:
        sig = _check_multiple_dots(raw_balance_text) or \
              _check_punctuation_corruption(raw_balance_text) or \
              _check_numeric_shape_anomaly(raw_balance_text)
        if sig:
            suspicious["balance"] = sig
            logger.debug(f"OCR signature [{sig['reason']}] on balance: {raw_balance_text!r}")

    # ── Debit field checks ────────────────────────────────────────────────────
    if raw_debit_text:
        sig = _check_multiple_dots(raw_debit_text) or \
              _check_punctuation_corruption(raw_debit_text) or \
              _check_numeric_shape_anomaly(raw_debit_text)
        if sig:
            suspicious["debit"] = sig
            logger.debug(f"OCR signature [{sig['reason']}] on debit: {raw_debit_text!r}")

    # ── Credit field checks ───────────────────────────────────────────────────
    if raw_credit_text:
        sig = _check_multiple_dots(raw_credit_text) or \
              _check_punctuation_corruption(raw_credit_text) or \
              _check_numeric_shape_anomaly(raw_credit_text)
        if sig:
            suspicious["credit"] = sig
            logger.debug(f"OCR signature [{sig['reason']}] on credit: {raw_credit_text!r}")

    # ── Column boundary checks ────────────────────────────────────────────────
    debit_zone  = zones.get("debit_zone")
    credit_zone = zones.get("credit_zone")

    if debit_x0 is not None and debit_zone and credit_zone:
        # Check distance from debit token to the debit/credit boundary
        boundary = debit_zone[1]  # right edge of debit zone = left edge of credit zone
        sig = _check_column_boundary_suspect(debit_x0, boundary)
        if sig:
            suspicious.setdefault("debit", {})
            suspicious["debit"]["column_boundary"] = sig
            logger.debug(f"OCR signature [COLUMN_BOUNDARY_SUSPECT] on debit x0={debit_x0}")

    if credit_x0 is not None and debit_zone and credit_zone:
        boundary = credit_zone[0]  # left edge of credit zone = right edge of debit zone
        sig = _check_column_boundary_suspect(credit_x0, boundary)
        if sig:
            suspicious.setdefault("credit", {})
            suspicious["credit"]["column_boundary"] = sig
            logger.debug(f"OCR signature [COLUMN_BOUNDARY_SUSPECT] on credit x0={credit_x0}")

    # ── Date token merge check ────────────────────────────────────────────────
    if date_token_text:
        sig = _check_date_narration_merge(date_token_text, in_date_zone=True)
        if sig:
            suspicious["date"] = sig
            logger.debug(f"OCR signature [DATE_NARRATION_MERGE] on date: {date_token_text[:40]!r}")

    if suspicious:
        logger.info(f"OCR signatures detected: {list(suspicious.keys())} → {[v.get('reason', v.get('column_boundary',{}).get('reason')) for v in suspicious.values()]}")

    return suspicious
