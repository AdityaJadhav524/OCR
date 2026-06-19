import sys
sys.path.append(r'C:\Users\adity\Downloads\CA')
from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'C:\Users\adity\Downloads\CA\tests\BOI\BOI_01.pdf'
print(f"Testing {pdf_path}")
full_text, pages, telemetry, page_tokens = route_document(pdf_path)
txns, tel = parse_with_coordinates(page_tokens, pdf_name='BOI_01.pdf', statement_id='test', job_id='test', bank_name='BANK OF INDIA')
print('Transactions extracted:', len(txns))
if tel.get('abort_reason'):
    print('Abort reason:', tel.get('abort_reason'))
