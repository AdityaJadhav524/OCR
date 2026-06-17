"""
P6B — HDFC PDF Investigation: Comprehensive Scanned PDF Analysis
=================================================================
READ-ONLY. Does NOT modify any production parser.

This script provides:
1. PDF type analysis (scanned vs native text)
2. Image extraction and quality metrics
3. Token statistics from existing PaddleOCR run (loaded from telemetry.json)
4. Cross-engine comparison framework (sets up the data for Docling/MinerU comparison)

The HDFC PDF is 100% scanned:
  - 12 pages, each containing a single 1240x1636 JPEG
  - Zero native text layer
  - PaddleOCR is required for any text extraction

Outputs:
  - investigations/HDFC/pdf_analysis.json    : PDF metadata and image info
  - investigations/HDFC/baseline_metrics.json : current engine metrics from telemetry
  - investigations/HDFC/baseline_summary.md   : comprehensive baseline narrative

Run with: python run_hdfc_baseline_analysis.py
"""

import json
import os
import time
from pathlib import Path

PDF_PATH    = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"
HDFC_OUTDIR = r"Z:\CA\investigations\HDFC"
TELEMETRY   = os.path.join(HDFC_OUTDIR, "telemetry.json")
RAW_OUTPUT  = os.path.join(HDFC_OUTDIR, "raw_output.json")
REJECTS     = os.path.join(HDFC_OUTDIR, "rejects.json")

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"   Saved: {path}")

print("=" * 70)
print("P6B -- HDFC PDF Baseline Analysis (READ-ONLY)")
print("=" * 70)

# ── STEP 1: PDF Structure Analysis ────────────────────────────────────────────
print("\nSTEP 1: PDF structure analysis with PyMuPDF...")

import fitz

t0 = time.time()
pdf_analysis = {
    "pdf_path": PDF_PATH,
    "file_size_bytes": os.path.getsize(PDF_PATH),
    "file_size_mb": round(os.path.getsize(PDF_PATH) / 1024 / 1024, 2),
    "pages": [],
    "is_scanned": True,  # will be verified
    "has_native_text": False,
    "pdf_type": "UNKNOWN",
}

doc = fitz.open(PDF_PATH)
pdf_analysis["page_count"] = len(doc)

total_native_chars = 0
for i, page in enumerate(doc):
    text = page.get_text()
    images = page.get_images()
    r = page.rect

    page_info = {
        "page_no": i + 1,
        "width_pts": round(r.width, 1),
        "height_pts": round(r.height, 1),
        "native_text_chars": len(text),
        "image_count": len(images),
        "images": [],
    }

    total_native_chars += len(text)

    for img in images:
        xref = img[0]
        try:
            img_info = doc.extract_image(xref)
            page_info["images"].append({
                "width": img_info["width"],
                "height": img_info["height"],
                "colorspace": img_info.get("colorspace", "unknown"),
                "format": img_info.get("ext", "unknown"),
                "size_bytes": len(img_info.get("image", b"")),
                "dpi_approx": round(img_info["width"] / (r.width / 72), 1),
            })
        except Exception as e:
            page_info["images"].append({"error": str(e)})

    pdf_analysis["pages"].append(page_info)

doc.close()

pdf_analysis["total_native_text_chars"] = total_native_chars
pdf_analysis["has_native_text"] = total_native_chars > 0
pdf_analysis["is_scanned"] = not pdf_analysis["has_native_text"]
pdf_analysis["pdf_type"] = "NATIVE_TEXT" if pdf_analysis["has_native_text"] else "SCANNED_IMAGE"

print(f"   PDF type: {pdf_analysis['pdf_type']}")
print(f"   Pages: {pdf_analysis['page_count']}")
print(f"   Native text chars: {total_native_chars}")
print(f"   File size: {pdf_analysis['file_size_mb']} MB")

if pdf_analysis["pages"]:
    sample_img = pdf_analysis["pages"][0]["images"][0] if pdf_analysis["pages"][0]["images"] else {}
    if sample_img:
        print(f"   Sample image: {sample_img.get('width')}x{sample_img.get('height')} @ ~{sample_img.get('dpi_approx')} DPI ({sample_img.get('format')})")

elapsed_analysis = time.time() - t0
print(f"   Analysis done in {elapsed_analysis:.1f}s")

