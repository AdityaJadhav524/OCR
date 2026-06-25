import logging
from typing import List, Dict, Any
import re
from core.validators.financial_audit import _parse_float

logger = logging.getLogger("core.extractors.candidate_generator")

def generate_balance_candidates(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Layer 3: Candidate Generator
    Interprets raw tokens to generate all possible balance candidates for each transaction.
    """
    for txn in transactions:
        balance_zone = txn.get("balance_zone")
        if not balance_zone:
            # If no balance zone, just create a candidate from the parsed balance if it exists
            if txn.get("balance") is not None:
                txn["balance_candidates"] = [{
                    "value": txn["balance"],
                    "source_text": str(txn["balance"]),
                    "evidence": ["no_balance_zone_fallback"]
                }]
            else:
                txn["balance_candidates"] = []
            continue
            
        all_tokens = txn.get("_source_tokens", [])
        candidates = []
        
        # We need to find all tokens in the balance zone
        balance_tokens = [tok for tok in all_tokens if balance_zone[0] <= tok.get("x0", 0) <= balance_zone[1]]
        
        for tok in balance_tokens:
            text = tok.get("text", "").strip()
            if not text:
                continue
                
            # Evidence generation
            evidence = []
            
            if "." in text:
                evidence.append("decimal_present")
            if "CR" in text.upper() or "DR" in text.upper():
                evidence.append("direction_suffix")
                
            # Attempt to parse
            # The sanitizer in _parse_float will find the longest match.
            parsed_val = _parse_float(text)
            
            # Is there a purely numeric string that might be a watermark?
            # Axis watermark example: "95142". Length 5, no decimal.
            if len(text) >= 4 and "." not in text and text.isdigit():
                evidence.append("watermark_pattern_suspect")
                
            if parsed_val is not None and parsed_val > 0:
                # Add the primary sanitized candidate
                candidates.append({
                    "value": parsed_val,
                    "source_text": text,
                    "x0": tok.get("x0"),
                    "evidence": evidence
                })
                
                # Check if the sanitizer stripped trailing digits that were actually valid,
                # or if the string is like "23595142" which might need a decimal shift (235951.42)
                if "." not in text and len(text) >= 6:
                    # Synthetic candidate for missed decimal (e.g., 23595142 -> 235951.42)
                    synthetic_val = parsed_val / 100.0
                    syn_evidence = evidence.copy()
                    syn_evidence.append("synthetic_decimal_shift")
                    candidates.append({
                        "value": synthetic_val,
                        "source_text": text,
                        "x0": tok.get("x0"),
                        "evidence": syn_evidence
                    })
        
        # Also ensure the original parser's choice is in the candidate list if valid
        orig_balance = txn.get("balance")
        if orig_balance is not None:
            exists = any(c["value"] == orig_balance for c in candidates)
            if not exists:
                candidates.append({
                    "value": orig_balance,
                    "source_text": str(orig_balance),
                    "evidence": ["parser_legacy_fallback"]
                })
                
        txn["balance_candidates"] = candidates

    return transactions
