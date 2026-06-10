"""
pipeline.py — Pure OCR Execution Pipeline
"""
import time
import cv2
import logging

from ocr_engine import extract_text_from_image
from pdf_renderer import render_pdf_to_images
from layout_tree import Document, Page
from normalizer import normalize_boxes, normalize_paddle_result
from line_engine import build_lines
from pipeline_manager import PipelineManager, PipelineStageError

logger = logging.getLogger(__name__)

# OCR input size cap: inference speed without accuracy loss
MAX_OCR_W = 1600


def run_pipeline(
    file_bytes: bytes,
    filename: str,
    run_id: str = "local_run",
    max_seconds: float = 600,
) -> Document:
    """
    Executes the OCR pipeline for a document.
    Returns a populated Document layout tree.
    """
    total_start = time.time()
    manager = PipelineManager(run_id)
    doc = Document(title=filename)

    try:
        # ── 1. RENDER ─────────────────────────────────────────────────────────
        def _render():
            return render_pdf_to_images(file_bytes, max_width=1800)

        pages_img = manager.execute_stage("render", _render)
        total_pages = len(pages_img)

        for page_idx, img in enumerate(pages_img):
            elapsed = time.time() - total_start
            if elapsed > max_seconds:
                raise TimeoutError(
                    f"OCR timeout after {elapsed:.0f}s (limit={max_seconds}s) "
                    f"at page {page_idx + 1}/{total_pages}"
                )

            ph, pw = img.shape[:2]
            page_obj = Page(page_number=page_idx + 1, width=pw, height=ph)

            # ── 2. OCR ────────────────────────────────────────────────────────
            def _ocr():
                h_img, w_img = img.shape[:2]
                if w_img > MAX_OCR_W:
                    scale = MAX_OCR_W / w_img
                    ocr_img = cv2.resize(
                        img,
                        (MAX_OCR_W, int(h_img * scale)),
                        interpolation=cv2.INTER_AREA,
                    )
                else:
                    ocr_img = img

                denoised = cv2.medianBlur(ocr_img, 3)
                raw = extract_text_from_image(denoised)
                if raw and isinstance(raw, list) and len(raw) > 0:
                    raw = raw[0]
                return normalize_paddle_result(raw)

            boxes = manager.execute_stage(f"ocr_p{page_idx}", _ocr)

            # ── 3. NORMALIZE ──────────────────────────────────────────────────
            words = manager.execute_stage(f"normalize_p{page_idx}", normalize_boxes, boxes)

            # ── 4. LINES ──────────────────────────────────────────────────────
            lines = manager.execute_stage(f"lines_p{page_idx}", build_lines, words)

            page_obj.words = words
            page_obj.lines = lines
            doc.pages.append(page_obj)

    except PipelineStageError as e:
        logger.warning("Pipeline halted early at stage: %s", e.stage)
        raise RuntimeError(f"Pipeline failed at {e.stage}: {str(e)}") from e
    except Exception as e:
        logger.exception("Pipeline crash")
        raise RuntimeError(f"Pipeline crash: {e}") from e

    return doc
