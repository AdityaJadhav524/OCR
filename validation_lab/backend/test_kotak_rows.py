import sys
sys.path.append('C:/Users/adity/Downloads/CA')

from core.extractors.pdf_extractor import extract_pdf_text
from core.layout.row_detector import detect_rows
import re

pdf_path = r'C:\Users\adity\Downloads\CA\AccountStatement_01-Feb-2026_20-Feb-2026 5.pdf'
full_text, merge_stats, page_tokens = extract_pdf_text(pdf_path)
rows = detect_rows(page_tokens)

for i, r in enumerate(rows[20:40]):
    row_text = ' '.join(t['text'] for t in r.get('tokens', []))
    print(f"Row {i}: {row_text}")
