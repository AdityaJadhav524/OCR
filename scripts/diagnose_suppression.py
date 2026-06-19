"""
Suppression Audit — BOI Digital
--------------------------------
No code changes. Evidence only.

Question:
  Do 403 tokens become 170 because the header row is suppressed?

Output: tests/audit_reports/boi_suppression_audit.json
"""

import sys, os, json, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PDF_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    "validation_lab", "backend", "temp",
    "11707454011-JUL-25221947 2.PDF"
)
PASSWORD = sys.argv[1] if len(sys.argv) > 1 else "1170AKSH"
OUT_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    "tests", "audit_reports", "boi_suppression_audit.json"
)

# ── Step 1: Extract tokens (same as API) ──────────────────────────────────────
print("Step 1: Extracting tokens via route_document...")
from core.extractors.document_router import route_document
full_text, pages, telemetry, page_tokens_before = route_document(PDF_PATH, password=PASSWORD)
print(f"  tokens BEFORE suppression : {len(page_tokens_before)}")

# ── Step 2: Apply suppression (same as API) ───────────────────────────────────
print("Step 2: Applying suppress_headers_and_footers...")
from core.detection.header_suppression import suppress_headers_and_footers
page_tokens_after = suppress_headers_and_footers(page_tokens_before)
print(f"  tokens AFTER  suppression : {len(page_tokens_after)}")
print(f"  tokens REMOVED            : {len(page_tokens_before) - len(page_tokens_after)}")

# ── Step 3: Find which tokens were removed ────────────────────────────────────
before_ids = set(id(t) for t in page_tokens_before)
after_ids  = set(id(t) for t in page_tokens_after)
removed_tokens = [t for t in page_tokens_before if id(t) not in after_ids]

print(f"\nStep 3: Auditing removed tokens...")
print(f"  Unique removed token texts (first 40):")
seen = set()
removed_unique = []
for t in removed_tokens:
    txt = t.get("text", "").strip()
    if txt and txt not in seen:
        seen.add(txt)
        removed_unique.append(txt)

for txt in removed_unique[:40]:
    print(f"    '{txt}'")

# ── Step 4: Check header row survival ─────────────────────────────────────────
HEADER_KEYWORDS = ["DATE", "PARTICULARS", "WITHDRAWAL", "DEPOSIT", "BALANCE"]

def find_header_row_in_tokens(tokens, label):
    """Scan through rows to find the transaction table header."""
    from core.layout.row_detector import detect_rows
    rows = detect_rows(tokens)
    for i, row in enumerate(rows):
        row_text = " ".join(t["text"].upper() for t in row.get("tokens", []))
        hits = [kw for kw in HEADER_KEYWORDS if kw in row_text]
        if len(hits) >= 3:
            return {
                "found": True,
                "row_index": i,
                "row_text": row_text,
                "keywords_matched": hits
            }
    return {"found": False, "row_index": None, "row_text": None, "keywords_matched": []}

print("\nStep 4: Searching for transaction header row...")
header_before = find_header_row_in_tokens(page_tokens_before, "BEFORE")
header_after  = find_header_row_in_tokens(page_tokens_after,  "AFTER")

print(f"  Header BEFORE suppression : found={header_before['found']}  row={header_before['row_index']}  text='{header_before['row_text']}'")
print(f"  Header AFTER  suppression : found={header_after['found']}   row={header_after['row_index']}  text='{header_after['row_text']}'")

# ── Step 5: What does the column detector select? ─────────────────────────────
print("\nStep 5: Column detector run on AFTER tokens...")
from core.layout.row_detector import detect_rows
rows_after = detect_rows(page_tokens_after)

from core.layout.column_detector import detect_columns
zones_after, header_tokens_after = detect_columns(rows_after)
header_text_selected = " ".join(t.get("text", "") for t in header_tokens_after[:20])

print(f"  Rows after suppression    : {len(rows_after)}")
print(f"  Zones created             : {zones_after}")
print(f"  Header tokens selected    : {len(header_tokens_after)}")
print(f"  Selected header text (20) : '{header_text_selected}'")

# ── Step 6: Verdict ───────────────────────────────────────────────────────────
if not header_before["found"]:
    verdict = "A) HEADER NEVER EXISTS IN RAW TOKENS — extraction bug upstream of suppression"
elif not header_after["found"] and header_before["found"]:
    verdict = "A) SUPPRESSION DELETED THE HEADER ROW — fix suppression, not the detector"
elif header_after["found"] and not zones_after:
    verdict = "B) HEADER SURVIVES SUPPRESSION BUT DETECTOR STILL FAILS — candidate ranking bug (Row-19 vs Row-24 issue)"
elif header_after["found"] and zones_after:
    verdict = "C) HEADER SURVIVES AND ZONES CREATED — some other runtime difference between diagnostic and API run"
else:
    verdict = "D) UNKNOWN — review full report"

print(f"\n{'='*60}")
print(f"VERDICT: {verdict}")
print(f"{'='*60}")

# ── Write report ──────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
report = {
    "pdf": PDF_PATH,
    "tokens_before_suppression": len(page_tokens_before),
    "tokens_after_suppression":  len(page_tokens_after),
    "tokens_removed":            len(page_tokens_before) - len(page_tokens_after),
    "removed_token_texts":       removed_unique,
    "header_row_before_suppression": header_before,
    "header_row_after_suppression":  header_after,
    "column_detector_after_suppression": {
        "rows_available": len(rows_after),
        "zones_created": zones_after,
        "header_tokens_selected_count": len(header_tokens_after),
        "header_text_selected": header_text_selected,
    },
    "verdict": verdict
}
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print(f"\nReport written to: {OUT_PATH}")
