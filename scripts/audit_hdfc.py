import os
from collections import defaultdict
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.detection.header_suppression import suppress_headers_and_footers
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns

pdf_path = r'c:\Users\adity\Downloads\CA\tests\pdfs\HDFC_SAVINGS_SCANNED.pdf'
full_text, image_paths, ocr_tree, pages = extract_via_subprocess(pdf_path, password='1170AKSH')

page_tokens = []
for page in pages:
    p_num = page.get('page', 1)
    for block in page.get('blocks', []):
        for line in block.get('lines', []):
            for word in line.get('words', []):
                word['page'] = p_num
                page_tokens.append(word)

filtered_tokens = suppress_headers_and_footers(page_tokens)
rows = detect_rows(filtered_tokens)
zones, headers = detect_columns(rows)
blocks = detect_transaction_blocks(rows, zones.get('date_zone'))
txns, telemetry = parse_with_coordinates(blocks, zones)

reject_log = telemetry.get('reject_log', [])
reject_reasons = defaultdict(int)
for r in reject_log:
    reject_reasons[r.get('reason', 'UNKNOWN')] += 1

print('--- HDFC HISTOGRAM ---')
print(f'Rows detected: {len(blocks)}')
print(f'Rows accepted: {len(txns)}')
print(f'Rows rejected: {len(reject_log)}')
for reason, count in reject_reasons.items():
    print(f'{reason} = {count}')
