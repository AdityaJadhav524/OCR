import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("core.detection.footer_detector")

from dataclasses import dataclass, field

logger = logging.getLogger("core.detection.footer_detector")

@dataclass
class FooterDetectorConfig:
    footer_region: float = 0.85
    min_confidence: float = 0.70
    keyword_weight: float = 0.35
    geometry_weight: float = 0.20
    impossibility_weight: float = 0.40

class FooterDecision:
    def __init__(self, is_footer: bool, confidence: float, reasons: List[str], action: str = "CONTINUE"):
        self.is_footer = is_footer
        self.confidence = confidence
        self.reasons = reasons
        self.action = action  # "STOP_PAGE" | "IGNORE_ROW" | "CONTINUE"

class FooterDetector:
    def __init__(self, config: FooterDetectorConfig = None):
        self.config = config or FooterDetectorConfig()
        
        self.footer_keywords = [
            "GRAND TOTAL",
            "TOTAL",
            "DISCLAIMER",
            "ABBREVIATIONS USED",
            "END OF STATEMENT",
            "COMPUTER GENERATED",
            "SYSTEM GENERATED",
            "PAGE ",
            "CLOSING BALANCE",
            "FOR ANY QUERIES",
            "GENERATED ON"
        ]
        
        self.strong_terminal_keywords = [
            "GRAND TOTAL", 
            "END OF STATEMENT", 
            "DISCLAIMER", 
            "ABBREVIATIONS USED", 
            "COMPUTER GENERATED STATEMENT",
            "END OF REPORT"
        ]
        
        self.amount_re = re.compile(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b')
        self.date_prefix_re = re.compile(r'^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', re.IGNORECASE)

    def evaluate_row(self, row_str: str, page_pos: float, is_anchor: bool) -> FooterDecision:
        """
        Evaluates a row string and geometric context to determine if it is a statement footer.
        Returns a confidence-scored FooterDecision with an explicit action intent.
        """
        row_upper = row_str.upper()
        reasons = []
        confidence = 0.0
        
        # Level 1: Transaction Impossibility (Highest Weight)
        transaction_score = 0.0
        
        if is_anchor:
            transaction_score += 0.6
        elif self.date_prefix_re.match(row_str):
            transaction_score += 0.4
            
        amounts = self.amount_re.findall(row_str)
        if len(amounts) >= 2:
            transaction_score += 0.4
            
        if transaction_score < 0.5:
            confidence += self.config.impossibility_weight
            reasons.append("no_transaction_structure")
            
        # Level 2: Context (Geometric)
        if page_pos > self.config.footer_region:
            confidence += self.config.geometry_weight
            reasons.append("below_transaction_region")
            
        # Level 3: Keywords
        matched_keywords = [kw for kw in self.footer_keywords if kw in row_upper]
        if matched_keywords:
            confidence += self.config.keyword_weight
            reasons.append(f"footer_keyword({matched_keywords[0]})")
            
        is_footer = confidence >= self.config.min_confidence
        action = "CONTINUE"
        
        # Action Intents
        if any(kw in row_upper for kw in self.strong_terminal_keywords) and not is_anchor:
            is_footer = True
            confidence = max(confidence, 0.95)
            if "strong_terminal_keyword" not in reasons:
                reasons.append("strong_terminal_keyword")
            action = "STOP_PAGE"
        elif is_footer:
            action = "IGNORE_ROW"
            
        # Guard: Strong transaction structure overrides footer classification
        if transaction_score >= 0.8:
            is_footer = False
            confidence = 0.0
            reasons.append("strong_transaction_structure")
            action = "CONTINUE"
            
        if is_footer:
            # Telemetry integration
            try:
                from telemetry.logger import get_telemetry_logger
                t_logger = get_telemetry_logger()
                if t_logger:
                    t_logger.log_event(
                        "footer_detected",
                        {
                            "confidence": round(confidence, 2),
                            "action": action,
                            "reasons": reasons,
                            "text": row_str[:50]
                        }
                    )
            except ImportError:
                pass
                
            logger.debug(f"Footer detected (conf={confidence:.2f}, action={action}): {row_str[:50]}... Reasons: {reasons}")
            
        return FooterDecision(is_footer=is_footer, confidence=confidence, reasons=reasons, action=action)
