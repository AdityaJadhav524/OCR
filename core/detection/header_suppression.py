import logging
from typing import List, Dict, Any
from collections import defaultdict

logger = logging.getLogger("core.detection.header_suppression")

def suppress_headers_and_footers(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    P1: Header/Footer Suppression using heuristics.
    Suppresses tokens that are classified as headers or footers based on scoring.
    """
    if not tokens:
        return []
        
    pages = set(t.get('page', 0) for t in tokens)
    num_pages = len(pages)
    
    if num_pages < 2:
        return tokens  # Cannot reliably detect repeated headers on a single page
        
    # Find page boundaries to determine top/bottom 15%
    page_bounds = {}
    for p in pages:
        page_t = [t for t in tokens if t.get('page', 0) == p]
        if not page_t:
            continue
        min_y = min(t.get('y0', 0) for t in page_t)
        max_y = max(t.get('y1', 0) for t in page_t)
        page_bounds[p] = (min_y, max_y)
        
    import re
    def normalize_text(t_str: str) -> str:
        t_str = re.sub(r"(?i)page\s+\d+\s+of\s+\d+", "PAGE_N", t_str)
        t_str = re.sub(r"(?i)page\s+no\.?\s*\d+", "PAGE_N", t_str)
        t_str = re.sub(r"(?i)page\s+\d+", "PAGE_N", t_str)
        return t_str

    # Group tokens by normalized text
    text_to_tokens = defaultdict(list)
    for t in tokens:
        text = str(t.get('text', '')).strip()
        if len(text) > 0:
            norm_text = normalize_text(text)
            text_to_tokens[norm_text].append(t)
            
    keywords = ["Bank", "IFSC", "MICR", "Page", "Statement", "Account", "Currency", "Customer", "Nomination"]
    
    suppressed_texts = set()
    
    for text, tkns in text_to_tokens.items():
        pages_appeared = len(set(t.get('page', 0) for t in tkns))
        
        # Must appear on multiple pages to even be considered a repeating header
        if pages_appeared < 2:
            continue
            
        score = 0
        
        if pages_appeared / num_pages > 0.70:
            score += 3
            
        # Check if the majority are in top 15% or bottom 15%
        top_bottom_count = 0
        for t in tkns:
            p = t.get('page', 0)
            if p not in page_bounds: continue
            min_y, max_y = page_bounds[p]
            h = max_y - min_y
            if h <= 0: continue
            
            y_mid = (t.get('y0', 0) + t.get('y1', 0)) / 2
            relative_y = (y_mid - min_y) / h
            
            if relative_y <= 0.15 or relative_y >= 0.85:
                top_bottom_count += 1
                
        if top_bottom_count / len(tkns) > 0.5:
            # Check if it's top or bottom (majority)
            score += 2
            
        text_upper = text.upper()
        for kw in keywords:
            if kw.upper() in text_upper:
                score += 2
                
        if score >= 5:
            suppressed_texts.add(text)
            
    if suppressed_texts:
        logger.info(f"Header/Footer suppression removed {len(suppressed_texts)} unique strings (normalized).")
        logger.debug(f"Suppressed strings: {suppressed_texts}")
        
    filtered = [t for t in tokens if normalize_text(str(t.get('text', '')).strip()) not in suppressed_texts]
    return filtered
