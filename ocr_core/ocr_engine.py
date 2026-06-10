"""
ocr_engine.py — PaddleOCR Singleton

Safe optimizations applied (zero accuracy impact) — updated for PaddleOCR v3.6.0 API:

  use_textline_orientation=False — skip rotation classifier (was use_angle_cls in v2.x);
                                   upright docs only (A4, bank statements)
  lang='en'                      — English dict only; no multilingual overhead
  text_recognition_batch_size=16 — recognise 16 boxes at once vs default 6 (was rec_batch_num in v2.x)
  [use_gpu removed]              — not a constructor arg in v3.x (CPU is the default)
  [show_log removed]             — not a constructor arg in v3.x

DELIBERATELY NOT SET:
  text_det_limit_side_len  — left at Paddle default (960). Reducing this caused word-count
                             regression (734→673 words). Detection resolution must stay high
                             for dense bank-statement text.

Thread pinning (OMP_NUM_THREADS / MKL_NUM_THREADS) is set in main.py
before this module is imported.
"""
import logging

logger = logging.getLogger(__name__)
_OCR_INSTANCE = None


def get_ocr_engine():
    """
    Returns the global singleton PaddleOCR instance, initialised lazily.
    Never recreated after first load — inference graph stays warm across all requests.
    """
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        logger.info("Initializing PaddleOCR singleton…")
        from paddleocr import PaddleOCR

        _OCR_INSTANCE = PaddleOCR(
            # ── Accuracy settings (DO NOT CHANGE) ─────────────────────────────
            use_textline_orientation=False,   # upright docs: textline orient is pure overhead (v3: was use_angle_cls)
            lang='en',                        # English-only dict
            # use_gpu removed — CPU is default in v3.x, not a constructor arg

            # ── Safe throughput improvement ────────────────────────────────────
            text_recognition_batch_size=16,   # recognition batch: 6→16 (v3: was rec_batch_num)

            # ── show_log removed — not a constructor arg in PaddleOCR v3.x ────
        )
        logger.info("PaddleOCR singleton ready.")

    return _OCR_INSTANCE


def extract_text_from_image(img_array):
    """
    Runs OCR on a numpy BGR image array.
    PaddleOCR v3.x: ocr() is a deprecated shim → predict().
    predict() does NOT accept cls — orientation is controlled by
    use_textline_orientation=False set at construction time.
    """
    ocr = get_ocr_engine()
    result = ocr.ocr(img_array)
    return result
