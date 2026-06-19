import sys
import os
sys.path.append(r'c:\Users\adity\Downloads\CA')
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'C:\Users\adity\Downloads\CA\tests\pdfs\YESBANK.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

transactions, parser_telemetry = parse_with_coordinates(
    page_tokens, 
    pdf_name='YESBANK.pdf', 
    bank='YES BANK',
    pdf_type='scanned'
)

for t in transactions:
    b = t.get("balance")
    if b is not None and b > 150000:
        print(f"Date: {t.get('date')} | Deb: {t.get('debit')} | Cred: {t.get('credit')} | Bal: {b}")
