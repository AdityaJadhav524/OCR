import logging
from typing import List, Dict, Any
from core.layout.row_detector import detect_rows
import re

logger = logging.getLogger("core.layout.structural_token_protection")

STRUCTURAL_KEYWORDS = {
    "DATE", "BALANCE", "DEPOSIT", "WITHDRAWAL", "PARTICULARS",
    "AMOUNT", "DEBIT", "CREDIT", "NARRATION", "DESCRIPTION",
    "TRANSACTION", "DR", "CR", "CHQ", "REF"
}

def protect_table_header_tokens(tokens: List[Dict[str, Any]], telemetry: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Scans the token stream for rows that strongly match transaction table headers.
    Marks those tokens with `protected=True` so downstream suppression layers do not delete them.
    
    Operates heuristically: a row must contain >= 3 structural keywords to be protected.
    """
    if not tokens:
        return tokens

    # We use row_detector to group tokens spatially, identical to column_detector's input
    rows = detect_rows(tokens)
    
    protected_tokens_count = 0
    protection_events = []

    for i, row in enumerate(rows):
        row_tokens = row.get("tokens", [])
        if not row_tokens:
            continue
            
        row_text = " ".join([str(t.get("text", "")).upper() for t in row_tokens])
        
        # Find all structural keyword hits in this row
        hits = []
        for kw in STRUCTURAL_KEYWORDS:
            if re.search(rf"\b{kw}\b", row_text):
                hits.append(kw)
                
        # Threshold: >= 3 keywords means this is highly likely a table header
        if len(hits) >= 3:
            protected_texts = []
            for t in row_tokens:
                t["protected"] = True
                protected_tokens_count += 1
                protected_texts.append(t.get("text"))
                
            event = {
                "protected_row": i,
                "protected_tokens": protected_texts,
                "matched_keywords": hits,
                "reason": "STRUCTURAL_HEADER_CANDIDATE"
            }
            protection_events.append(event)
            logger.info(f"Protected row {i} as structural header. Keywords matched: {hits}")

    if telemetry is not None:
        telemetry["protection_events"] = protection_events
        telemetry["protected_token_count"] = protected_tokens_count

    return tokens
