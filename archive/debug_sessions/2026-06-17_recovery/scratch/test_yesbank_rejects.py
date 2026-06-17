import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

flat_tokens = []
if isinstance(page_tokens, dict):
    for p, tokens in page_tokens.items():
        flat_tokens.extend(tokens)
else:
    flat_tokens = page_tokens

txns, tel = parse_with_coordinates(flat_tokens)
rejects = tel.get('reject_log', [])
from collections import Counter
reasons = Counter(r.get('reject_reason') for r in rejects)
print("Reject reasons:", reasons)

print("First few rejected:")
for r in rejects[:5]:
    print(r.get('date'), r.get('debit'), r.get('credit'), r.get('balance'), "->", r.get('reject_reason'))
