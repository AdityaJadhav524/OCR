from typing import List, Dict, Any

def test_admission():
    page_heights = {12: 2200}
    
    # Simulate current_block containing POCKIT txn
    current_block = [
        {"page": 12, "y0": 800, "y1": 850, "tokens": [{"text": "22/05/25"}]}
    ]
    
    # Simulate footer row
    row = {"page": 12, "y0": 1900, "y1": 1950, "tokens": [{"text": "HDFC BANK LIMITED"}]}
    
    prev_row = current_block[-1]
    row_gap = row.get("y0", 0) - prev_row.get("y1", 0)
    print(f"row_gap: {row_gap}")
    
    same_page = row.get("page") == prev_row.get("page")
    if same_page and row_gap < -50:
        print("Rejected by row_gap < -50")
        return
        
    if same_page and row_gap > 45:
        print("Rejected by row_gap > 45")
        return
        
    print("Accepted!")
    
test_admission()
