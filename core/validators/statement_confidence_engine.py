import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.validators.statement_confidence_engine")

from core.validators.transaction_order_validator import validate_and_sort_transactions
from core.validators.running_balance_audit import run_running_balance_audit
from core.validators.financial_reconciliation import run_financial_reconciliation
from core.validators.ledger_direction_validator import run_ledger_direction_validator

from core.extractors.candidate_generator import generate_balance_candidates
from core.validators.balance_sanity_validator import run_balance_sanity_validator

def _detect_page_order_anomaly(transactions: List[Dict[str, Any]]) -> bool:
    """
    Detects if there are date reversals at page boundaries, indicating folded or scrambled physical order.
    """
    from dateutil.parser import parse as parse_date
    
    page_date_reversals = 0
    last_date = None
    prev_page = None
    
    for txn in transactions:
        curr_page = txn.get("_source_page", txn.get("page", 0))
        d_str = txn.get("date")
        if not d_str:
            continue
            
        try:
            curr_date = parse_date(d_str, dayfirst=True)
        except:
            continue
            
        if prev_page is not None and curr_page != prev_page:
            if last_date and curr_date < last_date:
                page_date_reversals += 1
                
        last_date = curr_date
        prev_page = curr_page
        
    return page_date_reversals > 0

def generate_statement_confidence(transactions: List[Dict[str, Any]], expected_transaction_count: int = None) -> Dict[str, Any]:
    """
    Orchestrates Sprints 0-3 to generate a final confidence score.
    Outputs:
    {
        "confidence": 96,
        "status": "AUTO_APPROVE",
        "continuity": 98,
        ...
    }
    """
    if not transactions:
        return {
            "confidence": 0,
            "status": "MANUAL_CHECK",
            "continuity": 0,
            "reconciliation": 0,
            "direction": 0,
            "transaction_completeness": 0,
            "transactions": []
        }
        
    # Layer 3: Candidate Generator
    transactions = generate_balance_candidates(transactions)
    
    # Layer 4: Balance Sanity Validator
    transactions = run_balance_sanity_validator(transactions)
    
    # Sprint 0: Order
    sorted_txns, order_meta = validate_and_sort_transactions(transactions)
    
    # Pre-audit check: Run a quick continuity check to see if we need Page Sequence Repair
    rb_audit = run_running_balance_audit(sorted_txns)
    continuity = rb_audit["continuity_percentage"]
    
    # Safegaurd for Page Sequence Repair
    page_set = set(t.get("_source_page", t.get("page", 0)) for t in sorted_txns)
    page_count = len(page_set)
    
    page_repaired = False
    if page_count > 3 and continuity < 90 and _detect_page_order_anomaly(sorted_txns):
        logger.info(f"Triggering Page Sequence Repair (continuity {continuity}% across {page_count} pages with anomalies)")
        from core.ordering.page_sequence_repair import run_page_sequence_repair
        sorted_txns = run_page_sequence_repair(sorted_txns)
        # Re-sort and re-audit after repair
        sorted_txns, order_meta = validate_and_sort_transactions(sorted_txns)
        rb_audit = run_running_balance_audit(sorted_txns)
        continuity = rb_audit["continuity_percentage"]
        page_repaired = True
    
    # Sprint 1: Direction (and heals the transactions in-place safely)
    direction_audit = run_ledger_direction_validator(sorted_txns)
    direction = direction_audit["direction_score"]
    healed_transactions = direction_audit["transactions"]
    
    # Sprint 2: Continuity (Re-calc with healed transactions)
    rb_audit = run_running_balance_audit(healed_transactions)
    continuity = rb_audit["continuity_percentage"]
    
    # Sprint 3: Reconciliation
    recon_audit = run_financial_reconciliation(sorted_txns)
    reconciliation = recon_audit["reconciliation_percentage"]
    
    # Completeness
    completeness = 100.0
    if expected_transaction_count:
        if len(transactions) >= expected_transaction_count:
            completeness = 100.0
        else:
            completeness = (len(transactions) / expected_transaction_count) * 100.0
    
    # Sprint 4: The Engine Math
    # Continuity (40%), Reconciliation (35%), Direction (15%), Completeness (10%)
    confidence_float = (
        (continuity * 0.40) +
        (reconciliation * 0.35) +
        (direction * 0.15) +
        (completeness * 0.10)
    )
    
    confidence = int(round(confidence_float))
    
    if confidence > 95:
        status = "AUTO_APPROVE"
    elif confidence >= 80:
        status = "REVIEW"
    else:
        status = "MANUAL_CHECK"
        
    # Calculate OCR suspected corruptions
    suspected_ocr_corruption = 0
    for t in sorted_txns:
        cands = t.get("balance_candidates", [])
        if any("watermark_pattern_suspect" in ev for c in cands for ev in c.get("evidence", [])):
            suspected_ocr_corruption += 1
        elif t.get("balance") is not None and not cands: # No valid candidates at all
            suspected_ocr_corruption += 1
            
    # Explainability
    explainability = []
    explainability.append(status)
    explainability.append("")
    explainability.append(f"Confidence: {confidence}")
    explainability.append("")
    if status == "AUTO_APPROVE":
        explainability.append("Reason:")
        if completeness >= 99.9: explainability.append("✓ 100% transaction completeness")
        if continuity >= 99.0: explainability.append(f"✓ {continuity:.1f}% running balance continuity")
        if reconciliation == 100.0: explainability.append("✓ 100% reconciliation")
        if not page_repaired: explainability.append("✓ No page ordering anomalies")
        if suspected_ocr_corruption == 0: explainability.append("✓ No OCR corruption detected")
    else:
        explainability.append("Primary causes\n")
        
        # Attribute missing confidence points
        total_lost = 100.0 - confidence_float
        if total_lost > 0:
            cont_lost = (100.0 - continuity) * 0.40
            recon_lost = (100.0 - reconciliation) * 0.35
            dir_lost = (100.0 - direction) * 0.15
            comp_lost = (100.0 - completeness) * 0.10
            
            causes = []
            
            # Map continuity to OCR or Missing Balances
            if cont_lost > 0:
                if suspected_ocr_corruption > 0:
                    causes.append(("OCR corruption", cont_lost))
                else:
                    causes.append(("Missing balances", cont_lost))
                    
            if recon_lost > 0:
                if page_repaired:
                    causes.append(("Page ordering", recon_lost))
                else:
                    causes.append(("Anchor discovery", recon_lost))
                    
            if dir_lost > 0:
                causes.append(("Direction uncertainty", dir_lost))
                
            if comp_lost > 0:
                causes.append(("Missing transactions", comp_lost))
                
            causes.sort(key=lambda x: x[1], reverse=True)
            
            for cause, lost in causes:
                percentage = int(round((lost / total_lost) * 100))
                if percentage > 0:
                    explainability.append(f"{percentage}%\n{cause}\n")
                    
    explainability_report = "\n".join(explainability).strip()
        
    return {
        "confidence": confidence,
        "status": status,
        "continuity": continuity,
        "reconciliation": reconciliation,
        "direction": direction,
        "transaction_completeness": completeness,
        "explainability_report": explainability_report,
        "transactions": healed_transactions,
        "details": {
            "order": order_meta,
            "ledger_breaks": rb_audit["ledger_breaks"],
            "reconciliation_difference": recon_audit["difference"],
            "corrected_directions": direction_audit["corrected_amounts"],
            "suspected_ocr_corruption": suspected_ocr_corruption
        }
    }
