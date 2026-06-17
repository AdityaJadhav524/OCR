import os
import sys
import glob
import json

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import run_financial_audit
from core.detection.bank_detector import classify_document_llm
from core.detection.header_suppression import suppress_headers_and_footers
from core.parsers.credit_card_parser import parse_credit_card_transactions

def evaluate():
    temp_dir = os.path.join(_root, "validation_lab", "backend", "temp")
    
    # Get all PDFs for the latest JOB
    pdf_files = glob.glob(os.path.join(temp_dir, "JOB_20260617_144436_EF6E_*.pdf"))
    
    # Filter to 3 PDFs for quick check
    target_pdfs = [
        "JOB_20260617_144436_EF6E_AccountStatement_02022026_233637 1_pages-to-jpg-0001.pdf",
        "JOB_20260617_144436_EF6E_CC_STMT_117048135_345073_1607202515082025 1 (1) 2_page-0001.pdf",
        "JOB_20260617_144436_EF6E_axis.pdf"
    ]
    pdf_files = [f for f in pdf_files if os.path.basename(f) in target_pdfs]
    
    results = {}
    
    for pdf_path in pdf_files:
        pdf_name = os.path.basename(pdf_path).replace("JOB_20260617_144436_EF6E_", "")
        print(f"Testing {pdf_name}...")
        try:
            full_text, pages, merge_stats, page_tokens = route_document(pdf_path)
            
            # Run Bank Detection
            identity = classify_document_llm(pages)
            bank_name = identity.get("institution_name", "Unknown")
            doc_family = identity.get("document_family", "BANK_STATEMENT")
            
            # Header suppression
            page_tokens = suppress_headers_and_footers(page_tokens)
            
            # Routing
            if doc_family == "CREDIT_CARD":
                v2_txns, v2_tel = parse_credit_card_transactions(page_tokens)
            else:
                # Using V2 parser
                v2_txns, v2_tel = parse_with_coordinates(page_tokens, bank=bank_name, identity=identity)
                
            v2_audit = run_financial_audit(v2_txns)
            
            results[pdf_name] = {
                "extracted_rows": len(v2_txns),
                "audit_passed": v2_audit.get("audit_passed", False),
                "impossible_jumps": v2_audit.get("impossible_jumps", 0),
                "running_balance_issues": v2_audit.get("running_balance_issues", 0),
                "negative_amounts": v2_audit.get("negative_amounts", 0),
                "warnings": v2_audit.get("warnings", []),
                "bank_detected": bank_name
            }
        except Exception as e:
            print(f"Error on {pdf_name}: {e}")
            results[pdf_name] = {"error": str(e)}
            
    output_file = os.path.join(_root, "upload_test_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"Done. Wrote results to {output_file}")

if __name__ == "__main__":
    evaluate()
