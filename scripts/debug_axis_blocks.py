import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document
from core.layout.row_detector import detect_transaction_blocks, detect_rows

pdf_path = ROOT / "tests" / "truth_corpus" / "axis.pdf"
full_text, pages, tel, page_tokens = route_document(str(pdf_path))
rows = detect_rows(page_tokens)
blocks = detect_transaction_blocks(rows)
print(f"Total Rows: {len(rows)}")
print(f"Total Blocks: {len(blocks)}")
for i, b in enumerate(blocks[:10]):
    print(f"Block {i}: {len(b)} rows")
    for r in b:
        print("  " + " ".join(t.get("text", "") for t in r.get("tokens", [])))
