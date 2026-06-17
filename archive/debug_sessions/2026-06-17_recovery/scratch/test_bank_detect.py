import sys
import json
import os

from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm

pdf_path = "validation_lab/backend/temp/YESBANK_page-0001.pdf"
print(f"Testing {pdf_path}")

full_text, pages, merge_stats, page_tokens = route_document(pdf_path)

print(f"Extracted {len(pages)} pages")
if pages:
    print("Page 0 length:", len(pages[0]))
    print("Page 0 text preview:", pages[0][:200].replace('\n', ' '))

identity_json = classify_document_llm(pages)
print(json.dumps(identity_json, indent=2))
