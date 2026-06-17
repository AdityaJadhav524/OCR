"""
analyze_latest_tokens.py
========================
Diagnose the exact token coordinates for the amounts 3000, 120, 200, 30
and the detected column zones from the recent upload.
"""
import json
import sys
import os

WORKSPACE = r"Z:\CA"
sys.path.insert(0, WORKSPACE)

TOKEN_FILE = os.path.join(WORKSPACE, "scratch", "latest_upload_tokens.json")

def main():
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        tokens = json.load(f)
    print(f"Loaded {len(tokens)} tokens.")

    from core.layout.row_detector import detect_rows
    from core.layout.column_detector import detect_columns

    rows = detect_rows(tokens)
    print(f"Total rows: {len(rows)}")
    
    zones, _ = detect_columns(rows)
    print("\n1. Detected Column Zones:")
    for zname, zbounds in zones.items():
        print(f"  {zname}: [{zbounds[0]:.2f}, {zbounds[1]:.2f}]")

    print("\n2. Finding specific tokens (3000, 120, 200, 30):")
    targets = ["3000", "3,000.00", "3000.00", "120", "120.00", "200", "200.00", "30", "30.00"]
    
    for tok in tokens:
        text = tok.get("text", "").strip()
        if any(t == text for t in targets) or "3000" in text or "120" in text or "200" in text or "30" in text:
            # specifically check exact matches or highly likely candidates
            # print it if it looks like an amount
            if text in targets or text.replace(",", "").replace(".", "").isdigit():
                x0 = tok.get("x0", 0)
                zone_name = "UNASSIGNED"
                for zname, zbounds in zones.items():
                    if zbounds[0] <= x0 <= zbounds[1]:
                        zone_name = zname
                        break
                print(f"  Token '{text}': x0={x0:.2f} -> Falls in zone: {zone_name}")

if __name__ == "__main__":
    main()
