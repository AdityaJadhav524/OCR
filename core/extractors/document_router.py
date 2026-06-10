"""
core/extractors/document_router.py
────────────────────────────────────
Phase 3: Digital vs Scanned PDF Detection and Routing

Flow:
  Input PDF
    ↓
  detect_document_type()       — fitz word-count heuristic
    ↓
  "digital" → pdf_extractor.extract_pdf_text()    → (full_text, pages)
  "scanned" → ocr_core pipeline → ocr_adapter     → (full_text, pages)
    ↓
  Both paths return identical (full_text: str, pages: List[str])
  The rest of the parse pipeline is UNCHANGED.

Detection heuristic:
  - Open PDF with PyMuPDF (zero rendering, cheap)
  - Sample first min(3, total) pages
  - Count embedded text words per sampled page
  - Average < SCANNED_WORD_THRESHOLD → scanned
  - Average ≥ SCANNED_WORD_THRESHOLD → digital

SCANNED_WORD_THRESHOLD = 30 words/page
  Rationale: a blank cover page or header-only page typically has 5-20 words.
  A genuine digital text page of a bank statement has 100-500+ words.
  30 words catches images-only pages while tolerating sparse pages.
"""

import logging
import os
import sys
from typing import List, Tuple

logger = logging.getLogger("core.extractors.document_router")

# ── Scanned/Digital threshold ──────────────────────────────────────────────────
SCANNED_WORD_THRESHOLD = 30      # avg words/page below this → treat as scanned
SAMPLE_PAGES           = 3       # number of pages to sample for detection


# ── OCR Core path injection ────────────────────────────────────────────────────
# ocr_core sits alongside core/ in the workspace root Z:\CA\.
# We add it to sys.path here so all ocr_core imports resolve without
# making core/ depend on a package install.
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_OCR_CORE_PATH  = os.path.join(_WORKSPACE_ROOT, "ocr_core")

if _OCR_CORE_PATH not in sys.path:
    sys.path.insert(0, _OCR_CORE_PATH)
    logger.debug("document_router: added ocr_core to sys.path → %s", _OCR_CORE_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_document_type(pdf_path: str) -> str:
    """
    Detect whether a PDF is digitally-encoded or a scanned image.

    Returns:
        "digital" or "scanned"
    """
    try:
        import fitz  # PyMuPDF — already a dependency of pdf_extractor

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        n_sample    = min(SAMPLE_PAGES, total_pages)

        word_counts = []
        for i in range(n_sample):
            page  = doc.load_page(i)
            words = page.get_text("words")   # cheap: no rendering
            word_counts.append(len(words))

        doc.close()

        if not word_counts:
            logger.warning("document_router: no words found — defaulting to scanned")
            return "scanned"

        avg_words = sum(word_counts) / len(word_counts)
        doc_type  = "digital" if avg_words >= SCANNED_WORD_THRESHOLD else "scanned"

        logger.info(
            "document_router: detected=%s  avg_words/page=%.1f  threshold=%d  "
            "sampled=%d/%d pages",
            doc_type, avg_words, SCANNED_WORD_THRESHOLD, n_sample, total_pages,
        )
        return doc_type

    except ImportError:
        logger.warning("document_router: PyMuPDF not available — defaulting to scanned")
        return "scanned"
    except Exception as e:
        logger.error("document_router: detection failed (%s) — defaulting to scanned", e)
        return "scanned"


# ─────────────────────────────────────────────────────────────────────────────
# Digital path
# ─────────────────────────────────────────────────────────────────────────────

def _extract_digital(pdf_path: str, password: str = None) -> Tuple[str, List[str]]:
    """
    Use the existing pdf_extractor for digitally-encoded PDFs.
    Returns (full_text, pages) using the exact same format parse.py already uses.
    """
    import re
    from core.extractors.pdf_extractor import extract_pdf_text

    full_text = extract_pdf_text(pdf_path, password=password)

    # Split on the same separator that statement_parser.py uses
    pages = [
        block.strip()
        for block in re.split(r"={80}", full_text)
        if block.strip() and not re.fullmatch(r"\s*PAGE\s+\d+\s*", block.strip(), re.IGNORECASE)
    ]
    if not pages:
        pages = [full_text]

    logger.info(
        "document_router [digital]: %d pages, %d chars",
        len(pages), len(full_text),
    )
    return full_text, pages


# ─────────────────────────────────────────────────────────────────────────────
# Scanned path
# ─────────────────────────────────────────────────────────────────────────────

def _extract_scanned(pdf_path: str) -> Tuple[str, List[str]]:
    """
    Use OCR Core for scanned/image-only PDFs.
    Passes the resulting Document through the OCR adapter.
    Returns (full_text, pages) in the same format as _extract_digital().
    """
    from pipeline import run_pipeline
    from core.adapters.ocr_adapter import document_to_text
    from core.validators.ocr_validation import validate_ocr_output

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    filename = os.path.basename(pdf_path)
    logger.info("document_router [scanned]: running OCR pipeline on %s", filename)

    doc = run_pipeline(file_bytes=file_bytes, filename=filename)

    # Validate before passing to parser
    issues = validate_ocr_output(doc)
    if issues:
        raise ValueError(
            f"OCR output failed validation for {filename}: {'; '.join(issues)}"
        )

    full_text, pages = document_to_text(doc)

    logger.info(
        "document_router [scanned]: %d pages, %d chars",
        len(pages), len(full_text),
    )
    return full_text, pages


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def route_document(pdf_path: str, password: str = None) -> Tuple[str, List[str]]:
    """
    Main entry point. Detects document type and routes to the correct extractor.

    Args:
        pdf_path : Absolute path to a PDF file.
        password : PDF password (digital PDFs only; ignored for scanned).

    Returns:
        Tuple of:
          full_text : str        — page-separated text string ready for parse_with_llm()
          pages     : List[str]  — per-page strings ready for classify_document_llm()

    Both outputs are in the IDENTICAL format that parse.py expects,
    regardless of whether the PDF was digital or scanned.
    """
    doc_type = detect_document_type(pdf_path)

    if doc_type == "digital":
        return _extract_digital(pdf_path, password=password)
    else:
        return _extract_scanned(pdf_path)
