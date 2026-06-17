"""
Verify whether 07/02/22 rows are in separate blocks or merged.
"""
import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.layout.row_detector import detect_rows, detect_transaction_blocks
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
date_zone = zones.get("date_zone", [0, 400])

blocks = detect_transaction_blocks(rows, date_x_bounds=date_zone)

# Find blocks containing 07/02/22
print(f"Total blocks: {len(blocks)}")
for i, block in enumerate(blocks):
    block_text = " | ".join(
        " ".join(t.get("text","") for t in row.get("tokens",[]))
        for row in block
    )
    if "07/02" in block_text:
        print(f"\nBlock {i}:")
        for row in block:
            toks = row.get("tokens",[])
            print(f"  Row y0={row.get('y0',0):.1f}:")
            for t in toks:
                print(f"    x0={t.get('x0',0):.1f}  text={t.get('text','')!r}")
