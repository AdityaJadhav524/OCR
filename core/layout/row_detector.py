import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.layout.row_detector")

def _compute_y_tolerance(tokens: List[Dict[str, Any]]) -> float:
    """
    Compute adaptive Y-tolerance for row grouping.

    Scales with actual word height so the same logic works for:
      - Digital PDFs   (word height ~8-14px)  → tolerance ~4-7px
      - Scanned PDFs   (word height ~25-40px at 1800px render) → tolerance ~13-20px

    Cap is now 50% of median_h (not a fixed 10px), preventing tokens
    from the same physical row being split into separate rows on high-DPI scans.
    An absolute minimum of 3px prevents merging for very small text fragments.
    """
    if not tokens:
        return 3.0
    heights = sorted(t['y1'] - t['y0'] for t in tokens if 'y1' in t and 'y0' in t)
    if not heights:
        return 3.0
    median_h = heights[len(heights) // 2]
    # Use 50% of median height — safe for both digital and scanned coordinate spaces.
    # Previous cap of 10.0px was too tight for scanned PDFs (25-40px word heights).
    return max(3.0, median_h * 0.50)

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
        r'\d{1,2}[\s\-\./][A-Za-z]{3,9}[\s\-\./]\d{2,4}'  
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
        tokens = row.get('tokens', [])
        if not tokens:
            continue
            
        is_anchor = False
        import re

        # OCR_TOLERANT_DATE_RE — matches date-column tokens with common OCR corruptions.
        # Approved substitutions: O/o->0, l->1, |->-, :->-
        # Also matches tokens with a leading J/j (e.g. "J03-11-2021", "Jo3-11-2021")
        # and tokens with a trailing alpha (e.g. "05-11-2021l", "30-10-202t").
        # NOT approved: s->5, missing separator insertion, date fabrication.
        OCR_TOLERANT_DATE_RE = re.compile(
            r'^[Jj\|]?[Ool\d]{1,2}[\-\.\/\|\):][Ool\d]{1,2}[\-\.\/\|\):]\d{2,4}[a-zA-Z]?$|'
            r'^[Jj\|]?[Ool\d]{1,2}[\-\.\/\|\):]\d{2,4}[a-zA-Z]?$|'
            r'^[Jj\|]?[a-zA-Z]{3}[\-\.\/\|\):]\d{2,4}[a-zA-Z]?$',
            re.IGNORECASE
        )

        # LEADING_J_RE: only strip J/j when followed by a digit or O/o (not "JOURNAL", "JNPT", etc.)
        LEADING_J_RE = re.compile(r'^[Jj]([0-9Oo])', re.IGNORECASE)

        zone_tokens = []
        for t in tokens:
            if date_x_bounds:
                if date_x_bounds[0] - 70 <= t['x0'] <= date_x_bounds[1] + 70:
                    zone_tokens.append(t)
            elif t['x0'] < 150:
                zone_tokens.append(t)
                
        # Also include the full row text for cases where date bleeds slightly outside the zone
        row_str = " ".join([t['text'] for t in tokens])
        zone_str = " ".join([t['text'] for t in zone_tokens]) if zone_tokens else row_str

        # Check zone_str first, fallback to row_str if needed
        for text_to_check in (zone_str, row_str):
            is_date = DATE_RE.search(text_to_check) or DATE_PREFIX_RE.match(text_to_check)

            # If not a strict date, attempt safe in-place OCR healing
            if not is_date and OCR_TOLERANT_DATE_RE.match(text_to_check):
                healed = text_to_check

                # 1. Strip safe leading stray characters:
                if LEADING_J_RE.match(healed):
                    healed = healed[1:]
                elif healed and healed[0] in ('|',):
                    healed = healed[1:]

                # 2. Strip single trailing alpha
                if healed and healed[-1].isalpha():
                    healed = healed[:-1]

                # 3. Core character repairs
                healed = (healed
                          .replace('O', '0').replace('o', '0')
                          .replace('l', '1')
                          .replace('|', '-')
                          .replace(':', '-')
                          .replace(')', '-'))

                if DATE_RE.search(healed) or DATE_PREFIX_RE.match(healed):
                    is_date = True
                    
            if is_date:
                # To prevent matching a random date in the middle of a narration row as an anchor,
                # ensure the date is found at the beginning of the string being checked.
                match = DATE_RE.search(text_to_check)
                if match and match.start() < 20: # Date must start within first 20 characters
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
                    # RULE: MAX_OVERLAY_DEPTH = 2 (anchor + 1 continuation)
                    if len(current_block) >= 2:
                        blocks.append(current_block)
                        current_block = [row]
                        continue
                        
                    prev_text = " ".join([t.get("text", "") for t in current_block[-1].get("tokens", [])])
                    curr_text = " ".join([t.get("text", "") for t in row.get("tokens", [])])
                    
                    # Rule 1: Both lines contain dates -> NO OVERLAY
                    if bool(DATE_RE.search(prev_text)) and bool(DATE_RE.search(curr_text)):
                        blocks.append(current_block)
                        current_block = [row]
                        continue
                        
                    # Rule 2: Both lines contain amounts -> NO OVERLAY
                    AMOUNT_RE = re.compile(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b')
                    if len(AMOUNT_RE.findall(prev_text)) > 0 and len(AMOUNT_RE.findall(curr_text)) > 0:
                        blocks.append(current_block)
                        current_block = [row]
                        continue
                        
                    current_block.append(row)
                
    if current_block:
        blocks.append(current_block)
        
    logger.info(f"Grouped {len(rows)} rows into {len(blocks)} transaction blocks.")
    return blocks
