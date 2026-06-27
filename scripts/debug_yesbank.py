import sys
import os
import json

sys.path.append(r'c:\Users\adity\Downloads\CA')
from ocr.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'C:\Users\adity\Downloads\CA\tests\pdfs\YESBANK.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

transactions, parser_telemetry = parse_with_coordinates(
    page_tokens, 
    pdf_name='YESBANK.pdf', 
    bank='YES BANK',
    pdf_type='scanned'
)

print(f"Accepted: {len(transactions)}")
print(f"Rejected: {len(parser_telemetry.get('reject_log', []))}")

print("\n--- REJECTED ROWS ---")
for r in parser_telemetry.get('reject_log', []):
    print(f"\nReason: {r['reject_reason']}")
    print(f"Row Tokens: {r['row_tokens']}")

