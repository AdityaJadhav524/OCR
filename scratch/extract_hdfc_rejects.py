import os
import sys
import json
from collections import defaultdict

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

details = []
grouped_reasons = defaultdict(int)

for i, rej in enumerate(reject_log):
    reason = rej.get("reject_reason", "unknown")
    grouped_reasons[reason] += 1
    
    details.append({
        "row_index": i,
        "reason": reason,
        "page": rej.get("_source_page"),
        "text": rej.get("block_text_snippet"),
        "raw_debit": rej.get("raw_extraction", {}).get("ocr_debit_text"),
        "raw_credit": rej.get("raw_extraction", {}).get("ocr_credit_text"),
        "raw_balance": rej.get("raw_extraction", {}).get("ocr_balance_text")
    })

out_file = os.path.join(_workspace, "HDFC_REJECT_ROOT_CAUSE.json")

output = {
    "summary": dict(grouped_reasons),
    "total_rejects": len(reject_log),
    "details": details
}

with open(out_file, "w") as f:
    json.dump(output, f, indent=2)

print(f"Saved {len(reject_log)} rejects to {out_file}")
print(json.dumps(output["summary"], indent=2))
