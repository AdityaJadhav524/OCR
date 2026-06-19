"""
Cross-Bank Suppression Risk Audit
----------------------------------
No code changes. Evidence only.

For each benchmark PDF (digital, non-password):
  - Count tokens before/after suppression
  - List any structural column-header keywords that get suppressed
  - Report verdict per PDF

Output: tests/audit_reports/cross_bank_suppression_risk.json
"""

import sys, os, json, re
from collections import defaultdict
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

STRUCTURAL_KEYWORDS = {"DATE", "BALANCE", "DEPOSIT", "WITHDRAWAL",
                       "PARTICULARS", "AMOUNT", "DEBIT", "CREDIT",
                       "NARRATION", "DESCRIPTION", "TRANSACTION"}

TEMP_DIR  = os.path.join(os.path.dirname(__file__), "..", "validation_lab", "backend", "temp")
OUT_PATH  = os.path.join(os.path.dirname(__file__), "..", "tests", "audit_reports", "cross_bank_suppression_risk.json")

# ── PDFs to audit (latest named copies, no password needed) ──────────────────
PDFS = [
    # (label, filename, password_or_None)
    # BOI_SAVINGS_SCANNED skipped — goes through PaddleOCR subprocess (too slow for audit)
    ("YESBANK_SAVINGS",       "JOB_20260618_122213_4B2B_YESBANK_SAVINGS_DIGITAL.pdf", None),
    ("ICICI_CC_DIGITAL_1",    "JOB_20260618_102941_061C_ICICI_1.pdf",                 None),
    ("ICICI_CC_DIGITAL_2",    "JOB_20260618_103128_86CE_ICICI_2.pdf",                 None),
    ("HDFC_SAVINGS_SCANNED",  "JOB_20260618_115001_5E18_HDFC_SAVINGS_SCANNED.pdf",    None),
]

SUPPRESSION_KEYWORDS = ["Bank", "IFSC", "MICR", "Page", "Statement",
                        "Account", "Currency", "Customer", "Nomination"]

def normalize_text(t_str):
    t_str = re.sub(r"(?i)page\s+\d+\s+of\s+\d+", "PAGE_N", t_str)
    t_str = re.sub(r"(?i)page\s+no\.?\s*\d+",     "PAGE_N", t_str)
    t_str = re.sub(r"(?i)page\s+\d+",             "PAGE_N", t_str)
    return t_str

def score_suppression(tokens):
    """Replicate the suppression logic and return per-token verdict."""
    pages = set(t.get("page", 0) for t in tokens)
    num_pages = len(pages)
    if num_pages < 2:
        return set(), num_pages

    page_bounds = {}
    for p in pages:
        pt = [t for t in tokens if t.get("page", 0) == p]
        page_bounds[p] = (
            min(t.get("y0", 0) for t in pt),
            max(t.get("y1", 0) for t in pt)
        )

    text_to_tokens = defaultdict(list)
    for t in tokens:
        txt = str(t.get("text", "")).strip()
        if txt:
            text_to_tokens[normalize_text(txt)].append(t)

    suppressed = set()
    for text, tkns in text_to_tokens.items():
        pa = len(set(t.get("page", 0) for t in tkns))
        if pa < 2:
            continue
        score = 0
        if pa / num_pages > 0.70:
            score += 3
        top_bottom = sum(
            1 for t in tkns
            if (p := t.get("page", 0)) in page_bounds and (
                h := page_bounds[p][1] - page_bounds[p][0]
            ) > 0 and (
                ((t.get("y0", 0) + t.get("y1", 0)) / 2 - page_bounds[p][0]) / h <= 0.15
                or
                ((t.get("y0", 0) + t.get("y1", 0)) / 2 - page_bounds[p][0]) / h >= 0.85
            )
        )
        if top_bottom / len(tkns) > 0.5:
            score += 2
        text_upper = text.upper()
        for kw in SUPPRESSION_KEYWORDS:
            if kw.upper() in text_upper:
                score += 2
        if score >= 5:
            suppressed.add(text)
    return suppressed, num_pages

from core.extractors.document_router import route_document
from core.detection.header_suppression import suppress_headers_and_footers
from core.layout.row_detector import detect_rows

results = []

for label, filename, password in PDFS:
    pdf_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(pdf_path):
        print(f"  SKIP {label}: file not found")
        results.append({"label": label, "status": "FILE_NOT_FOUND"})
        continue

    print(f"\nAuditing: {label}")
    try:
        _, _, _, tokens_before = route_document(pdf_path, password=password)
    except Exception as e:
        print(f"  ERROR extracting: {e}")
        results.append({"label": label, "status": f"EXTRACTION_ERROR: {e}"})
        continue

    tokens_after = suppress_headers_and_footers(tokens_before)
    suppressed_texts, num_pages = score_suppression(tokens_before)

    # Which structural keywords were suppressed?
    structural_removed = []
    for text in suppressed_texts:
        if text.upper() in STRUCTURAL_KEYWORDS:
            structural_removed.append(text)

    # Does the header row survive suppression?
    def find_header(tokens):
        rows = detect_rows(tokens)
        for i, row in enumerate(rows):
            row_text = " ".join(t["text"].upper() for t in row.get("tokens", []))
            hits = [kw for kw in STRUCTURAL_KEYWORDS if kw in row_text]
            if len(hits) >= 3:
                return {"found": True, "row_index": i, "row_text": row_text[:200], "keywords": hits}
        return {"found": False}

    header_before = find_header(tokens_before)
    header_after  = find_header(tokens_after)

    if structural_removed:
        verdict = "AT_RISK: Structural column keywords suppressed"
    elif header_before["found"] and not header_after["found"]:
        verdict = "AT_RISK: Header row lost during suppression (non-keyword tokens removed)"
    elif not header_before["found"]:
        verdict = "NO_HEADER_FOUND: Header detection fails even before suppression"
    else:
        verdict = "SAFE: Header survives suppression intact"

    print(f"  pages          : {num_pages}")
    print(f"  tokens before  : {len(tokens_before)}")
    print(f"  tokens after   : {len(tokens_after)}")
    print(f"  tokens removed : {len(tokens_before) - len(tokens_after)}")
    print(f"  structural kws removed: {structural_removed}")
    print(f"  header before  : {header_before.get('row_text', 'NOT FOUND')[:80]}")
    print(f"  header after   : {header_after.get('row_text', 'NOT FOUND')[:80]}")
    print(f"  VERDICT        : {verdict}")

    results.append({
        "label": label,
        "num_pages": num_pages,
        "tokens_before": len(tokens_before),
        "tokens_after": len(tokens_after),
        "tokens_removed": len(tokens_before) - len(tokens_after),
        "structural_keywords_suppressed": structural_removed,
        "header_before_suppression": header_before,
        "header_after_suppression": header_after,
        "verdict": verdict,
    })

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\n\nCROSS-BANK SUMMARY")
print("="*60)
for r in results:
    print(f"  {r['label']:30s} → {r.get('verdict', r.get('status'))}")
print(f"\nReport: {OUT_PATH}")
