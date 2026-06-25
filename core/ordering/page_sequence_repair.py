import logging
from typing import List, Dict, Any
from dateutil.parser import parse as parse_date
from core.validators.financial_audit import _parse_float

logger = logging.getLogger("core.ordering.page_sequence_repair")

def _get_date(txn: Dict[str, Any]):
    d = txn.get("date")
    if not d: return None
    try:
        return parse_date(d, dayfirst=True)
    except:
        return None

def score_page_link(page_a: Dict[str, Any], page_b: Dict[str, Any]) -> int:
    score = 0
    
    # 1. Date Continuity
    date_a = page_a["end_date"]
    date_b = page_b["start_date"]
    
    if date_a and date_b:
        delta_days = (date_b - date_a).days
        if 0 <= delta_days <= 2:
            score += 150  # Tight date continuity is excellent
        elif 2 < delta_days <= 10:
            score += 80
        elif delta_days > 10:
            score += 30   # Still valid, but weak
        else:
            score -= 300  # Negative delta -> Date reversal!
            
    # 2. Balance Continuity
    a_bal = _parse_float(page_a["end_balance"])
    b_bal = _parse_float(page_b["start_balance"])
    
    if a_bal is not None and b_bal is not None:
        first_b_txn = page_b["transactions"][0]
        c = _parse_float(first_b_txn.get("credit")) or 0.0
        d = _parse_float(first_b_txn.get("debit")) or 0.0
        
        diff = abs(a_bal + c - d - b_bal)
        
        if diff <= 1.0:
            score += 200
        elif diff <= 10.0:
            score += 100
        else:
            score -= 200  # Impossible balance jump
            
    # 3. Physical Distance Bonus (Tiny)
    dist = abs(page_a["page_index"] - page_b["page_index"])
    if dist == 1:
        score += 5
        
    return score

def run_page_sequence_repair(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups transactions by physical page, then uses a greedy graph search
    to restitch the pages in their true chronological sequence.
    """
    if not transactions:
        return transactions
        
    from collections import defaultdict
    pages_dict = defaultdict(list)
    for txn in transactions:
        page_num = txn.get("_source_page", txn.get("page", 0))
        pages_dict[page_num].append(txn)
        
    page_summaries = {}
    for p_num, p_txns in pages_dict.items():
        dates = [_get_date(t) for t in p_txns]
        dates = [d for d in dates if d]
        
        page_summaries[p_num] = {
            "page_index": p_num,
            "start_date": min(dates) if dates else None,
            "end_date": max(dates) if dates else None,
            "start_balance": p_txns[0].get("balance"),
            "end_balance": p_txns[-1].get("balance"),
            "transactions": p_txns
        }
        
    # Build Directed Graph
    graph = {}
    for p1 in page_summaries:
        graph[p1] = {}
        for p2 in page_summaries:
            if p1 == p2: continue
            graph[p1][p2] = score_page_link(page_summaries[p1], page_summaries[p2])
            
    # Find Earliest Page
    earliest_page = None
    earliest_date = None
    for p, summary in page_summaries.items():
        if summary["start_date"]:
            if not earliest_date or summary["start_date"] < earliest_date:
                earliest_date = summary["start_date"]
                earliest_page = p
                
    if not earliest_page:
        earliest_page = list(page_summaries.keys())[0]
        
    # Greedy Chain Builder
    current = earliest_page
    used = {current}
    chain = [current]
    
    while len(used) < len(page_summaries):
        best_next = None
        best_score = -9999
        
        for candidate in page_summaries:
            if candidate in used: continue
            score = graph[current][candidate]
            if score > best_score:
                best_score = score
                best_next = candidate
                
        if best_next is None:
            # Fallback if entirely disconnected
            for candidate in page_summaries:
                if candidate not in used:
                    best_next = candidate
                    break
                    
        chain.append(best_next)
        used.add(best_next)
        current = best_next
        
    logger.info(f"Page Sequence Repair complete. Original: {list(page_summaries.keys())} -> Repaired: {chain}")
    
    # Flatten
    repaired_txns = []
    for p in chain:
        repaired_txns.extend(page_summaries[p]["transactions"])
        
    return repaired_txns
