import sys
import json
import logging
sys.path.append('C:/Users/adity/Downloads/CA')

from core.extractors.pdf_extractor import extract_pdf_text
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

logging.basicConfig(level=logging.WARNING)
logging.getLogger("core").setLevel(logging.INFO)

pdf_path = r'C:\Users\adity\Downloads\CA\DetailedStatement24-25 2.pdf'
full_text, merge_stats, page_tokens = extract_pdf_text(pdf_path)

txns, tel = parse_with_coordinates(page_tokens, pdf_name='icici.pdf', statement_id='123', job_id='456', bank='ICICI BANK', pdf_type='DIGITAL')

print(f"Extracted: {len(txns)}")
print(f"Rejected: {tel.get('rejected_rows', 0)}")
if tel.get('reject_log'):
    from collections import Counter
    counts = Counter([r.get("reject_reason", "unknown") for r in tel['reject_log']])
    print(counts)
