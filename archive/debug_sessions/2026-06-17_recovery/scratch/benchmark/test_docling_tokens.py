import json
import sys
import os

# Add core to path
sys.path.insert(0, r"Z:\CA")
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import run_financial_audit

# Load Docling JSON
json_path = r"Z:\CA\investigations\DOCLING\diagnostics\docling_document_structure.json"
with open(json_path, 'r', encoding='utf-8') as f:
    d = json.load(f)

tokens = []

page_height = d["pages"]["1"]["size"]["height"]

# Process unstructured text
for t in d.get("texts", []):
    text = t.get("text", "").strip()
    if not text: continue
    provs = t.get("prov", [])
    if provs and "bbox" in provs[0]:
        bbox = provs[0]["bbox"]
        origin = bbox.get("coord_origin", "BOTTOMLEFT")
        if origin == "BOTTOMLEFT":
            y0 = page_height - bbox["t"]
            y1 = page_height - bbox["b"]
        else:
            y0 = bbox["t"]
            y1 = bbox["b"]
        
        tokens.append({
            "text": text,
            "x0": bbox["l"],
            "y0": y0,
            "x1": bbox["r"],
            "y1": y1
        })

# Process tables
for table in d.get("tables", []):
    cells = table.get("data", {}).get("table_cells", [])
    for c in cells:
        text = c.get("text", "").strip()
        if not text: continue
        bbox = c.get("bbox")
        if bbox:
            origin = bbox.get("coord_origin", "TOPLEFT")
            if origin == "BOTTOMLEFT":
                y0 = page_height - bbox["t"]
                y1 = page_height - bbox["b"]
            else:
                y0 = bbox["t"]
                y1 = bbox["b"]
                
            tokens.append({
                "text": text,
                "x0": bbox["l"],
                "y0": y0,
                "x1": bbox["r"],
                "y1": y1
            })

# Sort tokens by y0 then x0
tokens.sort(key=lambda t: (t["y0"], t["x0"]))

print(f"Generated {len(tokens)} tokens from Docling.")

# Parse with coordinate parser
try:
    df = parse_with_coordinates(tokens)
    print("Coordinates parser output rows:", len(df))
    # run audit
    df, audit_pass = run_financial_audit(df)
    print(f"Audit Pass: {audit_pass}")
    
    # print all rows
    print(df[['date', 'description', 'amount', 'balance']])
except Exception as e:
    print(f"Parse failed: {e}")
    import traceback
    traceback.print_exc()

