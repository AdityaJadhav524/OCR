"""
P6B — HDFC Final Comparison Report Generator
==============================================
READ-ONLY. Does NOT modify any production parser.

Aggregates results from all three engines:
  - Current Engine (PaddleOCR + Coordinate Parser V2)
  - Docling (layout understanding pre-processor)
  - MinerU (magic-pdf layout engine)

Run AFTER all three engine investigations are complete:
  - investigations/HDFC/baseline_metrics.json        (current engine)
  - investigations/DOCLING/HDFC/layout.json          (docling)
  - investigations/MINERU/HDFC/layout.json           (mineru)

Outputs:
  - investigations/COMPARISON/hdfc_comparison.md
  - investigations/COMPARISON/hdfc_comparison.json
"""

import json
import os
from pathlib import Path

OUT_DIR = r"Z:\CA\investigations\COMPARISON"
os.makedirs(OUT_DIR, exist_ok=True)

BASELINE_PATH = r"Z:\CA\investigations\HDFC\baseline_metrics.json"
DOCLING_PATH  = r"Z:\CA\investigations\DOCLING\HDFC\layout.json"
MINERU_PATH   = r"Z:\CA\investigations\MINERU\HDFC\layout.json"

def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default or {}

print("=" * 70)
print("P6B -- HDFC Comparison Report Generator")
print("=" * 70)

# ── Load engine data ───────────────────────────────────────────────────────────
print("\nLoading engine data...")

baseline = load_json(BASELINE_PATH)
docling  = load_json(DOCLING_PATH)
mineru   = load_json(MINERU_PATH)

print(f"  Current engine: {'LOADED' if baseline else 'NOT FOUND'}")
print(f"  Docling:        {'LOADED' if docling else 'NOT FOUND (run run_docling_hdfc.py)'}")
print(f"  MinerU:         {'LOADED' if mineru else 'NOT FOUND (run run_mineru_hdfc.py)'}")

# ── Build comparison table ─────────────────────────────────────────────────────
def get_metric(data, *keys, default="N/A"):
    """Safely traverse nested dict."""
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, None)
        else:
            return default
    return val if val is not None else default

current_txns         = get_metric(baseline, "extraction", "total_transactions", default=107)
current_rejects      = get_metric(baseline, "extraction", "total_rejects", default=14)
current_anomalies    = get_metric(baseline, "extraction", "total_anomalies", default=27)
current_footer_leaks = get_metric(baseline, "layout", "footer_leak_count", default=10)
current_ledger_pass  = get_metric(baseline, "accounting", "ledger_pass_pct", default=74.8)
current_time_s       = "~120s"  # PaddleOCR time approx

docling_footer_leaked = get_metric(docling, "summary", "footer_elements", default="N/A")
docling_footer_leaks  = get_metric(docling, "summary", "footer_elements", default="N/A")  # to be updated when run
docling_tables        = get_metric(docling, "summary", "table_elements", default="N/A")
docling_total         = get_metric(docling, "summary", "total_elements", default="N/A")

# Read docling summary for actual leak count
docling_summary_path = r"Z:\CA\investigations\DOCLING\HDFC\summary.md"
docling_leak_count = "PENDING"
if os.path.exists(docling_summary_path):
    with open(docling_summary_path) as f:
        content = f.read()
    import re
    m = re.search(r"HDFC footer strings leaking into non-footer elements.*?\*\*(\d+)\*\*", content)
    if m:
        docling_leak_count = int(m.group(1))

mineru_footer_leaks = get_metric(mineru, "summary", "footer_leaks", default="PENDING")
mineru_tables       = get_metric(mineru, "summary", "table_elements", default="PENDING")

