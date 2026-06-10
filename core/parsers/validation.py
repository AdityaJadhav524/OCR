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
