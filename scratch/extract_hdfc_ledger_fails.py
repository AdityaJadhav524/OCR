import os
import sys
import json

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

details = []
prev_balance = None

for txn in txns:
    if txn.get("agreement_state") == "CONFLICT":
        credit = txn.get("credit") or 0.0
        debit = txn.get("debit") or 0.0
        actual_balance = txn.get("balance") or 0.0
        
        # In the parser, if it fails conservation, it outputs CONFLICT.
        # But we need to know the 'prev_balance' it used. Since the parser updates prev_balance to actual_balance
        # even on CONFLICT, we can just track it ourselves here (or grab it from the reject log, but wait, it's accepted with CONFLICT).
        
        expected_balance = 0.0
        diff = 0.0
        if prev_balance is not None:
            expected_balance = prev_balance + credit - debit
            diff = abs(expected_balance - actual_balance)
            
        details.append({
            "page": txn.get("page"),
            "date": txn.get("date"),
            "prev_balance": prev_balance,
            "debit": debit,
            "credit": credit,
            "expected_balance": expected_balance,
            "actual_balance": actual_balance,
            "difference": diff,
            "raw_debit": txn.get("raw_extraction", {}).get("ocr_debit_text"),
            "raw_credit": txn.get("raw_extraction", {}).get("ocr_credit_text"),
            "raw_balance": txn.get("raw_extraction", {}).get("ocr_balance_text")
        })
        
    # The parser always advances prev_balance from the actual OCR balance
    prev_balance = txn.get("balance")

out_file = os.path.join(_workspace, "HDFC_LEDGER_FAIL_DETAILS.json")
with open(out_file, "w") as f:
    json.dump(details, f, indent=2)

print(f"Saved {len(details)} failures to {out_file}")
print(json.dumps(details, indent=2))
