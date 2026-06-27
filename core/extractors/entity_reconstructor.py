import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("core.extractors.entity_reconstructor")

@dataclass
class OCRToken:
    text: str
    x0: float
    x1: float
    y0: float
    y1: float
    confidence: float

@dataclass
class DocumentEntity:
    raw_text: str
    bbox: list
    token_ids: list
    merge_confidence: float

def _compute_merge_confidence(t1: OCRToken, t2: OCRToken) -> float:
    # Basic spatial heuristics
    x_gap = t2.x0 - t1.x1
    
    # 1. Negative Rule: Large x-gap
    if x_gap > 30.0 or x_gap < -10.0:  # Too far apart, or overlapping completely
        return 0.0
        
    # 2. Negative Rule: Different baseline
    y_overlap = max(0, min(t1.y1, t2.y1) - max(t1.y0, t2.y0))
    h1 = t1.y1 - t1.y0
    h2 = t2.y1 - t2.y0
    min_h = min(h1, h2)
    if min_h > 0 and (y_overlap / min_h) < 0.5:
        return 0.0  # Less than 50% vertical overlap = different lines
        
    # Calculate confidence based on gap
    if x_gap <= 5.0:
        return 0.99
    elif x_gap <= 10.0:
        return 0.90
    elif x_gap <= 20.0:
        return 0.75
    else:
        return 0.40

def reconstruct_entities(tokens: List[OCRToken]) -> List[DocumentEntity]:
    """
    Takes a row of OCRTokens and geometrically merges horizontally adjacent 
    tokens into unified DocumentEntitys, without making semantic guesses.
    """
    if not tokens:
        return []
        
    # Sort tokens strictly left-to-right
    sorted_tokens = sorted(enumerate(tokens), key=lambda x: x[1].x0)
    
    entities = []
    
    current_idx, current_tok = sorted_tokens[0]
    current_text = current_tok.text
    current_bbox = [current_tok.x0, current_tok.y0, current_tok.x1, current_tok.y1]
    current_ids = [current_idx]
    current_conf = 1.0 # Base confidence
    
    for idx, tok in sorted_tokens[1:]:
        merge_conf = _compute_merge_confidence(current_tok, tok)
        
        if merge_conf >= 0.70:
            # Auto-merge or high-confidence merge
            current_text += " " + tok.text if (tok.x0 - current_tok.x1 > 3) else tok.text
            current_bbox[0] = min(current_bbox[0], tok.x0)
            current_bbox[1] = min(current_bbox[1], tok.y0)
            current_bbox[2] = max(current_bbox[2], tok.x1)
            current_bbox[3] = max(current_bbox[3], tok.y1)
            current_ids.append(idx)
            current_conf = min(current_conf, merge_conf)
            current_tok = OCRToken(
                text=current_text, 
                x0=current_bbox[0], 
                x1=current_bbox[2], 
                y0=current_bbox[1], 
                y1=current_bbox[3], 
                confidence=current_conf
            )
        else:
            # Commit current entity
            entities.append(DocumentEntity(
                raw_text=current_text,
                bbox=current_bbox,
                token_ids=current_ids,
                merge_confidence=current_conf
            ))
            # Start new entity
            current_idx, current_tok = idx, tok
            current_text = tok.text
            current_bbox = [tok.x0, tok.y0, tok.x1, tok.y1]
            current_ids = [idx]
            current_conf = 1.0

    # Commit the last entity
    entities.append(DocumentEntity(
        raw_text=current_text,
        bbox=current_bbox,
        token_ids=current_ids,
        merge_confidence=current_conf
    ))
    
    return entities
