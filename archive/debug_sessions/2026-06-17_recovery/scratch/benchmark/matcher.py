import math
from .ground_truth import normalize_date, _to_float

def match_transactions(extracted, gt):
    """
    Match extracted transactions to ground truth.
    Returns: TP list (extracted, gt), FP list (extracted), FN list (gt)
    """
    unmatched_gt = list(gt)
    unmatched_ext = list(extracted)
    
    matched_pairs = []
    
    # Simple greedy matching
    for ext in extracted:
        best_match_idx = -1
        best_score = -1
        
        e_date = normalize_date(ext.get("date"))
        e_deb = _to_float(ext.get("debit"))
        e_cre = _to_float(ext.get("credit"))
        e_bal = _to_float(ext.get("balance"))
        
        for i, g in enumerate(unmatched_gt):
            score = 0
            g_date = normalize_date(g.get("date"))
            g_deb = _to_float(g.get("debit"))
            g_cre = _to_float(g.get("credit"))
            g_bal = _to_float(g.get("balance"))
            
            # Must match at least date
            if e_date and g_date and e_date == g_date:
                score += 1
            else:
                continue # Require date match for now, or maybe just amount? Let's just score.
            
            # Amount matching
            deb_match = e_deb is not None and g_deb is not None and math.isclose(e_deb, g_deb, abs_tol=0.01)
            cre_match = e_cre is not None and g_cre is not None and math.isclose(e_cre, g_cre, abs_tol=0.01)
            bal_match = e_bal is not None and g_bal is not None and math.isclose(e_bal, g_bal, abs_tol=0.01)
            
            if deb_match: score += 2
            if cre_match: score += 2
            if bal_match: score += 2
            
            if score > best_score and score >= 3: # Must match date + at least one amount/balance
                best_score = score
                best_match_idx = i
                
        if best_match_idx != -1:
            matched_pairs.append((ext, unmatched_gt.pop(best_match_idx)))
            unmatched_ext.remove(ext)
            
    return matched_pairs, unmatched_ext, unmatched_gt
