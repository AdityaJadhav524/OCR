"""
core/validators/ocr_validation.py
───────────────────────────────────
Phase 4: OCR Output Quality Validation

Validates an ocr_core Document before passing it to the parser.
Stops the pipeline if the OCR result is unusable — preventing the LLM
from receiving garbage text and producing phantom transactions.

Checks:
  1. page_count > 0
  2. total line count > MIN_LINE_COUNT
  3. total extracted text length > MIN_TEXT_LENGTH
  4. any bank-identification keyword present in the text
  5. (soft) average OCR word confidence available

All checks return a list of issue strings.
Empty list = valid. Non-empty list = caller should stop pipeline.
"""

import logging
import re
from typing import List

logger = logging.getLogger("core.validators.ocr_validation")

# ── Thresholds ────────────────────────────────────────────────────────────────
MIN_PAGE_COUNT   = 1
MIN_LINE_COUNT   = 5       # Total lines across all pages
MIN_TEXT_LENGTH  = 100     # Total characters across all pages
MIN_WORD_CONF    = 0.30    # Flag (not fail) if avg confidence below this

# ── Bank / financial keywords that must appear somewhere in the text ──────────
# Deliberately broad: even scanned noisy text usually preserves at least one.
BANK_KEYWORDS = [
    "account", "balance", "debit", "credit", "transaction",
    "statement", "bank", "date", "amount", "narration",
    "deposit", "withdrawal", "neft", "upi", "imps", "rtgs",
    "particulars", "description", "opening", "closing",
    # Common Indian bank name fragments
    "hdfc", "icici", "sbi", "axis", "kotak", "yes bank",
    "punjab", "canara", "union", "federal", "idbi",
]

_KW_RE = re.compile(
    "|".join(re.escape(kw) for kw in BANK_KEYWORDS),
    re.IGNORECASE,
)


def validate_ocr_output(document) -> List[str]:
    """
    Validate an ocr_core Document layout tree.

    Args:
        document: ocr_core.layout_tree.Document produced by pipeline.run_pipeline()

    Returns:
        List of issue strings. Empty list means the document passed all checks.
    """
    issues: List[str] = []

    # ── Check 1: pages exist ──────────────────────────────────────────────────
    if not document or not document.pages:
        issues.append(
            f"page_count=0 (minimum required: {MIN_PAGE_COUNT})"
        )
        logger.error("validate_ocr_output: FAIL — no pages in Document")
        return issues   # no point checking further

    page_count = len(document.pages)
    logger.info("validate_ocr_output: page_count=%d", page_count)

    # ── Check 2: total line count ─────────────────────────────────────────────
    total_lines = sum(len(page.lines) for page in document.pages)
    if total_lines < MIN_LINE_COUNT:
        issues.append(
            f"line_count={total_lines} (minimum required: {MIN_LINE_COUNT})"
        )
        logger.warning("validate_ocr_output: FAIL — only %d lines extracted", total_lines)

    # ── Check 3: total text length ────────────────────────────────────────────
    all_text = " ".join(
        line.text
        for page in document.pages
        for line in page.lines
        if line.text
    )
    text_len = len(all_text.strip())
    if text_len < MIN_TEXT_LENGTH:
        issues.append(
            f"text_length={text_len} chars (minimum required: {MIN_TEXT_LENGTH})"
        )
        logger.warning(
            "validate_ocr_output: FAIL — only %d chars of text extracted", text_len
        )

    # ── Check 4: bank/financial keywords present ──────────────────────────────
    if text_len > 0 and not _KW_RE.search(all_text):
        issues.append(
            "no bank/financial keywords found in extracted text "
            "(document may not be a financial statement, or OCR quality is too low)"
        )
        logger.warning("validate_ocr_output: FAIL — no financial keywords found")

    # ── Check 5 (soft): confidence ────────────────────────────────────────────
    # Word objects from normalizer.py may not carry a confidence attribute.
    # This check is a warning only — it does not add to issues[].
    conf_values = []
    for page in document.pages:
        for word in page.words:
            if hasattr(word, "confidence"):
                conf_values.append(word.confidence)

    if conf_values:
        avg_conf = sum(conf_values) / len(conf_values)
        if avg_conf < MIN_WORD_CONF:
            logger.warning(
                "validate_ocr_output: LOW CONFIDENCE warning — avg=%.2f (threshold=%.2f). "
                "Pipeline continues but accuracy may be poor.",
                avg_conf, MIN_WORD_CONF,
            )
        else:
            logger.info("validate_ocr_output: avg_confidence=%.3f OK", avg_conf)
    else:
        logger.debug(
            "validate_ocr_output: Word objects carry no confidence field — "
            "confidence check skipped."
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    if not issues:
        logger.info(
            "validate_ocr_output: PASS — pages=%d lines=%d text_len=%d",
            page_count, total_lines, text_len,
        )
    else:
        logger.error(
            "validate_ocr_output: FAIL — %d issue(s): %s",
            len(issues), " | ".join(issues),
        )

    return issues
