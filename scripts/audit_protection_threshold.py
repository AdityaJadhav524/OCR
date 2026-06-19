"""
Audit script: Find keyword thresholds for structural protection
--------------------------------------------------------------
Scans all benchmark PDFs and outputs the rows that contain
structural keywords, along with the keyword count.

This determines the safe threshold for protection without guessing.
"""

import sys, os, json, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.extractors.document_router import route_document
from core.layout.row_detector import detect_rows

STRUCTURAL_KEYWORDS = {
    "DATE", "BALANCE", "DEPOSIT", "WITHDRAWAL", "PARTICULARS",
    "AMOUNT", "DEBIT", "CREDIT", "NARRATION", "DESCRIPTION",
    "TRANSACTION", "DR", "CR", "CHQ", "REF"
}

TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "validation_lab", "backend", "temp")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "audit_reports", "protection_threshold_audit.json")

PDFS = [
    ("BOI_DIGITAL",          "JOB_20260618_121804_8C99_BOI_SAVINGS_DIGITAL.pdf",       "1170AKSH"),
    ("BOI_SCANNED",          "JOB_20260618_121808_497C_BOI_SAVINGS_SCANNED.pdf",        None),
    ("YESBANK_SAVINGS",      "JOB_20260618_122213_4B2B_YESBANK_SAVINGS_DIGITAL.pdf",    None),
    ("ICICI_CC_1",           "JOB_20260618_102941_061C_ICICI_1.pdf",                    None),
    ("HDFC_SAVINGS_SCANNED", "JOB_20260618_115001_5E18_HDFC_SAVINGS_SCANNED.pdf",       None),
]

def extract_tokens_direct(pdf_path, password=None):
    import fitz
    doc = fitz.open(pdf_path)
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            return [], False
    tokens = []
    has_text = False
    for page_num in range(len(doc)):
        words = doc[page_num].get_text("words")
        if words: has_text = True
        for w in words:
            text = w[4].strip()
            if text:
                tokens.append({
                    "text": text,
                    "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3],
                    "page": page_num + 1,
                    "yc": (w[1] + w[3]) / 2
                })
    return tokens, has_text

results = []

for label, filename, password in PDFS:
    pdf_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(pdf_path):
        continue
    
    tokens, has_text = extract_tokens_direct(pdf_path, password)
    
    # We can use row_detector on the raw PyMuPDF tokens to find candidate rows
    # Even if scanned, the text layer might have something, or we skip if no text.
    if not tokens:
        continue
        
    rows = detect_rows(tokens)
    
    candidates = []
    for i, row in enumerate(rows):
        row_text = " ".join([t["text"].upper() for t in row.get("tokens", [])])
        
        # Count structural keywords
        hits = set()
        for kw in STRUCTURAL_KEYWORDS:
            if re.search(rf"\b{kw}\b", row_text):
                hits.add(kw)
                
        if hits:
            candidates.append({
                "row_index": i,
                "text": row_text[:150],
                "matched_keywords": list(hits),
                "keyword_count": len(hits)
            })
            
    # Sort by keyword count descending
    candidates.sort(key=lambda c: c["keyword_count"], reverse=True)
    
    results.append({
        "label": label,
        "total_rows": len(rows),
        "top_candidates": candidates[:5]  # Top 5 rows with most keywords
    })

print("PROTECTION THRESHOLD AUDIT")
print("="*60)
for r in results:
    print(f"\n{r['label']}:")
    for c in r['top_candidates']:
        print(f"  Row {c['row_index']:>3} | Count: {c['keyword_count']} | KWs: {c['matched_keywords']}")
        print(f"            Text: {c['text']}")

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w") as f:
    json.dump(results, f, indent=2)
