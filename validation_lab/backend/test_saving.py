import sys
import os
import logging
logging.basicConfig(level=logging.INFO)
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, _WORKSPACE_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "core"))
sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "ocr_core"))

from core.extractors.pdf_extractor import extract_pdf_text
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

import fitz
pdf_path = r'C:\Users\adity\Downloads\CA\validation_lab\backend\temp\JOB_20260619_174708_E5E8_SavingAccountStatement_20260421090553 1 (2)_page-0001.pdf'
doc = fitz.open(pdf_path)
print("FITZ Encrypted:", doc.is_encrypted)
print("FITZ Pages:", len(doc))
for i in range(len(doc)):
    page = doc[i]
    words = page.get_text("words")
    print(f"Page {i} Words:", len(words))

    pdf_bytes = f.read()

ocr_doc = run_pipeline(pdf_bytes, 'saving.pdf', 'job123', 600, None)

page_tokens = []
for p in ocr_doc.pages:
    for word in p.words:
        page_tokens.append({
            "text": word.text,
            "x0": word.x0, "y0": word.y0, "x1": word.x1, "y1": word.y1,
            "page": p.page_number
        })

print("OCR TOKENS:", len(page_tokens))

txns, tel = parse_with_coordinates(page_tokens, pdf_name='saving.pdf', statement_id='123', job_id='456', bank='UNKNOWN', pdf_type='SCANNED')

print(f"Extracted: {len(txns)}")
for idx, t in enumerate(txns):
    print(f"[{idx}] Date: {t.get('date')} | Dr: {t.get('debit')} | Cr: {t.get('credit')} | Bal: {t.get('balance')} | {t.get('narration')}")
