import os
import sys
import json
import logging

# Mute noisy logs
logging.getLogger("core.adapters.ocr_subprocess").setLevel(logging.WARNING)

sys.path.insert(0, os.path.abspath('.'))
from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth

pdfs_to_test = [
    "BOI_SAVINGS_SCANNED.pdf",
    "HDFC_SAVINGS_SCANNED.pdf",
    "YESBANK_SAVINGS_DIGITAL.pdf",
    "ICICI_CC_DIGITAL.pdf"
]

results = {}

for pdf in pdfs_to_test:
    path = os.path.join("tests", "pdfs", pdf)
    if not os.path.exists(path):
        print(f"Skipping {pdf} - not found locally.")
        continue
        
    print(f"\nProcessing {pdf}...")
    full_text, pages, ocr_tel, page_tokens = route_document(path)
    
    # We suppress structural tokens
    from core.layout.structural_token_protection import protect_table_header_tokens
    from core.detection.header_suppression import suppress_headers_and_footers
    from core.detection.bank_detector import classify_document_llm
    
    # We need identity for coordinate_parser_v2
    identity = classify_document_llm(pages)
    
    page_tokens = protect_table_header_tokens(page_tokens, {})
    page_tokens = suppress_headers_and_footers(page_tokens)
    
    txns, telemetry = parse_with_coordinates(page_tokens, pdf_name=pdf, pdf_type="UNKNOWN", identity=identity)
    
    final_txns = annotate_ledger_truth(txns, full_text=full_text)
    
    failures = sum(1 for t in final_txns if t.get("ledger_truth", {}).get("ledger_status") != "PASS")
    
    zones = telemetry.get("zones_detected", {})
    bz = zones.get("balance_zone")
    
    merged = telemetry.get("merged_header_detected", False)
    merged_info = telemetry.get("merged_header_info", {})
    
    res = {
        "merged_headers_detected": 1 if merged else 0,
        "virtual_anchors_created": len(merged_info.get("virtual_columns", [])) if merged else 0,
        "balance_zone_created": bz is not None,
        "balance_zone": bz,
        "ledger_failures_after": failures
    }
    
    if "BOI" in pdf:
        res["ledger_failures_before"] = 259
        
    results[pdf] = res
    print(json.dumps(res, indent=2))
    
print("\n=== FINAL VERIFICATION RESULTS ===")
print(json.dumps(results, indent=2))
