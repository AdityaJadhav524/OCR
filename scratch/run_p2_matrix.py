import os
import sys
import json

_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
sys.path.insert(0, _workspace)

from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.parsers.credit_card_parser import parse_credit_card_transactions
from core.validators.financial_audit import run_financial_audit

test_files = {
    "YES": os.path.join(_workspace, "tests", "pdfs", "YESBANK_SAVINGS_DIGITAL.pdf"),
    "HDFC": os.path.join(_workspace, "tests", "pdfs", "HDFC_SAVINGS_SCANNED.pdf"),
    "AXIS": os.path.join(_workspace, "validation_lab", "backend", "temp", "JOB_20260619_111429_0BB8_axis.pdf"),
    "CC": os.path.join(_workspace, "validation_lab", "backend", "temp", "JOB_20260619_111429_0BB8_CC_STMT_117048135_345073_1607202515082025 1 (1) 2_page-0001.pdf"),
    "BOI": os.path.join(_workspace, "tests", "pdfs", "BOI_SAVINGS_SCANNED.pdf")
}

results = {}

print("Bank | Accepted | Rejected | Financial Corruption")
print("---- | -------: | -------: | -------------------:")

for name, path in test_files.items():
    if not os.path.exists(path):
        print(f"{name:<4} | {'?':>8} | {'?':>8} | {'?':>20}")
        continue
        
    try:
        full_text, pages, routing_telemetry, page_tokens = route_document(path)
        identity = classify_document_llm(pages)
        doc_family = identity.get("family", "BANK_STATEMENT") if identity else "BANK_STATEMENT"
        
        if doc_family == "CREDIT_CARD" or name == "CC":
            txns, telemetry = parse_credit_card_transactions(page_tokens)
            accepted = len(txns)
            rejected = telemetry.get("rejected_rows", 0)
        else:
            txns, telemetry = parse_with_coordinates(page_tokens, bank=identity.get("institution_name"))
            accepted = len(txns)
            rejected = telemetry.get("v2_rejected_rows", 0)
            
        contaminated = sum(1 for t in txns if t.get("contamination_detected"))
        
        print(f"{name:<4} | {accepted:>8} | {rejected:>8} | {contaminated:>20}")
    except Exception as e:
        print(f"{name:<4} | {'ERROR':>8} | {'ERROR':>8} | {str(e):>20}")

