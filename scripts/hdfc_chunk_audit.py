import sys
import os
import json
import glob
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from dateutil.parser import parse as parse_date

CORPUS_DIR  = ROOT / "tests" / "truth_corpus"
TEMP_DIR    = ROOT / "validation_lab" / "backend" / "temp"

def find_latest_temp_file(corpus_file: str):
    pattern = str(TEMP_DIR / f"*{corpus_file}")
    matches = glob.glob(pattern)
    if not matches:
        exact = TEMP_DIR / corpus_file
        if exact.exists(): return exact
        return None
    return Path(sorted(matches, key=os.path.getmtime)[-1])

def run_hdfc_chunk_audit():
    pdf_name = "HDFC_SAVINGS_SCANNED.pdf"
    pdf_path = find_latest_temp_file(pdf_name)
    if not pdf_path:
        print(f"Error: {pdf_name} not found.")
        return
        
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, _ = parse_with_coordinates(
        page_tokens,
        pdf_name=pdf_name,
        statement_id="audit",
        job_id="audit",
        bank="HDFC BANK",
        pdf_type="SCANNED"
    )
    
    # Group by page
    from collections import defaultdict
    pages_dict = defaultdict(list)
    
    for txn in txns:
        # Some parsers put page in _source_page, some in page
        page_num = txn.get("_source_page", txn.get("page", 0))
        pages_dict[page_num].append(txn)
        
    results = []
    
    for page_num in sorted(pages_dict.keys()):
        page_txns = pages_dict[page_num]
        
        dates = []
        for t in page_txns:
            date_str = t.get("date")
            if date_str:
                try:
                    d = parse_date(date_str, dayfirst=True)
                    dates.append(d)
                except Exception:
                    pass
                
        if dates:
            date_min = min(dates).strftime("%d/%m/%y")
            date_max = max(dates).strftime("%d/%m/%y")
        else:
            date_min = None
            date_max = None
            
        # Balances
        balance_start = page_txns[0].get("balance")
        balance_end = page_txns[-1].get("balance")
        
        results.append({
            "page": page_num,
            "rows": len(page_txns),
            "date_min": date_min,
            "date_max": date_max,
            "balance_start": balance_start,
            "balance_end": balance_end
        })
        
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_hdfc_chunk_audit()
