import sys
import logging
sys.path.append('C:/Users/adity/Downloads/CA')

from core.extractors.pdf_extractor import extract_pdf_text
from core.layout.row_detector import detect_rows

logging.basicConfig(level=logging.WARNING)

pdf_path = r'C:\Users\adity\Downloads\CA\AccountStatement_01-DEC-2025_to_31-DEC-2025 (1).pdf'
full_text, merge_stats, page_tokens = extract_pdf_text(pdf_path)
rows = detect_rows(page_tokens)

for i, r in enumerate(rows[:30]):
    row_text = ' '.join(t['text'] for t in r.get('tokens', []))
    print(f"Row {i}: {row_text}")
