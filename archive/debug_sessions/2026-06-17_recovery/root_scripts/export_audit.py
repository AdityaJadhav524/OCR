import os
import json
import sys
import glob

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.parsers.deterministic_parser import parse_deterministic_transactions
from core.validators.financial_audit import run_financial_audit

def main():
    export_dir = os.path.join(_root, "audit_export")
    os.makedirs(export_dir, exist_ok=True)
    
    tests_dir = os.path.join(_root, "tests")
    expected_files = glob.glob(os.path.join(tests_dir, "*", "*.expected.json"))
    
    benchmark_export = {
        "summary": {},
        "banks": {}
    }
    
    for exp_path in expected_files:
        pdf_path = exp_path.replace(".expected.json", ".pdf")
        if not os.path.exists(pdf_path):
            continue
            
        bank_name = os.path.basename(os.path.dirname(pdf_path))
        pdf_name = os.path.basename(pdf_path)
        
        with open(exp_path, "r") as f:
            expected = json.load(f)
            
        full_text, pages, merge_stats, page_tokens = route_document(pdf_path)
        
        # V2 Parser
        v2_txns, v2_tel = parse_with_coordinates(page_tokens)
        v2_audit = run_financial_audit(v2_txns, expected_transaction_count=expected.get("transaction_count"))
        
        best_parser = "V2"
        final_txns = v2_txns
        final_audit = v2_audit
                
        # Compare to expected
        missing = max(0, len(expected.get("transactions", [])) - len(final_txns))
        extra = max(0, len(final_txns) - len(expected.get("transactions", [])))
        
        bank_data = {
            "pdf_name": pdf_name,
            "expected_count": len(expected.get("transactions", [])),
            "actual_count": len(final_txns),
            "audit_passed": final_audit.get("audit_passed", False),
            "missing_rows": missing,
            "extra_rows": extra,
            "parser_used": best_parser,
            "negative_amounts": final_audit.get("negative_amounts", 0),
            "impossible_jumps": final_audit.get("impossible_jumps", 0),
            "running_balance_issues": final_audit.get("running_balance_issues", 0),
            "warnings": final_audit.get("warnings", [])
        }
        
        benchmark_export["banks"][bank_name] = bank_data
        
        # Dump output JSON for this bank
        output_data = {
            "bank": bank_name,
            "parser_used": best_parser,
            "transactions": final_txns,
            "audit": final_audit,
            "telemetry": v2_tel if best_parser == "V2" else v1_tel
        }
        
        with open(os.path.join(export_dir, f"{bank_name}_output.json"), "w") as f:
            json.dump(output_data, f, indent=2)
            
    with open(os.path.join(export_dir, "benchmark_export.json"), "w") as f:
        json.dump(benchmark_export, f, indent=2)
        
    print(f"Export completed. Check {export_dir}")

if __name__ == "__main__":
    main()
