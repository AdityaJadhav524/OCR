import re
import json
import logging
import time
from typing import Dict, List, Optional

try:
    from config import CLASSIFIER_MODEL
except ModuleNotFoundError:
    from core.config import CLASSIFIER_MODEL
from core.llm.provider import call_llm

logger = logging.getLogger("ledgerai.identifier_service")


# ════════════════════════════════════════════════════════════════════════════
# LAYER 1 — KEYWORD / BRAND PATTERN MATCHING  (< 10 ms)
# ════════════════════════════════════════════════════════════════════════════

# Each entry: canonical name → list of keyword patterns (searched in UPPERCASE text)
_BANK_PATTERNS: Dict[str, List[str]] = {
    "BANK OF INDIA":         ["BANK OF INDIA", "BKID"],
    "HDFC BANK":             ["HDFC BANK", "HDFC"],
    "STATE BANK OF INDIA":   ["STATE BANK OF INDIA", "SBI"],
    "ICICI BANK":            ["ICICI BANK", "ICICI"],
    "AXIS BANK":             ["AXIS BANK", "AXIS"],
    "KOTAK MAHINDRA BANK":   ["KOTAK MAHINDRA BANK", "KOTAK"],
    "YES BANK":              ["YES BANK"],
    "TJSB SAHAKARI BANK":    ["TJSB", "SAVINGACCOUNTSTATEMENT"],
    "UNION BANK OF INDIA":   ["UNION BANK OF INDIA"],
    "CANARA BANK":           ["CANARA BANK"],
    "PUNJAB NATIONAL BANK":  ["PUNJAB NATIONAL BANK", "PNB"],
    "BANK OF BARODA":        ["BANK OF BARODA", "BOB"],
    "IDBI BANK":             ["IDBI BANK", "IDBI"],
    "FEDERAL BANK":          ["FEDERAL BANK"],
    "INDUSIND BANK":         ["INDUSIND BANK"],
    "IDFC FIRST BANK":       ["IDFC FIRST BANK", "IDFC FIRST"],
}

def _detect_by_keywords(first_page_text: str) -> Optional[str]:
    """
    Layer 1: Scan the first page for known bank name patterns.
    Returns canonical bank name or None.
    Expected time: < 10 ms.
    """
    t0 = time.monotonic()
    text_upper = first_page_text.upper()
    # Remove spaces for collapsed-word patterns like "SAVINGACCOUNTSTATEMENT"
    text_nospace = text_upper.replace(" ", "")

    for bank_name, patterns in _BANK_PATTERNS.items():
        for pat in patterns:
            # Try both normal (spaced) and no-space text
            if pat in text_upper or pat.replace(" ", "") in text_nospace:
                elapsed_ms = (time.monotonic() - t0) * 1000
                logger.info(
                    "bank_detector Layer1: matched %r → %s  (%.1f ms)",
                    pat, bank_name, elapsed_ms,
                )
                return bank_name

    elapsed_ms = (time.monotonic() - t0) * 1000
    logger.info("bank_detector Layer1: no keyword match  (%.1f ms)", elapsed_ms)
    return None


# ════════════════════════════════════════════════════════════════════════════
# LAYER 2 — IFSC PREFIX DETECTION  (< 5 ms)
# ════════════════════════════════════════════════════════════════════════════

_IFSC_MAP: Dict[str, str] = {
    "BKID": "BANK OF INDIA",
    "SBIN": "STATE BANK OF INDIA",
    "HDFC": "HDFC BANK",
    "ICIC": "ICICI BANK",
    "UTIB": "AXIS BANK",
    "KKBK": "KOTAK MAHINDRA BANK",
    "YESB": "YES BANK",
    "TJSB": "TJSB SAHAKARI BANK",
    "UBIN": "UNION BANK OF INDIA",
    "CNRB": "CANARA BANK",
    "PUNB": "PUNJAB NATIONAL BANK",
    "BARB": "BANK OF BARODA",
    "IBKL": "IDBI BANK",
    "FDRL": "FEDERAL BANK",
    "INDB": "INDUSIND BANK",
    "IDFB": "IDFC FIRST BANK",
}

