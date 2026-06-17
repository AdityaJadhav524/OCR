import json
import sys
import logging
import asyncio

sys.path.insert(0, r"Z:\CA")

from core.parsers.statement_parser import parse_with_llm
from core.parsers.deterministic_parser import parse_deterministic_transactions

def main():
    # Load BOI OCR Text
    with open(r"Z:\CA\validation_lab\backend\dumps\SESSION_20260610_175231_CFE4_ocr.txt", "r", encoding="utf-8") as f:
        full_text = f.read()

    # 1. Run LedgerAI parser (LLM)
    try:
        print("Running LedgerAI (LLM) Parser...")
        llm_result = parse_with_llm(full_text, {"institution_name": "BANK OF INDIA"})
        llm_txns = llm_result["transactions"]
        with open("llm_txns.json", "w") as f:
            json.dump(llm_txns, f, indent=2)
    except Exception as e:
        print("LLM Error:", e)
        llm_txns = []

    # 2. Run Current Project Parser (Deterministic)
    try:
        print("Running Current Project (Deterministic) Parser...")
        det_txns, telemetry = parse_deterministic_transactions(full_text)
        with open("det_txns.json", "w") as f:
            json.dump(det_txns, f, indent=2)
    except Exception as e:
        print("Deterministic Error:", e)
        det_txns = []

    print("LLM Txns:", len(llm_txns))
    print("Det Txns:", len(det_txns))

if __name__ == "__main__":
    main()
