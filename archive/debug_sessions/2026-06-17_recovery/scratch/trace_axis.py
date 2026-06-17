import sys, os
sys.path.append('c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = 'c:/Users/adity/Downloads/CA/validation_lab/backend/temp/JOB_20260617_144436_EF6E_axis.pdf'
full_text, pages, merge_stats, page_tokens = route_document(pdf_path)
identity = classify_document_llm(pages)
v2_txns, v2_tel = parse_with_coordinates(page_tokens, bank=identity.get('institution_name'), identity=identity)

print('--- AXIS TRACE ---')
print(f'Pages: {len(pages)}')
print(f'Tokens: {len(page_tokens)}')
print(f'Merge Stats: {merge_stats}')
print(f'Rows Detected (V2 Telemetry): {v2_tel.get("v2_extracted_rows")}')
print(f'Final Txns: {len(v2_txns)}')
