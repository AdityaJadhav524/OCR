# P6B — HDFC Baseline Investigation Summary

## PDF Characteristics

| Property | Value |
|----------|-------|
| File | `JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf` |
| Size | 1.69 MB |
| Pages | 12 |
| PDF Type | **SCANNED_IMAGE** |
| Native Text | NONE (0 chars) |
| Image Format | JPEG 1240x1636 (~150 DPI) per page |
| OCR Required | **YES** (mandatory for all engines) |

> **CRITICAL FINDING**: The HDFC PDF is entirely scanned — 12 pages, each containing
> a single JPEG image (1240×1636 pixels, ~150 DPI). No engine can extract text
> without running OCR. This means:
> - pdfplumber, PyMuPDF → **extract nothing** without OCR
> - Docling → must use its internal OCR pipeline (EasyOCR/Tesseract)
> - MinerU → must use its internal OCR pipeline
> - Current Engine → uses PaddleOCR 2.7.3 (via ocr_legacy_env)

---

## Current Engine Metrics (Baseline)

### Extraction
| Metric | Value |
|--------|-------|
| Total Transactions | **107** |
| Rejects | **14** |
| Reject Rate | 11.6% |
| Transactions with Debit | 101 |
| Transactions with Credit | 6 |

### Layout (Header/Footer Contamination)
| Metric | Value |
|--------|-------|
| Footer Leak Transactions | **10** |
| Footer Leak Rate | 9.3% of all txns |
| Header Leaks | 0 (correctly rejected via no_balance/no_date) |

### Accounting (Ledger Truth Engine)
| Metric | Value |
|--------|-------|
| Anomaly Count | **27** |
| Ledger Pass | 80 / 107 (74.8%) |
| Ledger Fail | 27 |

### Anomaly Breakdown
| PRIMARY_BALANCE_ANOMALY | 15 |
| MULTIPLE_DOTS | 11 |
| POWER_OF_TEN_DRIFT | 2 |
| DATE_NARRATION_MERGE | 1 |

### Reject Breakdown
| no_balance | 9 |
| no_date | 3 |
| both_debit_and_credit | 2 |

---

## Footer Leak Transactions

The following 10 transactions have HDFC page footer text
merged into their `narration` field:

**Leak 1** — Date: `17/05/25` | Keyword: `HDFC BANK LIMITED`
```
HDFC BANK LIMITED Contes of this statemen will be considered correct if ao error is reported within 30 days of receipt of statemea.The address on this staemeat is that ou secord with the Bank as at th
```

**Leak 2** — Date: `27/05/25` | Keyword: `HDFC BANK LIMITED`
```
*Closing balance includes funds earmarked for hold and uncleared funds HDFC BANK LIMITED Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement REST
```

**Leak 3** — Date: `03/05/25` | Keyword: `HDFC BANK LIMITED`
```
*Closing balance includes funds earmarked for hold and uncleared funds HDFC BANK LIMITED Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement tbra
```

**Leak 4** — Date: `29/05/25` | Keyword: `HDFC BANK LIMITED`
```
Contes of this statemen will be considered correct if ao error is reported within 30 days of receipt of statemea.The address on this staemeat is that ou secord with the Bank as at the day of requestig
```

**Leak 5** — Date: `02/05/25` | Keyword: `HDFC BANK LIMITED`
```
*Closing balance includes funds earmarked for hold and uncleared funds Coutens of this statement will be considered carrectif ao error is reported within 30 days of receipt of statemeat.The address HD
```

**Leak 6** — Date: `30/05/25` | Keyword: `HDFC BANK LIMITED`
```
HDFC BANK LIMITED *Closing balance includes funds earmarked for hold and uncleared funds Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement UPI-
```

**Leak 7** — Date: `06/05/25` | Keyword: `HDFC BANK LIMITED`
```
HDFC BANK LIMITED *Closing balance includes funds earmarked for hold and uncleared funds Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement t br
```

**Leak 8** — Date: `12/05/25` | Keyword: `HDFC BANK LIMITED`
```
*Closing balance includes funds earmarked for hold and uncleared funds HDFC BANK LIMITED Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement P-94
```

**Leak 9** — Date: `08/05/25` | Keyword: `HDFC BANK LIMITED`
```
*Closing balance includes funds earmarked for hold and uncleared funds HDFC BANK LIMITED Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg Lowe ParelMumbai 400013 State accou ns statement SAPK
```

**Leak 10** — Date: `22/05/25` | Keyword: `HDFC BANK LIMITED`
```
HDFC BANK LIMITED *Closing balance includes funds earmarked for hold and uncleared funds Contes of this statemen will be considered correct if ao error is reported within 30 days of receipt of statmea
```

---

## Root Causes (from prior investigation)

### ISSUE-HDFC-001: V2 Bypasses Header Suppression
- `header_suppression.py` is never called by `parse_with_coordinates` (V2)
- V2 takes raw tokens → `detect_rows()` → transaction groups directly
- The P1 suppression firewall is completely bypassed

### ISSUE-HDFC-002: Suppression Fails on OCR Noise
- Footer paragraphs are long and OCR-unstable
- "Contents" → "Contes", "statement" → "statemen", etc.
- Exact string match fails, so footer tokens survive suppression

### ISSUE-HDFC-003: Row Grouper Blind Append (The Core Bug)
```python
else:
    if current_block:
        current_block.append(row)   # NO ADMISSION TEST
```
- Any row without a date in date-zone is blindly appended to current block
- Footer rows (which have no date, no amounts) get swept into last transaction

---

## What Docling/MinerU Must Do to Win

For **ADD DOCLING/MINERU PRE-PROCESSOR** recommendation, they must:

| Requirement | Threshold |
|-------------|-----------|
| Footer leaks | < 10 (currently 10) |
| Transaction count | >= 102 (within 5 of 107) |
| Ledger pass% | >= 69.8% (within 5pp) |
| Tables detected | >= 1 per page |
| Processing time | < 300s (acceptable for batch) |

If an engine correctly isolates footer regions as non-transaction content,
AND preserves transaction count, it should be adopted as a pre-processing layer.

---

## Benchmark Protocol

For each engine:
1. Run independently on same HDFC PDF
2. Count footer elements classified correctly
3. Count footer strings leaking into non-footer content  
4. Count transaction-like rows extracted from table detection
5. Report processing time

**DO NOT** mix engine outputs or modify any production parser.
