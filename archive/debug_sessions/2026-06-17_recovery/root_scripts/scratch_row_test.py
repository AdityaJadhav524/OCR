import re

def test_row_extraction():
    line = "    03-Oct-2024 APBS CR INW - MUKHYAMANTRI MAZI LA            1,500.00    68,435.30"
    
    DATE_RE = re.compile(r'\d{2}-[A-Za-z]{3}-\d{2,4}')
    
    raw_credit = "1,500.00"
    raw_balance = "68,435.30"
    
    line_clean = line.strip()
    
    date_match = DATE_RE.search(line_clean)
    if date_match:
        line_clean = line_clean.replace(date_match.group(0), "", 1).strip()
        
    for raw_val in [raw_credit, raw_balance]:
        if raw_val.strip():
            idx = line_clean.rfind(raw_val.strip())
            if idx != -1:
                line_clean = line_clean[:idx] + line_clean[idx + len(raw_val.strip()):]
                
    # Normalize spaces
    dynamic_narration = re.sub(r'\s+', ' ', line_clean).strip()
    print(f"Narration: '{dynamic_narration}'")

test_row_extraction()
