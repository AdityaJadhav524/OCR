import sys
import json
import traceback
sys.path.insert(0, r'z:\CA')
sys.path.insert(0, r'z:\CA\core')

from core.parsers.statement_parser import parse_with_llm

import logging
logging.basicConfig(level=logging.DEBUG)

def main():
    print("Testing extraction on YESBANK PDF...")
    try:
        from core.adapters.ocr_subprocess import _extract_scanned
        print("Extracting scanned PDF...")
        full_text, pages = _extract_scanned(r'z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf')
        
        from core.detection.bank_detector import classify_document_llm
        print("Running Bank Detection...")
        identity = classify_document_llm(pages)
        print("Identity:", json.dumps(identity, indent=2))
        
        print("Running Transaction Extraction...")
        
        raw = parse_with_llm(full_text, identity)
        print("Response received!", len(raw))
        
    except Exception as e:
        print("EXCEPTION OCCURRED:", type(e).__name__)
        traceback.print_exc()

if __name__ == '__main__':
    main()
