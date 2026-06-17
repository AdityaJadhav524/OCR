import sys
import json
import logging
sys.path.append('Z:\\CA')
from core.layout.row_detector import detect_rows
from ocr_core.extract import OCRService

logging.basicConfig(level=logging.WARNING)

ocr = OCRService(method='paddle')
res = ocr.extract(r'Z:\CA\investigations\DOCLING\HDFC\page12_test.pdf')
tokens = res[1] # tokens for page 12
rows = detect_rows(tokens)

for i, r in enumerate(rows):
    text = ' '.join(t['text'] for t in r['tokens'])
    if 'POCKIT' in text or 'HDFC BANK LIMITED' in text or 'Closing balance' in text or 'Registered' in text:
        prev_r = rows[i-1] if i > 0 else None
        gap = r['y0'] - prev_r['y1'] if prev_r else 0
        print(f"Row {i}: y0={r['y0']:.1f}, y1={r['y1']:.1f}, gap_to_prev={gap:.1f} | {text}")
