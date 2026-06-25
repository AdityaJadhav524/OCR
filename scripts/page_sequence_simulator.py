import sys
import os
import json
import glob
from pathlib import Path
from dateutil.parser import parse as parse_date

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.statement_confidence_engine import validate_and_sort_transactions
from core.validators.running_balance_audit import run_running_balance_audit
from core.extractors.candidate_generator import generate_balance_candidates
from core.validators.balance_sanity_validator import run_balance_sanity_validator
from core.validators.financial_audit import _parse_float

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def find_latest_temp_file(corpus_file: str):
    pattern = str(TEMP_DIR / f"*{corpus_file}")
    matches = glob.glob(pattern)
    if not matches:
        exact = TEMP_DIR / corpus_file
        if exact.exists(): return exact
        return None
    return Path(sorted(matches, key=os.path.getmtime)[-1])

def get_date(txn):
    d = txn.get("date")
    if not d: return None
    try:
        return parse_date(d, dayfirst=True)
    except:
        return None

def score_page_link(page_A, page_B):
    score = 0
    
    # 1. Date Continuity
    if page_A["end_date"] and page_B["start_date"]:
        if page_A["end_date"] <= page_B["start_date"]:
            score += 100
        else:
            score -= 300 # Date Reversal
            
    # 2. Balance Continuity
    # Expected: A.end_balance + B.first.credit - B.first.debit == B.start_balance
    a_bal = _parse_float(page_A["end_balance"])
    b_bal = _parse_float(page_B["start_balance"])
    
    if a_bal is not None and b_bal is not None:
        first_b_txn = page_B["transactions"][0]
        c = _parse_float(first_b_txn.get("credit")) or 0.0
        d = _parse_float(first_b_txn.get("debit")) or 0.0
        
        diff = abs(a_bal + c - d - b_bal)
        
        if diff <= 1.0:
            score += 200
        elif diff <= 10.0:
            score += 150
        else:
            score -= 200 # Impossible balance jump
            
    # 3. Physical Page Distance Bonus
    dist = abs(page_A["page_index"] - page_B["page_index"])
    if dist == 1:
        score += 5
        
    return score

def simulate():
    pdf_name = "HDFC_SAVINGS_SCANNED.pdf"
    pdf_path = find_latest_temp_file(pdf_name)
    
    print("Parsing document...")
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, _ = parse_with_coordinates(page_tokens, pdf_name=pdf_name, bank="HDFC BANK", pdf_type="SCANNED")
    
    # Run Candidates and Sanity so we have clean balances
    txns = generate_balance_candidates(txns)
    txns = run_balance_sanity_validator(txns)
    
    # BASELINE
    sorted_txns, _ = validate_and_sort_transactions(txns)
    baseline_audit = run_running_balance_audit(sorted_txns)
    baseline_continuity = baseline_audit["continuity_percentage"]
    
    print(f"\nBASELINE CONTINUITY: {baseline_continuity}%\n")
    
    # PAGE SEQUENCE REPAIR
    from collections import defaultdict
    pages_dict = defaultdict(list)
    for txn in txns:
        page_num = txn.get("_source_page", txn.get("page", 0))
        pages_dict[page_num].append(txn)
        
    page_summaries = {}
    for p_num, p_txns in pages_dict.items():
        dates = [get_date(t) for t in p_txns]
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
                
    # Greedy Chain Builder
    current = earliest_page
    used = {current}
    chain = [current]
    
    while len(used) < len(page_summaries):
        best_next = None
        best_score = -9999
        
        scores_for_current = {}
        for candidate in page_summaries:
            if candidate in used: continue
            score = graph[current][candidate]
            scores_for_current[candidate] = score
            if score > best_score:
                best_score = score
                best_next = candidate
                
        print(f"From Page {current}, scores: {scores_for_current}, chose {best_next}")
                
        if best_next is None:
            # Fallback if disconnected
            for candidate in page_summaries:
                if candidate not in used:
                    best_next = candidate
                    break
                    
        chain.append(best_next)
        used.add(best_next)
        current = best_next
        
    print(f"Original Page Order: {list(page_summaries.keys())}")
    print(f"Predicted Page Order: {chain}")
    
    # Flatten
    repaired_txns = []
    for p in chain:
        repaired_txns.extend(page_summaries[p]["transactions"])
        
    # Run the standard ordering on the globally stitched list
    repaired_sorted, _ = validate_and_sort_transactions(repaired_txns)
    
    # REPAIRED AUDIT
    repaired_audit = run_running_balance_audit(repaired_sorted)
    repaired_continuity = repaired_audit["continuity_percentage"]
    
    print(f"\nREPAIRED CONTINUITY: {repaired_continuity}%\n")
    
if __name__ == "__main__":
    simulate()
