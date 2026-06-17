# Date Token Merge Forensic Report

## 1. Frequency

- Total PDFs scanned: 2
- Pure date tokens: 163
- Merged date tokens: 1
- Total date tokens: 164
- Percentage merged: **0.61%**

## 2. Merged Instances

| PDF | Page | Original Token | Extracted Date | Remainder | x0 | y0 |
|-----|------|----------------|----------------|-----------|----|----|
| YESBANK_page-0001.pdf | 4 | `07/02/22UPI-HARPREET SINGH-` | `07/02/22` | `UPI-HARPREET SINGH-` | 78 | 1240 |

## 3. Impact & Recoverability

Simulation: If parser logic was updated to split `Date+Text` tokens:
- Recoverable transactions: **1**

## 4. Conclusion

**Classification: SYSTEMIC OCR ISSUE**

Occurs frequently enough to warrant a dedicated token splitting pre-processor step.
