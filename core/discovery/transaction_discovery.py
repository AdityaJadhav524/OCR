"""
transaction_discovery.py
========================

Layer 1: Find every row that is likely a transaction.

NO header dependency.
NO zone dependency.
NO column assumptions.

Operates on raw OCR tokens (pre-merged) to prevent data destruction.
Uses Multi-Hypothesis Scoring to prevent false positives.

Output per candidate:
    {
        "transaction_score": 17,
        "header_score": 2,
        "account_info_score": 1,
        "signals": ["DATE", "AMOUNT", "UPI"],
        "amount_candidates": [100.0, 10325.79],
        "raw_text": "...",
        "page": 1,
    }
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("core.discovery.transaction_discovery")

from core.layout.row_detector import detect_rows

# ── Signal patterns ────────────────────────────────────────────────────────

_DATE_RE = re.compile(
    r'\b('
    r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|'    # dd/mm/yyyy
    r'\d{2,4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|'    # yyyy-mm-dd
    r'\d{1,2}[\s\-/][A-Za-z]{3,9}(?:[\s\-/]\d{2,4})?'  # dd-Mon or dd-Mon-yyyy
    r')\b',
    re.IGNORECASE
)

_MONEY_RE = re.compile(
    r'\b\d{1,3}(?:[,]\d{2,3})*(?:\.\d{1,2})?\b'
)

_NARRATION_KEYWORDS = re.compile(
    r'\b(UPI|NEFT|IMPS|RTGS|ATM|ACH|NACH|ECS|CHEQUE|CHQ|DD|'
    r'BY CLRG|TO CLRG|SALARY|EMI|LOAN|INTEREST|DIVIDEND|REFUND|'
    r'CASHBACK|CREDIT|DEBIT|TRANSFER|TRF|IFT|MANDATE|AUTO)\b',
    re.IGNORECASE
)

_REFERENCE_RE = re.compile(r'\b\d{10,}\b')

_HEADER_KEYWORDS = re.compile(
    r'\b(DATE|NARRATION|PARTICULARS|DESCRIPTION|DEBIT|CREDIT|BALANCE|WITHDRAWAL|DEPOSIT|AMOUNT)\b',
    re.IGNORECASE
)

_ACCOUNT_INFO_KEYWORDS = re.compile(
    r'\b(ACCOUNT|A/C|BRANCH|IFSC|MICR|CUSTOMER|CUST ID|STATEMENT|GENERATED|PAGE|OPENING|CLOSING|NAME|ADDRESS)\b',
    re.IGNORECASE
)

_STATEMENT_PERIOD_RE = re.compile(
    r'(FROM\s+\d{1,2}.*?TO\s+\d{1,2}|'
    r'\b\d{1,2}[\s\-/][A-Za-z]{3,9}[\s\-/]\d{2,4}\s*-\s*\d{1,2}[\s\-/][A-Za-z]{3,9}[\s\-/]\d{2,4}\b)',
    re.IGNORECASE
)

# ── Data types ─────────────────────────────────────────────────────────────

class TransactionCandidate:
    """A candidate transaction row — no column assignment yet."""

    def __init__(
        self,
        transaction_score: int,
        header_score: int,
        account_info_score: int,
        signals: List[str],
        amount_candidates: List[float],
        raw_text: str,
        page: int,
        tokens: List[Dict],
    ):
        self.transaction_score  = transaction_score
        self.header_score       = header_score
        self.account_info_score = account_info_score
        self.signals            = signals
        self.amount_candidates  = amount_candidates
        self.raw_text           = raw_text
        self.page               = page
        self.tokens             = tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_score":  self.transaction_score,
            "header_score":       self.header_score,
            "account_info_score": self.account_info_score,
            "signals":            self.signals,
            "amount_candidates":  self.amount_candidates,
            "raw_text":           self.raw_text,
            "page":               self.page,
        }


# ── Main function ──────────────────────────────────────────────────────────

def discover_transactions(page_tokens: List[Dict[str, Any]]) -> List[TransactionCandidate]:
    """
    Find all transaction candidate rows from raw tokens using multi-hypothesis scoring.
    """
    # 1. Group physical lines robustly
    lines = detect_rows(page_tokens)
    
    # 2. Pre-process and score lines, but also group them vertically if they belong together
    #    Rule: A new transaction starts with a Date. If a line has no date, it might be a 
    #    continuation of the previous transaction if they are vertically close.
    
    blocks = []
    current_block = []
    current_block_has_date = False
    last_y1 = -1
    last_page = -1
    
    for row_dict in lines:
        line_tokens = row_dict.get('tokens', [])
        if not line_tokens: continue
        
        raw_text = " ".join(t.get("text", "") for t in line_tokens)
        page = row_dict.get("page", 0)
        y0 = row_dict.get("y0", 0)
        y1 = row_dict.get("y1", 0)

        
        has_date = has_date_signal(raw_text) is not None
        
        # Determine if we should start a new block
        # Start new if: has a date, OR page changed, OR vertical gap is too large (> 15px)
        gap = y0 - last_y1
        is_new_block = False
        
        if not current_block:
            is_new_block = True
        elif has_date:
            is_new_block = True
        elif page != last_page:
            is_new_block = True
        elif gap > 15.0:
            is_new_block = True
            
        if is_new_block:
            if current_block:
                blocks.append(current_block)
            current_block = list(line_tokens)
        else:
            current_block.extend(line_tokens)
            
        last_y1 = y1
        last_page = page
        
    if current_block:
        blocks.append(current_block)
        
    candidates = []
    
    # 3. Score each block
    for block_tokens in blocks:
        # Sort tokens in block by y0 then x0 for stable text reading
        block_tokens = sorted(block_tokens, key=lambda t: (t.get("y0", 0), t.get("x0", 0)))
        raw_text = " ".join(t.get("text", "") for t in block_tokens)
        page = block_tokens[0].get("page", 0)
        
        # Gather Signals
        date_match = has_date_signal(raw_text)
        amounts = has_money_signal(raw_text)
        has_narr = has_narration_signal(raw_text)
        has_ref = has_reference_signal(raw_text)
        
        has_header_kws = bool(_HEADER_KEYWORDS.search(raw_text))
        has_account_kws = bool(_ACCOUNT_INFO_KEYWORDS.search(raw_text))
        is_statement_period = bool(_STATEMENT_PERIOD_RE.search(raw_text))
        
        signals = []
        if date_match: signals.append("DATE")
        if len(amounts) >= 1: signals.append("AMOUNT")
        if len(amounts) >= 2: signals.append("BALANCE")
        if has_narr: signals.append("NARRATION_KW")
        if has_ref: signals.append("REFERENCE")
        
        # Multi-Hypothesis Scoring
        txn_score = 0
        header_score = 0
        acct_score = 0
        
        # Positive Transaction Signals
        if date_match: txn_score += 5
        if len(amounts) >= 1: txn_score += 4
        if len(amounts) >= 2: txn_score += 4
        if has_narr: txn_score += 3
        if has_ref: txn_score += 2
            
        # Negative Transaction Signals (Boost other hypotheses)
        if has_header_kws:
            txn_score -= 10
            header_score += 10
        if has_account_kws:
            txn_score -= 10
            acct_score += 10
        if is_statement_period:
            txn_score -= 15
            acct_score += 10
            
        # Decision
        if txn_score >= 8 and txn_score > header_score and txn_score > acct_score:
            candidates.append(TransactionCandidate(
                transaction_score=txn_score,
                header_score=header_score,
                account_info_score=acct_score,
                signals=signals,
                amount_candidates=amounts,
                raw_text=raw_text,
                page=page,
                tokens=block_tokens
            ))

            
    logger.info(f"Discovery Engine found {len(candidates)} transaction candidates.")
    return candidates


# ── Signal detection utilities ──────────────────────────────────────────────

def has_date_signal(text: str) -> Optional[str]:
    """Return matched date string if text contains a date pattern."""
    m = _DATE_RE.search(text)
    return m.group(0) if m else None


def has_money_signal(text: str) -> List[float]:
    """Return list of numeric values found in text (potential amounts/balances)."""
    matches = _MONEY_RE.findall(text)
    result = []
    for m in matches:
        try:
            # simple filter for years acting as money
            if len(m) == 4 and m.isdigit() and 1990 <= int(m) <= 2100:
                continue
            result.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return result


def has_narration_signal(text: str) -> bool:
    """Return True if text contains a known transaction narration keyword."""
    return bool(_NARRATION_KEYWORDS.search(text))


def has_reference_signal(text: str) -> bool:
    """Return True if text contains a long numeric reference number."""
    return bool(_REFERENCE_RE.search(text))

