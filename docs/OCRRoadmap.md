# OCR & Document AI Roadmap

The Validation Pipeline is officially frozen. Phase 2 of the project concentrates entirely on upstream image processing and bounding box extraction. 

## Phase 2 Architecture Goals
To elevate challenging scanned documents (Axis, HDFC), we must improve the initial extraction vectors before they hit the deterministic parser.

### Track A: Image Preprocessing Pipeline
We need to normalize the image fidelity before submitting to the OCR engine.
- **Watermark Suppression:** Removing dense background text that fuses with digits (e.g. Axis).
- **Adaptive Deskewing:** Properly orienting individual page chunks.
- **Binarization & Shadow Removal:** Adaptive thresholding to rescue faded numbers.

### Track B: Modular OCR Engine Hub
Instead of locking into a single provider, the system will orchestrate adapters for various engines, picking the best tool for the specific document profile:
- Document Intelligence (Azure)
- PaddleOCR
- Tesseract
- Surya
- EasyOCR

### Track C: OCR Evaluation Framework
We must measure improvements deterministically without polluting the Validation Engine metrics.
The upcoming `evaluation/metrics/` stack will natively track:
- Amount/Date Recall
- Character Error Rate (CER)
- Word Error Rate (WER)
- OCR Model Confidence Values
