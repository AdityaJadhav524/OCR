import json
import sys
import os

sys.path.insert(0, os.path.abspath('core'))
from core.extractors.document_router import route_document

pdf_path = r"c:\Users\adity\Downloads\CA\validation_lab\backend\temp\JOB_20260617_144436_EF6E_E_STATEMENT_20260301_20260331_054506_27011738 (3)_page-0001.pdf"

full_text, pages, merge_stats, page_tokens = route_document(pdf_path)

for tok in page_tokens:
    text = tok.get("text", "")
    if "81510" in text or "81" in text:
        print(f"FOUND TOKEN: '{text}'")

