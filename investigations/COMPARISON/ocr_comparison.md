# OCR Quality Comparison

Comparing OCR output from the 3 engines (Current PaddleOCR, Docling OCR, MinerU OCR) specifically on known failure points to determine if switching OCR engines adds standalone value.

## 1. The Multiple-Dots Anomaly

Indian currency formatting uses commas `XX,XXX.XX`. PaddleOCR often reads commas as dots `XX.XXX.XX` causing `MULTIPLE_DOTS` anomalies. 

**Test Row 1:** Amount `14,640.00` and Balance `714,022.39` (Date: 18/05/25)
| Engine | Extracted Debit | Extracted Balance | Notes |
|--------|-----------------|-------------------|-------|
| PaddleOCR | `14,640.00` | `714.022.39` | Failed on balance (comma → dot) |
| Docling OCR | `14.640.00` | `714,022.39` | Failed on debit (comma → dot) |
| MinerU OCR | TBD | TBD | TBD |

**Test Row 2:** Amount `1.00` and Balance `701,159.52` (Date: 22/05/25)
| Engine | Extracted Debit | Extracted Balance | Notes |
|--------|-----------------|-------------------|-------|
| PaddleOCR | `1.00` | `701.159.52` | Failed on balance (comma → dot) |
| Docling OCR | `1.00` | `701,159.52` | Handled correctly |
| MinerU OCR | TBD | TBD | TBD |

## 2. Footer Text Quality (OCR Noise)

Evaluating how each OCR engine transcribes the noisy, ~150 DPI JPEG footer.

**Target String:** `HDFC BANK LIMITED *Closing balance includes... Registered Office Address...`

| Engine | OCR Output | Notes |
|--------|------------|-------|
| PaddleOCR | `HDFC BANK LIMITED *Closing balance includes funds earmarked for hold and uncleared funds... Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013` | Missing some spaces, spelling errors (`Offce`, `Senapan Bapar`). |
| Docling OCR | `HDFCBANKLIMITED *Closingbalanceincludesfundsearmarkedforhold andunclearedfunds RegisteredOffceAddress:HDFCBankHouse,SenapatiBapatMarg,LowerParel,Mumbai400013` | Stripped almost all spaces entirely. Unusable for exact-match. |
| MinerU OCR | TBD | TBD |

## Preliminary Conclusion (Pending MinerU)

If MinerU can consistently output `XX,XXX.XX` and preserve spaces in the footer, its OCR component might be worth adopting. Currently, Docling OCR trades one set of dot/comma errors for another and completely fails at space preservation in dense text.
