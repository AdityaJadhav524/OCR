import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

txns, tel = parse_with_coordinates(page_tokens)
print(f"V2 extracted: {len(txns)} txns")
print(f"V2 rejected: {len(tel.get('reject_log', []))} txns")

if txns:
    print("First txn:", txns[0]['date'], txns[0]['debit'], txns[0]['credit'], txns[0]['balance'])
    print("Last txn:", txns[-1]['date'], txns[-1]['debit'], txns[-1]['credit'], txns[-1]['balance'])
