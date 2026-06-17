import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.validators.confidence_scorer")

def score_transaction(txn: Dict[str, Any], signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a deterministic, explainable confidence score for a transaction.
    Instead of hardcoding math, we rely on clear signals.
    """
    weights = {
        "balance_reconciled": 40,
        "date_valid": 10,
        "amount_valid": 15,
        "column_confidence": 20,     # Percentage (0.0 to 1.0)
        "narration_confidence": 15   # Percentage (0.0 to 1.0)
    }
    
    score = 0.0
    
    if signals.get("balance_reconciled"):
        score += weights["balance_reconciled"]
    if signals.get("date_valid"):
        score += weights["date_valid"]
    if signals.get("amount_valid"):
        score += weights["amount_valid"]
        
    score += weights["column_confidence"] * signals.get("column_confidence", 0.0)
    score += weights["narration_confidence"] * signals.get("narration_confidence", 0.0)
    
    warnings = []
    if not signals.get("balance_reconciled"):
        warnings.append("Balance reconciliation failed.")
    if signals.get("column_confidence", 0.0) < 0.8:
        warnings.append("Tokens poorly aligned with expected columns.")
        
    return {
        "score": round(score, 2),
        "signals": signals,
        "warnings": warnings
    }

def score_statement(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Rolls up transaction scores into a statement-level confidence score.
    """
    if not transactions:
        return {"statement_score": 0.0, "warnings": ["No transactions found."]}
        
    total_score = sum(txn.get("_confidence", {}).get("score", 0.0) for txn in transactions)
    avg_score = total_score / len(transactions)
    
    statement_warnings = []
    failed_recon = sum(1 for txn in transactions if not txn.get("_confidence", {}).get("signals", {}).get("balance_reconciled"))
    
    if failed_recon > 0:
        statement_warnings.append(f"{failed_recon} out of {len(transactions)} rows failed reconciliation.")
        
    # Deduct statement level penalties
    if failed_recon > len(transactions) * 0.2:
        avg_score *= 0.8 # 20% penalty if > 20% rows fail recon
        
    return {
        "statement_score": round(avg_score, 2),
        "row_scores": [txn.get("_confidence", {}).get("score", 0.0) for txn in transactions],
        "warnings": statement_warnings
    }
