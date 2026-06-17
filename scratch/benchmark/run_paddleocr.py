import sys
import json
import time

sys.path.insert(0, r"Z:\CA")
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import run_financial_audit
from scratch.benchmark.ground_truth import load_ground_truth
from scratch.benchmark.matcher import match_transactions
from scratch.benchmark.metrics import compute_metrics

TOKENS_FILES = {
    "YES": r"Z:\CA\scratch\yes_tokens.json",
    "SBI": r"Z:\CA\scratch\latest_upload_tokens.json",
    "HDFC": r"Z:\CA\investigations\HDFC\raw_output.json" # Special case, HDFC has no raw tokens saved for all 12 pages. We'll load the already parsed txns for HDFC just to evaluate its ledger/runtime
}

def run_phase1():
    results = {}
    
    for bank in ["YES", "SBI", "HDFC"]:
        gt = load_ground_truth(bank)
        
        start_time = time.time()
        
        if bank == "HDFC":
            # For HDFC, we load the baseline raw_output as the 'extracted'
            with open(TOKENS_FILES[bank], "r") as f:
                extracted = json.load(f)
            telemetry = {}
        else:
            with open(TOKENS_FILES[bank], "r", encoding="utf-8") as f:
                tokens = json.load(f)
                
            # Normalize tokens
            normalized = []
            for t in tokens:
                new_t = dict(t)
                if 'y1' in t and 'y2' in t and 'y0' not in t:
                    new_t['y0'] = t['y1']; new_t['y1'] = t['y2']
                    new_t['x0'] = t['x1']; new_t['x1'] = t['x2']
                new_t['page'] = t.get('page_number', t.get('page', 1))
                normalized.append(new_t)
                
            extracted, telemetry = parse_with_coordinates(normalized)
            
        runtime = round(time.time() - start_time, 2)
        
        # Run audit
        audit = run_financial_audit(extracted, telemetry=telemetry)
        
        if bank == "HDFC":
            # Option C: Ledger and OCR quality only
            metrics = {
                "bank": bank,
                "extracted": len(extracted),
                "ledger_pass_pct": round(max(0, len(extracted) - audit.get("running_balance_issues", 0)) / max(1, len(extracted)) * 100, 1),
                "runtime": runtime
            }
        else:
            TP, FP, FN = match_transactions(extracted, gt)
            metrics = compute_metrics(bank, extracted, gt, TP, FP, FN, audit, runtime)
            
        results[bank] = metrics
        
    with open(r"Z:\CA\scratch\benchmark\benchmark_current.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("Phase 1 (PaddleOCR) completed.")

if __name__ == "__main__":
    run_phase1()
