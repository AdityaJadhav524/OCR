"""
test_midpoint_zones.py
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

    from core.layout.row_detector import detect_rows
    rows = detect_rows(tokens)
    
    # Simulating column detector logic
    date_kws = ["DATE", "TXN DATE", "VALUE DATE"]
    narration_kws = ["PARTICULARS", "NARRATION", "DESCRIPTION", "DETAILS"]
    debit_kws = ["WITHDRAWAL", "DEBIT", "DR"]
    credit_kws = ["DEPOSIT", "CREDIT", "CR"]
    balance_kws = ["BALANCE", "BAL"]
    
    header_row = None
    for row in rows:
        r_tokens = row.get("tokens", [])
        text_upper = " ".join([t["text"].upper() for t in r_tokens])
        has_date = any(kw in text_upper for kw in date_kws)
        has_balance = any(kw in text_upper for kw in balance_kws)
        if has_date and has_balance:
            header_row = r_tokens
            break
            
    cols_found = []
    for t in header_row:
        text = t["text"].upper().replace(".", "").strip()
        if any(kw in text for kw in date_kws):
            cols_found.append({"type": "date", "x0": t["x0"]})
        elif any(kw in text for kw in narration_kws):
            cols_found.append({"type": "narration", "x0": t["x0"]})
        elif any(kw in text for kw in debit_kws) or "WITHDRAW" in text:
            cols_found.append({"type": "debit", "x0": t["x0"]})
        elif any(kw in text for kw in credit_kws) or "DEPOSIT" in text:
            cols_found.append({"type": "credit", "x0": t["x0"]})
        elif any(kw in text for kw in balance_kws):
            cols_found.append({"type": "balance", "x0": t["x0"]})
            
    cols_found.sort(key=lambda c: c["x0"])
    
    zones = {}
    for i in range(len(cols_found)):
        col = cols_found[i]
        if i == 0:
            start_x = col["x0"] - 10
        else:
            start_x = (cols_found[i-1]["x0"] + col["x0"]) / 2.0
            
        if i < len(cols_found) - 1:
            end_x = (col["x0"] + cols_found[i+1]["x0"]) / 2.0
        else:
            end_x = 9999.0
            
        zones[f"{col['type']}_zone"] = [start_x, end_x]

    print("\nNew Midpoint Zones:")
    for zname, zbounds in zones.items():
        print(f"  {zname}: [{zbounds[0]:.2f}, {zbounds[1]:.2f}]")

    print("\nToken Assignments:")
    targets = ["3,000.00", "120.00", "200.00", "30.00", "3,200.00"]
    for tok in tokens:
        text = tok.get("text", "").strip()
        if text in targets:
            x0 = tok.get("x0", 0)
            zone_name = "UNASSIGNED"
            for zname, zbounds in zones.items():
                if zbounds[0] <= x0 <= zbounds[1]:
                    zone_name = zname
                    break
            print(f"  Token '{text}': x0={x0:.2f} -> {zone_name}")

if __name__ == "__main__":
    main()
