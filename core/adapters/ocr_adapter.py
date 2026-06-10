"""
core/adapters/ocr_adapter.py
─────────────────────────────
Phase 2: OCR Output → Parser Input Adapter

Responsibilities:
  - Accept an ocr_core Document layout tree object
  - Convert it into the two parser-compatible inputs:
      1. full_text: str   (for statement_parser.parse_with_llm)
      2. pages: List[str] (for bank_detector.classify_document_llm)

Rules:
  - NO business logic
  - NO bank logic
  - NO transaction logic
  - Pure text joining only

Schema Mapping (from Phase 1 analysis):
  OCR: Document.pages[n].lines[i].text  (already reading-order sorted)
  → join lines with '\n'                → page_text[n]
  → join pages with ={80} separator     → full_text  (matches pdf_extractor.py output exactly)
"""

import logging
from typing import List, Tuple

logger = logging.getLogger("core.adapters.ocr_adapter")

# Must exactly match the separator used in pdf_extractor.py (line 499) and
# the regex used in statement_parser.py (re.split(r'={80}', full_text))
_PAGE_SEP = "=" * 80


def document_to_text(document) -> Tuple[str, List[str]]:
    """
    Convert an ocr_core Document layout tree into parser-compatible text.

    Args:
        document: ocr_core.layout_tree.Document instance produced by
                  ocr_core.pipeline.run_pipeline()

    Returns:
        Tuple of:
          full_text : str        — single string joining all pages with ={80}
                                   page separators. This is the exact format
                                   that statement_parser.parse_with_llm() expects.
          pages     : List[str]  — list where pages[n] is the plain text of
                                   page n+1. This is the exact format that
                                   bank_detector.classify_document_llm() expects.
    """
    if not document or not document.pages:
        logger.warning("ocr_adapter: received empty Document — returning empty strings")
        return "", []

    page_texts: List[str] = []

    for page in document.pages:
        # Lines are already sorted top→bottom, left→right by reading_order.py.
        # We only need to join them.
        lines = [line.text for line in page.lines if line.text and line.text.strip()]
        page_text = "\n".join(lines)
        page_texts.append(page_text)

        logger.debug(
            "ocr_adapter: page %d → %d lines, %d chars",
            page.page_number, len(lines), len(page_text),
        )

    # Build full_text with the exact separator format pdf_extractor.py uses.
    # First page has no leading newline; subsequent pages get a blank line before
    # the separator so the LLM sees clean page boundaries.
    text_blocks: List[str] = []
    for i, (page, page_text) in enumerate(zip(document.pages, page_texts)):
        leading = "" if i == 0 else "\n"
        sep = f"{leading}{_PAGE_SEP}\nPAGE {page.page_number}\n{_PAGE_SEP}\n"
        text_blocks.append(sep + page_text)

    full_text = "\n".join(text_blocks)

    logger.info(
        "ocr_adapter: converted %d pages → full_text %d chars",
        len(page_texts), len(full_text),
    )

    return full_text, page_texts
