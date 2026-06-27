import logging
from typing import List
from core.models.entity import DocumentEntity, MergeEvidence

logger = logging.getLogger("core.extractors.entity_grouper")

# This would ideally be dynamic based on the page's median character width, but 
# for the TDD prototype we'll assume a standard 8px-12px median char width
MEDIAN_CHAR_WIDTH = 10.0

def _compute_merge_evidence(t1, t2) -> MergeEvidence:
    x_gap = t2.x0 - t1.x1
    h1 = t1.y1 - t1.y0
    h2 = t2.y1 - t2.y0
    
    y_overlap = max(0, min(t1.y1, t2.y1) - max(t1.y0, t2.y0))
    min_h = min(h1, h2)
    line_overlap = (y_overlap / min_h) if min_h > 0 else 0.0
    
    baseline_similarity = 1.0 - (abs(t1.y1 - t2.y1) / min_h) if min_h > 0 else 0.0
    height_similarity = min_h / max(h1, h2) if max(h1, h2) > 0 else 0.0
    
    return MergeEvidence(
        x_gap=x_gap,
        baseline_similarity=baseline_similarity,
        font_similarity=1.0,  # Placeholder
        height_similarity=height_similarity,
        ocr_confidence=min(t1.confidence, t2.confidence),
        line_overlap=line_overlap,
        merged_by="UNKNOWN"
    )

def _can_merge(t1, t2, evidence: MergeEvidence) -> bool:
    # Negative Rules
    if t1.page_id != t2.page_id:
        return False
    if t1.line_id != t2.line_id:
        # In a real system, OCR lines might differ if OCR engine broke the line early
        pass 
    if evidence.x_gap > MEDIAN_CHAR_WIDTH * 2.5:
        return False
    if evidence.x_gap < - (MEDIAN_CHAR_WIDTH * 2): # massive overlap
        return False
    if evidence.baseline_similarity < 0.5:
        return False
    if evidence.line_overlap < 0.3:
        return False
        
    return True

def _determine_strategy(t1_text: str, t2_text: str) -> str:
    if t2_text.upper() in ["CR", "DR"]:
        return "suffix_attach"
    if t1_text == "₹" or t1_text.upper() in ["RS", "RS.", "INR"]:
        return "currency_prefix_merge"
    return "horizontal_merge"

def group_entities(tokens: list) -> List[DocumentEntity]:
    """
    Pure geometric grouping. Groups adjacent tokens on the same line into DocumentEntitys.
    """
    if not tokens:
        return []
        
    # Strictly sort left-to-right (assuming single row)
    sorted_tokens = sorted(enumerate(tokens), key=lambda x: x[1].x0)
    
    entities = []
    
    current_idx, current_tok = sorted_tokens[0]
    current_text = current_tok.text
    current_bbox = [current_tok.x0, current_tok.y0, current_tok.x1, current_tok.y1]
    current_ids = [current_idx]
    current_evidence = None
    
    for idx, tok in sorted_tokens[1:]:
        evidence = _compute_merge_evidence(current_tok, tok)
        
        if _can_merge(current_tok, tok, evidence):
            strategy = _determine_strategy(current_text, tok.text)
            evidence.merged_by = strategy
            
            # Always space-separate merged fragments to preserve provenance
            current_text += " " + tok.text
                
            current_bbox[0] = min(current_bbox[0], tok.x0)
            current_bbox[1] = min(current_bbox[1], tok.y0)
            current_bbox[2] = max(current_bbox[2], tok.x1)
            current_bbox[3] = max(current_bbox[3], tok.y1)
            current_ids.append(idx)
            
            # Create dummy token representing the merged box for the next iteration's gap check
            current_tok = type(current_tok)(
                text=current_text, 
                x0=current_bbox[0], 
                x1=current_bbox[2], 
                y0=current_bbox[1], 
                y1=current_bbox[3], 
                confidence=evidence.ocr_confidence,
                page_id=current_tok.page_id,
                line_id=current_tok.line_id
            )
            current_evidence = evidence
        else:
            # Commit
            entities.append(DocumentEntity(
                raw_text=current_text,
                bbox=current_bbox,
                children=current_ids,
                evidence=current_evidence
            ))
            # Start new
            current_idx, current_tok = idx, tok
            current_text = tok.text
            current_bbox = [tok.x0, tok.y0, tok.x1, tok.y1]
            current_ids = [idx]
            current_evidence = None

    entities.append(DocumentEntity(
        raw_text=current_text,
        bbox=current_bbox,
        children=current_ids,
        evidence=current_evidence
    ))
    
    return entities
