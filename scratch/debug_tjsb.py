import sys, json, os
from pathlib import Path
sys.path.insert(0, '.')
from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.detection.bank_detector import classify_document_llm

pdf_path = list(Path('tests/truth_corpus').glob('*24-25 -2 2.pdf'))
if not pdf_path:
    pdf_path = list(Path('validation_lab/backend/temp').glob('*24-25 -2 2.pdf'))

if pdf_path:
    pdf_path = pdf_path[0]
    print(f'Processing {pdf_path}')
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    identity = classify_document_llm(pages)
    txns, telemetry = parse_with_coordinates(page_tokens, pdf_name=pdf_path.name, identity=identity)
    
    print(f'Extracted {len(txns)} transactions.')
    for t in txns[:5]:
        print(f'Date: {t.get("date")}')
        print(f'  Narration: {t.get("narration")[:40]}...')
        print(f'  Debit: {t.get("debit")} | Credit: {t.get("credit")} | Balance: {t.get("balance")}')
        print(f'  Raw Debit: {t.get("raw_extraction", {}).get("parsed_debit")} | Raw Credit: {t.get("raw_extraction", {}).get("parsed_credit")}')
        print(f'  Ledger Truth: {t.get("ledger_truth")}')
        print(f'  Corrected: {t.get("direction_corrected")} - {t.get("direction_corrected_reason")}')
        print('---')
else:
    print('PDF not found')
