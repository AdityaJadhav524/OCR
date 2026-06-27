import logging
from typing import List
from core.models.entity import DocumentEntity, EntityDecision, EntityType

logger = logging.getLogger("core.extractors.entity_filter")

def filter_entities(entities: List[DocumentEntity]) -> List[EntityDecision]:
    """
    Decides whether an entity should continue down the pipeline.
    Output: list of EntityDecision(entity, action="KEEP"|"DROP", reason=...)
    """
    decisions = []
    
    for entity in entities:
        # Check if the entity is in a numerical zone
        in_numeric_zone = entity.column_assignment in ["debit", "credit", "balance", "withdrawal", "deposit", "cheque"]
        
        if entity.entity_type == EntityType.FOOTER:
            decisions.append(EntityDecision(entity=entity, action="DROP", reason="FOOTER"))
            continue
            
        if entity.entity_type == EntityType.HEADER:
            decisions.append(EntityDecision(entity=entity, action="DROP", reason="HEADER"))
            continue
            
        if entity.entity_type == EntityType.DATE and in_numeric_zone:
            decisions.append(EntityDecision(entity=entity, action="DROP", reason="DATE_IN_NUMERIC_COLUMN"))
            continue
            
        if entity.entity_type == EntityType.TEXT and in_numeric_zone:
            # We don't drop it outright because sometimes text like "CR" or "NEFT" leaks in
            # But if it's purely alphabetical and long, we drop it.
            clean = "".join(c for c in entity.raw_text if c.isalnum())
            if clean.isalpha() and len(clean) > 3:
                decisions.append(EntityDecision(entity=entity, action="DROP", reason="TEXT_IN_NUMERIC_COLUMN"))
                continue
                
        # Default
        decisions.append(EntityDecision(entity=entity, action="KEEP", reason="VALID"))
        
    return decisions
