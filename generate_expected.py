import os
import json
import sys

# Ensure core root is on sys.path
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

def generate_expected(pdf_path: str, output_path: str):
    print(f"Extracting coordinates from {pdf_path}...")
    full_text, pages, merge_stats, page_tokens = route_document(pdf_path)
    
    print("Running V2 Parser...")
    v2_txns, v2_telemetry = parse_with_coordinates(page_tokens)
    
    # Store clean format in expected.json
    expected_data = {
        os.path.basename(pdf_path): {
            "transaction_count": len(v2_txns),
            "transactions": v2_txns
        }
    }
    
    with open(output_path, "w") as f:
        json.dump(expected_data, f, indent=2)
        
    print(f"Saved {len(v2_txns)} transactions to {output_path}")

if __name__ == "__main__":
    generate_expected("tests/BOI_01.pdf", "tests/expected.json")