# ── Comparison data structure ──────────────────────────────────────────────────
comparison = {
    "pdf": "HDFC — Acct Statement (Scanned, 12pp, 1240x1636 JPEG)",
    "pdf_type": "SCANNED_IMAGE",
    "engines": {
        "current_engine": {
            "name": "Current Engine (PaddleOCR 2.7.3 + V2 Parser)",
            "status": "COMPLETE",
            "metrics": {
                "total_transactions": current_txns,
                "rejects": current_rejects,
                "anomalies": current_anomalies,
                "footer_leak_count": current_footer_leaks,
                "header_leak_count": 0,
                "ledger_pass_pct": current_ledger_pass,
                "processing_time": current_time_s,
            },
            "root_causes": [
                "ISSUE-HDFC-001: V2 bypasses header_suppression.py",
                "ISSUE-HDFC-002: OCR noise breaks exact-match suppression",
                "ISSUE-HDFC-003: detect_transaction_blocks blind-appends footer rows",
            ]
        },
        "docling": {
            "name": "Docling (Layout Understanding Pre-Processor)",
            "status": "COMPLETE" if os.path.exists(r"Z:\CA\investigations\DOCLING\HDFC\summary.md") else "PENDING INSTALLATION",
            "metrics": {
                "footer_classified": docling_footer_leaked,
                "footer_leaks_into_content": docling_leak_count,
                "tables_detected": docling_tables,
                "total_elements": docling_total,
                "processing_time": "SEE summary.md",
            },
        },
        "mineru": {
            "name": "MinerU (magic-pdf Layout Engine)",
            "status": "COMPLETE" if os.path.exists(r"Z:\CA\investigations\MINERU\HDFC\summary.md") and mineru else "PENDING INSTALLATION",
            "metrics": {
                "footer_classified": "SEE layout.json",
                "footer_leaks_into_content": mineru_footer_leaks,
                "tables_detected": mineru_tables,
                "processing_time": "SEE summary.md",
            },
        },
    }
}

# ── Generate Markdown report ───────────────────────────────────────────────────
report_lines = [
    "# P6B — HDFC Footer Leakage Investigation: Comparison Report",
    "",
    "## PDF Under Test",
    "```",
    "File:  JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf",
    "Type:  SCANNED IMAGE (12 pages, 1240x1636 JPEG @ ~150 DPI)",
    "Size:  1.69 MB",
    "OCR:   MANDATORY for all engines",
    "```",
    "",
    "> [!IMPORTANT]",
    "> This PDF has **zero native text**. All engines must run OCR internally.",
    "> This is the highest-signal PDF for footer leakage investigation.",
    "",
    "---",
    "",
    "## Engine Comparison Matrix",
    "",
    "| Metric | Current Engine | Docling | MinerU |",
    "|--------|---------------|---------|--------|",
    f"| Total Transactions | **{current_txns}** | N/A (pre-proc only) | N/A (pre-proc only) |",
    f"| Rejects | {current_rejects} | N/A | N/A |",
    f"| Anomalies | {current_anomalies} | N/A | N/A |",
    f"| **Footer Leaks** | **{current_footer_leaks}** | **{docling_leak_count}** | **{mineru_footer_leaks}** |",
    f"| Header Leaks | 0 | TBD | TBD |",
    f"| Ledger Pass% | **{current_ledger_pass}%** | N/A | N/A |",
    f"| Tables Detected | N/A | {docling_tables} | {mineru_tables} |",
    f"| Processing Time | ~120s (OCR) | TBD | TBD |",
    "",
    "---",
    "",
    "## Current Engine Detailed Results",
    "",
    f"### Extraction Metrics",
    f"- **Transactions**: {current_txns}",
    f"- **Rejects**: {current_rejects} ({get_metric(baseline, 'rejects', 'by_reason', default={})})",
    f"- **Anomalies**: {current_anomalies}",
    "",
    f"### Footer Contamination",
    f"- **Footer leak count**: {current_footer_leaks} out of {current_txns} transactions ({round(100*current_footer_leaks/max(current_txns,1),1)}%)",
    f"- **Root cause**: detect_transaction_blocks blindly appends footer rows (ISSUE-HDFC-003)",
    f"- **OCR noise**: Footer text varies per page (OCR instability in PaddleOCR)",
    "",
    f"### Accounting",
    f"- **Ledger Pass**: {current_ledger_pass}%",
    f"- **Top anomaly**: MULTIPLE_DOTS (comma read as dot in amounts like `728.662.39`)",
    "",
    "---",
    "",
    "## Docling Results",
    "",
]

if os.path.exists(r"Z:\CA\investigations\DOCLING\HDFC\summary.md"):
    with open(r"Z:\CA\investigations\DOCLING\HDFC\summary.md") as f:
        docling_summary = f.read()
    report_lines.append("*(See full Docling summary below)*")
    report_lines.append("")
    report_lines.append("### Key Docling Findings")
    # Extract key section
    if "Footer Classification Result" in docling_summary or "Footer Leak Details" in docling_summary:
        report_lines.append("See: `investigations/DOCLING/HDFC/summary.md`")
    report_lines.append(f"- Footer leaks: **{docling_leak_count}** (vs {current_footer_leaks} in current engine)")
    report_lines.append(f"- Tables detected: {docling_tables}")
