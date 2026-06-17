import os
import sys
import json
import re

_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _WORKSPACE_ROOT)

from core.adapters.ocr_subprocess import extract_via_subprocess
from core.layout.row_detector import detect_rows

PDF_PATH = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"

print("1. Extracting OCR tokens...")
full_text, pages_text, telemetry, tokens = extract_via_subprocess(PDF_PATH)

print("2. Detecting physical rows...")
rows = detect_rows(tokens)

# Compute max y1 for each page
page_heights = {}
for t in tokens:
    p = t.get("page", 0)
    y1 = t.get("y1", 0)
    if p not in page_heights or y1 > page_heights[p]:
        page_heights[p] = y1

DATE_RE = re.compile(
    r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|\d{1,2}[\s\-\.][A-Za-z]{3,9}[\s\-\.]\d{2,4})\b',
    re.IGNORECASE
)
DATE_PREFIX_RE = re.compile(r'^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\D', re.IGNORECASE)

contamination_keywords = ["IFSC", "MICR", "Branch", "Address", "Statement", "Page", "Customer", "Nomination", "Registered", "Closing balance"]
valid_keywords = ["UPI", "REF", "PHONEPE", "GOOGLEPAY", "IMPS", "NEFT", "TRANSFER", "PAYMENT", "PAYTM"]

dataset = {
    "valid_candidates": [],
    "footer_candidates": []
}

current_block = []

for row in rows:
    row_tokens = row.get("tokens", [])
    if not row_tokens:
        continue
        
    page = row.get("page", 0)
    page_height = page_heights.get(page, 1000)
    
    is_anchor = False
    for t in row_tokens[:5]: # Check first few tokens for date
        if t['x0'] < 300 and (DATE_RE.search(t['text']) or DATE_PREFIX_RE.match(t['text'])):
            is_anchor = True
            break
            
    if is_anchor:
        current_block = [row]
    else:
        if current_block:
            # This is a continuation row!
            prev_row = current_block[-1]
            row_gap = row["y0"] - prev_row["y1"]
            page_pos = row["y1"] / page_height
            row_text = " ".join([t["text"] for t in row_tokens])
            
            contaminants = [kw for kw in contamination_keywords if kw.upper() in row_text.upper()]
            val_kws = [kw for kw in valid_keywords if kw.upper() in row_text.upper()]
            
            is_footer_like = len(contaminants) > 0 or page_pos > 0.88
            
            entry = {
                "text": row_text,
                "row_gap": round(row_gap, 2),
                "page_position": round(page_pos, 3),
                "token_count": len(row_tokens),
                "contaminants": contaminants,
                "valid_kws": val_kws,
                "page": page
            }
            
            if is_footer_like or len(row_text) > 40:
                dataset["footer_candidates"].append(entry)
            else:
                dataset["valid_candidates"].append(entry)
                
            current_block.append(row)

# Limit to 20 each
dataset["footer_candidates"] = dataset["footer_candidates"][:20]
dataset["valid_candidates"] = dataset["valid_candidates"][:20]

with open(r"Z:\CA\investigations\HDFC\continuation_dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2)

print("\n--- Valid Continuation Rows Summary ---")
for e in dataset["valid_candidates"][:5]:
    print(f"Gap: {e['row_gap']:>5.1f} | Pos: {e['page_position']:.2f} | Kws: {e['valid_kws']} | Text: {e['text']}")

print("\n--- Footer/Header Continuation Rows Summary ---")
for e in dataset["footer_candidates"][:5]:
    print(f"Gap: {e['row_gap']:>5.1f} | Pos: {e['page_position']:.2f} | Contaminants: {e['contaminants']} | Text: {e['text'][:60]}...")

print("\nDataset written to investigations/HDFC/continuation_dataset.json")
