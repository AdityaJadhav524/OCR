# Supported Banks & Document Profiles

The system explicitly supports and natively handles the specific metadata routing for the following institutions:

- **TJSB Sahakari Bank:** Handles overlay compression and tightly packed tabular boundaries.
- **Kotak Mahindra Bank:** Handles standard digital extraction.
- **Yes Bank:** Handles complex multi-column digital extraction.
- **Bank of India (BOI):** Handles aggressive opening/closing balance anchor discovery across complex summary pages.
- **HDFC Bank:** Handles chunk-based document order scrambling natively via Page Sequence Repair.
- **Axis Bank:** Supported, but currently faces upstream OCR challenges (watermark contamination and numeric fusion).
