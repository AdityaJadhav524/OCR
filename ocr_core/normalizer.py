"""
normalizer.py — Document Normalization Engine

Cleans raw OCR boxes before structure analysis.
- Fixes unicode artifacts
- Strips trailing/leading whitespace
- Filters low-confidence OCR garbage (< CONF_THRESHOLD)
- Validates box geometry (non-zero area)
"""
from layout_tree import Word
import logging

logger = logging.getLogger(__name__)

# Drop words with confidence below this threshold.
# Removes corrupted OCR fragments from dense/compressed documents.
CONF_THRESHOLD = 0.55

# Minimum word dimensions to be considered real text (pixels)
MIN_WIDTH  = 2.0
MIN_HEIGHT = 3.0


def normalize_paddle_result(raw_result) -> list:
    """Converts PaddleOCR raw output into unified Box dicts.

    Supports both output formats:
      v3.x (PaddleOCR >= 3.0): OCRResult dict with keys
            rec_polys, rec_texts, rec_scores
      v2.x (legacy fallback):  list of [coords, (text, conf)] tuples

    Also stores confidence so normalize_boxes can filter it.
    """
    boxes = []
    if not raw_result:
        return boxes

    dropped = 0

    # ── PaddleOCR v3.x format ─────────────────────────────────────────────────
    # predict() returns a list of OCRResult objects (dict subclasses).
    # Each element has: rec_polys (list of 4-pt coords), rec_texts, rec_scores.
    if isinstance(raw_result, dict) or (
        hasattr(raw_result, "keys") and "rec_texts" in raw_result
    ):
        rec_polys  = raw_result.get("rec_polys",  [])
        rec_texts  = raw_result.get("rec_texts",  [])
        rec_scores = raw_result.get("rec_scores", [])

        for coords, text, conf in zip(rec_polys, rec_texts, rec_scores):
            conf = float(conf)
            if conf < CONF_THRESHOLD:
                dropped += 1
                logger.debug("Dropped low-conf word %r (%.2f)", text, conf)
                continue

            xs = [p[0] for p in coords]
            ys = [p[1] for p in coords]
            w  = max(xs) - min(xs)
            h  = max(ys) - min(ys)

            if w < MIN_WIDTH or h < MIN_HEIGHT:
                dropped += 1
                continue

            boxes.append({
                "text":  text,
                "conf":  conf,
                "x1":    min(xs),
                "y1":    min(ys),
                "x2":    max(xs),
                "y2":    max(ys),
                "cx":    (min(xs) + max(xs)) / 2,
                "cy":    (min(ys) + max(ys)) / 2,
                "width": w,
                "height": h,
            })

        if dropped:
            logger.info("normalizer (v3): dropped %d low-conf/tiny boxes", dropped)
        return boxes

    # ── PaddleOCR v2.x legacy format ──────────────────────────────────────────
    # predict() returned a nested list of [coords, (text, conf)] items.
    for item in raw_result:
        if len(item) == 2:
            coords, (text, conf) = item

            if conf < CONF_THRESHOLD:
                dropped += 1
                logger.debug("Dropped low-conf word %r (%.2f)", text, conf)
                continue

            xs = [p[0] for p in coords]
            ys = [p[1] for p in coords]
            w  = max(xs) - min(xs)
            h  = max(ys) - min(ys)

            if w < MIN_WIDTH or h < MIN_HEIGHT:
                dropped += 1
                continue

            boxes.append({
                "text":  text,
                "conf":  conf,
                "x1":    min(xs),
                "y1":    min(ys),
                "x2":    max(xs),
                "y2":    max(ys),
                "cx":    (min(xs) + max(xs)) / 2,
                "cy":    (min(ys) + max(ys)) / 2,
                "width": w,
                "height": h,
            })

    if dropped:
        logger.info("normalizer (v2): dropped %d low-conf/tiny boxes", dropped)
    return boxes



def normalize_boxes(raw_boxes: list) -> list[Word]:
    """Cleans text, validates geometry, converts to Word objects."""
    cleaned = []
    for b in raw_boxes:
        text = b.get("text", "")

        # Unicode cleanup
        text = (text
                .replace("\u2013", "-").replace("\u2014", "-")
                .replace("\u2018", "'").replace("\u2019", "'")
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u00a0", " ")   # non-breaking space
                )
        text = text.strip()
        if not text:
            continue

        x1 = float(b["x1"]); x2 = float(b["x2"])
        y1 = float(b["y1"]); y2 = float(b["y2"])

        if (x2 - x1) < MIN_WIDTH or (y2 - y1) < MIN_HEIGHT:
            continue

        cleaned.append(Word(
            text=text,
            x1=x1, y1=y1, x2=x2, y2=y2,
            cx=float(b["cx"]),
            cy=float(b["cy"]),
            width=x2 - x1,
            height=y2 - y1,
        ))
    return cleaned
