import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.parsers.credit_card_parser import parse_credit_card_transactions
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns

def main():
    temp_dir = os.path.join("validation_lab", "backend", "temp")
    pdf_name = "JOB_20260614_221721_E385_CC_STMT_117048135_345073_1607202515082025 1 (1) 2_page-0001.pdf"
    pdf_path = os.path.join(temp_dir, pdf_name)
    
    print(f"Tracing CC Parsing for {pdf_name}")
    
    # 1. document_router
    full_text, pages, merge_stats, page_tokens = route_document(pdf_path)
    print(f"Tokens extracted: {len(page_tokens)}")
    
    # 2. bank_detector
    # identity = classify_document_llm(pages)
    # print(f"Detected Bank: {identity.get('institution_name')} ({identity.get('document_family')})")
    
    # Let's peek into credit_card_parser internals
    rows = detect_rows(page_tokens)
    print(f"Rows detected: {len(rows)}")
    
    zones, _ = detect_columns(rows)
    print(f"Zones detected: {zones.keys()}")
    date_zone = zones.get("date_zone")
    print(f"Date Zone: {date_zone}")
    
    blocks = detect_transaction_blocks(rows, date_x_bounds=date_zone)
    print(f"Blocks detected: {len(blocks)}")
    
    # Preview first 3 blocks
    for i, b in enumerate(blocks[:3]):
        text = " | ".join([" ".join(t.get('text', '') for t in r.get('tokens', [])) for r in b])
        print(f"Block {i}: {text[:100]}...")
    
    # 3. credit_card_parser
    v2_txns, v2_tel = parse_credit_card_transactions(page_tokens)
    print(f"Transactions accepted: {len(v2_txns)}")
    
    print("Reject Log snippet:")
    for r in v2_tel.get('reject_log', [])[:10]:
        print(f"  - {r.get('reason')}: {r.get('row_text', '')[:60]}")

if __name__ == "__main__":
    main()
