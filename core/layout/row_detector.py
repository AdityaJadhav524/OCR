import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.layout.row_detector")

def _compute_y_tolerance(tokens: List[Dict[str, Any]]) -> float:
    if not tokens:
        return 3.0
    heights = sorted(t['y1'] - t['y0'] for t in tokens if 'y1' in t and 'y0' in t)
    if not heights:
        return 3.0
    median_h = heights[len(heights) // 2]
    return max(2.5, min(median_h * 0.85, 10.0))

def detect_rows(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes a flat list of tokens and clusters them into physical rows by page and Y-coordinate.
    Returns a list of 'Row' objects.
    """
    if not tokens:
        return []

    # Group tokens by page first
    pages = {}
    for t in tokens:
        p = t.get('page', 1)
        if p not in pages:
            pages[p] = []
        # Calculate Y-center for sorting
        t['yc'] = (t['y0'] + t['y1']) / 2.0
        pages[p].append(t)

    all_rows = []

    for page_num in sorted(pages.keys()):
        page_tokens = pages[page_num]
        
        y_tol = _compute_y_tolerance(page_tokens)
        sorted_tokens = sorted(page_tokens, key=lambda w: (w['yc'], w['x0']))
        
        cur_row_tokens = [sorted_tokens[0]]
        cur_y = sorted_tokens[0]['yc']
        
        for w in sorted_tokens[1:]:
            y = w['yc']
            if abs(y - cur_y) <= y_tol:
                cur_row_tokens.append(w)
            else:
                cur_row_tokens.sort(key=lambda x: x['x0'])
                all_rows.append({
                    "page": page_num,
                    "y0": min(t['y0'] for t in cur_row_tokens),
                    "y1": max(t['y1'] for t in cur_row_tokens),
                    "tokens": cur_row_tokens
                })
                cur_row_tokens = [w]
                cur_y = y
                
        if cur_row_tokens:
            cur_row_tokens.sort(key=lambda x: x['x0'])
            all_rows.append({
                "page": page_num,
                "y0": min(t['y0'] for t in cur_row_tokens),
                "y1": max(t['y1'] for t in cur_row_tokens),
                "tokens": cur_row_tokens
            })

    logger.info(f"Detected {len(all_rows)} physical rows from {len(tokens)} tokens.")
    return all_rows

def detect_transaction_blocks(rows: List[Dict[str, Any]], date_x_bounds: tuple = None) -> List[List[Dict[str, Any]]]:
    """
    Groups physical rows into transaction blocks (Main row + Continuation rows).
    This requires knowing where the Date column is, to anchor a new block.
    If date_x_bounds is provided, it uses spatial anchoring.
    """
    import re
    
    DATE_RE = re.compile(
        r'\b('
        r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|'           
        r'\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|'           
        r'\d{1,2}[\s\-\.][A-Za-z]{3,9}[\s\-\.]\d{2,4}'  
        r')\b',
        re.IGNORECASE
    )

    # Secondary pattern: some PDFs concatenate the date with the narration in a
    # single token (e.g. "07/02/22UPI-HARPREET SINGH-").  DATE_RE won't match
    # because there is no \b word boundary between the trailing digit and 'U'.
    # This prefix pattern specifically targets tokens whose TEXT STARTS with a
    # date immediately followed by a non-digit, so we don't accidentally split
    # on reference numbers that happen to contain date-like subsequences.
    DATE_PREFIX_RE = re.compile(
        r'^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\D',
        re.IGNORECASE
    )
    
    blocks = []
    current_block = []
    
    # Pre-calculate approximate page heights for geometric firewall
    page_heights = {}
    for r in rows:
        p = r.get("page", 1)
        if p not in page_heights or r.get("y1", 0) > page_heights[p]:
            page_heights[p] = r.get("y1", 0)

    contamination_keywords = ["IFSC", "MICR", "Branch", "Address", "Statement", "Page", "Customer", "Nomination", "Registered", "Closing balance"]
    
    for row in rows:
        tokens = row['tokens']
        if not tokens:
            continue
            
        is_anchor = False
        
        # Check if row has a date in the expected bounds, or just generally at the start
        for t in tokens:
            is_date = DATE_RE.search(t['text']) or DATE_PREFIX_RE.match(t['text'])
            if is_date:
                # Check if it falls within a very generous tolerance of the detected date column
                if date_x_bounds and (date_x_bounds[0] - 70 <= t['x0'] <= date_x_bounds[1] + 70):
                    is_anchor = True
                    break
                # Fallback: if it's on the far left, it's likely a date anchor regardless of headers
                elif t['x0'] < 150:
                    is_anchor = True
                    break
                    
        if is_anchor:
            if current_block:
                blocks.append(current_block)
            current_block = [row]
        else:
            if current_block:
                # Continuation Admission Firewall
                prev_row = current_block[-1]
                row_gap = row.get("y0", 0) - prev_row.get("y1", 0)
                
                # Check page wrap (different pages or massively negative gap)
                # If the current row is on a new page, it might be a valid wrap.
                # Wait, if row_gap < -50 AND it's the SAME page, it's definitely overlapping/weird.
                # If it's a new page, the gap will be negative, but we need to check if it's a valid narration.
                # Actually, our analysis showed page wrap headers have gap < -50 (like -2063).
                # But a valid continuation on a new page will also have a negative gap!
                # Wait, if it's a new page, the y-coordinate resets. So we should NOT reject just for negative gap if the page changed.
                same_page = row.get("page") == prev_row.get("page")
                if same_page and row_gap < -50:
                    continue
                    
                # Large Vertical Gap (Orphans like Statement Summary)
                if same_page and row_gap > 45:
                    continue
                    
                page_pos = row.get("y1", 0) / max(page_heights.get(row.get("page", 1), 1000), 1)
                row_text = " ".join([t.get("text", "") for t in row.get("tokens", [])]).lower()
                
                # Geometric Footer Zone (>88% down the page)
                is_footer = False
                if page_pos > 0.88:
                    if any(kw.lower() in row_text for kw in contamination_keywords):
                        is_footer = True
                        
                # Geometric Header Zone (<25% down the page)
                if page_pos < 0.25:
                    if any(kw.lower() in row_text for kw in contamination_keywords):
                        is_footer = True
                        
                if not is_footer:
                    current_block.append(row)
                
    if current_block:
        blocks.append(current_block)
        
    logger.info(f"Grouped {len(rows)} rows into {len(blocks)} transaction blocks.")
    return blocks
