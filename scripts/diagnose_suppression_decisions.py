"""
Suppression Decision Audit — BOI Digital
-----------------------------------------
No code changes. Evidence only.

Answers:
  1. How does suppression decide what to remove?
  2. Does it use position or only frequency?
  3. Which structural banking keywords are being removed?
  4. Why specifically was DATE removed?

Output: tests/audit_reports/boi_suppression_decision_audit.json
"""

import sys, os, json, re
from collections import defaultdict
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PDF_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    "validation_lab", "backend", "temp",
    "11707454011-JUL-25221947 2.PDF"
)
PASSWORD = sys.argv[1] if len(sys.argv) > 1 else "1170AKSH"
OUT_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    "tests", "audit_reports", "boi_suppression_decision_audit.json"
)

STRUCTURAL_KEYWORDS = {"DATE", "BALANCE", "DEPOSIT", "WITHDRAWAL", "PARTICULARS",
                       "AMOUNT", "DEBIT", "CREDIT", "NARRATION", "DESCRIPTION"}

# ── Step 1: Extract tokens ────────────────────────────────────────────────────
print("Step 1: Extracting tokens...")
from core.extractors.document_router import route_document
_, _, _, tokens = route_document(PDF_PATH, password=PASSWORD)
print(f"  Total tokens: {len(tokens)}")

# ── Step 2: Replicate suppression scoring logic — WITH REASONS ───────────────
print("Step 2: Replicating suppression scoring for every candidate...")

pages = set(t.get("page", 0) for t in tokens)
num_pages = len(pages)

page_bounds = {}
for p in pages:
    pt = [t for t in tokens if t.get("page", 0) == p]
    if not pt:
        continue
    page_bounds[p] = (min(t.get("y0", 0) for t in pt),
                      max(t.get("y1", 0) for t in pt))

def normalize_text(t_str):
    t_str = re.sub(r"(?i)page\s+\d+\s+of\s+\d+", "PAGE_N", t_str)
    t_str = re.sub(r"(?i)page\s+no\.?\s*\d+",     "PAGE_N", t_str)
    t_str = re.sub(r"(?i)page\s+\d+",             "PAGE_N", t_str)
    return t_str

SUPPRESSION_KEYWORDS = ["Bank", "IFSC", "MICR", "Page", "Statement",
                        "Account", "Currency", "Customer", "Nomination"]

text_to_tokens = defaultdict(list)
for t in tokens:
    txt = str(t.get("text", "")).strip()
    if txt:
        text_to_tokens[normalize_text(txt)].append(t)

all_candidates = []

for text, tkns in text_to_tokens.items():
    pages_appeared = len(set(t.get("page", 0) for t in tkns))
    if pages_appeared < 2:
        continue  # Not a repeat — suppression won't touch it

    score = 0
    reasons = []

    # Criterion 1: frequency
    freq_ratio = pages_appeared / num_pages
    if freq_ratio > 0.70:
        score += 3
        reasons.append(f"FREQ_ACROSS_PAGES: appears on {pages_appeared}/{num_pages} pages (+3)")

    # Criterion 2: top/bottom position
    top_bottom_count = 0
    position_detail = []
    for t in tkns:
        p = t.get("page", 0)
        if p not in page_bounds:
            continue
        min_y, max_y = page_bounds[p]
        h = max_y - min_y
        if h <= 0:
            continue
        y_mid = (t.get("y0", 0) + t.get("y1", 0)) / 2
        relative_y = (y_mid - min_y) / h
        in_zone = relative_y <= 0.15 or relative_y >= 0.85
        if in_zone:
            top_bottom_count += 1
        position_detail.append({
            "page": p,
            "y0": t.get("y0"),
            "y1": t.get("y1"),
            "relative_y": round(relative_y, 3),
            "in_top_or_bottom_15pct": in_zone
        })

    position_ratio = top_bottom_count / len(tkns) if tkns else 0
    if position_ratio > 0.5:
        score += 2
        reasons.append(f"POSITION: {top_bottom_count}/{len(tkns)} tokens in top/bottom 15% (+2)")
    else:
        reasons.append(f"POSITION: only {top_bottom_count}/{len(tkns)} in top/bottom 15% (did not score)")

    # Criterion 3: keyword match
    text_upper = text.upper()
    kw_hits = [kw for kw in SUPPRESSION_KEYWORDS if kw.upper() in text_upper]
    if kw_hits:
        score += 2 * len(kw_hits)
        reasons.append(f"KEYWORD_MATCH: {kw_hits} (+{2*len(kw_hits)})")

    will_suppress = score >= 5

    all_candidates.append({
        "text": text,
        "pages_appeared": pages_appeared,
        "score": score,
        "will_suppress": will_suppress,
        "reasons": reasons,
        "positions": position_detail,
        "is_structural_keyword": text.upper() in STRUCTURAL_KEYWORDS,
    })

