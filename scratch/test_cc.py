import os
import sys

sys.path.insert(0, os.path.abspath('core'))
from core.extractors.document_router import route_document
from core.parsers.credit_card_parser import parse_credit_card_transactions

pdf_path = r"c:\Users\adity\Downloads\CA\validation_lab\backend\temp\JOB_20260617_144436_EF6E_CC_STMT_117048135_345073_1607202515082025 1 (1) 2_page-0001.pdf"

full_text, pages, merge_stats, page_tokens = route_document(pdf_path)

txns, tel = parse_credit_card_transactions(page_tokens)

print(f"Extracted {len(txns)} transactions")
for r in tel.get("reject_log", []):
    print(r)
