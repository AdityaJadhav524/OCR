import json
import logging
from core.extractors.document_router import route_document
from core.detection.header_suppression import suppress_headers_and_footers
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

logging.basicConfig(level=logging.INFO)

pdf_path = "tests/pdfs/HDFC_SAVINGS_SCANNED.pdf"
print(f"Routing document: {pdf_path}")
full_text, pages, routing_telemetry, page_tokens = route_document(pdf_path)

print(f"Tokens before suppression: {len(page_tokens)}")
page_tokens = suppress_headers_and_footers(page_tokens)
print(f"Tokens after suppression: {len(page_tokens)}")

v2_txns, v2_telemetry = parse_with_coordinates(page_tokens)

print(f"V2 Txns Accepted: {len(v2_txns)}")
print(f"V2 Txns Rejected: {v2_telemetry.get('v2_rejected_rows', 0)}")
print(f"V2 Rejects details: {json.dumps(v2_telemetry.get('reject_reasons', {}), indent=2)}")

# Let's see the rejected blocks
for rej in v2_telemetry.get("rejected_blocks", []):
    print("Rejected block snippet:", rej.get("block_text_snippet"))
