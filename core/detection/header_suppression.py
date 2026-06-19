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
        
    # --- Targeted Fingerprint Suppression (e.g. HDFC Page Boundaries) ---
    fingerprint_suppressed_token_ids = set()
    date_pattern = re.compile(r'\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}')
    
    for p in pages:
        page_t = [t for t in tokens if t.get('page', 0) == p]
        
        statement_tokens = [t for t in page_t if "statement of account" in str(t.get('text', '')).lower()]
        
        for stmt_tok in statement_tokens:
            stmt_yc = (stmt_tok.get('y0', 0) + stmt_tok.get('y1', 0)) / 2
            
            # Find tokens in the same horizontal band (+/- 20 pixels)
            band_tokens = [t for t in page_t if abs((t.get('y0', 0) + t.get('y1', 0))/2 - stmt_yc) <= 20]
            
            band_text = " ".join([str(t.get('text', '')).lower() for t in band_tokens])
            dates_found = date_pattern.findall(band_text)
            
            if len(dates_found) >= 2 and ("from" in band_text or "to" in band_text):
                # Fingerprint matched! Suppress the structural parts of this band.
                for t in band_tokens:
                    txt = str(t.get('text', '')).lower()
                    if ("statement of account" in txt or 
                        "from" in txt or 
                        "to" in txt or 
                        date_pattern.search(txt)):
                        fingerprint_suppressed_token_ids.add(id(t))
                        
    if fingerprint_suppressed_token_ids:
        logger.info(f"Targeted Fingerprint Suppression removed {len(fingerprint_suppressed_token_ids)} tokens matching specific bank headers.")

    # Do not suppress tokens that are structurally protected
    filtered = []
    for t in tokens:
        if t.get('protected') is True:
            filtered.append(t)
        elif id(t) in fingerprint_suppressed_token_ids:
            continue
        elif normalize_text(str(t.get('text', '')).strip()) not in suppressed_texts:
            filtered.append(t)
            
    return filtered
