import re
import json
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

from core.extractors.document_router import _extract_digital
from core.layout.row_detector import detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.validators.financial_audit import _parse_float

def normalize_zone_tokens(tokens: List[Dict]) -> List[Dict]:
    """
    Phase A.5: Zone Normalization
    Splits suffixes like CR/DR into separate tokens and isolates punctuation.
    """
    normalized = []
    _CR_DR_RE = re.compile(r'(CR|DR)$', re.IGNORECASE)
    
    for t in tokens:
        text = t.get("text", "").strip()
        if not text:
            continue
            
        m = _CR_DR_RE.search(text)
        if m and text != m.group(1):
            # Split into numeric and suffix
            numeric_part = text[:m.start()].strip()
            suffix_part = m.group(1)
            
            if numeric_part:
                normalized.append({"text": numeric_part, "x0": t["x0"], "x1": t["x1"]})
            normalized.append({"text": suffix_part, "x0": t["x1"], "x1": t["x1"]})
        else:
            normalized.append({"text": text, "x0": t["x0"], "x1": t["x1"]})
            
    return normalized

def score_candidate(candidate_str: str, merged_count: int, tokens: List[Dict]) -> float:
    """
    Score using parser-local evidence.
    """
    score = 0.0
    
    # +5 Valid decimal
    if '.' in candidate_str and candidate_str.rsplit('.', 1)[1].isdigit():
        score += 5.0
        
    # +4 CR/DR suffix
    if "CR" in candidate_str.upper() or "DR" in candidate_str.upper():
        score += 4.0
        
    # +4 Contiguous merge (if it was a merge)
    if merged_count > 1:
        score += 4.0
        
    # +2 Indian formatting (rough check: contains comma before last 3 digits)
    if re.search(r',\d{3}\.', candidate_str):
        score += 2.0
        
    # -6 Multiple decimal groups
    if candidate_str.count('.') > 1:
        score -= 6.0
        
    # -5 Isolated fragment (if it's just 1 or 2 digits with no decimals and was part of a larger set but not merged)
    # This is handled dynamically by preferring merges or decimals
    
    # OCR confidence (simulated for now since we use PyMuPDF here)
    # PyMuPDF doesn't give confidence, so we omit for digital files
    
    return score

def generate_zone_candidates(tokens: List[Dict], zone_type: str) -> List[Dict]:
    """
    Phase B: Contiguous window reconstruction.
    Generates contiguous windows of tokens and scores them.
    """
    normalized = normalize_zone_tokens(tokens)
    if not normalized:
        return []
        
    candidates = []
    n = len(normalized)
    
    for i in range(n):
        for j in range(i + 1, n + 1):
            window = normalized[i:j]
            merged_text = "".join(t["text"] for t in window)
            
            val = _parse_float(merged_text)
            if val is not None and val > 0:
                score = score_candidate(merged_text, j - i, window)
                
                # Bonus if right-most numeric token is included in the window
                if j == n:
                    score += 5.0
                    
                candidates.append({
                    "raw_text": merged_text,
                    "value": val,
                    "score": score,
                    "tokens_used": [t["text"] for t in window],
                    "window": (i, j)
                })
                
    # Sort by score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates

def _in_zone(x: float, zone: List[float]) -> bool:
    return zone is not None and zone[0] <= x <= zone[1]

def run_audit(pdf_path: str):
    print(f"--- TOKEN RECONSTRUCTION AUDIT ---")
    print(f"Document: {pdf_path}\n")
    
    full_text, pages, ext_stats, page_tokens = _extract_digital(pdf_path)
    blocks = detect_transaction_blocks(page_tokens)
    column_zones = detect_columns(page_tokens)
    
    for idx, row in enumerate(blocks[:30]):
        all_tokens = row.get("tokens", [])
        
        # Analyze Debit, Credit, Balance
        for zone_type in ["debit", "credit", "balance"]:
            zone_key = f"{zone_type}_zone"
            zone_bounds = column_zones.get(zone_key)
            if not zone_bounds: continue
            
            zone_tokens = [t for t in all_tokens if _in_zone(t["x0"], zone_bounds)]
            if not zone_tokens: continue
            
            # Print row and zone info
            print(f"ROW {idx+1}")
            print(f"{zone_type.capitalize()} Zone")
            print("Raw Tokens:")
            for t in zone_tokens:
                print(f"  {t['text']}")
                
            candidates = generate_zone_candidates(zone_tokens, zone_type)
            if candidates:
                print("Candidates:")
                for c in candidates:
                    print(f"  {c['raw_text']} -> {c['value']} (Score: {c['score']})")
                    
                winner = candidates[0]
                print(f"Winner:\n  {winner['value']}\nReason:\n  Highest parser score ({winner['score']})")
            else:
                print("Candidates:\n  None")
                
            print("-" * 40)

if __name__ == "__main__":
    import glob
    import os
    # Target the latest TJSB PDF in temp
    pdf_files = glob.glob("validation_lab/backend/temp/*24-25 -2 2.pdf")
    if pdf_files:
        latest = max(pdf_files, key=os.path.getmtime)
        run_audit(latest)
    else:
        print("No PDF found")
