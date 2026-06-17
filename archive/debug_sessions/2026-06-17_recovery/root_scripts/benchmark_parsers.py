import sys
import logging
import json
import argparse
from typing import List, Dict, Any

# Ensure core root is on sys.path
import os
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("benchmark")

from core.extractors.document_router import route_document
from core.parsers.deterministic_parser import parse_deterministic_transactions
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import run_financial_audit

def run_benchmark(pdf_path: str, password: str = None):
    logger.info(f"--- Benchmarking {os.path.basename(pdf_path)} ---")
    
    # 1. Extraction (Phase 1 Coordinate Preservation)
    logger.info("Extracting text and coordinates...")
    full_text, pages, merge_stats, page_tokens = route_document(pdf_path, password=password)
    
    if not page_tokens:
        logger.warning("No token coordinates extracted. V2 parser cannot run.")
        page_tokens = []
        
    # 2. Run V1 (String Deterministic)
    logger.info("Running V1 (String Regex Parser)...")
    v1_txns, v1_telemetry = parse_deterministic_transactions(full_text)
    v1_audit = run_financial_audit(v1_txns)
    
    # 3. Run V2 (Coordinate Parser)
    logger.info("Running V2 (Coordinate Shadow Parser)...")
    v2_txns, v2_telemetry = parse_with_coordinates(page_tokens)
    v2_audit = run_financial_audit(v2_txns)
    
    # 4. Compare Referee Results
    logger.info("\n=== BENCHMARK RESULTS ===")
    
    def print_result(version, txns, audit):
        passed = audit.get('audit_passed', False)
        jumps = audit.get('impossible_jumps', 0)
        bal_issues = audit.get('running_balance_issues', 0)
        neg_amts = audit.get('negative_amounts', 0)
        open_recon = audit.get('opening_balance_reconciled', False)
        
        logger.info(f"[{version}] Extracted Rows : {len(txns)}")
        logger.info(f"[{version}] Audit Passed   : {passed}")
        logger.info(f"[{version}] Bal Issues     : {bal_issues}")
        logger.info(f"[{version}] Neg Amounts    : {neg_amts}")
        logger.info(f"[{version}] Imposs Jumps   : {jumps}")
        logger.info(f"[{version}] Open Reconciled: {open_recon}")
        logger.info(f"[{version}] Warnings     : {audit.get('warnings', [])}")
        logger.info("-" * 30)

    print_result("V1 String Parser", v1_txns, v1_audit)
    print_result("V2 Coord  Parser", v2_txns, v2_audit)
    
    # V1 vs V2 Winner Selection
    v1_passed = v1_audit.get('audit_passed', False)
    v2_passed = v2_audit.get('audit_passed', False)
    
    if v2_passed and not v1_passed:
        logger.info("🏆 V2 WINS: V2 passed audit while V1 failed.")
    elif v1_passed and not v2_passed:
        logger.info("🏆 V1 WINS: V1 passed audit while V2 failed.")
    else:
        # Both passed or both failed, compare row counts
        v1_rows = len(v1_txns)
        v2_rows = len(v2_txns)
        if v2_rows > v1_rows and v2_passed:
            logger.info("🏆 V2 WINS: V2 extracted more valid rows.")
        elif v1_rows > v2_rows and v1_passed:
            logger.info("🏆 V1 WINS: V1 extracted more valid rows.")
        else:
            logger.info("🤝 TIE: Both parsers performed similarly according to the audit.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Path to PDF to benchmark")
    parser.add_argument("--password", default=None, help="PDF password if any")
    args = parser.parse_args()
    
    run_benchmark(args.pdf, args.password)
