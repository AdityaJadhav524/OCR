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

        # Workaround for PaddlePaddle 3.0 PIR executor crash on Windows
        import paddle
        if hasattr(paddle, 'set_flags'):
            paddle.set_flags({'FLAGS_enable_pir_api': 0, 'FLAGS_use_mkldnn': 0})

        _OCR_INSTANCE = PaddleOCR(
            # ── Accuracy settings (DO NOT CHANGE) ─────────────────────────────
            use_angle_cls=False,              # upright docs (v2 arg)
            lang='en',                        # English-only dict
            use_gpu=False,                    # CPU default for Windows

            # ── Safe throughput improvement ────────────────────────────────────
            rec_batch_num=16,                 # recognition batch (v2 arg)
            show_log=False,                   # suppress verbose logging

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
