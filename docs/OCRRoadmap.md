# OCR & Document AI Roadmap

Phase 2 of the project concentrates entirely on upstream image processing and bounding box extraction. 
The V1.1.0 Validation Engine is strictly frozen. The core KPI of Phase 2 is the **Reduction in validator failures caused by OCR**, measured directly through `run_regression.py`.

## Phase 2 Priority Tracks

### Priority 1 — Layout Detection (Highest ROI)
Before OCR executes, classify the document architecture. Different layouts (Savings, Passbook, Credit Card, Scanned vs Digital, Landscape vs Portrait) must be explicitly routed to specialized pipelines.

### Priority 2 — Image Quality Pipeline
Deconstruct the monolithic OCR run into a measurable image preprocessing chain:
1. Deskew & Orientation
2. Crop margins & Remove borders
3. Contrast Normalization
4. Adaptive Thresholding & Noise Removal
5. Watermark Suppression (Critical for Axis)

### Priority 3 — OCR Ensemble
Benchmarking and orchestrating multiple extraction engines (PaddleOCR, EasyOCR, Tesseract, Docling, RapidOCR) rather than hardcoding a single provider. The best engine is selected dynamically based on Priority 1's Layout Detection.

### Priority 4 — Region-based OCR
Targeting specific bounding boxes (Transaction table, Balance column, Header, Footer) to radically improve token accuracy and extraction speed while ignoring noise (watermarks, logos).

### Priority 5 — Token Confidence
Tracking native OCR character-confidence arrays inside the `_source_tokens` schema to empower downstream validators to distinguish between parser heuristic failures and fundamental OCR corruption.

## Definition of Done
Phase 2 is considered successful when:
- OCR improvements produce measurable gains against the **same** frozen parser and validator stack.
- Every OCR experiment is successfully evaluated using the regression framework.
- No changes to the parser contract are required.
- Telemetry explicitly identifies whether remaining failures are due to OCR or parser logic.
