import os
import sys
from core.extractors.document_router import route_document
from core.detection.header_suppression import suppress_headers_and_footers
from core.layout.row_detector import detect_rows

pdf_path = "tests/pdfs/HDFC_SAVINGS_SCANNED.pdf"
_, _, _, tokens = route_document(pdf_path)
tokens = suppress_headers_and_footers(tokens)

pages = {}
for t in tokens:
    p = t.get('page', 0)
    if p not in pages: pages[p] = []
    pages[p].append(t)

for p in sorted(pages.keys()):
    print(f"\n--- Page {p} ---")
    page_tokens = pages[p]
    rows = detect_rows(page_tokens)
    
    # Filter rows around the table header / first transaction zone
    target_rows = [r for r in rows if r.get('y0', 0) > 550 and r.get('y0', 0) < 750]
    
    for i, r in enumerate(target_rows[:10]):
        text = " ".join([t.get('text', '') for t in r.get('tokens', [])])
        print(f"Row {i} (y0={r.get('y0')}, y1={r.get('y1')}): {text}")
