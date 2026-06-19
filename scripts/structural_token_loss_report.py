"""
Structural Token Loss Report — All Benchmark PDFs
---------------------------------------------------
No code changes. Evidence only.

Strategy:
  Use fitz (PyMuPDF) directly to extract word tokens WITHOUT routing.
  This is fast for all PDFs regardless of scan status.
  For scanned PDFs with no text layer, we still get the suppression
  simulation result (which will show 0 tokens — a different data point).

  This answers:
    1. Which structural keywords does suppression remove?
    2. Is this BOI-only or cross-bank?
    3. How many tokens are lost per bank?

Output: tests/audit_reports/structural_token_loss_report.json
"""

import sys, os, json, re
from collections import defaultdict
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

STRUCTURAL_KEYWORDS = {
    "DATE", "BALANCE", "DEPOSIT", "WITHDRAWAL", "PARTICULARS",
    "AMOUNT", "DEBIT", "CREDIT", "NARRATION", "DESCRIPTION",
    "TRANSACTION", "DR", "CR", "CHQ", "REF"
}

SUPPRESSION_KEYWORDS = ["Bank", "IFSC", "MICR", "Page", "Statement",
                        "Account", "Currency", "Customer", "Nomination"]

OUT_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    "tests", "audit_reports", "structural_token_loss_report.json"
)

TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "validation_lab", "backend", "temp")

# All benchmark PDFs — use latest named copies
PDFS = [
    ("BOI_DIGITAL",          "JOB_20260618_121804_8C99_BOI_SAVINGS_DIGITAL.pdf",       "1170AKSH"),
    ("BOI_SCANNED",          "JOB_20260618_121808_497C_BOI_SAVINGS_SCANNED.pdf",        None),
    ("YESBANK_SAVINGS",      "JOB_20260618_122213_4B2B_YESBANK_SAVINGS_DIGITAL.pdf",    None),
    ("ICICI_CC_1",           "JOB_20260618_102941_061C_ICICI_1.pdf",                    None),
    ("ICICI_CC_2",           "JOB_20260618_103128_86CE_ICICI_2.pdf",                    None),
    ("HDFC_SAVINGS_SCANNED", "JOB_20260618_115001_5E18_HDFC_SAVINGS_SCANNED.pdf",       None),
]

def normalize_text(t_str):
    t_str = re.sub(r"(?i)page\s+\d+\s+of\s+\d+", "PAGE_N", t_str)
    t_str = re.sub(r"(?i)page\s+no\.?\s*\d+",     "PAGE_N", t_str)
    t_str = re.sub(r"(?i)page\s+\d+",             "PAGE_N", t_str)
    return t_str

def extract_tokens_direct(pdf_path, password=None):
    """
    Extract word-level tokens directly via fitz.
    Returns list of token dicts and whether the PDF has a text layer.
    Does NOT call OCR.
    """
    import fitz
    doc = fitz.open(pdf_path)
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            return [], False, "INVALID_PASSWORD"
    
    tokens = []
    has_text_layer = False
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        words = page.get_text("words")  # (x0, y0, x1, y1, word, block, line, word_idx)
        if words:
            has_text_layer = True
        for w in words:
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            text = text.strip()
            if text:
                tokens.append({
                    "text": text,
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                    "page": page_num + 1,
                    "yc": (y0 + y1) / 2
                })
    doc.close()
    return tokens, has_text_layer, "OK"

def score_suppression(tokens):
    """Replicate suppression scoring. Returns set of texts that would be suppressed."""
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
        top_bottom = 0
        for t in tkns:
            p = t.get("page", 0)
            if p not in page_bounds:
                continue
            min_y, max_y = page_bounds[p]
            h = max_y - min_y
            if h <= 0:
                continue
            y_mid = (t.get("y0", 0) + t.get("y1", 0)) / 2
            rel_y = (y_mid - min_y) / h
            if rel_y <= 0.15 or rel_y >= 0.85:
                top_bottom += 1
        if top_bottom / len(tkns) > 0.5:
            score += 2
        text_upper = text.upper()
        for kw in SUPPRESSION_KEYWORDS:
            if kw.upper() in text_upper:
                score += 2
        if score >= 5:
            suppressed.add(text)
    return suppressed, num_pages

