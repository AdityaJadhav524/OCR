import re
from typing import Optional

def sanitize_balance_text(text: Optional[str]) -> Optional[str]:
    """
    Sanitizes raw OCR text for balance/amount columns to remove watermark 
    contamination and other garbage characters.
    
    Instead of aggressively stripping all non-digits (which causes 67882.00L128 
    to become 6788200128), this finds the first valid money pattern and ignores
    trailing/leading garbage.
    """
    if not text:
        return text
        
    text = str(text).strip()
    
    # 1. Handle DR/CR suffixes correctly
    suffix = ""
    upper_text = text.upper()
    if upper_text.endswith("CR"):
        suffix = "CR"
        text = text[:-2].strip()
    elif upper_text.endswith("DR"):
        suffix = "DR"
        text = text[:-2].strip()
        
    # 2. Find the first valid money pattern
    # Allow spaces, commas, periods as valid internal characters.
    # We want to match the LONGEST numeric block.
    # This matches digits, commas, and spaces, optionally followed by a dot and 1-2 digits
    pattern = r"-?[\d][\d,\s]*\.\s*\d{1,2}"
    
    match = re.search(pattern, text)
    if match:
        clean_val = match.group(0).replace(" ", "")
        return clean_val + suffix
        
    # If it doesn't match the strict decimal pattern, try a whole number pattern
    whole_pattern = r"-?[\d][\d,\s]*"
    match = re.search(whole_pattern, text)
    if match:
        clean_val = match.group(0).replace(" ", "")
        return clean_val + suffix

    return text
