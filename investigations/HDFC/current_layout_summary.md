# P6B — Current Engine Layout Baseline: HDFC PDF

## Engine
**Current Engine** — pdfplumber geometry analysis (READ-ONLY, no parser modification)
- pdfplumber extraction time: 0.0s

## PDF Analysed
`JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf`

## From Existing Investigation (run_investigation.py output)

| Metric | Value |
|--------|-------|
| Transactions extracted | 107 |
| Rejects | 14 |
| Anomalies (suspicious_fields) | 27 |
| Footer leaks (known) | 10 |

## Layout Geometry (pdfplumber)

| Metric | Value |
|--------|-------|
| Total words extracted | 0 |
| Header-classified lines | 0 |
| Footer-classified lines | 0 |
| Body lines | 0 |
| Tables detected | 0 |
| Footer leaks (geo analysis) | **0** |

## Page Statistics

**page_1**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_10**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_11**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_12**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_2**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_3**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_4**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_5**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_6**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_7**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_8**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables
**page_9**: 0 words | 0 header lines | 0 footer lines | 0 body lines | 0 tables

## Footer Leak Analysis
Footer-text found OUTSIDE footer zone (y_frac < 0.88): **0**

## Tables (pdfplumber)
Tables detected: **0**

## Root Cause Summary (from prior investigation)

### ISSUE-HDFC-001: Footer Merging into Narration
- V2 bypasses header_suppression.py entirely
- Row detector blindly appends non-anchor rows to current transaction block

### ISSUE-HDFC-002: Suppression Algorithm Failure
- Exact string match fails due to OCR noise in footer text
- Footer paragraphs are long and OCR-unstable

### ISSUE-HDFC-003: Row Grouping Vulnerability
- detect_transaction_blocks has no admission test for continuation rows
- Any row without a date in date-zone is blindly appended

## This is the Baseline for Docling/MinerU Comparison

| Metric | Current Engine |
|--------|---------------|
| Footer leaks (investigation) | 10 |
| Footer leaks (geometry) | 0 |
| Tables detected (pdfplumber) | 0 |
| Transaction count | 107 |