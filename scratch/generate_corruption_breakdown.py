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

test_files = {
    "HDFC": os.path.join(_workspace, "tests", "pdfs", "HDFC_SAVINGS_SCANNED.pdf"),
    "BOI": os.path.join(_workspace, "tests", "pdfs", "BOI_SAVINGS_SCANNED.pdf")
}

def analyze_txn(txn):
    bal = txn.get("balance") or 0.0
    cr = txn.get("credit")
    db = txn.get("debit")
    date_str = str(txn.get("date", ""))
    narr = str(txn.get("narration", ""))
    
    m = re.search(r'\d{4}', date_str)
    year = float(m.group(0)) if m else None
    
    # 1. Balance as Credit
    if cr is not None and bal > 0 and abs(cr - bal) < 0.01:
        return "BALANCE_AS_CREDIT"
        
    # 2. Balance as Debit
    if db is not None and bal > 0 and abs(db - bal) < 0.01:
        return "BALANCE_AS_DEBIT"
        
    # 3. Date as Amount
    if year and ((cr is not None and abs(cr - year) < 0.01) or (db is not None and abs(db - year) < 0.01)):
        return "DATE_AS_AMOUNT"
        
    # 4. Date as Balance
    if year and bal and abs(bal - year) < 0.01:
        return "DATE_AS_BALANCE"
        
    # 5. Multiple Amounts (unclaimed float amounts sitting in narration)
    # We look for typical comma-separated numeric structures with 2 decimals that aren't dates
    if re.search(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b', narr):
        return "MULTIPLE_AMOUNTS"
        
    # 6. Ledger Fail
    if txn.get("agreement_state") == "CONFLICT":
        return "LEDGER_FAIL"
        
    return None

for name, path in test_files.items():
    print(f"Processing {name}...")
    full_text, pages, routing_telemetry, page_tokens = route_document(path)
    identity = classify_document_llm(pages)
    txns, telemetry = parse_with_coordinates(page_tokens, bank=identity.get("institution_name"))
    
    breakdown = {
        "BALANCE_AS_CREDIT": 0,
        "BALANCE_AS_DEBIT": 0,
        "DATE_AS_AMOUNT": 0,
        "DATE_AS_BALANCE": 0,
        "MULTIPLE_AMOUNTS": 0,
        "LEDGER_FAIL": 0
    }
    
    for txn in txns:
        category = analyze_txn(txn)
        if category:
            breakdown[category] += 1
            
    out_file = os.path.join(_workspace, f"{name}_CORRUPTION_BREAKDOWN.json")
    with open(out_file, "w") as f:
        json.dump(breakdown, f, indent=2)
    print(f"Saved {out_file}")
    print(json.dumps(breakdown, indent=2))
