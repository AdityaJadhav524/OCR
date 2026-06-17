import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

# page_tokens is a dict: {1: [tokens...], 2: [tokens...]}
# We need to flatten it
flat_tokens = []
if isinstance(page_tokens, dict):
    for p, tokens in page_tokens.items():
        flat_tokens.extend(tokens)
else:
    flat_tokens = page_tokens

txns, tel = parse_with_coordinates(flat_tokens)
print(f"V2 extracted: {len(txns)} txns")
print(f"V2 rejected: {len(tel.get('reject_log', []))} txns")

debits = sum(t.get('debit') or 0 for t in txns)
credits = sum(t.get('credit') or 0 for t in txns)

if txns:
    print(f"opening = {txns[0].get('balance') - (txns[0].get('credit') or 0) + (txns[0].get('debit') or 0):.2f}")
    print(f"closing = {txns[-1].get('balance'):.2f}")

print(f"debits = {debits:.2f}")
print(f"credits = {credits:.2f}")
print(f"transactions = {len(txns)}")
