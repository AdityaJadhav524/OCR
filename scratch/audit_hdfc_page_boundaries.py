import os
import sys
import json
import re

_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
sys.path.insert(0, _workspace)

from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = os.path.join(_workspace, "tests", "pdfs", "HDFC_SAVINGS_SCANNED.pdf")

full_text, pages, routing_telemetry, page_tokens = route_document(pdf_path)
identity = classify_document_llm(pages)
txns, telemetry = parse_with_coordinates(page_tokens, bank=identity.get("institution_name"))

reject_log = telemetry.get("reject_log", [])

audit_results = []
header_contamination_count = 0
balance_present_count = 0
merged_block_count = 0

def is_amount(text):
    text = text.strip().replace(',', '')
    if re.match(r'^\d+\.\d{2}$', text):
        return True
    return False

for i, rej in enumerate(reject_log):
    page_idx = rej.get("_source_page", 0)
    text = rej.get("block_text_snippet", "").lower()
    reason = rej.get("reject_reason", "unknown")
    
    header_present = "statement of account" in text or "from" in text or "to" in text
    
    # Check if there is transaction text (length > 50 or other keywords)
    # The header is typically "from 01/05/2025 to 31/05/2025 statement of account"
    header_str = "from 01/05/2025 to31/05/2025 statement of account"
    remaining_text = text.replace(header_str, "").strip()
    txn_present = len(remaining_text) > 5 and not remaining_text.startswith("date")
    
    # Find the Y bounds of this block in page_tokens
    # We look for tokens that contain parts of the snippet
    pts = [t for t in page_tokens if t.get("page", 0) == page_idx]
    
    block_top = 9999
    block_bottom = 0
    
    snippet_words = [w for w in text.split() if len(w) > 3]
    for pt in pts:
        try:
            pt_text = pt["text"].lower()
            if any(w in pt_text for w in snippet_words):
                if pt["y0"] < block_top: block_top = pt["y0"]
                if pt["y1"] > block_bottom: block_bottom = pt["y1"]
        except Exception as e:
            print(f"Error on pt {pt}: {e}")
            
    # Now look for balance tokens around this block (+/- 20 pixels)
    balance_exists = False
    amount_exists = False
    for pt in pts:
        try:
            if pt["y0"] >= block_top - 20 and pt["y1"] <= block_bottom + 20:
                if is_amount(pt["text"]):
                    # If it's on the far right (x0 > 400 usually), it's a balance
                    if pt["x0"] > 400:
                        balance_exists = True
                    else:
                        amount_exists = True
        except Exception:
            pass
                    
    merged_block = header_present and txn_present
    
    if header_present: header_contamination_count += 1
    if balance_exists: balance_present_count += 1
    if merged_block: merged_block_count += 1
    
    audit_results.append({
        "page": page_idx,
        "reason": reason,
        "header_text_present": header_present,
        "transaction_text_present": txn_present,
        "balance_token_exists_in_raw_ocr": balance_exists,
        "amount_token_exists_in_raw_ocr": amount_exists,
        "merged_block": merged_block,
        "text": text
    })

out_file = os.path.join(_workspace, "HDFC_PAGE_BOUNDARY_AUDIT.json")
with open(out_file, "w") as f:
    json.dump({
        "summary": {
            "header_contamination_count": f"{header_contamination_count}/{len(reject_log)}",
            "balance_token_present_count": f"{balance_present_count}/{len(reject_log)}",
            "merged_block_count": f"{merged_block_count}/{len(reject_log)}"
        },
        "details": audit_results
    }, f, indent=2)

print(f"Saved {len(audit_results)} rows to {out_file}")
print(json.dumps({
    "header_contamination_count": f"{header_contamination_count}/{len(reject_log)}",
    "balance_token_present_count": f"{balance_present_count}/{len(reject_log)}",
    "merged_block_count": f"{merged_block_count}/{len(reject_log)}"
}, indent=2))
