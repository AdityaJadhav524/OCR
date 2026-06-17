import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.layout.row_detector import detect_rows

pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)
rows = detect_rows(page_tokens)

for i, row in enumerate(rows[:20]):
    text = ' '.join(t['text'] for t in row.get('tokens', []))
    print(f'Row {i:2d} (Y={row.get("y0",0):.1f}): {text}')