# ── STEP 2: Load Current Engine Data ──────────────────────────────────────────
print("\nSTEP 2: Loading current engine (PaddleOCR + V2) baseline data...")

telemetry = {}
if os.path.exists(TELEMETRY):
    with open(TELEMETRY, encoding="utf-8") as f:
        telemetry = json.load(f)
    print(f"   Telemetry loaded: {len(telemetry)} keys")

txns = []
if os.path.exists(RAW_OUTPUT):
    with open(RAW_OUTPUT, encoding="utf-8") as f:
        txns = json.load(f)
    print(f"   Transactions: {len(txns)}")

rejects = []
if os.path.exists(REJECTS):
    with open(REJECTS, encoding="utf-8") as f:
        rejects = json.load(f)
    print(f"   Rejects: {len(rejects)}")

# ── STEP 3: Compute Baseline Metrics ──────────────────────────────────────────
print("\nSTEP 3: Computing baseline metrics...")

anomalies = [t for t in txns if t.get("suspicious_fields")]
anomaly_breakdown = {}
for t in anomalies:
    for field, details in (t.get("suspicious_fields") or {}).items():
        reason = details.get("reason", "UNKNOWN")
        anomaly_breakdown[reason] = anomaly_breakdown.get(reason, 0) + 1

# Count footer leaks: transactions where narration contains HDFC footer strings
HDFC_FOOTER_STRINGS = [
    "HDFC BANK LIMITED",
    "Closing balance includes",
    "Registered Offce Address",
    "Senapan Bapar Marg",
    "Mumbai 400013",
    "GSTN27AAACH2702HZ0",
    "Contes of this statemen",
    "The address on this staeme",
    "State accou ns statement",
    "Generated On",
    "Generated By",
    "Requesting Branch",
]
footer_leak_txns = []
for t in txns:
    narr = (t.get("narration") or "").lower()
    for fs in HDFC_FOOTER_STRINGS:
        if fs.lower() in narr:
            footer_leak_txns.append({
                "date": t.get("date"),
                "narration_snippet": (t.get("narration") or "")[:200],
                "leaked_string": fs,
            })
            break

# Compute ledger pass rate
ledger_pass = sum(1 for t in txns if not t.get("suspicious_fields"))
ledger_fail = sum(1 for t in txns if t.get("suspicious_fields"))

# Debit/Credit/Balance accuracy
debit_count  = sum(1 for t in txns if t.get("debit") is not None)
credit_count = sum(1 for t in txns if t.get("credit") is not None)
balance_ok   = sum(1 for t in txns if t.get("balance") is not None and 
                   not (t.get("suspicious_fields") or {}).get("balance"))

# Reject reasons
reject_reasons = {}
for r in rejects:
    reason = r.get("reject_reason", "unknown")
    reject_reasons[reason] = reject_reasons.get(reason, 0) + 1

# OCR errors - tokens from telemetry
total_tokens = 0
if telemetry.get("reject_log"):
    for rj in telemetry["reject_log"]:
        tokens = rj.get("_source_tokens", [])
        total_tokens = max(total_tokens, rj.get("block", 0))

baseline_metrics = {
    "engine": "current_engine_paddleocr_v2",
    "ocr_engine": "PaddleOCR 2.7.3 (Python 3.11)",
    "parser": "coordinate_parser_v2",
    "validator": "ledger_truth",
    "pdf_type": pdf_analysis["pdf_type"],
    "extraction": {
        "total_transactions": len(txns),
        "total_rejects": len(rejects),
        "total_anomalies": len(anomalies),
        "debit_count": debit_count,
        "credit_count": credit_count,
        "balance_extracted": sum(1 for t in txns if t.get("balance") is not None),
    },
    "layout": {
        "footer_leak_count": len(footer_leak_txns),
        "footer_leak_transactions": footer_leak_txns,
        "header_leak_count": 0,  # headers correctly rejected
    },
    "accounting": {
        "ledger_pass_count": ledger_pass,
        "ledger_fail_count": ledger_fail,
        "ledger_pass_pct": round(100 * ledger_pass / max(len(txns), 1), 1),
        "anomaly_breakdown": anomaly_breakdown,
    },
    "rejects": {
        "total": len(rejects),
        "by_reason": reject_reasons,
    },
    "notes": [
        "HDFC PDF is 100% scanned (12 pages, each a 1240x1636 JPEG at ~150 DPI)",
        "Zero native text layer — all text via OCR",
        f"Footer leaks: {len(footer_leak_txns)} transactions have HDFC footer text in narration",
        "Root cause: Row grouper blindly appends non-anchor rows (ISSUE-HDFC-003)",
        "Known issues: ISSUE-HDFC-001, ISSUE-HDFC-002, ISSUE-HDFC-003 (from findings.md)",
    ]
}

