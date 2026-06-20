import sys, os, logging
logging.basicConfig(level=logging.INFO)
sys.path.insert(0, 'c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'c:\Users\adity\Downloads\CA\validation_lab\backend\temp\DocScanner 17-Apr-2026 11-06 AM 1.pdf'

doc_type, _ = detect_document_type(pdf_path)
print(f'DOC TYPE: {doc_type}')

full_text, pages, telemetry, page_tokens = route_document(pdf_path)
print(f'PAGE TOKENS: {len(page_tokens)}')

identity = classify_document_llm(pages)
print(f'IDENTITY: {identity}')

pdf_type = 'SCANNED' if doc_type.upper() == 'SCANNED' else 'DIGITAL'
txns, tel = parse_with_coordinates(page_tokens, pdf_name='test.pdf', statement_id='123', job_id='456', bank='Kotak', pdf_type=pdf_type, identity=identity)

print(f'TRANSACTIONS: {len(txns)}')
rej = tel.get('reject_log', [])
print(f'REJECTS: {len(rej)}')
if len(rej) > 0:
    for r in rej[:5]:
        print(f"REASON: {r.get('reject_reason')}")
