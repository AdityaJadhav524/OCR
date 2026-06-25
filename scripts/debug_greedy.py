from datetime import datetime

def score_page_link(page_a, page_b):
    score = 0
    
    date_a = page_a["end_date"]
    date_b = page_b["start_date"]
    
    if date_a and date_b:
        delta_days = (date_b - date_a).days
        if 0 <= delta_days <= 2:
            score += 150
        elif 2 < delta_days <= 10:
            score += 80
        elif delta_days > 10:
            score += 30
        else:
            score -= 300
            
    a_bal = page_a["end_balance"]
    b_bal = page_b["start_balance"]
    
    if a_bal is not None and b_bal is not None:
        c = 0.0
        d = 0.0
        diff = abs(a_bal + c - d - b_bal)
        if diff <= 1.0:
            score += 200
        elif diff <= 10.0:
            score += 100
        else:
            score -= 200
            
    dist = abs(page_a["page_index"] - page_b["page_index"])
    if dist == 1:
        score += 5
        
    return score

summaries = {
    1: {"page_index": 1, "start_date": datetime(2025, 5, 13), "end_date": datetime(2025, 5, 17), "end_balance": 728.66},
    2: {"page_index": 2, "start_date": datetime(2025, 5, 30), "end_date": datetime(2025, 5, 31), "start_balance": 693893.42, "end_balance": 691.77},
    4: {"page_index": 4, "start_date": datetime(2025, 5, 23), "end_date": datetime(2025, 5, 27), "start_balance": 701079.52, "end_balance": 698933.52},
    6: {"page_index": 6, "start_date": datetime(2025, 5, 27), "end_date": datetime(2025, 5, 29), "start_balance": 698808.52, "end_balance": 697.72},
    8: {"page_index": 8, "start_date": datetime(2025, 5, 29), "end_date": datetime(2025, 5, 30), "start_balance": 697719.42, "end_balance": 694693.42},
    12: {"page_index": 12, "start_date": datetime(2025, 5, 18), "end_date": datetime(2025, 5, 22), "start_balance": 714.02, "end_balance": 701.15},
}

for b in [2, 4, 6, 8, 12]:
    print(f"Page 1 -> Page {b}: {score_page_link(summaries[1], summaries[b])}")
