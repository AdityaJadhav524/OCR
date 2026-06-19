import os
import sys
import json
import glob
from collections import Counter
from typing import Dict, Any

# Ensure path is set to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests")
PDF_DIR = os.path.join(TEST_DIR, "pdfs")
TRUTH_DIR = os.path.join(TEST_DIR, "ground_truth")

os.makedirs(TRUTH_DIR, exist_ok=True)

# Config for specific tests (e.g., passwords or known bank names)
TEST_CONFIG = {
    "BOI_Digital.pdf": {"password": "11707454011", "bank": "BANK OF INDIA", "pdf_type": "digital"},
    "BOI_Scanned.pdf": {"password": None, "bank": "BANK OF INDIA", "pdf_type": "scanned"},
    "YESBANK.pdf": {"password": None, "bank": "YES BANK", "pdf_type": "scanned"},
    "ICICI_1.pdf": {"password": None, "bank": "ICICI BANK", "pdf_type": "scanned"},
    "ICICI_2.pdf": {"password": None, "bank": "ICICI BANK", "pdf_type": "scanned"},
    "test_normal.pdf": {"password": None, "bank": "UNKNOWN", "pdf_type": "scanned"}
}

def get_truth(filename: str) -> Dict[str, Any]:
    truth_path = os.path.join(TRUTH_DIR, f"{os.path.splitext(filename)[0]}_truth.json")
    if os.path.exists(truth_path):
        with open(truth_path, 'r') as f:
            return json.load(f)
    return {}

def save_truth(filename: str, data: Dict[str, Any]):
    truth_path = os.path.join(TRUTH_DIR, f"{os.path.splitext(filename)[0]}_truth.json")
    with open(truth_path, 'w') as f:
        json.dump(data, f, indent=2)

def run_suite(generate_truth=False):
    pdfs = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    
    print("========================================")
    print("      V2 REGRESSION BENCHMARK SUITE     ")
    print("========================================")
    
    for pdf_path in pdfs:
        filename = os.path.basename(pdf_path)
        print(f"\n--- Testing: {filename} ---")
        
        config = TEST_CONFIG.get(filename, {})
        password = config.get("password")
        bank = config.get("bank", "Unknown")
        pdf_type = config.get("pdf_type", "Unknown")
        
        try:
            print("Running extraction pipeline...")
            full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path, password=password)
            
            transactions, parser_telemetry = parse_with_coordinates(
                page_tokens, 
                pdf_name=filename, 
                bank=bank,
                pdf_type=pdf_type
            )
            
            # Extract metrics
            accepted_rows = len(transactions)
            reject_log = parser_telemetry.get("reject_log", [])
            rejected_rows = len(reject_log)
            
            total_debit = sum(t.get("debit", 0.0) or 0.0 for t in transactions)
            total_credit = sum(t.get("credit", 0.0) or 0.0 for t in transactions)
            
            closing_balance = None
            if transactions:
                # Find last valid balance
                for t in reversed(transactions):
                    if t.get("balance") is not None:
                        closing_balance = t["balance"]
                        break
            
            metrics = {
                "expected_transactions": accepted_rows,
                "expected_debit_total": round(total_debit, 2),
                "expected_credit_total": round(total_credit, 2),
                "closing_balance": round(closing_balance, 2) if closing_balance is not None else None
            }
            
            if generate_truth:
                save_truth(filename, metrics)
                print(f"[GENERATE] Saved ground truth for {filename}")
                continue
                
            truth = get_truth(filename)
            if not truth:
                print(f"[WARNING] No ground truth found for {filename}. Run with --generate to create baseline.")
                continue
                
            # Compare
            passed = True
            for key, expected_val in truth.items():
                actual_val = metrics.get(key)
                if actual_val != expected_val:
                    passed = False
                    print(f"[FAIL] {key}: expected {expected_val}, got {actual_val}")
            
            if passed:
                print(f"[PASS] {filename} matched ground truth perfectly.")
                
            if not passed or "YESBANK" in filename or "BOI" in filename:
                print(f"Accepted: {accepted_rows} | Rejected: {rejected_rows}")
                if rejected_rows > 0:
                    reasons = Counter([r.get("reject_reason") for r in reject_log])
                    print("Reject Reasons:", dict(reasons))
                    
        except Exception as e:
            print(f"[ERROR] Exception testing {filename}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Generate missing ground truth files from current parse")
    args = parser.parse_args()
    
    run_suite(generate_truth=args.generate)
