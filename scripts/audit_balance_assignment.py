import os
import sys
import json
import logging

logging.getLogger("core.adapters.ocr_subprocess").setLevel(logging.WARNING)

sys.path.insert(0, os.path.abspath('.'))
from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth
from core.layout.structural_token_protection import protect_table_header_tokens
from core.detection.header_suppression import suppress_headers_and_footers
from core.detection.bank_detector import classify_document_llm

path = r"validation_lab\backend\temp\JOB_20260618_173225_EEF2_DocScanner 17-Apr-2026 11-07 AM 1.pdf"

print(f"=== AUDIT BALANCE ASSIGNMENT: {path} ===")
full_text, pages, ocr_tel, page_tokens = route_document(path)
identity = classify_document_llm(pages)
page_tokens = protect_table_header_tokens(page_tokens, {})
page_tokens = suppress_headers_and_footers(page_tokens)
txns, telemetry = parse_with_coordinates(page_tokens, pdf_name="DocScanner", pdf_type="UNKNOWN", identity=identity)
final_txns = annotate_ledger_truth(txns, full_text=full_text)

zones = telemetry.get("zones_detected", {})
print("\nDETECTED ZONES:")
print(json.dumps(zones, indent=2))
bz = zones.get("balance_zone")
print("\n--- ROW BY ROW BALANCE ASSIGNMENT ---")
for i, txn in enumerate(final_txns):
    ledger = txn.get("ledger_truth", {})
    date_val = txn.get("date")
    bal_val = txn.get("raw_extraction", {}).get("parsed_balance")
    tokens = txn.get("_source_tokens", [])
    
    balance_tokens = [t for t in tokens if bz and bz[0] <= (t.get("xc", (t.get("x0",0)+t.get("x1",0))/2)) <= bz[1]]
    date_tokens = [t for t in tokens if zones.get("date_zone") and zones["date_zone"][0] <= (t.get("xc", (t.get("x0",0)+t.get("x1",0))/2)) <= zones["date_zone"][1]]
    
    print(json.dumps({
        "row": i,
        "status": ledger.get("ledger_status"),
        "extracted_date": date_val,
        "extracted_balance": bal_val,
        "date_tokens_in_zone": " | ".join(t.get('text', '') for t in date_tokens),
        "balance_tokens_in_zone": " | ".join(t.get('text', '') for t in balance_tokens),
    }, indent=2))
