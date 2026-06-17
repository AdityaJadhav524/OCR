import sys
import json
import numpy as np

sys.path.insert(0, r"Z:\CA")
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

TOKENS_FILES = {
    "HDFC": r"Z:\CA\scratch\hdfc_tokens.json",
    "SBI": r"Z:\CA\scratch\latest_upload_tokens.json",
    "YES": r"Z:\CA\scratch\yes_tokens.json",
    "BOI": r"Z:\CA\scratch\boi_tokens.json"
}

def get_tokens(bank_name):
    with open(TOKENS_FILES[bank_name], "r", encoding="utf-8") as f:
        tokens = json.load(f)
    normalized = []
    for t in tokens:
        new_t = dict(t)
        if 'y1' in t and 'y2' in t and 'y0' not in t:
            new_t['y0'] = t['y1']
            new_t['y1'] = t['y2']
            new_t['x0'] = t['x1']
            new_t['x1'] = t['x2']
        if 'page_number' in t:
            new_t['page'] = t['page_number']
        elif 'page' not in t:
            new_t['page'] = 1
        normalized.append(new_t)
    return normalized

def study():
    # To identify footers vs legitimate continuations robustly, we will examine ALL
    # tokens that fall into the continuation section of a block.
    
    # We will classify based on whether the row was ultimately in a block that got
    # ACCEPTED or REJECTED. Or we just look at the text manually.
    
    # Since the user specifically wants to see delta_x for HDFC, YES, SBI, BOI
    
    print(f"{'BANK':<5} | {'CLS':<15} | {'DX':>5} | {'ZONE_L':>6} | {'X0':>6} | TEXT")
    print("-" * 80)
    
    for bank in TOKENS_FILES.keys():
        tokens = get_tokens(bank)
        
        # We need the column zones
        from core.layout.row_detector import detect_rows, detect_transaction_blocks
        from core.layout.column_detector import detect_columns
        
        rows = detect_rows(tokens)
        zones, _ = detect_columns(rows)
        if not zones or "date_zone" not in zones:
            continue
            
        date_zone_left = zones["date_zone"][0]
        blocks = detect_transaction_blocks(rows, date_x_bounds=zones["date_zone"])
        
        for block in blocks:
            # Anchor is block[0], continuation is block[1:]
            for row in block[1:]:
                row_tokens = row.get("tokens", [])
                if not row_tokens: continue
                
                text = " ".join([t.get("text", "") for t in row_tokens])
                row_x0 = min([t['x0'] for t in row_tokens])
                delta_x = row_x0 - date_zone_left
                
                text_lower = text.lower()
                cls = "CONTINUATION"
                
                # Manual flagging for the study
                if "hdfc bank limited" in text_lower or "registered" in text_lower or "contens of" in text_lower or "closing balance" in text_lower:
                    cls = "FOOTER_LEAK"
                elif "please do not share" in text_lower or "statement of account" in text_lower:
                    cls = "FOOTER_LEAK"
                elif "branch" in text_lower or "ifsc" in text_lower or "account" in text_lower:
                    if len(text_lower.split()) < 10:
                        cls = "HEADER_LEAK"
                
                if delta_x < -20 or cls != "CONTINUATION":
                    print(f"{bank:<5} | {cls:<15} | {round(delta_x):>5} | {round(date_zone_left):>6} | {round(row_x0):>6} | {text[:60]}")

if __name__ == "__main__":
    study()
