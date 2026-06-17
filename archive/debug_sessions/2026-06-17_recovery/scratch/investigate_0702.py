"""
Deep dive on 07/02/22 - why does it have both_debit_and_credit?
Check what tokens are on that row and what the PDF actually looks like.
"""
import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.layout.row_detector import detect_rows
from core.layout.column_detector import detect_columns

PDF_PATH = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'

full_text, pages, telemetry, page_tokens = extract_via_subprocess(PDF_PATH)
flat = []
if isinstance(page_tokens, dict):
    for _, toks in page_tokens.items():
        flat.extend(toks)
else:
    flat = page_tokens

rows = detect_rows(flat)
zones, headers = detect_columns(rows)

print(f"Zones: {zones}")
print()

# Find the row with date near 07/02/22 and look at its tokens
for row in rows:
    toks = row.get("tokens", [])
    texts = [t.get("text","") for t in toks]
    row_text = " ".join(texts)
    if "07/02" in row_text or "07.02" in row_text:
        print(f"Row text: {row_text}")
        print("Tokens:")
        for t in toks:
            print(f"  x0={t.get('x0',0):.1f}  x1={t.get('x1',0):.1f}  text={t.get('text','')!r}")
        print()
