import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.validators.financial_audit import _parse_float
from core.parsers.coordinate_parser_v2 import _prove_balance

def main():
    raw_text = "81,510.17CR"
    print(f"RAW OCR TOKEN: {raw_text}")
    
    # Simulate token extraction
    token = {"text": raw_text, "x0": 100, "x1": 150, "y0": 100, "y1": 110}
    zone = [50, 200]
    
    # Prove balance (calls _parse_float internally)
    print("-> Column Extraction: token fits in zone")
    
    amount = _prove_balance(token, zone)
    print(f"-> Amount Parser (_prove_balance): {amount}")
    
    val = _parse_float(raw_text)
    print(f"-> Financial Audit (_parse_float): {val}")

if __name__ == "__main__":
    main()
