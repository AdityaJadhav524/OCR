from typing import Dict, Optional

class LayoutProfile:
    """
    Standardizes bank-specific column headers into a canonical schema.
    Every downstream layer works against the canonical field names.
    """
    def __init__(self, canonical_mapping: Dict[str, str]):
        # Mapping from lowercase header to CANONICAL_FIELD
        # e.g. {"withdrawal": "DEBIT", "deposit": "CREDIT", "value date": "VALUE_DATE"}
        self.canonical_mapping = canonical_mapping

    def get_canonical_field(self, raw_header: str) -> Optional[str]:
        if not raw_header:
            return None
            
        clean_header = raw_header.lower().strip()
        
        # Direct match
        if clean_header in self.canonical_mapping:
            return self.canonical_mapping[clean_header]
            
        # Fallback keyword match
        for key, canonical in self.canonical_mapping.items():
            if key in clean_header:
                return canonical
                
        return None

# Example fallback generic profile for banks without specific profiles
GENERIC_LAYOUT_PROFILE = LayoutProfile({
    "date": "DATE",
    "txn date": "DATE",
    "transaction date": "DATE",
    "value date": "VALUE_DATE",
    "val date": "VALUE_DATE",
    "narration": "NARRATION",
    "description": "NARRATION",
    "particulars": "NARRATION",
    "details": "NARRATION",
    "cheque": "CHEQUE",
    "chq": "CHEQUE",
    "ref": "REFERENCE",
    "withdrawal": "DEBIT",
    "debit": "DEBIT",
    "dr": "DEBIT",
    "deposit": "CREDIT",
    "credit": "CREDIT",
    "cr": "CREDIT",
    "balance": "BALANCE",
    "bal": "BALANCE"
})
