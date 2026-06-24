import sys, json, os
from pathlib import Path
sys.path.insert(0, '.')
from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.detection.bank_detector import classify_document_llm

pdf_path = list(Path('validation_lab/backend/temp').glob('*24-25 -2 1 (2)_page-0006.pdf'))

if pdf_path:
    pdf_path = sorted(pdf_path, key=os.path.getmtime)[-1] # latest
    print(f'Processing {pdf_path}')
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    identity = {"family": "BANK_STATEMENT"}
    txns, telemetry = parse_with_coordinates(page_tokens, pdf_name=pdf_path.name, identity=identity)
    
    print(f'zones_detected: {telemetry.get("zones_detected")}')
    print(f'zones_swapped: {telemetry.get("zones_swapped")}')
    print(f'direction_corrections_math: {telemetry.get("direction_corrections_math")}')
    print(f'direction_corrections_narr: {telemetry.get("direction_corrections_narr")}')
    print('---')
    
    for t in txns[:8]:
        print(f'Date: {t.get("date")}')
        print(f'  Narration: {str(t.get("narration"))[:40]}...')
        print(f'  Debit: {t.get("debit")} | Credit: {t.get("credit")} | Balance: {t.get("balance")}')
        print(f'  Raw Debit: {t.get("raw_extraction", {}).get("parsed_debit")} | Raw Credit: {t.get("raw_extraction", {}).get("parsed_credit")} | Raw Bal: {t.get("raw_extraction", {}).get("parsed_balance")}')
        print(f'  Ledger Truth: {t.get("ledger_truth")}')
        print(f'  Corrected: {t.get("direction_corrected")} - {t.get("direction_corrected_reason")}')
        print('---')
else:
    print('PDF not found')