# IFSC codes are always 11 chars: 4-letter bank code + 0 + 6-char branch code
_IFSC_RE = re.compile(r"\b([A-Z]{4})0[A-Z0-9]{6}\b")

def _detect_by_ifsc(all_pages_text: str) -> Optional[str]:
    """
    Layer 2: Scan all pages for an IFSC code and map the 4-letter prefix.
    Returns canonical bank name or None.
    Expected time: < 5 ms.
    """
    t0 = time.monotonic()
    text_upper = all_pages_text.upper()
    for m in _IFSC_RE.finditer(text_upper):
        prefix = m.group(1)
        if prefix in _IFSC_MAP:
            bank_name = _IFSC_MAP[prefix]
            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.info(
                "bank_detector Layer2: IFSC %s → %s  (%.1f ms)",
                m.group(0), bank_name, elapsed_ms,
            )
            return bank_name

    elapsed_ms = (time.monotonic() - t0) * 1000
    logger.info("bank_detector Layer2: no IFSC match  (%.1f ms)", elapsed_ms)
    return None


# ════════════════════════════════════════════════════════════════════════════
# LAYER 3 — OCR HEADER TEXT SCAN  (uses already-extracted OCR, no extra cost)
# ════════════════════════════════════════════════════════════════════════════

def _detect_by_ocr_header(pages: List[str]) -> Optional[str]:
    """
    Layer 3: Look at the top 20% of the first page OCR output (header area).
    Same patterns as Layer 1 but restricted to the header slice so noise from
    transaction narrations (e.g. "HDFC UPI" as a counterparty) is excluded.
    Returns canonical bank name or None.
    """
    if not pages:
        return None
    t0 = time.monotonic()
    first_page = pages[0]
    lines = first_page.splitlines()
    header_lines = lines[: max(1, len(lines) // 5)]  # top 20%
    header_text = " ".join(header_lines).upper().replace(" ", "")

    for bank_name, patterns in _BANK_PATTERNS.items():
        for pat in patterns:
            if pat.replace(" ", "") in header_text:
                elapsed_ms = (time.monotonic() - t0) * 1000
                logger.info(
                    "bank_detector Layer3: OCR header matched %r → %s  (%.1f ms)",
                    pat, bank_name, elapsed_ms,
                )
                return bank_name

    elapsed_ms = (time.monotonic() - t0) * 1000
    logger.info("bank_detector Layer3: no OCR header match  (%.1f ms)", elapsed_ms)
    return None


# ════════════════════════════════════════════════════════════════════════════
# MINIMAL IDENTITY JSON BUILDER — used when a fast layer succeeds
# ════════════════════════════════════════════════════════════════════════════

def _detect_document_family(text: str) -> str:
    """
    Score the document to determine if it is a credit card statement or a bank statement.
    """
    score = 0
    text_upper = text.upper()
    
    if "TOTAL AMOUNT DUE" in text_upper:
        score += 3
    if "MINIMUM AMOUNT DUE" in text_upper:
        score += 3
    if "AVAILABLE CREDIT LIMIT" in text_upper:
        score += 3
    if "PAYMENT DUE DATE" in text_upper:
        score += 3
    if "CARD STATEMENT" in text_upper:
        score += 3
    if "LEGEND CREDIT CARD" in text_upper:
        score += 3
    if "PLATINUM CREDIT CARD" in text_upper:
        score += 3
    if "CASH LIMIT" in text_upper:
        score += 3
        
    # Only score "CREDIT CARD" if it appears in the top 15% of the text 
    # to avoid falsely matching security warnings in the footer.
    top_15_percent = text_upper[:max(1, int(len(text_upper) * 0.15))]
    if "CREDIT CARD" in top_15_percent:
        score += 5
        
    return "CREDIT_CARD" if score >= 5 else "BANK_STATEMENT"

def _build_minimal_identity(bank_name: str, layer: str, all_text: str = "") -> Dict:
    """
    Build the same identity JSON shape the LLM would return, but with safe
    defaults, so that the rest of the pipeline is unchanged.
    """
    abbr = bank_name.split()[0]  # first word e.g. "HDFC", "TJSB"
    doc_family = _detect_document_family(all_text)
    subtype = "CreditCard" if doc_family == "CREDIT_CARD" else "Savings"
    
    return {
        "id": f"{doc_family}_{abbr}_{subtype.upper()}_V1",
        "document_family": doc_family,
        "document_subtype": subtype,
        "institution_name": bank_name,
        "country": "India",
        "confidence_score": 0.95,
        "detection_layer": layer,
        "exclusion_markers": {"patterns": []},
        "parsing_hints": {
            "layout_type": "SINGLE_COLUMN",
            "summary_section_labels": [],
            "transaction_boundary_signals": ["DATE"],
            "ref_no_pattern": None,
            "page_break_pattern": r"Page \d+ of \d+",
            "details_strip_patterns": [],
            "known_summary_amounts": [],
        },
        "identity_markers": {
            "issuer_identity": {
                "issuer_name": {"rule": "keyword", "patterns": [bank_name]},
                "regulatory_identifiers": {
                    "ifsc": {"rule": "regex", "pattern": None},
                    "swift": {"rule": "regex", "pattern": None},
                    "iban": {"rule": "regex", "pattern": None},
                    "gstin": {"rule": "regex", "pattern": None},
                    "other": [],
                },
            },
            "document_structure_identity": {
                "document_title_phrase": {"rule": "keyword", "patterns": ["ACCOUNT STATEMENT"]},
                "document_reference_number": {"rule": "regex", "pattern": None},
                "generation_phrase": {"rule": "keyword", "patterns": []},
            },
            "period_identity": {
                "statement_period": {"rule": "regex", "pattern": None},
                "statement_date": {"rule": "regex", "pattern": None},
                "billing_cycle": {"rule": "regex", "pattern": None},
                "tax_period": {"rule": "regex", "pattern": None},
            },
            "entity_identity": {
                "account_number": {"rule": "regex", "pattern": None},
                "masked_card_number": {"rule": "regex", "pattern": None},
                "loan_account_number": {"rule": "regex", "pattern": None},
                "customer_id": {"rule": "regex", "pattern": None},
                "wallet_id": {"rule": "regex", "pattern": None},
                "merchant_id": {"rule": "regex", "pattern": None},
                "pan": {"rule": "regex", "pattern": None},
                "bo_id": {"rule": "regex", "pattern": None},
                "dp_id": {"rule": "regex", "pattern": None},
            },
            "transaction_table_identity": {
                "table_header_markers": ["Date", "Narration", "Debit", "Credit", "Balance"],
                "minimum_column_count": 4,
                "presence_of_running_balance": True,
                "debit_credit_style": True,
            },
            "financial_summary_identity": {
                "total_outstanding": {"rule": "regex", "pattern": None},
                "minimum_due": {"rule": "regex", "pattern": None},
                "emi_amount": {"rule": "regex", "pattern": None},
                "credit_limit": {"rule": "regex", "pattern": None},
                "drawing_power": {"rule": "regex", "pattern": None},
                "portfolio_value": {"rule": "regex", "pattern": None},
                "total_tax": {"rule": "regex", "pattern": None},
            },
            "footer_identity": {"footer_markers": []},
        },
    }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# INSTITUTION NAME NORMALISATION  [UNTOUCHED]
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
_LEGAL_SUFFIX_RE = re.compile(
    r"\s*,?\s*\b(limited|ltd\.?|pvt\.?|private)\s*$",
    re.IGNORECASE,
)


_COMMON_ABBREVIATIONS = {
    "BOI": "BANK OF INDIA",
    "SBI": "STATE BANK OF INDIA",
    "HDFC": "HDFC BANK",
    "ICICI": "ICICI BANK",
    "AXIS": "AXIS BANK",
    "TJSB": "TJSB SAHAKARI BANK",
}


def normalise_institution_name(raw: str) -> str:
    """
    Strip trailing legal registration suffixes, bracketed text, and punctuation.
    Returns UPPERCASE.
    Example: "TJSB (Thane Janata Sahakari Bank)" -> "TJSB SAHAKARI BANK"
    """
    if not raw or not raw.strip():
        return "UNKNOWN"
    
    # 1. Basic cleaning: uppercase and strip
    name = raw.strip().upper()
    
    # 2. Remove bracketed content (often contains abbreviations or full names)
    # e.g., "BANK OF BARODA (BOB)" -> "BANK OF BARODA"
    # e.g., "TJSB (THANE JANATA SAHAKARI BANK)" -> "TJSB"
    # We try to keep the part OUTSIDE the brackets if possible.
    if "(" in name and ")" in name:
        parts = re.split(r"[\(\)]", name)
        # Find the most "meaningful" part (longest or specifically TJSB)
        meaningful_parts = [p.strip() for p in parts if p.strip()]
        if meaningful_parts:
            # If any part is "TJSB", prefer that
            if any("TJSB" in p for p in meaningful_parts):
                name = "TJSB"
            else:
                name = meaningful_parts[0]

    # 3. Handle common abbreviations / synonyms
    # We do this BEFORE stripping legal suffixes to catch "SBI LTD"
    if name in _COMMON_ABBREVIATIONS:
        return _COMMON_ABBREVIATIONS[name]
    
    # Also check if any abbreviation is PART of the name
    for abbr, full in _COMMON_ABBREVIATIONS.items():
        if name == abbr or name == full:
            return full

    # 4. Strip common leading articles like "THE "
    if name.startswith("THE "):
        name = name[4:].strip()
        
    # 5. Strip trailing legal registration suffixes (Limited, Ltd, etc.)
    prev = None
    while prev != name:
        prev = name
        name = _LEGAL_SUFFIX_RE.sub("", name).strip().rstrip(",").strip()
        
    # 6. Final check against abbreviations after stripping
    if name in _COMMON_ABBREVIATIONS:
        return _COMMON_ABBREVIATIONS[name]
        
    return name


# ════════════════════════════════════════════════════════════════════════════
# FIRST N PAGES EXTRACTION
# Own function — does not reuse any existing service function
# ════════════════════════════════════════════════════════════════════════════

def _get_first_pages_text(pages: List[str], max_pages: int = 3) -> str:
    """
    Concatenate text from the first `max_pages` pages only.
    Adds a lightweight page marker so the LLM can orient itself.

    Sending only the first 2-3 pages to the LLM keeps token usage low
    while still capturing all structural signals (title, column headers,
    account markers, regulatory IDs) that appear at the top of a statement.
    """
    chunks = []
    for i, page_text in enumerate(pages[:max_pages], start=1):
        text = page_text.strip()
        if text:
            chunks.append(f"--- PAGE {i} ---\n{text}")
    return "\n\n".join(chunks)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CLASSIFY DOCUMENT â€” GENERATE IDENTIFICATION JSON  (LLM)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def classify_document_llm(pages: List[str]) -> Dict:
    """
    Generate the identification marker JSON for a new document.

    Detection order (fastest first):
      1. Layer 1 -- keyword / brand pattern match on first page   (< 10 ms)
      2. Layer 2 -- IFSC prefix scan on all pages                 (<  5 ms)
      3. Layer 3 -- OCR header text scan (top 20% of first page)  (<  5 ms)
      4. Layer 4 -- LLM fallback (first 2-3 pages sent to Gemini)

    The LLM is invoked ONLY when all three fast layers fail to identify
    the issuing bank.  For the vast majority of Indian bank statements,
    the bank name or an IFSC code appears in plain text, so the LLM is
    almost never needed for detection.

    Args:
        pages: Per-page text list produced by the page-split logic in
               processing_engine.py.

    Returns:
        Parsed identification JSON dict with institution_name normalised.
    """
    t_start = time.monotonic()
    first_page_text = pages[0] if pages else ""
    all_text = "\n".join(pages)

    # -- LAYER 3: OCR header text scan (SAFEST FIRST) ------------------------
    bank_name = _detect_by_ocr_header(pages)
    if bank_name:
        logger.info(
            "classify_document_llm: FAST-PATH Layer3 -> %s  (%.1f ms total)",
            bank_name, (time.monotonic() - t_start) * 1000,
        )
        return _build_minimal_identity(bank_name, "Layer3-ocr-header", all_text)

    # -- LAYER 1: keyword / brand name match ---------------------------------
    bank_name = _detect_by_keywords(first_page_text)
    if bank_name:
        logger.info(
            "classify_document_llm: FAST-PATH Layer1 -> %s  (%.1f ms total)",
            bank_name, (time.monotonic() - t_start) * 1000,
        )
        return _build_minimal_identity(bank_name, "Layer1-keyword", all_text)

    # -- LAYER 2: IFSC prefix match ------------------------------------------
    bank_name = _detect_by_ifsc(all_text)
    if bank_name:
        logger.info(
            "classify_document_llm: FAST-PATH Layer2 -> %s  (%.1f ms total)",
            bank_name, (time.monotonic() - t_start) * 1000,
        )
        return _build_minimal_identity(bank_name, "Layer2-ifsc", all_text)

    # -- LAYER 4: LLM fallback -----------------------------------------------
    logger.info(
        "classify_document_llm: all fast layers missed -- falling back to LLM  (%.1f ms so far)",
        (time.monotonic() - t_start) * 1000,
    )

    # -- Build page text (first 2-3 pages only) ------------------------------
    first_pages_text = _get_first_pages_text(pages, max_pages=3)



    prompt = f"""
You are a financial document structure analyst. Your task is to analyze a financial statement PDF and generate a comprehensive identification marker JSON that captures all unique structural, textual, and formatting patterns that distinguish this specific statement type.

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
ANALYSIS WORKFLOW
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

STEP 1: DOCUMENT CLASSIFICATION
- Identify the issuing institution name. 
  CRITICAL: Prioritize the document header, footer, logo area, and official contact sections. 
  CAUTION: Many Indian bank statements (like TJSB, Federal, etc.) have minimal headers. Look for bank names in branch addresses or copyright notes. 
  HINT: The concatenated string "SavingAccountStatement" (no spaces) is a strong marker for TJSB (Thane Janata Sahakari Bank).
  WARNING: DO NOT assume a bank mentioned in a single transaction (e.g., "BOI EMI", "BKID", "HDFC UPI") is the issuer if it appears in the description/narration column. These are almost always counterparties.
- Identify the document family: BANK_STATEMENT | CREDIT_CARD | WALLET | LOAN | INVESTMENT | INSURANCE | TAX | OTHER
- Identify the document subtype: Savings, Current, Platinum Card, Gold Card, Mutual Fund, Demat, etc.
- Assign confidence score (0.0-1.0) based on clarity of identification

STEP 2: EXTRACT ISSUER IDENTITY MARKERS
- Bank/Institution name patterns (exact strings that appear)
- Regulatory identifiers:
  * IFSC code pattern (if bank statement)
  * SWIFT code pattern (if applicable)
  * IBAN pattern (if applicable)
  * GSTIN (if applicable)
  * Any other regulatory IDs visible

STEP 3: EXTRACT DOCUMENT STRUCTURE IDENTITY
- Document title phrase (exact text, e.g., "ACCOUNT STATEMENT", "CREDIT CARD STATEMENT")
- Document reference number pattern (statement number, reference ID format)
- Generation phrase patterns (e.g., "Generated on", "Statement Date")

STEP 4: EXTRACT PERIOD IDENTITY MARKERS
- Statement period format (e.g., "01-Jan-2024 to 31-Jan-2024")
- Statement date format
- Billing cycle patterns (for credit cards)
- Tax period patterns (for investment/tax statements)

STEP 5: EXTRACT ENTITY IDENTITY MARKERS
Capture regex patterns for:
- Account number (full or masked format)
- Card number (masked, e.g., XXXX XXXX XXXX 1234)
- Loan account number
- Customer ID / CIF number
- Wallet ID (for payment wallets)
- Merchant ID (if applicable)
- PAN number
- BO ID / DP ID (for demat/investment accounts)

STEP 6: EXTRACT TRANSACTION TABLE IDENTITY
- List ALL column headers exactly as they appear (e.g., ["Date", "Description", "Debit", "Credit", "Balance"])
- Count minimum columns in transaction table
- Note if running balance column exists (true/false)
- Note if debit/credit style is used vs. single amount column (true/false)

STEP 7: EXTRACT FINANCIAL SUMMARY IDENTITY
Capture regex patterns that extract:
- Total outstanding amount (credit cards)
- Minimum amount due
- EMI amount (for loans)
- Credit limit (for credit cards/overdraft)
- Drawing power (for overdraft accounts)
- Portfolio value (for investment accounts)
- Total tax (for tax statements)

STEP 8: EXTRACT FOOTER IDENTITY
- List footer text patterns that consistently appear (disclaimers, contact info, etc.)

STEP 9: DEFINE EXCLUSION MARKERS
List patterns that should EXCLUDE lines from being treated as transactions:
- Page headers/footers (e.g., "Page 1 of 5")
- Section headers (e.g., "Transaction Details", "Summary")
- Disclaimer text
- Total/subtotal lines (e.g., "Total Debits", "Closing Balance")
- Empty or separator lines

STEP 10: DEFINE PARSING HINTS
- layout_type: SINGLE_COLUMN | TWO_COLUMN_PDF | MULTI_SECTION
- summary_section_labels: Labels that mark summary lines, not transactions (e.g., ["Opening Balance", "Closing Balance", "Total Credits"])
- transaction_boundary_signals: Signals that mark start of transaction (typically ["DATE"])
- ref_no_pattern: Regex to match and strip ONLY the raw reference code/number from descriptions. CRITICAL: Do NOT include words like "Ref No" or "ID" in the pattern unless they are truly noiseâ€”prefer keeping descriptive labels.
- page_break_pattern: Pattern for page numbering (e.g., "Page \\\\d+ of \\\\d+")
- details_strip_patterns: Regex patterns to remove raw alphanumeric ID hashes or long reference numbers (e.g., 12-digit UPI refs) from narrations. CRITICAL: NEVER include words like "UPI", "Ref No", "NEFT", "RTGS", "IMPS", or "ID" in these patterns. ONLY target the variable numbers/codes, preserving the descriptive labels.
- known_summary_amounts: Exact amount strings that are summary values, never transactions

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
STATEMENT ID VERSIONING RULE
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
ID format: [document_family]_[institution_abbreviation]_[document_subtype]_V[version_number]

Examples:
- BANK_STATEMENT_HDFC_SAVINGS_V1
- CREDIT_CARD_ICICI_PLATINUM_V1
- WALLET_PAYTM_MAIN_V1
- LOAN_SBI_HOME_V1
- INVESTMENT_ZERODHA_DEMAT_V1

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
REGEX PATTERN RULES
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
- Use Python regex syntax
- Escape special characters properly (\\\\d, \\\\s, \\\\., etc.)
- Make patterns specific but flexible enough to handle minor variations
- Use named groups where helpful: (?P<account>\\\\d{{10,16}})
- For dates, match actual format seen (e.g., "\\\\d{{2}}-[A-Z][a-z]{{2}}-\\\\d{{4}}" for "01-Jan-2024")
- For amounts, match format with commas/decimals: "[\\\\d,]+\\\\.\\\\d{{2}}"
- Return null if a field is not applicable to this statement type

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
OUTPUT FORMAT
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
Return ONLY valid JSON matching this exact structure:

{{
  "id": "[document_family]_[institution]_[subtype]_V1",
  "document_family": "BANK_STATEMENT|CREDIT_CARD|WALLET|LOAN|INVESTMENT|INSURANCE|TAX|OTHER",
  "document_subtype": "<e.g., Savings, Current, Platinum Card>",
  "institution_name": "<detected institution>",
  "country": "India",
  "confidence_score": 0.95,

  "exclusion_markers": {{
    "patterns": ["pattern1", "pattern2", "..."]
  }},

  "parsing_hints": {{
    "layout_type": "SINGLE_COLUMN|TWO_COLUMN_PDF|MULTI_SECTION",
    "summary_section_labels": ["label1", "label2"],
    "transaction_boundary_signals": ["DATE"],
    "ref_no_pattern": "<regex or null>",
    "page_break_pattern": "Page \\\\d+ of \\\\d+",
    "details_strip_patterns": ["pattern1", "pattern2"],
    "known_summary_amounts": ["amount1", "amount2"]
  }},

  "identity_markers": {{
    "issuer_identity": {{
      "issuer_name": {{ "rule": "keyword", "patterns": ["exact name"] }},
      "regulatory_identifiers": {{
        "ifsc": {{ "rule": "regex", "pattern": "<regex or null>" }},
        "swift": {{ "rule": "regex", "pattern": "<regex or null>" }},
        "iban": {{ "rule": "regex", "pattern": "<regex or null>" }},
        "gstin": {{ "rule": "regex", "pattern": "<regex or null>" }},
        "other": []
      }}
    }},
    "document_structure_identity": {{
      "document_title_phrase": {{ "rule": "keyword", "patterns": ["EXACT TITLE"] }},
      "document_reference_number": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "generation_phrase": {{ "rule": "keyword", "patterns": ["Generated on", "Statement Date"] }}
    }},
    "period_identity": {{
      "statement_period": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "statement_date": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "billing_cycle": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "tax_period": {{ "rule": "regex", "pattern": "<regex or null>" }}
    }},
    "entity_identity": {{
      "account_number": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "masked_card_number": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "loan_account_number": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "customer_id": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "wallet_id": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "merchant_id": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "pan": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "bo_id": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "dp_id": {{ "rule": "regex", "pattern": "<regex or null>" }}
    }},
    "transaction_table_identity": {{
      "table_header_markers": ["Column1", "Column2", "Column3"],
      "minimum_column_count": 4,
      "presence_of_running_balance": true,
      "debit_credit_style": true
    }},
    "financial_summary_identity": {{
      "total_outstanding": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "minimum_due": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "emi_amount": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "credit_limit": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "drawing_power": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "portfolio_value": {{ "rule": "regex", "pattern": "<regex or null>" }},
      "total_tax": {{ "rule": "regex", "pattern": "<regex or null>" }}
    }},
    "footer_identity": {{
      "footer_markers": ["footer text pattern 1", "footer text pattern 2"]
    }}
  }}
}}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
CRITICAL OUTPUT RULES
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
âœ“ Return ONLY the JSON object
âœ“ No markdown code blocks (no ```json```)
âœ“ No explanations before or after
âœ“ No comments in the JSON
âœ“ All regex patterns must use double backslashes (\\\\d not \\d)
âœ“ Set null for fields not applicable to the document type
âœ“ confidence_score must be between 0.0 and 1.0

BEGIN ANALYSIS OF THE PROVIDED FINANCIAL STATEMENT NOW.

Analyze this financial statement and generate identification markers:

{first_pages_text}
"""

    llm_result = call_llm(
        prompt=prompt,
        model=CLASSIFIER_MODEL,
        temperature=0,
    )
    raw = llm_result["raw_response"]

    # â”€â”€ Clean and parse the LLM JSON response â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _clean_json(s: str) -> str:
        s = re.sub(r"```(?:json)?", "", s).strip()   # strip markdown fences
        start = s.find("{")
        end   = s.rfind("}")
        if start != -1 and end != -1:
            s = s[start:end + 1]
        s = re.sub(r",\s*([\]}])", r"\1", s)          # trailing commas
        s = re.sub(r":\s*True\b",  ": true",  s)      # Python bool â†’ JSON bool
        s = re.sub(r":\s*False\b", ": false", s)
        s = re.sub(r":\s*None\b",  ": null",  s)
        if s.count("{") > s.count("}"):                # auto-close open braces
            s += "}" * (s.count("{") - s.count("}"))
        return s

    try:
        identifier = json.loads(_clean_json(raw))
    except Exception as e:
        logger.error(
            "classify_document_llm: JSON parse failed â€” %s | raw_preview=%s",
            e, raw[:500],
        )
        m = re.search(r"(\{.*\})", raw, re.DOTALL)
        if m:
            try:
                identifier = json.loads(_clean_json(m.group(1)))
            except Exception:
                raise ValueError(f"LLM returned invalid JSON: {e}")
        else:
            raise ValueError(f"LLM returned no JSON-like content: {e}")

    # â”€â”€ Ensure parsing_hints exists with safe defaults â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if "parsing_hints" not in identifier:
        logger.warning("classify_document_llm: parsing_hints missing â€” injecting defaults")
        identifier["parsing_hints"] = {
            "layout_type":                  "SINGLE_COLUMN",
            "summary_section_labels":       [],
            "transaction_boundary_signals": ["DATE"],
            "ref_no_pattern":               None,
            "page_break_pattern":           r"Page \d+ of \d+",
            "details_strip_patterns":       [],
            "known_summary_amounts":        [],
        }
    else:
        ph = identifier["parsing_hints"]
        ph.setdefault("layout_type",                  "SINGLE_COLUMN")
        ph.setdefault("summary_section_labels",       [])
        ph.setdefault("transaction_boundary_signals", ["DATE"])
        ph.setdefault("ref_no_pattern",               None)
        ph.setdefault("page_break_pattern",           r"Page \d+ of \d+")
        ph.setdefault("details_strip_patterns",       [])
        ph.setdefault("known_summary_amounts",        [])

    # â”€â”€ Normalise institution_name â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    raw_inst = identifier.get("institution_name") or "Unknown"
    norm_inst = normalise_institution_name(raw_inst)

    # â”€â”€ Heuristic Fallback for TJSB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # TJSB statements often have no bank name in text, only a logo.
    # The concatenated string "SavingAccountStatement" or "TJSB" in text are markers.
    if norm_inst == "UNKNOWN":
        header_text = "\n".join(pages[:2]).lower().replace(" ", "")
        if "savingaccountstatement" in header_text or "tjsb" in header_text:
            logger.info("classify_document_llm: TJSB heuristic match triggered")
            norm_inst = "TJSB SAHAKARI BANK"
            if identifier.get("id"):
                identifier["id"] = identifier["id"].replace("UNKNOWN", "TJSB")

    identifier["institution_name"] = norm_inst

    logger.info(
        "classify_document_llm: family=%s  institution=%s (raw=%r)  "
        "layout=%s  id=%s",
        identifier.get("document_family"),
        identifier.get("institution_name"),
        raw_inst,
        identifier.get("parsing_hints", {}).get("layout_type"),
        identifier.get("id"),
    )

    return identifier

