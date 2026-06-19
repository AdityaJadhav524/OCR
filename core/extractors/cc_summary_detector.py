import re
from typing import Dict, Any

def extract_cc_summary(full_text: str) -> Dict[str, float]:
    """
    Deterministically extracts Credit Card summary blocks from text using regex.
    Returns a dictionary of float values. If a field is not found, it is None.
    """
    summary = {
        "statement_due_amount": None,
        "minimum_amount_due": None,
        "previous_balance": None,
        "total_purchases": None,
        "total_payments": None,
        "total_fees": None
    }
    
    # Pre-process text: collapse multiple spaces and remove commas in numbers
    text = re.sub(r' +', ' ', full_text).replace('\n', ' ')
    
    # Helper to find a value after a keyword pattern
    def find_amount(patterns):
        for p in patterns:
            # Look for the pattern followed by optional spaces, optional colon/rupee symbol, and then a number
            match = re.search(p + r'\s*[:=\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(',', '')
                try:
                    return float(val_str)
                except ValueError:
                    pass
            
            # Alternative: sometimes the amount is right before the keyword in some table layouts
            # Or separated by lots of spaces. Let's try a broader search if the strict one fails.
            # But the user asked for DETERMINISM. Strict is better.
        return None

    # Define regex patterns for each field
    due_patterns = [
        r'TOTAL AMOUNT DUE',
        r'TOTAL DUE',
        r'NEW BALANCE',
        r'STATEMENT DUE',
        r'AMOUNT DUE'
    ]
    summary['statement_due_amount'] = find_amount(due_patterns)
    
    min_due_patterns = [
        r'MINIMUM AMOUNT DUE',
        r'MINIMUM DUE',
        r'MINIMUM PAYMENT DUE',
        r'MIN AMT DUE'
    ]
    summary['minimum_amount_due'] = find_amount(min_due_patterns)
    
    prev_bal_patterns = [
        r'PREVIOUS BALANCE',
        r'OPENING BALANCE',
        r'LAST STATEMENT BALANCE'
    ]
    summary['previous_balance'] = find_amount(prev_bal_patterns)
    
    purchases_patterns = [
        r'TOTAL PURCHASES',
        r'PURCHASES\s*(?:AND|&)?\s*OTHER CHARGES',
        r'PURCHASES',
        r'DEBITS'
    ]
    summary['total_purchases'] = find_amount(purchases_patterns)
    
    payments_patterns = [
        r'PAYMENTS\s*(?:AND|&)?\s*CREDITS',
        r'TOTAL PAYMENTS',
        r'PAYMENTS RECEIVED',
        r'PAYMENTS',
        r'CREDITS'
    ]
    summary['total_payments'] = find_amount(payments_patterns)
    
    fees_patterns = [
        r'FINANCE CHARGES',
        r'TOTAL FEES',
        r'FEES\s*(?:AND|&)?\s*TAXES'
    ]
    summary['total_fees'] = find_amount(fees_patterns)
    
    return summary
