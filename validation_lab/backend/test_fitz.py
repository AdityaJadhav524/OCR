import sys
import os
import logging
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, _WORKSPACE_ROOT)
sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "core"))

from core.adapters.ocr_subprocess import extract_via_subprocess

pdf_path = r'C:\Users\adity\Downloads\CA\validation_lab\backend\temp\JOB_20260619_174708_E5E8_SavingAccountStatement_20260421090553 1 (2)_page-0001.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

print("TOKENS:", len(page_tokens))
print("FULL_TEXT:", full_text[:500])

from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.layout.row_detector import detect_rows
from core.layout.column_detector import detect_columns

rows = detect_rows(page_tokens)
zones, detected_headers = detect_columns(rows, identity={"institution_name": "UNKNOWN"})
print("ZONES DETECTED:", zones)
print("DETECTED HEADERS:", [t['text'] for t in detected_headers])

txns, tel = parse_with_coordinates(page_tokens, pdf_name='saving.pdf', statement_id='123', job_id='456', bank='UNKNOWN', pdf_type='SCANNED')

print(f"V2 Extracted: {len(txns)}")
for idx, t in enumerate(txns):
    print(f"[{idx}] Date: {t.get('date')} | Dr: {t.get('debit')} | Cr: {t.get('credit')} | Bal: {t.get('balance')} | {t.get('narration')}")

txns, tel = parse_with_coordinates(page_tokens, pdf_name='saving.pdf', statement_id='123', job_id='456', bank='UNKNOWN', pdf_type='DIGITAL')

print(f"Extracted: {len(txns)}")
for idx, t in enumerate(txns):
    print(f"[{idx}] Date: {t.get('date')} | Dr: {t.get('debit')} | Cr: {t.get('credit')} | Bal: {t.get('balance')} | {t.get('narration')}")
