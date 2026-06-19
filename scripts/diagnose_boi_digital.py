"""
Diagnostic script: BOI Digital Header Detection Trace
------------------------------------------------------
No code changes. Evidence only.

Outputs to: tests/audit_reports/boi_digital_token_dump.json

Structure:
  top_100_tokens_page1  - first 100 tokens on page 1, sorted by y then x
  top_100_tokens_page2  - first 100 tokens on page 2
  header_window         - the 6-row window the detector searched in
  header_candidates     - every row with the reason it passed/failed the 3-condition gate
  final_header_tokens   - tokens selected as header (empty if none)
  found_date / found_amount / found_balance
  column_detector_reason - plain-English verdict
"""

import sys, os, json

# Make sure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PDF_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    "validation_lab", "backend", "temp",
    "11707454011-JUL-25221947 2.PDF"
)
# Password: pass via command line: python diagnose_boi_digital.py <password>
# The filename suggests account number: 11707454011
PASSWORD = sys.argv[1] if len(sys.argv) > 1 else "11707454011"

OUT_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    "tests", "audit_reports", "boi_digital_token_dump.json"
)

# ── 1. Extract text + tokens via the same path the API uses ──────────────────
print("Step 1: Routing document...")
from core.extractors.document_router import route_document
full_text, pages, telemetry, page_tokens = route_document(PDF_PATH, password=PASSWORD)

print(f"  pages extracted : {len(pages)}")
print(f"  total tokens    : {len(page_tokens)}")
print(f"  chars extracted : {len(full_text)}")

# ── 2. Sort tokens into pages ─────────────────────────────────────────────────
page1 = sorted([t for t in page_tokens if t.get("page", 1) == 1], key=lambda t: (t.get("yc", t.get("y0", 0)), t.get("x0", 0)))
page2 = sorted([t for t in page_tokens if t.get("page", 1) == 2], key=lambda t: (t.get("yc", t.get("y0", 0)), t.get("x0", 0)))

top100_p1 = page1[:100]
top100_p2 = page2[:100]

# ── 3. Run row detector to get physical rows ──────────────────────────────────
print("Step 2: Running row detector...")
from core.layout.row_detector import detect_rows
rows = detect_rows(page_tokens)
print(f"  physical rows   : {len(rows)}")

# ── 4. Replicate column detector logic to trace every candidate ───────────────
print("Step 3: Tracing column detector logic...")
import re

date_kws     = ["DATE", "TXN DATE", "VALUE DATE"]
narration_kws = ["PARTICULARS", "NARRATION", "DESCRIPTION", "DETAILS"]
debit_kws    = ["WITHDRAWAL", "DEBIT", "DR", "AMOUNT"]
credit_kws   = ["DEPOSIT", "CREDIT", "CR", "AMOUNT"]
balance_kws  = ["BALANCE", "BAL"]

min_page = min(r.get("page", 1) for r in rows) if rows else 1
search_rows = [r for r in rows if r.get("page", 1) <= min_page + 1]

header_candidates = []

for i, row in enumerate(search_rows):
    window = search_rows[i:i+6]
    found_date = found_balance = found_amt = False
    window_audit = []

    for j, w_row in enumerate(window):
        text_upper = " ".join([t["text"].upper() for t in w_row.get("tokens", [])])
        
        def row_has_strict(kws, text=text_upper):
            return any(re.search(rf"(?<![a-zA-Z]){re.escape(kw)}S?(?![a-zA-Z])", text, re.IGNORECASE) for kw in kws)
        
        rh_date = row_has_strict(date_kws)
        rh_bal  = row_has_strict(balance_kws)
        rh_amt  = row_has_strict(debit_kws + credit_kws)

        if rh_date and not found_date:
            found_date = True
        if rh_bal and not found_balance:
            found_balance = True
        if rh_amt and not found_amt:
            found_amt = True

        window_audit.append({
            "row_idx": i + j,
            "text": text_upper[:200],
            "has_date": rh_date,
            "has_balance": rh_bal,
            "has_amount": rh_amt,
        })

    header_candidates.append({
        "anchor_row": i,
        "anchor_text": " ".join([t["text"] for t in search_rows[i].get("tokens", [])])[:200],
        "window_result": {
            "found_date": found_date,
            "found_balance": found_balance,
            "found_amount": found_amt,
            "passes_3_conditions": found_date and found_balance and found_amt
        },
        "window_rows": window_audit
    })

# ── 5. Check if fuzzy fallback would also fail ────────────────────────────────
def fuzzy_has(kws, text):
    return any(kw in text for kw in kws)

fuzzy_header_found = False
for row in rows:
    text_upper = " ".join([t["text"].upper() for t in row.get("tokens", [])])
    if fuzzy_has(date_kws, text_upper) and fuzzy_has(balance_kws, text_upper) and fuzzy_has(debit_kws + credit_kws, text_upper):
        fuzzy_header_found = True
        break

# ── 6. Actual column detector call to get final verdict ──────────────────────
print("Step 4: Calling column detector...")
from core.layout.column_detector import detect_columns
zones, final_header_tokens = detect_columns(rows)
print(f"  zones detected  : {zones}")
print(f"  header tokens   : {len(final_header_tokens)}")

passed = any(c["window_result"]["passes_3_conditions"] for c in header_candidates)

if zones:
    reason = "SUCCESS: Column zones were created."
elif passed:
    reason = "PARTIAL: At least one window passed 3-condition check but zone extraction still failed."
elif fuzzy_header_found:
    reason = "FUZZY_FOUND_BUT_ZONE_FAILED: Fuzzy match found a header row but could not extract column boundaries."
else:
    reason = ("NO_HEADER_FOUND: No row window contained all three signals (DATE + BALANCE + AMOUNT). "
              "The text extracted by PyMuPDF does not contain recognisable column header keywords.")

# ── 7. Write output ───────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
report = {
    "pdf_path": PDF_PATH,
    "pages_extracted": len(pages),
    "total_tokens": len(page_tokens),
    "total_rows": len(rows),
    "top_100_tokens_page1": top100_p1,
    "top_100_tokens_page2": top100_p2,
    "header_candidates": header_candidates,
    "final_header_tokens": final_header_tokens,
    "found_date": any(c["window_result"]["found_date"] for c in header_candidates),
    "found_amount": any(c["window_result"]["found_amount"] for c in header_candidates),
    "found_balance": any(c["window_result"]["found_balance"] for c in header_candidates),
    "fuzzy_fallback_would_find_header": fuzzy_header_found,
    "zones_created": zones,
    "column_detector_reason": reason,
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print(f"\nReport written to: {OUT_PATH}")
print(f"Reason: {reason}")
