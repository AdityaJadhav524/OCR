import json
import re
import logging
from datetime import datetime

logger = logging.getLogger("ledgerai.validation_service")


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def normalize_date(date_str):
    if not date_str:
        return None
    clean_str = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return clean_str


def extract_json_from_response(response_text: str) -> list:
    """Parse a JSON array from raw LLM response text."""
    cleaned = response_text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse JSON from LLM response.")
            return []
    return []


def calculate_similarity(a, b) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def normalize_amount(text):
    """
    DEPRECATED: Simplified helper kept for reference only.
    Use normalize_amount_v2() which starts from the battle-tested _parse_float
    logic and adds only the proven OCR letter-cleanup and re.search patches.
    """
    return normalize_amount_v2(text)


def normalize_amount_v2(text):
    """
    Canonical amount normalizer built from the old _parse_float parser.

    Patches applied on top of the original logic:
      1. OCR letter substitution BEFORE stripping non-numeric chars:
         o,O -> 0  |  l -> 1  |  I,i,| -> removed
         This fixes trailing OCR garbage like '400000.90i', '290000.0o'.
      2. re.search() is already used in the original; no change needed there.

    All original logic is preserved:
      - Indian comma-as-decimal fix (81,510,17 -> 81510.17)
      - Multiple-period fix (81.510.17 -> 81510.17)
      - 3-digit decimal elision (2.000 -> 2000)
      - 5-digit decimal split (2.00000 -> 2000.00)
    """
    if text is None:
        return None

    if isinstance(text, (int, float)):
        return float(text)

    s = str(text).strip()

    # PATCH 1: OCR letter substitution — applied before stripping
    # Replaces visually similar letters before any numeric parsing.
    s = (
        s.replace("o", "0")
         .replace("O", "0")
         .replace("l", "1")
         .replace("i", "")
         .replace("I", "")
         .replace("|", "")
    )

    # Strip everything except digits, comma, period, minus
    s = re.sub(r'[^\d.,-]', '', s)

    # Apply OCR comma-as-decimal fix
    # Indian formatting: 2 decimal places. OCR often reads '.' as ','
    # e.g. 81,510,17 -> 81,510.17
    if '.' not in s and ',' in s:
        last_comma_idx = s.rfind(',')
        if len(s) - last_comma_idx - 1 == 2:
            s = s[:last_comma_idx] + '.' + s[last_comma_idx+1:]

    s = s.replace(',', '')

    # Multiple-period fix: last period is the decimal, others are thousands separators
    # e.g. 81.510.17 -> 81510.17
    if s.count('.') > 1:
        parts = s.rsplit('.', 1)
        s = parts[0].replace('.', '') + '.' + parts[1]
    elif s.count('.') == 1:
        parts = s.split('.')
        if len(parts[1]) == 3:
            # OCR misread: "2.000" is actually "2000" (thousands separator read as decimal)
            s = s.replace('.', '')
        elif len(parts[1]) == 5:
            # OCR misread: "2.00000" is actually "2000.00"
            s = parts[0] + parts[1][:3] + '.' + parts[1][3:]

    # PATCH 2: re.search (already used in original — no change, but explicitly documented)
    # Allows trailing OCR garbage after a valid number to be ignored.
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    if not m:
        return None

    return float(m.group())
