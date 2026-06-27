import logging
from typing import Optional
from core.models.entity import NumericToken, NumericCandidate

logger = logging.getLogger("core.extractors.candidate_selector")

class CandidateSelector:
    """
    Selects the best candidate purely based on evidence (OCR confidence, merge confidence, format score)
    and NOT on ledger math. Ledger math is reserved for the validation engine.
    """
    
    @staticmethod
    def select_best(numeric_token: NumericToken) -> Optional[NumericCandidate]:
        if not numeric_token or not numeric_token.candidates:
            return None
            
        # Candidates are already ranked by the NumericNormalizer based on format confidence.
        # However, CandidateSelector can apply final weighting if needed.
        # For now, we simply take the highest confidence candidate.
        
        # Ensure they are sorted just in case
        sorted_candidates = sorted(numeric_token.candidates, key=lambda c: c.confidence, reverse=True)
        
        best_candidate = sorted_candidates[0]
        
        if numeric_token.log:
            numeric_token.log.winning_candidate = best_candidate
            
        return best_candidate
