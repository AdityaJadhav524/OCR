import sys
sys.path.append(r'C:\Users\adity\Downloads\CA')
import logging
import json
from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.layout.column_detector import detect_columns
from core.layout.row_detector import detect_rows

logging.basicConfig(level=logging.DEBUG)

pdf_path = r'C:\Users\adity\Downloads\CA\tests\pdfs\BOI_SAVINGS_DIGITAL.pdf'
password = '11707454011'

print('--- ROUTE DOCUMENT ---')
full_text, pages, telemetry, page_tokens = route_document(pdf_path, password=password)

print('--- DETECT ROWS & COLUMNS ---')
rows = detect_rows(page_tokens)
zones, header_row = detect_columns(rows)

print(f'Detected column zones: {zones}')
print(f'First 20 tokens from header area: {[t.get("text") for t in header_row[:20]]}')

print('--- PARSING ---')
result = parse_with_coordinates(page_tokens, pdf_path, 'BOI')

print('--- RESULTS ---')
print(f'rows_detected_before_validation: {result.get("rows_detected", 0)}')
print(f'rows_after_validation: {len(result.get("accepted_transactions", []))}')
print(f'reject_reason Counter: {result.get("reject_reason_counts", {})}')
