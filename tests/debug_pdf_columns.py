import os
import sys
import json
import fitz  # PyMuPDF
from collections import defaultdict

# Setup sys path
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

from core.extractors.document_router import route_document
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

def debug_hdfc(pdf_path: str):
    print(f"--- Debugging {pdf_path} ---")
    
    # 1. Extract tokens
    full_text, pages, telemetry, page_tokens = route_document(pdf_path)
    
    if not page_tokens:
        print("ERROR: No page tokens extracted!")
        return
        
    print(f"Extracted {len(page_tokens)} tokens.")
    
    # 2. Detect rows and columns
    rows = detect_rows(page_tokens)
    print(f"Detected {len(rows)} physical rows.")
    
    zones, detected_headers = detect_columns(rows)
    
    if not zones:
        print("ERROR: Failed to detect columns.")
        return
        
    # --- Artifact 1: hdfc_headers.json ---
    # Simplify the tokens to just text, x0, x1
    simple_headers = []
    for t in detected_headers:
        simple_headers.append({
            "text": t.get("text", ""),
            "x0": t.get("x0", 0.0),
            "x1": t.get("x1", 0.0)
        })
        
    artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    with open(os.path.join(artifacts_dir, "hdfc_headers.json"), "w", encoding="utf-8") as f:
        json.dump({"detected_headers": simple_headers}, f, indent=2)
    print("Wrote hdfc_headers.json")
    
    # --- Artifact 2: hdfc_zones.json ---
    with open(os.path.join(artifacts_dir, "hdfc_zones.json"), "w", encoding="utf-8") as f:
        json.dump(zones, f, indent=2)
    print("Wrote hdfc_zones.json")
    
    # --- Artifact 4 & 5: Row Debug and Occupancy ---
    blocks = detect_transaction_blocks(rows, date_x_bounds=zones.get("date_zone", [0, 9999]))
    
    row_debug = []
    occupancy = {
        "date_tokens": 0,
        "narration_tokens": 0,
        "debit_tokens": 0,
        "credit_tokens": 0,
        "balance_tokens": 0
    }
    
    for block_idx, block in enumerate(blocks):
        debug_info = {
            "row": block_idx + 1,
            "date_tokens": [],
            "narration_tokens": [],
            "debit_tokens": [],
            "credit_tokens": [],
            "balance_tokens": [],
            "unassigned_tokens": []
        }
        
        for row_idx, row in enumerate(block):
            is_main_row = (row_idx == 0)
            for t in row.get("tokens", []):
                x = t["x0"]
                text = t["text"].strip()
                
                tok_data = {
                    "text": text,
                    "x0": x,
                    "x1": t.get("x1", x),
                    "y0": t.get("y0", 0),
                    "y1": t.get("y1", 0)
                }
                
                if zones.get("date_zone") and zones["date_zone"][0] <= x <= zones["date_zone"][1]:
                    debug_info["date_tokens"].append(tok_data)
                    occupancy["date_tokens"] += 1
                elif is_main_row and zones.get("debit_zone") and zones["debit_zone"][0] <= x <= zones["debit_zone"][1]:
                    debug_info["debit_tokens"].append(tok_data)
                    occupancy["debit_tokens"] += 1
                elif is_main_row and zones.get("credit_zone") and zones["credit_zone"][0] <= x <= zones["credit_zone"][1]:
                    debug_info["credit_tokens"].append(tok_data)
                    occupancy["credit_tokens"] += 1
                elif is_main_row and zones.get("balance_zone") and zones["balance_zone"][0] <= x <= zones["balance_zone"][1]:
                    debug_info["balance_tokens"].append(tok_data)
                    occupancy["balance_tokens"] += 1
                elif zones.get("narration_zone") and zones["narration_zone"][0] <= x <= zones["narration_zone"][1]:
                    debug_info["narration_tokens"].append(tok_data)
                    occupancy["narration_tokens"] += 1
                else:
                    debug_info["unassigned_tokens"].append(tok_data)
                    # Fallback assigns to narration
                    occupancy["narration_tokens"] += 1
                    
        if block_idx < 5:
            row_debug.append(debug_info)
            
    with open(os.path.join(artifacts_dir, "hdfc_row_debug.json"), "w", encoding="utf-8") as f:
        json.dump(row_debug, f, indent=2)
    print("Wrote hdfc_row_debug.json")
    
    with open(os.path.join(artifacts_dir, "column_occupancy.json"), "w", encoding="utf-8") as f:
        json.dump(occupancy, f, indent=2)
    print("Wrote column_occupancy.json")
    
    # --- Verification Run ---
    txns, telemetry = parse_with_coordinates(page_tokens)
    
    total_debits = sum(t.get("debit") or 0.0 for t in txns)
    total_credits = sum(t.get("credit") or 0.0 for t in txns)
    
    print("\n--- Parsed Verification ---")
    print(f"Total Transactions: {len(txns)}")
    print(f"Total Debits Extracted: {total_debits}")
    print(f"Total Credits Extracted: {total_credits}")
    
    if txns:
        print("\nFirst Transaction:")
        print(json.dumps(txns[0], indent=2))
        
    print("\nCopied all artifacts to the AntiGravity artifacts folder.")

if __name__ == "__main__":
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else r"Z:\CA\Akshata_Dhanyakumar_Patil_30112025_182828759 1 1.pdf"
    debug_hdfc(pdf_file)
