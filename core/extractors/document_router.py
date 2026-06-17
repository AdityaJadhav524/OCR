import logging
import os
import sys
from typing import List, Tuple, Dict, Any

logger = logging.getLogger("core.extractors.document_router")

# -- Scanned/Digital threshold --------------------------------------------------
SCANNED_WORD_THRESHOLD = 30      # avg words/page below this ? treat as scanned
SAMPLE_PAGES           = 3       # number of pages to sample for detection


# -- OCR Core path injection ----------------------------------------------------
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_OCR_CORE_PATH  = os.path.join(_WORKSPACE_ROOT, "ocr_core")

if _OCR_CORE_PATH not in sys.path:
    sys.path.insert(0, _OCR_CORE_PATH)
    logger.debug("document_router: added ocr_core to sys.path ? %s", _OCR_CORE_PATH)


# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------

def check_pdf_security(pdf_path: str, password: str = None) -> Dict[str, Any]:
    """
    Checks if a PDF is encrypted, password-protected, or requires a password.
    Returns a dict with state.
    """
    try:
        import fitz
        doc = fitz.open(pdf_path)
        needs_pass = doc.needs_pass
        
        if not needs_pass:
            doc.close()
            return {"status": "PASS", "is_encrypted": False}
            
        if password:
            success = doc.authenticate(password)
            doc.close()
            if success:
                return {"status": "UNLOCKED", "is_encrypted": True}
            else:
                return {"status": "INVALID_PASSWORD", "is_encrypted": True}
                
        doc.close()
        return {"status": "PASSWORD_REQUIRED", "is_encrypted": True}
        
    except Exception as e:
        logger.error("document_router: security check failed (%s)", e)
        # If fitz fails, we just pass it on and let the pipeline crash normally if invalid
        return {"status": "PASS", "is_encrypted": False}


# -----------------------------------------------------------------------------
# Detection
# -----------------------------------------------------------------------------

def detect_document_type(pdf_path: str, password: str = None) -> str:
    """
    Detect whether a PDF is digitally-encoded or a scanned image.
    """
    try:
        import fitz

        doc = fitz.open(pdf_path)
        if doc.needs_pass and password:
            doc.authenticate(password)
            
        total_pages = len(doc)
        n_sample    = min(SAMPLE_PAGES, total_pages)

        word_counts = []
        for i in range(n_sample):
            try:
                page  = doc.load_page(i)
                words = page.get_text("words")   # cheap: no rendering
                word_counts.append(len(words))
            except Exception:
                pass

        doc.close()

        if not word_counts:
            logger.warning("document_router: no words found - defaulting to scanned")
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
        logger.warning("document_router: PyMuPDF not available - defaulting to scanned")
        return "scanned"
    except Exception as e:
        logger.error("document_router: detection failed (%s) - defaulting to scanned", e)
        return "scanned"


# -----------------------------------------------------------------------------
# Digital path
# -----------------------------------------------------------------------------

def _extract_digital(pdf_path: str, password: str = None) -> Tuple[str, List[str], dict, list]:
    import re
    from core.extractors.pdf_extractor import extract_pdf_text

    full_text, merge_stats, page_tokens = extract_pdf_text(pdf_path, password=password)

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
    return full_text, pages, merge_stats, page_tokens


# -----------------------------------------------------------------------------
# Scanned path
# -----------------------------------------------------------------------------

def _extract_scanned(pdf_path: str, password: str = None) -> Tuple[str, List[str], dict, list]:
    from core.adapters.ocr_subprocess import extract_via_subprocess

    filename = os.path.basename(pdf_path)
    logger.info(
        "document_router [scanned]: delegating to OCR subprocess for '%s'", filename
    )

    full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path, password=password)

    logger.info(
        "document_router [scanned]: %d page(s), %d chars",
        len(pages), len(full_text),
    )
    return full_text, pages, telemetry, page_tokens


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def route_document(pdf_path: str, password: str = None) -> Tuple[str, List[str], dict, list]:
    doc_type = detect_document_type(pdf_path, password=password)

    if doc_type == "digital":
        return _extract_digital(pdf_path, password=password)
    else:
        return _extract_scanned(pdf_path, password=password)

