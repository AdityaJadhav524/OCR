import sys, os
from pathlib import Path
sys.path.insert(0, '.')
from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
pdf_path = sorted(Path('validation_lab/backend/temp').glob('*24-25 -2 1 (2)_page-0006.pdf'), key=os.path.getmtime)[-1]
full_text, pages, tel, page_tokens = route_document(str(pdf_path))
txns, telemetry = parse_with_coordinates(page_tokens, pdf_name=pdf_path.name, identity={'family':'BANK_STATEMENT'})
print(f'direction_corrections_math: {telemetry.get("direction_corrections_math")}')
print(f'direction_corrections_narr: {telemetry.get("direction_corrections_narr")}')
for t in txns[-5:]:
    print(f'Date: {t.get("date")} Narration: {str(t.get("narration"))[:20]}')
    print(f'  Debit: {t.get("debit")} Credit: {t.get("credit")}')
    print(f'  Ledger Truth: {t.get("ledger_truth")}')
