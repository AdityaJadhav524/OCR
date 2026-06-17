import re
import logging
from typing import List, Dict, Any, Tuple

from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.validators.financial_audit import _parse_float

logger = logging.getLogger("core.parsers.credit_card_parser")

STOP_SECTIONS = [
    "Reward Summary",
    "Rewards Summary",
    "Important Messages",
    "Marketing Message",
    "Statement Generated",
    "Insurance",
    "Billing & Statement",
    "Fees & Charges",
    "How To Make Payments",
    "Credit Limit",
    "Available Credit Limit",
    "Cash Limit",
    "Minimum Amount Due",
    "Total Amount Due",
    "Total",
    "DISCOVER IRRESISTIBLE GIFTS",
    "NEVER FALL FOR FAKE THREATS"
]

_DATE_RE = re.compile(
    r'^\s*('
    r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|'
    r'\d{2,4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|'
    r'\d{1,2}[\s\-][A-Za-z]{3,9}[\s\-]\d{2,4}'
    r')',
    re.IGNORECASE
)

_DR_CR_SUFFIX_RE = re.compile(r'(?i)\b(CR|DR)\b$')

def parse_credit_card_transactions(tokens: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts transactions from a Credit Card statement.
    Does NOT enforce running balance conservation.
    Relies on date anchors and hard section stops.
    """
    rows = detect_rows(tokens)
    
    # We might not find a perfect header row if the statement is heavily segmented,
    # but we try to find date column bounds if possible.
    zones, _ = detect_columns(rows)
    date_zone = zones.get("date_zone")
    
    blocks = detect_transaction_blocks(rows, date_x_bounds=date_zone)
    
    accepted = []
    reject_log = []
    
    # A flag to stop parsing if we hit a terminal footer section 
    # (Though we might want to resume if we hit a new valid table, for now we skip invalid blocks)
    for bi, block in enumerate(blocks):
        valid_rows = []
        for row in block:
            row_text = " ".join([t.get("text", "") for t in row.get("tokens", [])])
            hit_stop = False
            for stop_word in STOP_SECTIONS:
                if stop_word.lower() in row_text.lower():
                    hit_stop = True
                    reject_log.append({
                        "reason": "hit_stop_word",
                        "stop_word": stop_word,
                        "row_text": row_text
                    })
                    break
            
            if hit_stop:
                # If we hit a stop word, stop collecting rows for this block.
                # If it's the anchor row, the block will have 0 rows and be skipped.
                break
                
            valid_rows.append(row)
            
        if not valid_rows:
            continue
            
        block = valid_rows
        
        # 2. Extract Date from the first row (anchor row)
        date_str = None
        anchor_tokens = block[0].get("tokens", [])
        for t in anchor_tokens:
            text = t.get("text", "").strip()
            m = _DATE_RE.match(text)
            if m:
                # Check within generous tolerance or generic left alignment
                if date_zone and not (date_zone[0] - 70 <= t["x0"] <= date_zone[1] + 70):
                    if t["x0"] > 150:
                        continue
                date_str = m.group(1)
                break
                    
        if not date_str:
            reject_log.append({
                "reason": "no_date_in_anchor"
            })
            continue

        # 3. Extract Amount & DR/CR
        # Credit cards usually have amounts at the far right. 
        # We look for amounts with "CR" or "DR" suffix, or just amounts in debit/credit zones.
        debit = None
        credit = None
        
        # Scan all tokens in the block to find amounts
        # We prefer tokens that end in CR/DR, or tokens that fall in known zones.
        # "First valid wins" to avoid footer pollution.
        
        amount_found = False
        
        for row in block:
            for t in row.get("tokens", []):
                text = t.get("text", "").strip().upper()
                
                # Check for explicit DR/CR suffix in the same token (e.g. "3000.00 DR" or "3000.00DR")
                if text.endswith("DR") or text.endswith("CR"):
                    clean_text = text[:-2].strip()
                    val = _parse_float(clean_text)
                    if val is not None:
                        if text.endswith("DR"):
                            if debit is None: debit = val
                        else:
                            if credit is None: credit = val
                        amount_found = True
                        continue
                
                # Check if it's just a number
                val = _parse_float(text)
                if val is not None and val > 0:
                    # If we have zones, use them
                    x0 = t["x0"]
                    
                    if "credit_zone" in zones and zones["credit_zone"][0] <= x0 <= zones["credit_zone"][1]:
                        if credit is None: credit = val
                        amount_found = True
                    elif "debit_zone" in zones and zones["debit_zone"][0] <= x0 <= zones["debit_zone"][1]:
                        if debit is None: debit = val
                        amount_found = True
                    # If it falls in a generic amount zone and there's a subsequent token "DR" or "CR"
                    elif "balance_zone" not in zones: # if no specific zones, we might rely on the next token
                        pass

            # Some layouts have the amount and then the next token is "CR" or "DR"
            if not amount_found:
                tokens = row.get("tokens", [])
                for i, t in enumerate(tokens):
                    val = _parse_float(t.get("text", ""))
                    if val is not None and val > 0:
                        if i + 1 < len(tokens):
                            next_text = tokens[i+1].get("text", "").strip().upper()
                            if next_text in ["DR", "CR"]:
                                if next_text == "DR" and debit is None:
                                    debit = val
                                    amount_found = True
                                elif next_text == "CR" and credit is None:
                                    credit = val
                                    amount_found = True

        if debit is None and credit is None:
            # Fallback: if we found an amount but no explicit DR/CR, default to DR for purchases
            # only if it's placed very far right (typical amount column)
            for row in block:
                for t in row.get("tokens", []):
                    val = _parse_float(t.get("text", ""))
                    if val is not None and val > 0 and t["x0"] > 300: # heuristic for far right
                        if debit is None: 
                            debit = val
                            amount_found = True
                            break
                if amount_found:
                    break

        if debit is None and credit is None:
            reject_log.append({
                "reason": "no_amount_found"
            })
            continue

        # 4. Extract Narration (Everything else)
        narration_parts = []
        for row in block:
            for t in row.get("tokens", []):
                text = t.get("text", "").strip()
                # Exclude date
                if text == date_str:
                    continue
                # Exclude exact amount strings
                if debit and _parse_float(text) == debit:
                    continue
                if credit and _parse_float(text) == credit:
                    continue
                if text.upper() in ["DR", "CR"]:
                    continue
                if text.upper().endswith("DR") and debit and _parse_float(text[:-2]) == debit:
                    continue
                if text.upper().endswith("CR") and credit and _parse_float(text[:-2]) == credit:
                    continue
                    
                narration_parts.append(text)
                
        narration = " ".join(narration_parts)

        accepted.append({
            "date": date_str,
            "narration": narration,
            "debit": debit,
            "credit": credit,
            "balance": None, # Credit cards don't have running balance per row
            "conservation_state": "CREDIT_CARD",
            "delta_amount": None,
            "amount_conflict": False,
            "source_statement_blank": not narration.strip()
        })
        
    tel = {
        "zones_detected": list(zones.keys()),
        "reject_log": reject_log
    }
        
    return accepted, tel