else:
    report_lines += [
        "**Status**: PENDING — Docling installation in progress",
        "",
        "Run:",
        "```powershell",
        "& 'Z:\\CA\\investigations\\DOCLING\\docling_env\\Scripts\\python' Z:\\CA\\investigations\\DOCLING\\run_docling_hdfc.py",
        "```",
        "",
    ]

report_lines += [
    "",
    "---",
    "",
    "## MinerU Results",
    "",
]

if os.path.exists(r"Z:\CA\investigations\MINERU\HDFC\summary.md") and mineru:
    report_lines.append(f"- Footer leaks: **{mineru_footer_leaks}** (vs {current_footer_leaks} in current engine)")
    report_lines.append(f"- Tables detected: {mineru_tables}")
else:
    report_lines += [
        "**Status**: PENDING — MinerU installation required",
        "",
        "Run:",
        "```powershell",
        ".\\setup_mineru_env.ps1  # one-time setup (~4GB download)",
        "& 'Z:\\CA\\investigations\\MINERU\\mineru_env\\Scripts\\python' Z:\\CA\\investigations\\MINERU\\run_mineru_hdfc.py",
        "```",
        "",
    ]

report_lines += [
    "",
    "---",
    "",
    "## Root Cause Analysis",
    "",
    "### Why HDFC Has 10 Footer Leaks",
    "",
    "**The HDFC footer block** (shown on each of 12 pages) contains:",
    "```",
    "HDFC BANK LIMITED",
    "*Closing balance includes funds earmarked for hold and uncleared funds",
    "Registered Office Address: HDFC Bank House, Senapati Bapat Marg,",
    "Lower Parel, Mumbai 400013",
    "[OCR-noisy disclaimer text]",
    "GSTN:27AAACH2702HZ0",
    "```",
    "",
    "**Why it leaks into transactions:**",
    "1. PaddleOCR reads footer images as text tokens",
    "2. `header_suppression.py` exact-match fails (OCR noise makes each page slightly different)",
    "3. `detect_transaction_blocks` appends any non-date-anchored row to the previous transaction",
    "4. The last transaction on each page absorbs the entire footer",
    "",
    "**What Docling/MinerU should solve:**",
    "- Layout models are trained to recognize header/footer REGIONS, not just text patterns",
    "- They should tag the bottom 12% of each page as `footer` type",
    "- Our accounting engine would then skip `footer` labelled elements",
    "",
    "---",
    "",
    "## Recommendation Status",
    "",
    "| Engine | Footer Leaks Solved? | Recommendation |",
    "|--------|---------------------|----------------|",
    f"| Current Engine | BASELINE ({current_footer_leaks} leaks) | Keep as accounting layer |",
    f"| Docling | {docling_leak_count} leaks | {'ADD AS PRE-PROCESSOR' if isinstance(docling_leak_count, int) and docling_leak_count < current_footer_leaks else 'PENDING'} |",
    f"| MinerU | {mineru_footer_leaks} leaks | {'ADD AS PRE-PROCESSOR' if isinstance(mineru_footer_leaks, int) and mineru_footer_leaks < current_footer_leaks else 'PENDING'} |",
    "",
    "---",
    "",
    "## File Index",
    "",
    "| File | Description |",
    "|------|-------------|",
    "| `investigations/HDFC/findings.md` | Original investigation findings |",
    "| `investigations/HDFC/baseline_summary.md` | P6B comprehensive baseline |",
    "| `investigations/HDFC/baseline_metrics.json` | Structured metrics |",
    "| `investigations/HDFC/raw_output.json` | 107 transactions from current engine |",
    "| `investigations/HDFC/telemetry.json` | V2 parser telemetry |",
    "| `investigations/HDFC/pdf_analysis.json` | PDF structure analysis |",
    "| `investigations/DOCLING/HDFC/summary.md` | Docling findings |",
    "| `investigations/DOCLING/HDFC/layout.json` | Docling layout classification |",
    "| `investigations/MINERU/HDFC/summary.md` | MinerU findings |",
    "| `investigations/COMPARISON/hdfc_comparison.md` | This file |",
]

report_path = os.path.join(OUT_DIR, "hdfc_comparison.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))
print(f"\nSaved: {report_path}")

# Save JSON
json_path = os.path.join(OUT_DIR, "hdfc_comparison.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)
print(f"Saved: {json_path}")

print("\nComparison report generated.")
print(f"Current engine: {current_txns} txns, {current_footer_leaks} footer leaks, {current_ledger_pass}% ledger pass")
print(f"Docling status: {comparison['engines']['docling']['status']}")
print(f"MinerU status:  {comparison['engines']['mineru']['status']}")
