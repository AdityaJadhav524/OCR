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
            
    # Explainability Structured API
    explainability = {
        "summary": "",
        "strengths": [],
        "issues": [],
        "root_causes": [],
        "evidence": {
            "continuity_breaks": rb_audit.get("ledger_breaks", 0),
            "reconciliation_difference": recon_audit.get("difference", 0.0),
            "direction_corrections": direction_audit.get("corrected_amounts", 0),
            "missing_balances": sum(1 for t in sorted_txns if t.get("balance") is None),
            "page_reorders": 1 if page_repaired else 0,
            "suspected_ocr_corruption": suspected_ocr_corruption
        },
        "validators": {
            "continuity": {
                "score": continuity,
                "breaks": rb_audit.get("ledger_breaks", 0)
            },
            "reconciliation": {
                "score": reconciliation,
                "difference": recon_audit.get("difference", 0.0)
            },
            "direction": {
                "score": direction,
                "corrected": direction_audit.get("corrected_amounts", 0)
            },
            "completeness": {
                "score": completeness,
                "missing": expected_transaction_count - len(transactions) if expected_transaction_count and len(transactions) < expected_transaction_count else 0
            }
        }
    }
    
    # Analyze Strengths
    if continuity >= 99.0:
        explainability["strengths"].append(f"Running balance continuity {continuity:.1f}%")
    if reconciliation >= 99.0:
        explainability["strengths"].append(f"Statement reconciliation {reconciliation:.1f}%")
    if completeness >= 99.9:
        explainability["strengths"].append("100% transaction completeness")
    if recon_audit.get("reconciliation_percentage", 0) > 0 and reconciliation >= 99.0:
        explainability["strengths"].append("Opening/Closing balance anchors recovered")
        explainability["root_causes"].append("ANCHOR_RECOVERED")
    if direction_audit.get("corrected_amounts", 0) > 0:
        explainability["strengths"].append(f"Debit/Credit directions healed ({direction_audit['corrected_amounts']} rows)")
        explainability["root_causes"].append("DIRECTION_HEALED")
    if page_repaired:
        explainability["strengths"].append("Page ordering recovered automatically")
        
    # Analyze Issues and Root Causes
    if suspected_ocr_corruption > 0:
        explainability["issues"].append(f"OCR corrupted {suspected_ocr_corruption} fields")
        explainability["root_causes"].append("OCR_CORRUPTION")
        
    if continuity < 99.0:
        breaks = rb_audit.get("ledger_breaks", 0)
        explainability["issues"].append(f"{breaks} continuity breaks remain")
        if "OCR_CORRUPTION" not in explainability["root_causes"]:
            explainability["root_causes"].append("BALANCE_CORRUPTION")
            
    if reconciliation < 99.0:
        explainability["issues"].append("Reconciliation failed (anchors mismatch)")
        if page_repaired:
            explainability["root_causes"].append("PAGE_ORDERING")
            
    if completeness < 99.0:
        explainability["issues"].append(f"Low transaction completeness ({completeness:.1f}%)")
        explainability["root_causes"].append("LOW_COMPLETENESS")
        
    if direction < 99.0:
        explainability["issues"].append("Direction errors could not be healed")
        explainability["root_causes"].append("DIRECTION_ERROR")
        
    # Summary
    if status == "AUTO_APPROVE":
        explainability["summary"] = "The statement is mathematically reliable and safe for automated processing."
    elif status == "REVIEW":
        explainability["summary"] = "The statement is mathematically consistent but contains OCR or ordering anomalies. Safe for accountant review."
    else:
        explainability["summary"] = "The statement failed multiple mathematical audits. Requires strict manual verification."
        
    # Human-readable report
    report_lines = []
    report_lines.append(f"Confidence: {confidence} ({status})")
    report_lines.append("")
    report_lines.append("Summary")
    report_lines.append(explainability["summary"])
    report_lines.append("")
    if explainability["strengths"]:
        report_lines.append("Strengths")
        for s in explainability["strengths"]:
            report_lines.append(f"✓ {s}")
        report_lines.append("")
    if explainability["issues"]:
        report_lines.append("Issues")
        for i in explainability["issues"]:
            report_lines.append(f"• {i}")
        report_lines.append("")
        
    explainability["human_readable_report"] = "\n".join(report_lines).strip()
        
    # Deduplicate root causes
    explainability["root_causes"] = list(set(explainability["root_causes"]))
        
    return {
        "confidence": confidence,
        "status": status,
        "explainability": explainability,
        "transactions": healed_transactions
    }
