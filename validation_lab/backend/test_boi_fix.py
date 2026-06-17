import sys
import json
sys.path.insert(0, r"Z:\CA")

from core.parsers.deterministic_parser import parse_deterministic_transactions

def test_boi():
    with open(r"Z:\CA\validation_lab\backend\dumps\SESSION_20260610_175231_CFE4_ocr.txt", "r", encoding="utf-8") as f:
        full_text = f.read()

    txns, telemetry = parse_deterministic_transactions(full_text)
    
    print(f"Transactions: {len(txns)}")
    
    debit_total = sum(t["debit"] for t in txns if t["debit"])
    credit_total = sum(t["credit"] for t in txns if t["credit"])
    
    print(f"Debit Total: {debit_total}")
    print(f"Credit Total: {credit_total}")
    if txns:
        print(f"Final Balance: {txns[-1]['balance']}")
    
    for i, t in enumerate(txns):
        print(f"[{i+1}] {t['date']} | {t['narration']} | D:{t['debit']} | C:{t['credit']} | B:{t['balance']}")

test_boi()
