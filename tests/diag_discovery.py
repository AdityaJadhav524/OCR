import sys, os, json
from pathlib import Path
from pprint import pprint

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document
from core.discovery.transaction_discovery import discover_transactions

def main():
    pdf_name = "DocScanner 17-Apr-2026 11-06 AM 1.pdf"
    import glob
    matches = glob.glob(str(ROOT / "validation_lab/backend/temp" / f"*{pdf_name}"))
    if not matches:
        print("PDF not found")
        return
    pdf_path = sorted(matches, key=os.path.getmtime)[-1]
    
    print(f"Routing document: {pdf_path}")
    full_text, pages, tel, page_tokens = route_document(pdf_path)
    
    candidates = discover_transactions(page_tokens)
    print(f"\nFound {len(candidates)} candidates.")
    
    for i, c in enumerate(candidates):
        d = c.to_dict()
        print(f"\n--- Candidate {i+1} (Page {d['page']}) ---")
        print(f"Scores  : Txn={d['transaction_score']}, Hdr={d['header_score']}, Acct={d['account_info_score']}")
        print(f"Signals : {d['signals']}")
        print(f"Amounts : {d['amount_candidates']}")
        print(f"Text    : {d['raw_text']}")

if __name__ == "__main__":
    main()
