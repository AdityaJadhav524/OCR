import os
import glob
import json
import subprocess
from core.adapters.ocr_subprocess import extract_via_subprocess

# Determine if we are currently BEFORE or AFTER
# We will do this manually by running the script twice.

# The 10 PDFs from the recent job
JOB_PREFIX = "JOB_20260614_233121_48AC"
PDF_DIR = r"Z:\CA\validation_lab\backend\temp"

pdfs = glob.glob(os.path.join(PDF_DIR, f"{JOB_PREFIX}*.pdf"))

def process_pdf(pdf_path):
    from core.parsers.coordinate_parser_v2 import parse_with_coordinates
    from core.validators.ledger_truth import annotate_ledger_truth
    
    # OCR
    full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)
    
    # If header suppression exists (AFTER), run it
    try:
        from core.detection.header_suppression import suppress_headers_and_footers
        page_tokens = suppress_headers_and_footers(page_tokens)
    except ImportError:
        pass
        
    # Extract
    try:
        # Check if signature accepts statement_id
        txns, tel = parse_with_coordinates(page_tokens, pdf_name=os.path.basename(pdf_path), statement_id="123", job_id="456", bank="Bank")
    except TypeError:
        txns, tel = parse_with_coordinates(page_tokens)
        
    # Validation
    final_txns = annotate_ledger_truth(txns)
    
    # Calculate stats
    debit_total = sum((float(t["debit"]) if t.get("debit") else 0.0) for t in final_txns)
    credit_total = sum((float(t["credit"]) if t.get("credit") else 0.0) for t in final_txns)
    rejected = tel.get("rejected_rows", len(tel.get("reject_log", [])))
    
    return {
        "pdf": os.path.basename(pdf_path),
        "count": len(final_txns),
        "debit": debit_total,
        "credit": credit_total,
        "rejected": rejected,
        "txns": final_txns,
        "reject_log": tel.get("reject_log", [])
    }

def main():
    import sys
    import concurrent.futures
    mode = sys.argv[1] if len(sys.argv) > 1 else "AFTER"
    
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_pdf = {executor.submit(process_pdf, pdf): pdf for pdf in pdfs}
        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf = future_to_pdf[future]
            try:
                res = future.result()
                results[os.path.basename(pdf)] = res
                print(f"Finished {os.path.basename(pdf)}")
            except Exception as e:
                print(f"Failed {pdf}: {e}")
            
    with open(rf"Z:\CA\scratch\regression_{mode}.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
