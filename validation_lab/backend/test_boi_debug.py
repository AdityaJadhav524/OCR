import sys
import json
sys.path.insert(0, r"Z:\CA")

from core.parsers.deterministic_parser import parse_deterministic_transactions

def test_boi():
    with open(r"Z:\CA\validation_lab\backend\dumps\SESSION_20260610_175231_CFE4_ocr.txt", "r", encoding="utf-8") as f:
        full_text = f.read()
        
    lines = full_text.splitlines()
    for i, line in enumerate(lines):
        if "30-10-2024" in line:
            print(f"DEBUG: Found 30-10-2024 on line {i}: '{line}'")

    txns, telemetry = parse_deterministic_transactions(full_text)
    
test_boi()
