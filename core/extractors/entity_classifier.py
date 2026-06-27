import re
from typing import List
from core.models.entity import DocumentEntity, EntityType

def _classify_single(text: str) -> EntityType:
    text_clean = text.strip()
    
    if not text_clean:
        return EntityType.UNKNOWN
        
    # DATE Check (DD/MM/YYYY, DD-MM-YY, etc)
    # Simple regex for typical banking dates
    date_pattern = r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$'
    if re.match(date_pattern, text_clean):
        return EntityType.DATE
        
    # NUMERIC Check (digits, commas, decimals, optional CR/DR, optional currency)
    # Allows spaces because grouper preserves them
    numeric_pattern = r'^([₹]?(?:rs\.?)?\s*)[0-9][0-9\s,\.]*(?:\s*[A-Za-z]{2})?$'
    if re.match(numeric_pattern, text_clean.lower()):
        # Ensure it actually has numbers
        if any(char.isdigit() for char in text_clean):
            return EntityType.NUMERIC
            
    # HEADER/FOOTER checks
    upper_text = text_clean.upper()
    if any(keyword in upper_text for keyword in ["PAGE", "GENERATED ON", "GRAND TOTAL", "IFSC", "MICR", "BRANCH"]):
        if len(text_clean) < 30: # Avoid classifying a whole narration as a footer just because it mentions a branch
            return EntityType.FOOTER
            
    if upper_text in ["DATE", "NARRATION", "PARTICULARS", "CHQ NO", "DEBIT", "CREDIT", "BALANCE", "WITHDRAWAL", "DEPOSIT"]:
        return EntityType.HEADER
        
    # Default
    return EntityType.TEXT

def classify_entities(entities: List[DocumentEntity]) -> List[DocumentEntity]:
    classified = []
    for entity in entities:
        new_type = _classify_single(entity.raw_text)
        classified.append(
            DocumentEntity(
                raw_text=entity.raw_text,
                bbox=entity.bbox,
                children=entity.children,
                entity_type=new_type,
                evidence=entity.evidence,
                column_assignment=entity.column_assignment,
                canonical_field=entity.canonical_field
            )
        )
    return classified