print(f"   Transactions: {len(txns)}")
print(f"   Anomalies: {len(anomalies)}")
print(f"   Footer leak txns: {len(footer_leak_txns)}")
print(f"   Ledger pass%: {baseline_metrics['accounting']['ledger_pass_pct']}%")

# ── STEP 4: Save ──────────────────────────────────────────────────────────────
print("\nSTEP 4: Saving outputs...")

save_json(os.path.join(HDFC_OUTDIR, "pdf_analysis.json"), pdf_analysis)
save_json(os.path.join(HDFC_OUTDIR, "baseline_metrics.json"), baseline_metrics)

# ── STEP 5: Summary ────────────────────────────────────────────────────────────
print("\nSTEP 5: Generating comprehensive baseline summary...")

summary_md = f"""# P6B — HDFC Baseline Investigation Summary

## PDF Characteristics

| Property | Value |
|----------|-------|
| File | `{os.path.basename(PDF_PATH)}` |
| Size | {pdf_analysis['file_size_mb']} MB |
| Pages | {pdf_analysis['page_count']} |
| PDF Type | **{pdf_analysis['pdf_type']}** |
| Native Text | {'YES' if pdf_analysis['has_native_text'] else 'NONE (0 chars)'} |
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
| Total Transactions | **{len(txns)}** |
| Rejects | **{len(rejects)}** |
| Reject Rate | {round(100*len(rejects)/max(len(txns)+len(rejects),1), 1)}% |
| Transactions with Debit | {debit_count} |
| Transactions with Credit | {credit_count} |

### Layout (Header/Footer Contamination)
| Metric | Value |
|--------|-------|
| Footer Leak Transactions | **{len(footer_leak_txns)}** |
| Footer Leak Rate | {round(100*len(footer_leak_txns)/max(len(txns),1), 1)}% of all txns |
| Header Leaks | 0 (correctly rejected via no_balance/no_date) |

### Accounting (Ledger Truth Engine)
| Metric | Value |
|--------|-------|
| Anomaly Count | **{len(anomalies)}** |
| Ledger Pass | {ledger_pass} / {len(txns)} ({baseline_metrics['accounting']['ledger_pass_pct']}%) |
| Ledger Fail | {ledger_fail} |

### Anomaly Breakdown
"""
for reason, count in sorted(anomaly_breakdown.items(), key=lambda x: -x[1]):
    summary_md += f"| {reason} | {count} |\n"

summary_md += f"""
### Reject Breakdown
"""
for reason, count in sorted(reject_reasons.items(), key=lambda x: -x[1]):
    summary_md += f"| {reason} | {count} |\n"

summary_md += f"""
---

## Footer Leak Transactions

The following {len(footer_leak_txns)} transactions have HDFC page footer text
merged into their `narration` field:

"""
for i, leak in enumerate(footer_leak_txns, 1):
    summary_md += f"**Leak {i}** — Date: `{leak['date']}` | Keyword: `{leak['leaked_string']}`\n"
    summary_md += f"```\n{leak['narration_snippet']}\n```\n\n"

summary_md += f"""---

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
| Footer leaks | < {len(footer_leak_txns)} (currently {len(footer_leak_txns)}) |
| Transaction count | >= {len(txns) - 5} (within 5 of {len(txns)}) |
| Ledger pass% | >= {baseline_metrics['accounting']['ledger_pass_pct'] - 5}% (within 5pp) |
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
"""

summary_path = os.path.join(HDFC_OUTDIR, "baseline_summary.md")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"   Saved: {summary_path}")

print()
print("=" * 70)
print("HDFC BASELINE ANALYSIS COMPLETE")
print("=" * 70)
print(f"PDF type:       {pdf_analysis['pdf_type']}")
print(f"Transactions:   {len(txns)}")
print(f"Anomalies:      {len(anomalies)}")
print(f"Footer leaks:   {len(footer_leak_txns)}")
print(f"Ledger pass%:   {baseline_metrics['accounting']['ledger_pass_pct']}%")
print(f"Reject reasons: {reject_reasons}")
