import os
import json
import sys
import glob
import csv

# Ensure core root is on sys.path
_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
if _workspace not in sys.path:
    sys.path.insert(0, _workspace)

from core.extractors.document_router import route_document
from core.detection.header_suppression import suppress_headers_and_footers
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
    
    # Find all PDFs in tests directory
    pdf_files = glob.glob(os.path.join(tests_dir, "**", "*.pdf"), recursive=True)
    
    if not pdf_files:
        print("No PDF files found.")
        sys.exit(1)
        
    audit_dir = os.path.join(tests_dir, "audit_reports")
    os.makedirs(audit_dir, exist_ok=True)
    summary_rows = []
        
    for pdf_path in pdf_files:
        exp_path = pdf_path.replace(".pdf", ".expected.json")
        
        bank_name = os.path.basename(os.path.dirname(pdf_path))
        print(f"\n--- Benchmarking {os.path.basename(pdf_path)} [{bank_name}] ---")
        
        expected = None
        if os.path.exists(exp_path):
            with open(exp_path, "r") as f:
                expected = json.load(f)
                
        routing_telemetry = {"engine": "Unknown", "classification": "Unknown", "fallback": False}
        parser_telemetry = {"rows_accepted": 0, "rows_rejected": 0, "abort_reason": "None"}
        page_tokens = []
        pages = []
        final_txns = []
        final_metrics = {}
        final_audit = {}
        best_parser = "None"
        fallback_used = False
            
        try:
            full_text, pages, routing_telemetry, page_tokens = route_document(pdf_path)
            
            # --- Suppression (Mirroring Production) ---
            page_tokens = suppress_headers_and_footers(page_tokens)
            
            # --- V2 (Primary) ---
            v2_txns, v2_telemetry = parse_with_coordinates(page_tokens)
            if expected:
                v2_audit = run_financial_audit(v2_txns, expected_transaction_count=expected.get("transaction_count", len(v2_txns)))
                v2_metrics = compare_results(v2_txns, expected)
                v2_metrics["audit_score"] = 100.0 if v2_audit.get("audit_passed") else 0.0
                v2_passed = v2_audit.get("audit_passed", False)
            else:
                v2_audit = run_financial_audit(v2_txns)
                v2_metrics = {}
                v2_passed = v2_audit.get("audit_passed", False)
                
            v2_metrics["contaminated_rows"] = sum(1 for t in v2_txns if t.get("contamination_detected"))
            v2_metrics["rejected_rows"] = v2_telemetry.get("v2_rejected_rows", 0)
            
            fallback_used = False
            final_txns = v2_txns
            final_metrics = v2_metrics
            final_audit = v2_audit
            best_parser = "V2"
            parser_telemetry = v2_telemetry

            if not v2_passed or len(v2_txns) == 0:
                print("  V2 failed audit or returned 0 rows. Triggering V1 Fallback...")
                fallback_used = True
                
                # --- V1 (Fallback) ---
                v1_txns, v1_telemetry = parse_deterministic_transactions(full_text)
                if expected:
                    v1_audit = run_financial_audit(v1_txns, expected_transaction_count=expected.get("transaction_count", len(v1_txns)))
                    v1_metrics = compare_results(v1_txns, expected)
                    v1_metrics["audit_score"] = 100.0 if v1_audit.get("audit_passed") else 0.0
                else:
                    v1_audit = run_financial_audit(v1_txns)
                    v1_metrics = {}
                    
                v1_metrics["contaminated_rows"] = sum(1 for t in v1_txns if t.get("contamination_detected"))
                v1_metrics["rejected_rows"] = v1_telemetry.get("rejected_rows", 0)
                
                # Choose the best result
                v1_passed = v1_audit.get("audit_passed", False)
                if v1_passed and not v2_passed:
                    final_txns = v1_txns
                    final_metrics = v1_metrics
                    final_audit = v1_audit
                    best_parser = "V1"
                    parser_telemetry = v1_telemetry
                elif len(v1_txns) > len(v2_txns) and not v2_passed:
                    final_txns = v1_txns
                    final_metrics = v1_metrics
                    final_audit = v1_audit
                    best_parser = "V1"
                    parser_telemetry = v1_telemetry
        except Exception as e:
            print(f"  Extraction aborted: {e}")
            parser_telemetry["abort_reason"] = f"Crash: {e}"

        # Output audit.json
        audit_data = {
            "classification": routing_telemetry.get("classification"),
            "classification_reason": routing_telemetry.get("classification_reason"),
            "engine": routing_telemetry.get("engine"),
            "fallback": routing_telemetry.get("fallback", False),
            "pages": len(pages),
            "token_count": len(page_tokens),
            "header_candidates": parser_telemetry.get("header_candidates", []),
            "chosen_header": parser_telemetry.get("chosen_header", None),
            "zones": parser_telemetry.get("zones", {}),
            "rows_detected": parser_telemetry.get("rows_detected", 0),
            "rows_accepted": parser_telemetry.get("rows_accepted", len(final_txns)),
            "rows_rejected": parser_telemetry.get("rows_rejected", 0),
            "reject_reasons": parser_telemetry.get("reject_reasons", {}),
            "abort_reason": parser_telemetry.get("abort_reason", None),
            "healed_rows": parser_telemetry.get("recovered_transactions", 0)
        }

        pdf_name = os.path.basename(pdf_path)
        audit_file = os.path.join(audit_dir, pdf_name.replace(".pdf", "_audit.json"))
        with open(audit_file, "w") as f:
            json.dump(audit_data, f, indent=2)

        summary_rows.append({
            "PDF": pdf_name,
            "Engine": routing_telemetry.get("engine"),
            "Tokens": len(page_tokens),
            "Rows": parser_telemetry.get("rows_accepted", len(final_txns)),
            "Abort": parser_telemetry.get("abort_reason", "None") or "None"
        })

        # Logging
        # log_run(pdf_path, bank_name, best_parser, len(final_txns), final_metrics, routing_telemetry, fallback_used)
        
        if expected:
            print(f"Final Score ({best_parser}): {final_metrics.get('date_accuracy', 0):.1f}% Date | {final_metrics.get('debit_accuracy', 0):.1f}% Amount | {final_metrics.get('balance_accuracy', 0):.1f}% Bal | Audit Passed: {final_audit.get('audit_passed')}")
        else:
            print(f"Final Score ({best_parser}): NO TRUTH DATA | Audit Passed: {final_audit.get('audit_passed')}")
            
        print(f"Metrics: Txns={len(final_txns)} | Rejects={final_metrics.get('rejected_rows', 0)} | Contaminated={final_metrics.get('contaminated_rows', 0)}")
        print(f"Fallback Used: {fallback_used}")
        if expected:
            print(f"Failure Buckets: { {k:v for k,v in final_metrics.items() if 'errors' in k or 'rows' in k} }")

    summary_file = os.path.join(tests_dir, "summary.csv")
    with open(summary_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["PDF", "Engine", "Tokens", "Rows", "Abort"])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\n--- Benchmark Summary written to {summary_file} ---")

if __name__ == "__main__":
    run_benchmarks()
