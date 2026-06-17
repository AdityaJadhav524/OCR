import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.layout.row_detector import detect_rows

pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)
rows = detect_rows(page_tokens)

for i, row in enumerate(rows):
    text = ' '.join(t['text'] for t in row.get('tokens', []))
    if '11/21' in text or '5000' in text or '309' in text:
        print(f'Row {i:2d} (Y={row.get("y0",0):.1f}): {text}')
        for tok in row.get('tokens', []):
            print(f"  {tok['text']:20s} x0={tok['x0']:.1f} x1={tok['x1']:.1f} y0={tok['y0']:.1f} y1={tok['y1']:.1f}")
