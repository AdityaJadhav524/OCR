import os
import sys
import time
import json

_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
sys.path.insert(0, _workspace)

from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

scanned_pdf = os.path.join(_workspace, "tests", "pdfs", "BOI_SAVINGS_SCANNED.pdf")

print("\n--- SCANNED PDF AFTER RESTORING BASELINE ---")
try:
    full_text, pages, routing_telemetry, page_tokens = route_document(scanned_pdf)
    identity = classify_document_llm(pages)
    txns, telemetry = parse_with_coordinates(page_tokens, bank=identity.get("institution_name"))
    
    rows_detected = telemetry.get('rows_detected', len(txns) + telemetry.get('v2_rejected_rows', 0))
    print(f"rows_detected: {rows_detected}")
    print(f"accepted_transactions: {len(txns)}")
    print(f"rejected_transactions: {telemetry.get('v2_rejected_rows', 0)}")
    print(f"reject reason histogram: {json.dumps(telemetry.get('reject_reasons', {}))}")
    
    reject_log = telemetry.get('reject_log', [])
    for r in reject_log:
        print(f"REJECT: {r.get('reject_reason')} | Amount: Dr {r.get('debit')}, Cr {r.get('credit')}, Bal {r.get('balance')} | Text: {r.get('block_text_snippet')}")
except Exception as e:
    print(f"Error processing Scanned PDF: {e}")
