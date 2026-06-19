import sys
import os
import json
from collections import Counter
sys.path.append(r'c:\Users\adity\Downloads\CA')

from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

scanned_pdf = r'C:\Users\adity\Downloads\CA\validation_lab\backend\temp\JOB_20260618_010028_2AA7_24-25 -2 1 (2)_page-0006.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(scanned_pdf)

transactions, parser_telemetry = parse_with_coordinates(
    page_tokens, 
    pdf_name='24-25 -2 1 (2)_page-0006.pdf', 
    bank='BANK OF INDIA'
)

print(f'Rows detected: {parser_telemetry.get("rows_detected")}')
print(f'Accepted: {len(transactions)}')
reject_log = parser_telemetry.get('reject_log', [])
print(f'Rejected: {len(reject_log)}')

reasons = Counter([r.get('reject_reason') for r in reject_log])
print('Reject Reasons:')
for r, count in reasons.items():
    print(f"{r}: {count}")
