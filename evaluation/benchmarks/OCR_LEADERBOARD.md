# OCR Benchmark Leaderboard

Every OCR pipeline experiment must be evaluated against the V1.1.0 Validation Engine. 
The KPI is not pure OCR text accuracy, but **Reduction in validator failures caused by OCR**. 

## Baseline Metrics (Confidence Score)

| Engine / Pipeline             | Axis | HDFC | BOI  | YES  | TJSB | KOTAK | Avg  |
| ----------------------------- | ---: | ---: | ---: | ---: | ---: | ----: | ---: |
| V1.1.0 Baseline (PaddleOCR)   |   46 |   86 |   92 |  100 |  100 |   100 | 87.3 |
| Tesseract (Raw)               |    - |    - |    - |    - |    - |     - |    - |
| EasyOCR (Raw)                 |    - |    - |    - |    - |    - |     - |    - |
| Paddle + Watermark Removal    |    - |    - |    - |    - |    - |     - |    - |
| Paddle + Adaptive Deskew      |    - |    - |    - |    - |    - |     - |    - |
| Paddle + Region OCR           |    - |    - |    - |    - |    - |     - |    - |

*Note: Any pipeline that regresses the Average score or drops a healthy bank (e.g., YES, TJSB) below 95 is automatically rejected by the `run_regression.py` gate.*
