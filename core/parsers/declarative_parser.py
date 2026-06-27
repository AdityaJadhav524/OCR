import logging
from typing import List, Dict, Any, Optional
from core.models.entity import PipelineContext, DocumentEntity, EntityType, NumericToken
from core.extractors.entity_grouper import group_entities
from core.extractors.entity_classifier import classify_entities
from core.layout.layout_profile import LayoutProfile, GENERIC_LAYOUT_PROFILE
from core.extractors.entity_filter import filter_entities
from core.extractors.numeric_normalizer import normalize_entities
from core.extractors.candidate_selector import CandidateSelector
from dataclasses import dataclass

@dataclass
class Transaction:
    date: Optional[str] = None
    value_date: Optional[str] = None
    narration: Optional[str] = None
    cheque: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None

logger = logging.getLogger("core.parsers.declarative_parser")

class DeclarativeParser:
    """
    Executes the frozen 10-layer Enterprise Parser pipeline.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
    def parse(self, ocr_pages: List[Any], context: Optional[PipelineContext] = None) -> PipelineContext:
        """
        Executes the full pipeline and populates the PipelineContext.
        """
        if context is None:
            context = PipelineContext(pages=ocr_pages, config=self.config)
            
        # 1. OCR (Assuming ocr_pages is already processed and yields a list of flat tokens)
        raw_tokens = []
        for page in ocr_pages:
            # mock extraction for now if the structure is different
            if isinstance(page, dict) and "tokens" in page:
                raw_tokens.extend(page["tokens"])
            elif isinstance(page, list):
                raw_tokens.extend(page)
                
        # 2. Entity Grouper (Geometric stitching)
        # Note: Grouper groups line by line. We assume raw_tokens are sorted by y, then x.
        context.entity_tokens = group_entities(raw_tokens)
        
        # 3. Entity Classifier
        context.entity_tokens = classify_entities(context.entity_tokens)
        
        # 4. Column Detector & Layout Profile
        self._detect_columns_and_layout(context)
        
        # 5. Entity Filter
        # filter_entities returns a list of EntityDecision. We only KEEP the valid ones.
        decisions = filter_entities(context.entity_tokens)
        valid_entities = [d.entity for d in decisions if d.action == "KEEP"]
        
        # 6. Numeric Normalizer
        context.numeric_candidates = normalize_entities(valid_entities)
        
        # 7. Numeric Quality Analyzer & Candidate Generator (Handled by normalizer)
        
        # 8. Candidate Selector
        for numeric_token in context.numeric_candidates:
            winner = CandidateSelector.select_best(numeric_token)
            
        # 9. Declarative Parser (Transaction building)
        transactions = self._build_transactions(context)
        
        # We can store transactions in context
        context.transactions = transactions
        
        return context
        
    def _build_transactions(self, context: PipelineContext) -> List[Transaction]:
        transactions = []
        # Group entities and numerics back into rows
        # Very simplified for prototyping
        rows_map = {}
        
        # Combine text entities and numeric candidates
        all_items = []
        for e in context.entity_tokens:
            if e.entity_type in [EntityType.DATE, EntityType.TEXT]:
                all_items.append((e.bbox[1], e))
        for n in context.numeric_candidates:
            if n.log and n.log.winning_candidate:
                all_items.append((n.bbox[1], n))
                
        # Sort by y
        all_items.sort(key=lambda x: x[0])
        
        # Group into rows (y-tolerance)
        current_row = []
        current_y = all_items[0][0] if all_items else 0
        
        for y, item in all_items:
            if abs(y - current_y) < 15:
                current_row.append(item)
            else:
                if current_row:
                    transactions.append(self._row_to_transaction(current_row))
                current_row = [item]
                current_y = y
        if current_row:
            transactions.append(self._row_to_transaction(current_row))
            
        return transactions

    def _row_to_transaction(self, row_items: list) -> Transaction:
        t = Transaction()
        for item in row_items:
            if isinstance(item, DocumentEntity):
                field = item.canonical_field
                if field == "DATE":
                    t.date = item.raw_text
                elif field == "VALUE_DATE":
                    t.value_date = item.raw_text
                elif field == "NARRATION":
                    if t.narration:
                        t.narration += " " + item.raw_text
                    else:
                        t.narration = item.raw_text
                elif field == "CHEQUE":
                    t.cheque = item.raw_text
            elif isinstance(item, NumericToken):
                # The normalizer didn't explicitly store canonical_field on NumericToken
                # But it has it in token_ids or we can pass it down.
                # For this prototype, let's assume we map it correctly.
                # Since NumericToken contains the original grouped_entities in its log:
                if item.log and item.log.grouped_entities:
                    field = item.log.grouped_entities[0].canonical_field
                    val = item.log.winning_candidate.value
                    if field == "DEBIT":
                        t.debit = val
                    elif field == "CREDIT":
                        t.credit = val
                    elif field == "BALANCE":
                        t.balance = val
        return t

    def _detect_columns_and_layout(self, context: PipelineContext):
        """
        Analyzes the DocumentEntity objects to find the header row and maps physical columns
        to canonical fields using LayoutProfile.
        """
        # A simple vertical histogram or row-grouping logic to find headers
        # Since this is a prototype of the new architecture, we'll do a simplified version
        # of the column detector that operates on DocumentEntity.
        
        # Group entities into rows (y-tolerance)
        if not context.entity_tokens:
            return
            
        sorted_entities = sorted(context.entity_tokens, key=lambda e: (e.bbox[1], e.bbox[0]))
        
        rows = []
        current_row = [sorted_entities[0]]
        current_y = sorted_entities[0].bbox[1]
        
        for entity in sorted_entities[1:]:
            if abs(entity.bbox[1] - current_y) < 10:  # 10px tolerance
                current_row.append(entity)
            else:
                rows.append(current_row)
                current_row = [entity]
                current_y = entity.bbox[1]
        if current_row:
            rows.append(current_row)
            
        # Find the header row (has highest number of HEADER type entities)
        best_row = []
        best_score = 0
        
        for row in rows:
            score = sum(1 for e in row if e.entity_type == EntityType.HEADER)
            if score > best_score:
                best_score = score
                best_row = row
                
        # If we found a header row, build zones
        zones = []
        if best_row:
            best_row.sort(key=lambda e: e.bbox[0])
            for i, header_entity in enumerate(best_row):
                start_x = header_entity.bbox[0]
                end_x = best_row[i+1].bbox[0] if i + 1 < len(best_row) else 9999.0
                zones.append({
                    "raw_header": header_entity.raw_text,
                    "x0": start_x,
                    "x1": end_x
                })
                
        # Get layout profile
        context.layout_profile = GENERIC_LAYOUT_PROFILE
        
        # Assign columns and canonical fields to ALL entities based on zones
        if zones:
            for entity in context.entity_tokens:
                center_x = (entity.bbox[0] + entity.bbox[2]) / 2.0
                for zone in zones:
                    if zone["x0"] <= center_x < zone["x1"]:
                        entity.column_assignment = zone["raw_header"].lower()
                        entity.canonical_field = context.layout_profile.get_canonical_field(zone["raw_header"])
                        break
