import json
import sys
import os

def load_data(mode):
    try:
        with open(rf"Z:\CA\scratch\regression_{mode}.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {mode} data: {e}")
        return {}

def main():
    before = load_data("BEFORE")
    after = load_data("AFTER")
    
    if not before or not after:
        return
        
    print(f"| {'Bank PDF':<65} | {'Txn Before':>10} | {'Txn After':>9} | {'Dr Before':>15} | {'Dr After':>15} | {'Cr Before':>15} | {'Cr After':>15} | {'Rej Before':>10} | {'Rej After':>9} |")
    print(f"|{'-'*67}|{'-'*12}|{'-'*11}|{'-'*17}|{'-'*17}|{'-'*17}|{'-'*17}|{'-'*12}|{'-'*11}|")
    
    total_contaminated = 0
    total_suppressed = 0 # Cannot easily track unless we mock logging, but we will print contaminated
    
    for pdf, b in before.items():
        a = after.get(pdf, {})
        if not a:
            print(f"MISSING IN AFTER: {pdf}")
            continue
            
        print(f"| {pdf[:65]:<65} | {b['count']:>10} | {a['count']:>9} | {b['debit']:>15.2f} | {a['debit']:>15.2f} | {b['credit']:>15.2f} | {a['credit']:>15.2f} | {b['rejected']:>10} | {a['rejected']:>9} |")
        
        # Check contaminated rows in AFTER
        for r in a.get("reject_log", []):
            if r.get("reject_reason") == "ROW_CONTAMINATION":
                total_contaminated += 1
                
    print(f"\nTotal Contaminated Rows Detected: {total_contaminated}")

if __name__ == "__main__":
    main()
