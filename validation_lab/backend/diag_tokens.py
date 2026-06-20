"""Show all header token raw x0/x1 values to understand column boundary source."""
import sys, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, 'c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_rows
from core.layout.column_detector import detect_columns

pdf_path = r'c:\Users\adity\Downloads\CA\validation_lab\backend\temp\DocScanner 17-Apr-2026 11-06 AM 1.pdf'
_, _ = detect_document_type(pdf_path)
full_text, pages, _, page_tokens = route_document(pdf_path)
identity = classify_document_llm(pages)
rows = detect_rows(page_tokens)
zones, header_row = detect_columns(rows, identity)

print("ZONES:", zones)
print()
print("HEADER TOKENS (all):")
for t in header_row:
    print(f"  text={t.get('text','')!r:40}  x0={t.get('x0',0):8.1f}  x1={t.get('x1',0):8.1f}")

print()
print("ALL TOKENS with x0 > 1000 (to see where amount/balance tokens land):")
for t in page_tokens:
    x0 = t.get('x0', 0)
    if x0 > 1000:
        print(f"  text={t.get('text','')!r:20}  x0={x0:8.1f}  x1={t.get('x1',0):8.1f}")
