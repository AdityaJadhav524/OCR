import sys
import json
import numpy as np

sys.path.insert(0, r"Z:\CA")
from core.layout.row_detector import detect_rows
from core.layout.column_detector import detect_columns

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

def classify_row(text):
    text_lower = text.lower()
    footer_keywords = ["hdfc bank limited", "registered offce", "contens of this statemen", "subject to", "closing balance", "total credits"]
    header_keywords = ["statement of account", "account number", "branch", "ifsc", "state account", "yes bank accouat", "from"]
    if any(kw in text_lower for kw in footer_keywords):
        return "invalid_footer"
    if any(kw in text_lower for kw in header_keywords) and len(text_lower.split()) < 10:
        return "invalid_header"
    return "valid_continuation"

def analyze_bank(bank_name):
    tokens = get_tokens(bank_name)
    rows = detect_rows(tokens)
    
    # We need to detect columns page by page or globally
    zones, _ = detect_columns(rows)
    date_zone = zones.get("date_zone")
    if not date_zone:
        print(f"Skipping {bank_name} - no date zone detected")
        return []

    date_zone_left = date_zone[0]

    import re
    DATE_RE = re.compile(
        r'\b('
        r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|'           
        r'\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|'           
        r'\d{1,2}[\s\-\.][A-Za-z]{3,9}[\s\-\.]\d{2,4}'  
        r')\b',
        re.IGNORECASE
    )
    DATE_PREFIX_RE = re.compile(r'^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\D', re.IGNORECASE)

    data = []
    current_block = []
    
    for row in rows:
        row_tokens = row['tokens']
        if not row_tokens: continue
        
        is_anchor = False
        for t in row_tokens:
            if t['x0'] <= date_zone[1] + 5 and (DATE_RE.search(t['text']) or DATE_PREFIX_RE.match(t['text'])):
                is_anchor = True
                break
                
        if is_anchor:
            current_block = [row]
        else:
            if current_block:
                text = " ".join([t.get("text", "") for t in row_tokens])
                cls = classify_row(text)
                
                # Minimum x0 of all tokens in this row
                row_x0 = min([t['x0'] for t in row_tokens])
                delta_x = row_x0 - date_zone_left
                
                data.append({
                    "bank": bank_name,
                    "class": cls,
                    "row_x0": round(row_x0, 1),
                    "date_zone_left": round(date_zone_left, 1),
                    "delta_x": round(delta_x, 1),
                    "text": text
                })
                current_block.append(row)
                
    return data

all_data = []
for bank in TOKENS_FILES.keys():
    all_data.extend(analyze_bank(bank))

# Group by class
classes = ["valid_continuation", "invalid_footer", "invalid_header"]

for cls in classes:
    subset = [d for d in all_data if d["class"] == cls]
    print(f"\n{cls.upper()}")
    print(f"Count: {len(subset)}")
    if subset:
        deltas = [d["delta_x"] for d in subset]
        print(f"Min delta_x: {min(deltas)}")
        print(f"Max delta_x: {max(deltas)}")
        print(f"Avg delta_x: {round(np.mean(deltas), 1)}")
        
        # Print the edge cases
        if cls == 'valid_continuation':
            print("  Top 3 lowest delta_x (closest to left margin):")
            for d in sorted(subset, key=lambda x: x["delta_x"])[:3]:
                print(f"    [{d['bank']}] delta: {d['delta_x']:>5} | text: {d['text']}")
        else:
            print("  Top 3 highest delta_x (closest to table):")
            for d in sorted(subset, key=lambda x: x["delta_x"], reverse=True)[:3]:
                print(f"    [{d['bank']}] delta: {d['delta_x']:>5} | text: {d['text']}")

