# P6B — HDFC Footer Leakage Investigation: Full Findings

## Investigation Overview

**Phase:** P6B — External Layout Engine Evaluation  
**Goal:** HDFC Footer Leakage Investigation  
**Status:** Baseline complete. Docling/MinerU runs pending.  
**Priority:** HIGHEST — footer leakage is the primary failure mode for this PDF.

---

## PDF Characteristics

| Property | Value |
|----------|-------|
| File | `JOB_20260614_233121_48AC_Acct Statement_3644...pdf` |
| Size | 1.69 MB |
| Pages | 12 |
| **PDF Type** | **SCANNED_IMAGE** (zero native text) |
| Image Format | JPEG 1240×1636 px (~150 DPI) per page |
| OCR Required | **YES — mandatory for ALL engines** |

> **CRITICAL DISCOVERY (P6B)**: The HDFC PDF has absolutely zero native text.
> Every page is a single full-page JPEG scan. This means:
> - pdfplumber → extracts **0 words**
> - PyMuPDF → extracts **0 chars**
> - **All engines must OCR the images** before any layout analysis can occur
> - The quality of OCR on these ~150 DPI JPEGs directly determines downstream quality

---

## Current Engine Baseline (PaddleOCR 2.7.3 + Coordinate Parser V2)

### Extraction Metrics

| Metric | Value |
|--------|-------|
| Total Transactions | **107** |
| Rejects | **14** (11.6%) |
| Anomalies | **27** (25.2%) |
| Transactions with Debit | 101 |
| Transactions with Credit | 6 |

### Reject Breakdown

| Reason | Count |
|--------|-------|
| no_balance | 9 |
| no_date | 3 |
| both_debit_and_credit | 2 |

### Layout Contamination

| Metric | Value |
|--------|-------|
| **Footer Leak Transactions** | **10 / 107 (9.3%)** |
| Header Leaks | 0 (correctly filtered) |
| Footer leak rate | 1 per page (approximately) |

### Accounting (Ledger Truth Engine)

| Metric | Value |
|--------|-------|
| Ledger Pass | 80 / 107 (**74.8%**) |
| Ledger Fail (anomalous) | 27 |
| PRIMARY_BALANCE_ANOMALY | 15 |
| MULTIPLE_DOTS | 11 |
| POWER_OF_TEN_DRIFT | 2 |
| DATE_NARRATION_MERGE | 1 |

---

## Root Cause Analysis

### ISSUE-HDFC-001 — V2 Bypasses Header Suppression
**Severity:** CRITICAL  
**Effect:** 10 footer leaks

`header_suppression.py` (built in Phase P1) is NEVER called by `parse_with_coordinates` (V2).
The V2 path is: `raw tokens → detect_rows() → transaction blocks → extraction`.
The P1 suppression firewall is completely bypassed.

### ISSUE-HDFC-002 — OCR Noise Breaks Exact-Match Suppression
**Severity:** HIGH  
**Effect:** Even if suppression were called, it would fail

The HDFC footer block reads differently on each page due to OCR instability:
```
Page 1:  "Contents of this statement will be considered correct..."
Page 5:  "Contes of this statemen will be considered correct..."
Page 9:  "Coutens of this statement will be considered carrect..."
```
The exact-match algorithm requires ≥2 identical pages to classify a block as repeated.
OCR noise prevents exact match → footer tokens survive suppression.

### ISSUE-HDFC-003 — Row Grouper Blind Append (The Core Bug)
**Severity:** CRITICAL  
**Effect:** Footer absorbed into last transaction on each page

```python
# core/layout/row_detector.py — detect_transaction_blocks()
else:
    if current_block:
        current_block.append(row)   # <--- BLIND APPEND, NO ADMISSION TEST
```

Footer rows have: no date in date-zone, no amounts in amount columns.
Yet `detect_transaction_blocks` has **no admission test** for continuation rows.
Any non-anchor row is blindly appended to the current block.

**Result**: The last transaction on each page absorbs the entire page footer:
```
Txn Date: 22/05/25
Narration: "HDFC BANK LIMITED *Closing balance includes funds earmarked...
            Registered Offce AddressHDFC Bank HouseSenapan Bapar Marg
            Lowe ParelMumbai 400013...GSTN27AAACH2702HZ0
            UPI-POCKIT TECHNOLOGIES 22/05/25"
```

---

## Footer Leak Evidence (10 Confirmed)

All 10 leaks follow the same pattern: last transaction on a page absorbs footer.

| # | Date | Footer Keyword | Page |
|---|------|---------------|------|
| 1 | 17/05/25 | HDFC BANK LIMITED | 3 |
| 2 | 27/05/25 | HDFC BANK LIMITED | 6 |
| 3 | 03/05/25 | HDFC BANK LIMITED | 7 |
| 4 | 29/05/25 | Contes of this statemen | 8 |
| 5 | 02/05/25 | Coutens of this statement | 9 |
| 6 | 30/05/25 | HDFC BANK LIMITED | 10 |
| 7 | 06/05/25 | HDFC BANK LIMITED | 11 |
| 8 | 12/05/25 | HDFC BANK LIMITED | 4 |
| 9 | 08/05/25 | HDFC BANK LIMITED | 5 |
| 10 | 22/05/25 | HDFC BANK LIMITED | 6 |

