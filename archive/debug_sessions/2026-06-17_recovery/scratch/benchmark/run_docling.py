import sys
import json
import time

sys.path.insert(0, r"Z:\CA")
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import run_financial_audit
from scratch.benchmark.ground_truth import load_ground_truth
from scratch.benchmark.matcher import match_transactions
from scratch.benchmark.metrics import compute_metrics

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    pass # run_docling will be executed in the docling env where this exists

def convert_docling_to_tokens(pdf_path):
    converter = DocumentConverter()
    print(f"Running Docling OCR on {pdf_path}...")
    result = converter.convert(pdf_path)
    doc = result.document
    
    tokens = []
    # Docling pages are 1-indexed in doc.pages dictionary
    for page_no, page in doc.pages.items():
        # Usually page.cells contains the OCR words
        if hasattr(page, 'cells'):
            for cell in page.cells:
                if hasattr(cell, 'text') and hasattr(cell, 'bbox'):
                    tokens.append({
                        "x0": cell.bbox.l,
                        "y0": cell.bbox.t,
                        "x1": cell.bbox.r,
                        "y1": cell.bbox.b,
                        "text": cell.text,
                        "page": page_no
                    })
    return tokens

PDF_FILES = {
    "YES": r"Z:\CA\validation_lab\backend\temp\JOB_20260614_215535_7B9C_YESBANK.pdf",
    "SBI": r"Z:\CA\validation_lab\backend\temp\JOB_20260615_102048_91EA_DocScanner 17-Apr-2026 11-07 AM 1.pdf", # Using one of the scanned ones as proxy or just skipping SBI Docling if we don't have the exact SBI pdf name
}

def run_phase2():
    results = {}
    
    for bank in ["YES"]:
        gt = load_ground_truth(bank)
        pdf_path = PDF_FILES.get(bank)
        if not pdf_path: continue
        
        start_time = time.time()
        
        # 1. OCR -> tokens
        tokens = convert_docling_to_tokens(pdf_path)
        
        # If docling didn't extract any cells, fail early
        if not tokens:
            print(f"Docling produced 0 tokens for {bank}. It may not expose page.cells.")
            return
            
        print(f"Docling extracted {len(tokens)} tokens for {bank}")
            
        # Normalize tokens (docling uses top as 0)
        # Wait, docling top is 0, bottom is larger. Paddle uses top=0, bottom is larger.
        # So we just pass them as is.
        normalized = tokens
            
        # 2. V2 Parser
        extracted, telemetry = parse_with_coordinates(normalized)
            
        runtime = round(time.time() - start_time, 2)
        
        # 3. Audit
        audit = run_financial_audit(extracted, telemetry=telemetry)
        
        # 4. Metrics
        TP, FP, FN = match_transactions(extracted, gt)
        metrics = compute_metrics(bank, extracted, gt, TP, FP, FN, audit, runtime)
            
        results[bank] = metrics
        
    with open(r"Z:\CA\scratch\benchmark\benchmark_docling.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("Phase 2 (Docling) completed.")

if __name__ == "__main__":
    run_phase2()
