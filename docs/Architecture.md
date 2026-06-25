# CA Architecture

The system is separated into two major subsystems:

## 1. OCR & Document Understanding (`ocr/`)
Handles raw image extraction, pre-processing, and generating text bounding boxes.
- **Preprocessing:** Watermark suppression, deskewing, binarization.
- **Adapters:** Wrappers for specific engines (e.g., Azure Document Intelligence, PaddleOCR, Tesseract).
- **Engines:** Core extraction routines.

## 2. Validation & Parsing Engine (`core/`)
Consumes standard OCR output and transforms it into a deterministic, double-entry financial ledger.
- **Extractors:** The Candidate Generator surfaces mathematical bounds for missing characters.
- **Parsers:** `coordinate_parser_v2.py` constructs rows using heuristic coordinate rules.
- **Ordering:** Page Sequence Repair fixes scrambled physical layouts.
- **Validators:** The heart of the platform. Verifies running balances, reconciliation anchors, and ledger directions.
- **Confidence Engine:** Orchestrates all validators and returns the final Trust Score.

*This separation ensures that upstream improvements in AI vision models do not break the deterministic financial accounting layer.*
