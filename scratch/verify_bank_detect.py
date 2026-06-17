import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm

def main():
    temp_dir = os.path.join("validation_lab", "backend", "temp")
    
    pdfs = [
        "YESBANK_page-0001.pdf",
        "JOB_20260614_221721_E385_axis.pdf",
        "JOB_20260614_221721_E385_CC_STMT_117048135_345073_1607202515082025 1 (1) 2_page-0001.pdf"
    ]
    
    for pdf_name in pdfs:
        pdf_path = os.path.join(temp_dir, pdf_name)
        if not os.path.exists(pdf_path):
            print(f"File not found: {pdf_path}")
            continue
            
        print(f"\n--- Testing: {pdf_name} ---")
        try:
            full_text, pages, merge_stats, page_tokens = route_document(pdf_path)
            identity = classify_document_llm(pages)
            print(f"Detected Bank: {identity.get('institution_name')}")
            print(f"Detected Family: {identity.get('document_family')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
