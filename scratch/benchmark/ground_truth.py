import json
import sys

def load_ground_truth(bank_name):
    if bank_name == "YES":
        with open(r"Z:\CA\scratch\yes_bank_83.json", "r", encoding="utf-8") as f:
            return json.load(f)
    elif bank_name == "SBI":
        # The SBI baseline is in regression_baseline.json
        with open(r"Z:\CA\scratch\regression_baseline.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            # Find the sbi_4txn one
            for d in data:
                if d.get("pdf") == "sbi_4txn":
                    return d.get("transactions", [])
    elif bank_name == "HDFC":
        return [] # We are using Option C for HDFC (no row-matched recall)
    return []

def normalize_date(d):
    if not d: return ""
    d = str(d).replace("-", "/").replace(".", "/")
    parts = d.split("/")
    if len(parts) == 3:
        y = parts[2]
        if len(y) == 2:
            y = "20" + y
        return f"{parts[0]:0>2}/{parts[1]:0>2}/{y}"
    return d

def _to_float(v):
    if v is None: return None
    if isinstance(v, str):
        v = v.replace(",", "").replace("CR", "").replace("DR", "").strip()
        if not v: return None
    try:
        return float(v)
    except:
        return None
