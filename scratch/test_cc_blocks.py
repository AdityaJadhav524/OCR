import os
import sys

sys.path.insert(0, os.path.abspath('core'))
from core.extractors.document_router import route_document
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns

pdf_path = r"c:\Users\adity\Downloads\CA\validation_lab\backend\temp\JOB_20260617_144436_EF6E_CC_STMT_117048135_345073_1607202515082025 1 (1) 2_page-0001.pdf"

full_text, pages, merge_stats, page_tokens = route_document(pdf_path)

rows = detect_rows(page_tokens)
print(f"Detected {len(rows)} rows")

zones, _ = detect_columns(rows)
date_zone = zones.get("date_zone")
print(f"Date zone: {date_zone}")

blocks = detect_transaction_blocks(rows, date_x_bounds=date_zone)
print(f"Detected {len(blocks)} blocks")
for i, b in enumerate(blocks):
    if i < 3:
        print(f"Block {i}:")
        for r in b:
            print("  ", " ".join([t.get("text", "") for t in r.get("tokens", [])]))
