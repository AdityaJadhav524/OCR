import sys
import os
import json
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.validators.financial_audit import _parse_float
from core.parsers.validation import normalize_amount_v2

def main():
    sources = [
        {"name": "YES Bank", "file": "scratch/yes_tokens.json"},
        {"name": "HDFC Bank", "file": "scratch/hdfc_tokens.json"},
        {"name": "BOI", "file": "scratch/boi_tokens.json"},
        {"name": "SBI", "file": "scratch/latest_upload_tokens.json"},
        {"name": "IndusInd Bank", "file": "scratch/indusind_tokens.json"},
    ]
    
    mismatches = []
    match_count = 0
    mismatch_count = 0
    
    report_lines = []
    report_lines.append("# AMOUNT DIFF REPORT")
    report_lines.append("")
    report_lines.append("| TOKEN | OLD_RESULT | NEW_RESULT | DIFFERENT | SOURCE_PDF |")
    report_lines.append("|-------|------------|------------|-----------|------------|")
    
    for source in sources:
        tokens = []
        if "file" in source and os.path.exists(source["file"]):
            with open(source["file"], 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    tokens = [t.get("text", "") for t in data if "text" in t]
                
        # Filter for amounts (has digits and maybe punctuation/letters)
        amount_tokens = set()
        for text in tokens:
            t = text.strip()
            # Only test things that have at least some digits
            if sum(c.isdigit() for c in t) > 1:
                # exclude long reference numbers without decimals
                if '.' in t or ',' in t or sum(c.isdigit() for c in t) <= 8:
                    amount_tokens.add(t)
                    
        # Also explicitly add some known difficult test cases for completeness
        if source["name"] == "YES Bank":
            amount_tokens.update(["400000.90i", "290000.0o", "24025.5o"])
            
        print(f"Source {source['name']} has {len(amount_tokens)} candidates")
        
        for val in amount_tokens:
            try:
                old_val = _parse_float(val)
            except:
                old_val = None
                
            try:
                new_val = normalize_amount_v2(val)
            except:
                new_val = None
                
            # If both are None, it wasn't a valid amount anyway, skip
            if old_val is None and new_val is None:
                continue
                
            # If they differ, or if one parsed and the other didn't
            if old_val != new_val:
                mismatch_count += 1
                report_lines.append(f"| `{val}` | {old_val} | {new_val} | ⚠️ YES | {source['name']} |")
                mismatches.append({"token": val, "old": old_val, "new": new_val, "source": source['name']})
            else:
                match_count += 1
                
    # Summary
    summary = []
    summary.append("## Summary")
    summary.append(f"- **MATCH_COUNT**: {match_count}")
    summary.append(f"- **MISMATCH_COUNT**: {mismatch_count}")
    summary.append("")
    summary.append("### Classification of Mismatches")
    
    ocr_garbage = 0
    multiple_period = 0
    comma_as_dec = 0
    date_contam = 0
    other = 0
    
    for m in mismatches:
        val = m["token"]
        if re.search(r'[a-zA-Z\|]', val):
            ocr_garbage += 1
        elif val.count('.') > 1:
            multiple_period += 1
        elif ',' in val and '.' not in val:
            comma_as_dec += 1
        elif '/' in val or '-' in val:
            date_contam += 1
        else:
            other += 1
            
    summary.append(f"1. OCR garbage recovery: {ocr_garbage}")
    summary.append(f"2. Multiple-period recovery: {multiple_period}")
    summary.append(f"3. Comma-as-decimal recovery: {comma_as_dec}")
    summary.append(f"4. Date contamination: {date_contam}")
    summary.append(f"5. Other: {other}")
    
    output_path = r"C:\Users\adity\.gemini\antigravity-ide\brain\a91c24b3-da82-413c-9098-5cc87be0fb55\AMOUNT_DIFF_REPORT.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n\n" + "\n".join(report_lines))
        
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    main()