print("STRUCTURAL TOKEN LOSS REPORT")
print("="*60)

results = []

for label, filename, password in PDFS:
    pdf_path = os.path.join(TEMP_DIR, filename)
    
    if not os.path.exists(pdf_path):
        print(f"\n{label}: FILE NOT FOUND — {filename}")
        results.append({"label": label, "status": "FILE_NOT_FOUND"})
        continue
    
    print(f"\n{label}:")
    
    tokens, has_text_layer, status = extract_tokens_direct(pdf_path, password)
    
    if status != "OK":
        print(f"  status: {status}")
        results.append({"label": label, "status": status})
        continue
    
    if not has_text_layer or len(tokens) == 0:
        print(f"  text layer: NO (scanned PDF — suppression runs on OCR output, not auditable here)")
        results.append({
            "label": label,
            "status": "SCANNED_NO_TEXT_LAYER",
            "note": "Suppression operates on OCR tokens. Cannot audit without running OCR."
        })
        continue
    
    suppressed_texts, num_pages = score_suppression(tokens)
    tokens_after_count = sum(
        1 for t in tokens
        if normalize_text(str(t.get("text", "")).strip()) not in suppressed_texts
    )
    
    # Which structural keywords are being suppressed?
    structural_removed = sorted([
        text for text in suppressed_texts
        if text.upper() in STRUCTURAL_KEYWORDS
    ])
    
    # Breakdown by keyword
    keyword_details = {}
    for kw in STRUCTURAL_KEYWORDS:
        matching = [t for t in tokens if t.get("text","").upper() == kw]
        will_be_removed = [t for t in matching
                           if normalize_text(t.get("text","").strip()) in suppressed_texts]
        if matching:
            keyword_details[kw] = {
                "total_occurrences": len(matching),
                "removed": len(will_be_removed),
                "safe": len(matching) - len(will_be_removed),
                "at_risk": len(will_be_removed) > 0
            }

    at_risk_keywords = [k for k, v in keyword_details.items() if v["at_risk"]]
    
    print(f"  pages          : {num_pages}")
    print(f"  tokens before  : {len(tokens)}")
    print(f"  tokens after   : {tokens_after_count}")
    print(f"  tokens removed : {len(tokens) - tokens_after_count}")
    print(f"  structural kws removed: {structural_removed}")
    print(f"  all structural at risk: {at_risk_keywords}")
    
    verdict = "SAFE" if not structural_removed else f"AT_RISK: {structural_removed}"
    
    results.append({
        "label": label,
        "status": "OK",
        "num_pages": num_pages,
        "tokens_before": len(tokens),
        "tokens_after": tokens_after_count,
        "tokens_removed": len(tokens) - tokens_after_count,
        "structural_keywords_removed": structural_removed,
        "structural_keyword_details": keyword_details,
        "verdict": verdict,
    })

# Summary table
print("\n\nSUMMARY TABLE")
print("="*60)
print(f"{'Bank':<25} {'Before':>7} {'After':>7} {'Lost':>6}  Structural Removed")
print("-"*60)
for r in results:
    label = r["label"]
    if r.get("status") not in ("OK",):
        print(f"{label:<25}  {r.get('status', 'UNKNOWN')}")
        continue
    removed_kw = r.get("structural_keywords_removed", [])
    print(f"{label:<25} {r['tokens_before']:>7} {r['tokens_after']:>7} {r['tokens_removed']:>6}  {removed_kw if removed_kw else '—'}")

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\nFull report: {OUT_PATH}")
