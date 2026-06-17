import os
import json
import sys
import glob

# Ensure core root is on sys.path
_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
if _workspace not in sys.path:
    sys.path.insert(0, _workspace)

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.parsers.deterministic_parser import parse_deterministic_transactions
from core.validators.financial_audit import run_financial_audit
from benchmark_db import log_run

def compare_results(extracted, expected):
    metrics = {
        "date_errors": 0,
        "amount_errors": 0,
        "balance_errors": 0,
        "narration_errors": 0,
        "missing_rows": 0,
        "extra_rows": 0,
        "date_accuracy": 0.0,
        "narration_accuracy": 0.0,
        "debit_accuracy": 0.0,
        "credit_accuracy": 0.0,
        "balance_accuracy": 0.0
    }
    
    exp_txns = expected.get("transactions", [])
    
    metrics["extra_rows"] = max(0, len(extracted) - len(exp_txns))
    metrics["missing_rows"] = max(0, len(exp_txns) - len(extracted))
    
    comp_len = min(len(extracted), len(exp_txns))
    if comp_len == 0:
        return metrics
        
    for i in range(comp_len):
        act = extracted[i]
        exp = exp_txns[i]
        
        if act.get("date") != exp.get("date"):
            metrics["date_errors"] += 1
        if act.get("debit") != exp.get("debit") or act.get("credit") != exp.get("credit"):
            metrics["amount_errors"] += 1
        if act.get("balance") != exp.get("balance"):
            metrics["balance_errors"] += 1
            
        # Simplified narration check: exact match. In real world, fuzzy match.
        if act.get("narration", "").strip() != exp.get("narration", "").strip():
            metrics["narration_errors"] += 1

    total = max(1, len(exp_txns))
    
    # Calculate % accuracy
    metrics["date_accuracy"] = 100.0 * (total - metrics["date_errors"]) / total
    metrics["debit_accuracy"] = 100.0 * (total - metrics["amount_errors"]) / total
    metrics["credit_accuracy"] = metrics["debit_accuracy"]
    metrics["balance_accuracy"] = 100.0 * (total - metrics["balance_errors"]) / total
    metrics["narration_accuracy"] = 100.0 * (total - metrics["narration_errors"]) / total
    
    return metrics

def run_benchmarks():
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find all expected json files
    expected_files = glob.glob(os.path.join(tests_dir, "*", "*.expected.json"))
    
    if not expected_files:
        print("No expected.json files found.")
        sys.exit(1)
        
    for exp_path in expected_files:
        pdf_path = exp_path.replace(".expected.json", ".pdf")
        if not os.path.exists(pdf_path):
            print(f"Skipping {os.path.basename(exp_path)} - matching PDF not found.")
            continue
            
        bank_name = os.path.basename(os.path.dirname(pdf_path))
        print(f"\n--- Benchmarking {os.path.basename(pdf_path)} [{bank_name}] ---")
        
        with open(exp_path, "r") as f:
            expected = json.load(f)
            
        full_text, pages, merge_stats, page_tokens = route_document(pdf_path)
        
        # --- V2 (Primary) ---
        v2_txns, _ = parse_with_coordinates(page_tokens)
        v2_audit = run_financial_audit(v2_txns, expected_transaction_count=expected["transaction_count"])
        v2_metrics = compare_results(v2_txns, expected)
        v2_metrics["audit_score"] = 100.0 if v2_audit.get("audit_passed") else 0.0
        v2_passed = v2_audit.get("audit_passed", False)
        v2_metrics["contaminated_rows"] = sum(1 for t in v2_txns if t.get("contamination_detected"))
        v2_metrics["rejected_rows"] = len(tel.get("reject_log", [])) if "tel" in locals() else 0
        
        fallback_used = False
        final_txns = v2_txns
        final_metrics = v2_metrics
        final_audit = v2_audit
        best_parser = "V2"

        if not v2_passed or len(v2_txns) == 0:
            print("  V2 failed audit or returned 0 rows. Triggering V1 Fallback...")
            fallback_used = True
            
            # --- V1 (Fallback) ---
            v1_txns, _ = parse_deterministic_transactions(full_text)
            v1_audit = run_financial_audit(v1_txns, expected_transaction_count=expected["transaction_count"])
            v1_metrics = compare_results(v1_txns, expected)
            v1_metrics["audit_score"] = 100.0 if v1_audit.get("audit_passed") else 0.0
            v1_metrics["contaminated_rows"] = sum(1 for t in v1_txns if t.get("contamination_detected"))
            v1_metrics["rejected_rows"] = len(tel.get("reject_log", [])) if "tel" in locals() else 0
            
            # Choose the best result
            v1_passed = v1_audit.get("audit_passed", False)
            if v1_passed and not v2_passed:
                final_txns = v1_txns
                final_metrics = v1_metrics
                final_audit = v1_audit
                best_parser = "V1"
            elif len(v1_txns) > len(v2_txns) and not v2_passed:
                final_txns = v1_txns
                final_metrics = v1_metrics
                final_audit = v1_audit
                best_parser = "V1"

        # Logging
        log_run(pdf_path, bank_name, best_parser, len(final_txns), final_metrics, merge_stats, fallback_used)
        
        print(f"Final Score ({best_parser}): {final_metrics['date_accuracy']:.1f}% Date | {final_metrics['debit_accuracy']:.1f}% Amount | {final_metrics['balance_accuracy']:.1f}% Bal | Audit Passed: {final_audit.get('audit_passed')}")
        print(f"Metrics: Txns={len(final_txns)} | Rejects={final_metrics.get('rejected_rows', 0)} | Contaminated={final_metrics.get('contaminated_rows', 0)}")
        print(f"Fallback Used: {fallback_used}")
        print(f"Failure Buckets: { {k:v for k,v in final_metrics.items() if 'errors' in k or 'rows' in k} }")

if __name__ == "__main__":
    run_benchmarks()
