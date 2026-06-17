import json
from pathlib import Path
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns

pdf_path = r'Z:\CA\validation_lab\documents\scanned\YESBANK.pdf'
if not Path(pdf_path).exists():
    pdf_path = r'Z:\CA\validation_lab\documents\YESBANK.pdf'
if not Path(pdf_path).exists():
    pdfs = list(Path(r'Z:\CA').rglob('*YESBANK*.pdf'))
    if pdfs: pdf_path = str(pdfs[0])

print(f'Using PDF: {pdf_path}')

if Path(pdf_path).exists():
    full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)
    rows = detect_rows(page_tokens)
    zones, detected_headers = detect_columns(rows)
    print('\n--- ZONES ---')
    for k, v in zones.items(): print(f'{k}: {v}')
    
    blocks = detect_transaction_blocks(rows, date_x_bounds=zones.get('date_zone'))
    
    print('\n--- FIRST BLOCK TOKENS ---')
    if blocks:
        for row in blocks[0]:
            print(f'Row Y-bounds: {row.get("y0", 0):.1f} to {row.get("y1", 0):.1f}')
            for tok in row.get('tokens', []):
                text = tok['text']
                x0, x1 = tok['x0'], tok['x1']
                y0, y1 = tok['y0'], tok['y1']
                print(f'{text:20s} x0={x0:.1f} x1={x1:.1f} y0={y0:.1f} y1={y1:.1f}')
    else:
        print('No blocks found')
else:
    print('PDF NOT FOUND')