---

## What Docling/MinerU Must Prove

For a **ADD PRE-PROCESSOR** recommendation, each engine must demonstrate:

| Requirement | Threshold |
|-------------|-----------|
| Footer leaks eliminated | < 10 (currently 10) |
| Transaction count preserved | ≥ 102 transactions |
| Ledger pass% not degraded | ≥ 70% |
| Tables per page detected | ≥ 1 |
| Processing time | < 300 seconds |

**Key question**: If a layout engine correctly labels the bottom ~12% of each page
as `footer`, and we skip those tokens before running the accounting parser,
do the 10 footer leak transactions become clean?

**Expected answer**: YES — if the OCR tokens in the footer zone are tagged as
`footer` class, our row detector would not receive them as candidates, and the
blind-append bug becomes irrelevant for those rows.

---

## Docling Investigation

**Status:** Installation in progress (`docling_env` venv)  
**Script:** `investigations/DOCLING/run_docling_hdfc.py`  
**Environment:** Python 3.14 + Docling ≥ 2.59.0 (isolated venv)

**Docling approach**: Uses DocLayNet-trained layout model to classify PDF regions into:
- `text`, `title`, `section_header`, `list_item`, `table`, `figure`, `formula`,
- `page_header`, `page_footer`, `caption`, `footnote`

**What we expect**: Docling's `page_footer` classification will capture the HDFC
footer block that our PaddleOCR pipeline currently fails to isolate.

**Limitation**: Docling must also run OCR on this scanned PDF — it uses EasyOCR
internally. OCR quality vs PaddleOCR is an open question.

**Results**: PENDING

---

## MinerU Investigation

**Status:** Installation pending (requires Python 3.10-3.12 + ~4GB model weights)  
**Script:** `investigations/MINERU/run_mineru_hdfc.py`  
**Environment:** Uses Python 3.11 from existing `ocr_legacy_env`

**MinerU approach**: Uses PaddleOCR-based OCR + DocLayout-YOLO model for layout detection.  
Specifically designed to remove headers, footers, footnotes, and page numbers.

**Key advantage over Docling**: MinerU's primary design goal includes
"automatically remove headers, footers, footnotes, and page numbers" — this
is precisely what we need for the HDFC footer leakage problem.

**Results**: PENDING

---

## Pending Investigation Steps

- [ ] Complete Docling installation → run `run_docling_hdfc.py`
- [ ] Set up MinerU environment → run `run_mineru_hdfc.py`
- [ ] Regenerate `COMPARISON/hdfc_comparison.md` with all three engines
- [ ] Determine if Docling/MinerU footer classification eliminates the 10 leaks
- [ ] Assess OCR quality (Docling vs PaddleOCR) on ~150 DPI JPEG scans
- [ ] Final recommendation: KEEP / ADD DOCLING / ADD MINERU / HYBRID

---

## Files Index

| File | Description |
|------|-------------|
| `findings.md` | This file — consolidated P6B HDFC findings |
| `baseline_summary.md` | P6B comprehensive baseline narrative |
| `baseline_metrics.json` | Structured metrics from current engine |
| `pdf_analysis.json` | PDF structure: scanned, 1240×1636 JPEG |
| `current_layout.json` | pdfplumber output (empty — scanned PDF) |
| `current_layout_summary.md` | Layout baseline (confirms scanned) |
| `raw_output.json` | 107 transactions from current engine |
| `telemetry.json` | V2 parser telemetry (5 keys) |
| `rejects.json` | 14 rejected transaction blocks |
| `anomaly_report.md` | 27 anomalies with suspicious_fields |
| `footer_leak_coordinates.json` | Exact coordinates of leaked footer tokens |
| `continuation_dataset.json` | Row continuation analysis data |

---

## Data Quality Notes

### MULTIPLE_DOTS Anomaly (11 occurrences)
The OCR reads Indian comma-separated numbers as dots:
- `728,662.39` → OCR reads → `728.662.39` → parsed as `728.66239` (wrong)
- This is a systematic OCR failure on the JPEG compression artifacts
- Affects balance column most severely

### PRIMARY_BALANCE_ANOMALY (15 occurrences)  
Large unexplained ledger drifts are caused by:
1. Footer-contaminated narrations disrupting transaction ordering
2. Multi-page transaction blocks losing their place in the sequence
3. OCR-noisy balances combining with the ordering confusion

### POWER_OF_TEN_DRIFT (2 occurrences)
Single digit substitution in OCR (e.g., `0` read as `9` in amounts):
- Difference of 10.0 → magnitude 1 (single digit)
- Difference of 9900.0 → magnitude 4 (likely `10000` read as `100`)

---

## Provisional Conclusion (Pending Docling/MinerU Results)

The HDFC footer leakage is entirely a **layout classification problem**, not
an OCR accuracy problem. The OCR reads the footer correctly — the text is there.
The failure is that no component correctly classifies those tokens as
`footer/non-transaction` before they enter the row grouping pipeline.

A layout engine (Docling or MinerU) that can tag footer regions geometrically
would — in theory — eliminate all 10 leaks without any modification to the
current accounting engine.

**Expected result**: ADD DOCLING or ADD MINERU as pre-processor for HDFC-type PDFs.
