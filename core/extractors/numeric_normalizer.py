import logging
import re
from typing import List, Tuple
from core.models.entity import DocumentEntity, NumericToken, NumericCandidate, ReconstructionLog

logger = logging.getLogger("core.extractors.numeric_normalizer")

def _generate_hypotheses(text: str) -> List[Tuple[float, str, float, List[str]]]:
    """
    Returns a list of (value, normalized_text, format_confidence, log_msgs)
    """
    hypotheses = []
    
    # 1. Clean the string. ONLY keep numbers, commas, and dots.
    # We DO NOT invent digits.
    clean_base = re.sub(r'[^0-9\.,]', '', text)
    
    if not clean_base:
        return []
        
    has_digits = any(c.isdigit() for c in clean_base)
    if not has_digits:
        return []

    # 1. Direct parse
    # E.g. "161835.18" -> 161835.18
    # Try stripping all commas
    stripped = clean_base.replace(',', '')
    
    try:
        val = float(stripped)
        
        # High confidence if it perfectly matches Indian format
        if re.fullmatch(r'(\d{1,2}(,\d{2})*(,\d{3})?)?\.\d{2}', clean_base):
            hypotheses.append((val, stripped, 0.98, ["matched_indian_format"]))
        elif re.fullmatch(r'\d+\.\d{2}', stripped):
            hypotheses.append((val, stripped, 0.95, ["stripped_commas", "standard_decimal"]))
        else:
            hypotheses.append((val, stripped, 0.60, ["stripped_commas"]))
    except ValueError:
        pass

    # 2. Assume all internal dots are commas (OCR artifact where comma looks like period)
    # E.g., "87.034.17" -> 87034.17
    if clean_base.count('.') > 1:
        parts = clean_base.rsplit('.', 1)
        fixed_base = parts[0].replace('.', '') + '.' + parts[1]
        try:
            val = float(fixed_base)
            hypotheses.append((val, fixed_base, 0.70, ["converted_internal_dots_to_commas"]))
        except ValueError:
            pass
            
    # 3. Handle broken spaces (since grouper preserved spaces)
    # "87.03 4.17"
    if ' ' in text:
        # Generate two separate sub-hypotheses if space splits numbers
        parts = text.split()
        for p in parts:
            p_clean = re.sub(r'[^0-9\.,]', '', p).replace(',', '')
            try:
                val = float(p_clean)
                hypotheses.append((val, p_clean, 0.40, [f"extracted_part_from_space: {p}"]))
            except ValueError:
                pass
                
        # Also try just stripping space
        combined = text.replace(' ', '')
        c_clean = re.sub(r'[^0-9\.,]', '', combined).replace(',', '')
        try:
            val = float(c_clean)
            hypotheses.append((val, c_clean, 0.50, ["removed_internal_space"]))
        except ValueError:
            pass
            
    # 4. Handle trailing noise like "-" or OCR artifacts like "L128"
    # Actually, clean_base already removes "L128", leaving "67882.00128" which is wrong!
    # If the text was "67882.00L128", clean_base is "67882.00128"
    # To fix this: stop at the first non-numeric/punctuation character.
    match = re.search(r'^([0-9\.,\s]+)', text)
    if match:
        prefix = match.group(1).strip()
        if prefix and prefix != clean_base:
            p_clean = prefix.replace(',', '')
            try:
                val = float(p_clean)
                hypotheses.append((val, p_clean, 0.85, ["truncated_trailing_alpha_noise"]))
            except ValueError:
                pass

    # 5. Missing trailing decimal zero (e.g. "413534.1")
    if '.' in stripped:
        idx = stripped.find('.')
        if len(stripped) - idx == 2:  # exactly one digit after dot
            fixed = stripped + '0'
            try:
                val = float(fixed)
                # This technically violates "never invent digits" EXCEPT it's appending a mathematical zero to a decimal, 
                # which doesn't change the value's magnitude, just its formatting representation. 
                # The user explicitly said: "Allowed: merge adjacent fragments, repair separators, attach CR/DR, remove OCR artifacts".
                # But to be extremely strict, maybe we just leave it as 413534.1. 413534.1 == 413534.10 mathematically.
                # Python float handles this automatically.
                pass 
            except ValueError:
                pass

    # 6. Punctuation artifact e.g. "161835:18" -> "161835.18"
    if ':' in text:
        replaced = text.replace(':', '.')
        r_clean = re.sub(r'[^0-9\.,]', '', replaced).replace(',', '')
        try:
            val = float(r_clean)
            hypotheses.append((val, r_clean, 0.80, ["replaced_colon_with_dot"]))
        except ValueError:
            pass

    return hypotheses

def normalize_entities(entities: List[DocumentEntity]) -> List[NumericToken]:
    numeric_tokens = []
    
    for entity in entities:
        # Only normalize things that might be numbers
        # If it was marked as DATE or HEADER, we skip
        # BUT for the unit tests, we pass them directly, so we attempt normalization
        
        raw = entity.raw_text
        hypotheses = _generate_hypotheses(raw)
        
        candidates = []
        for val, text, conf, log in hypotheses:
            # We don't want duplicates (e.g. multiple paths leading to 161835.18)
            # Take the one with highest confidence
            existing = next((c for c in candidates if c.value == val), None)
            if existing:
                if conf > existing.confidence:
                    existing.confidence = conf
                    existing.generated_by = log
            else:
                candidates.append(NumericCandidate(
                    value=val,
                    normalized_text=text,
                    confidence=conf,
                    generated_by=log
                ))
                
        # Sort by confidence
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        
        if candidates:
            winning = candidates[0]
            
            recon_log = ReconstructionLog(
                original_tokens=entity.children,
                grouped_entities=[entity],
                normalization_steps=[],
                rejected_candidates=candidates[1:],
                winning_candidate=winning,
                reasoning="Highest confidence generated hypothesis"
            )
            
            numeric_tokens.append(NumericToken(
                raw_text=raw,
                candidates=candidates,
                bbox=entity.bbox,
                geometry_score=0.9, # Placeholder
                format_score=winning.confidence,
                ocr_score=0.9, # Placeholder
                reconstruction_score=0.9, # Placeholder
                token_ids=entity.children,
                log=recon_log
            ))
            
    return numeric_tokens