# ── Step 3: Structural keyword analysis ──────────────────────────────────────
print("Step 3: Checking structural keywords...")
suppressed = [c for c in all_candidates if c["will_suppress"]]
structural_suppressed = [c for c in suppressed if c["is_structural_keyword"]]
structural_safe = [c for c in all_candidates
                   if c["is_structural_keyword"] and not c["will_suppress"]]

print(f"  Candidates evaluated       : {len(all_candidates)}")
print(f"  Will be suppressed         : {len(suppressed)}")
print(f"  Structural keywords total  : {len([c for c in all_candidates if c['is_structural_keyword']])}")
print(f"  Structural keywords REMOVED: {len(structural_suppressed)}")
print(f"  Structural keywords SAFE   : {len(structural_safe)}")

print("\n  Structural keywords that WILL BE REMOVED:")
for c in structural_suppressed:
    print(f"    '{c['text']}' — score={c['score']} — reasons: {c['reasons']}")

# ── Step 4: Explain DATE specifically ────────────────────────────────────────
print("\nStep 4: Why was DATE removed?")
date_entry = next((c for c in all_candidates if c["text"].upper() == "DATE"), None)
if date_entry:
    print(f"  score           = {date_entry['score']}")
    print(f"  will_suppress   = {date_entry['will_suppress']}")
    for r in date_entry["reasons"]:
        print(f"  reason          : {r}")
    print(f"  positions:")
    for pos in date_entry["positions"]:
        print(f"    page={pos['page']} y0={pos['y0']} rel_y={pos['relative_y']} in_zone={pos['in_top_or_bottom_15pct']}")
else:
    print("  DATE not found among multi-page repeating tokens (appears on only 1 page)")

# ── Step 5: Verdict ───────────────────────────────────────────────────────────
uses_position = any("POSITION:" in r and "did not score" not in r
                    for c in suppressed for r in c["reasons"])

print(f"\n{'='*60}")
print(f"Does suppression use Y-position? : {'YES' if uses_position else 'NO — frequency only'}")
print(f"Structural keywords suppressed   : {[c['text'] for c in structural_suppressed]}")
print(f"{'='*60}")

# ── Write report ──────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
report = {
    "pdf": PDF_PATH,
    "num_pages": num_pages,
    "tokens_total": len(tokens),
    "suppression_uses_position": uses_position,
    "suppression_uses_frequency": True,
    "suppression_uses_keyword_list": True,
    "suppression_keyword_list": SUPPRESSION_KEYWORDS,
    "candidates_evaluated": len(all_candidates),
    "candidates_suppressed": len(suppressed),
    "structural_keywords_suppressed": [
        {"text": c["text"], "score": c["score"], "reasons": c["reasons"], "positions": c["positions"]}
        for c in structural_suppressed
    ],
    "structural_keywords_safe": [c["text"] for c in structural_safe],
    "date_token_detail": date_entry,
    "all_suppressed_tokens": [
        {"text": c["text"], "score": c["score"], "is_structural": c["is_structural_keyword"],
         "reasons": c["reasons"]}
        for c in suppressed
    ]
}
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print(f"\nReport written to: {OUT_PATH}")
