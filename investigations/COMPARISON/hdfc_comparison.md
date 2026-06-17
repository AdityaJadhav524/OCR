# P6B — HDFC Footer Leakage Investigation: Comparison Report

## PDF Under Test
```
File:  JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf
Type:  SCANNED IMAGE (12 pages, 1240x1636 JPEG @ ~150 DPI)
Size:  1.69 MB
OCR:   MANDATORY for all engines
```

> [!IMPORTANT]
> This PDF has **zero native text**. All engines must run OCR internally.
> This is the highest-signal PDF for footer leakage investigation.

---

## Engine Comparison Matrix

| Metric | Current Engine | Docling | MinerU |
|--------|---------------|---------|--------|
| Total Transactions | **107** | N/A (pre-proc only) | N/A (pre-proc only) |
| Rejects | 14 | N/A | N/A |
| Anomalies | 27 | N/A | N/A |
| **Footer Leaks** | **10** | **PENDING** | **PENDING** |
| Header Leaks | 0 | TBD | TBD |
| Ledger Pass% | **74.8%** | N/A | N/A |
| Tables Detected | N/A | N/A | PENDING |
| Processing Time | ~120s (OCR) | TBD | TBD |

---

## Current Engine Detailed Results

### Extraction Metrics
- **Transactions**: 107
- **Rejects**: 14 ({'no_balance': 9, 'both_debit_and_credit': 2, 'no_date': 3})
- **Anomalies**: 27

### Footer Contamination
- **Footer leak count**: 10 out of 107 transactions (9.3%)
- **Root cause**: detect_transaction_blocks blindly appends footer rows (ISSUE-HDFC-003)
- **OCR noise**: Footer text varies per page (OCR instability in PaddleOCR)

### Accounting
- **Ledger Pass**: 74.8%
- **Top anomaly**: MULTIPLE_DOTS (comma read as dot in amounts like `728.662.39`)

---

## Docling Results

**Status**: PENDING — Docling installation in progress

Run:
```powershell
& 'Z:\CA\investigations\DOCLING\docling_env\Scripts\python' Z:\CA\investigations\DOCLING\run_docling_hdfc.py
```


---

## MinerU Results

**Status**: PENDING — MinerU installation required

Run:
```powershell
.\setup_mineru_env.ps1  # one-time setup (~4GB download)
& 'Z:\CA\investigations\MINERU\mineru_env\Scripts\python' Z:\CA\investigations\MINERU\run_mineru_hdfc.py
```


---

## Root Cause Analysis

### Why HDFC Has 10 Footer Leaks

**The HDFC footer block** (shown on each of 12 pages) contains:
```
HDFC BANK LIMITED
*Closing balance includes funds earmarked for hold and uncleared funds
Registered Office Address: HDFC Bank House, Senapati Bapat Marg,
Lower Parel, Mumbai 400013
[OCR-noisy disclaimer text]
GSTN:27AAACH2702HZ0
```

**Why it leaks into transactions:**
1. PaddleOCR reads footer images as text tokens
2. `header_suppression.py` exact-match fails (OCR noise makes each page slightly different)
3. `detect_transaction_blocks` appends any non-date-anchored row to the previous transaction
4. The last transaction on each page absorbs the entire footer

**What Docling/MinerU should solve:**
- Layout models are trained to recognize header/footer REGIONS, not just text patterns
- They should tag the bottom 12% of each page as `footer` type
- Our accounting engine would then skip `footer` labelled elements

---

## Recommendation Status

| Engine | Footer Leaks Solved? | Recommendation |
|--------|---------------------|----------------|
| Current Engine | BASELINE (10 leaks) | Keep as accounting layer |
| Docling | PENDING leaks | PENDING |
| MinerU | PENDING leaks | PENDING |

---

## File Index

| File | Description |
|------|-------------|
| `investigations/HDFC/findings.md` | Original investigation findings |
| `investigations/HDFC/baseline_summary.md` | P6B comprehensive baseline |
| `investigations/HDFC/baseline_metrics.json` | Structured metrics |
| `investigations/HDFC/raw_output.json` | 107 transactions from current engine |
| `investigations/HDFC/telemetry.json` | V2 parser telemetry |
| `investigations/HDFC/pdf_analysis.json` | PDF structure analysis |
| `investigations/DOCLING/HDFC/summary.md` | Docling findings |
| `investigations/DOCLING/HDFC/layout.json` | Docling layout classification |
| `investigations/MINERU/HDFC/summary.md` | MinerU findings |
| `investigations/COMPARISON/hdfc_comparison.md` | This file |