import json
import os
import sys
import time

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.document import DoclingDocument
except ImportError as e:
    print(f"ERROR: Docling not installed in this environment: {e}")
    sys.exit(1)

PDF_PATH = r"Z:\CA\investigations\DOCLING\HDFC\page12_test.pdf"
OUT_DIR  = r"Z:\CA\investigations\DOCLING\HDFC"

print("=" * 70)
print("P6B — Docling Forensic Single-Page Evaluation (Page 12)")
print("=" * 70)

t0 = time.time()
converter = DocumentConverter()
result = converter.convert(PDF_PATH)
doc: DoclingDocument = result.document

elapsed = time.time() - t0
print(f"Conversion took {elapsed:.2f}s")

def save_json(filename, data):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved: {path}")

page12_layout = []
footer_blocks = []
header_blocks = []
table_blocks = []
text_blocks = []

for item, level in doc.iterate_items():
    item_type = type(item).__name__
    label = getattr(item, "label", "unknown")
    text = ""
    if hasattr(item, "text"):
        text = item.text
    elif hasattr(item, "export_to_markdown"):
        try:
            text = item.export_to_markdown(doc=doc)
        except Exception as e:
            text = f"Error extracting text: {e}"
    
    bbox = None
    page = 12
    if hasattr(item, "prov") and item.prov:
        prov = item.prov[0]
        if hasattr(prov, "bbox") and prov.bbox:
            b = prov.bbox
            bbox = [b.l, b.t, b.r, b.b]

    block_data = {
        "type": label,
        "text": text,
        "page": page,
        "bbox": bbox
    }
    
    page12_layout.append(block_data)
    
    label_lower = str(label).lower()
    if "footer" in label_lower:
        footer_blocks.append(block_data)
    elif "header" in label_lower or "title" in label_lower:
        header_blocks.append(block_data)
    elif "table" in label_lower:
        table_blocks.append(block_data)
    else:
        text_blocks.append(block_data)

save_json("page12_layout.json", page12_layout)
save_json("footer_blocks.json", footer_blocks)
save_json("header_blocks.json", header_blocks)
save_json("table_blocks.json", table_blocks)
save_json("text_blocks.json", text_blocks)

print("\n--- Summary ---")
print(f"Total blocks: {len(page12_layout)}")
print(f"Headers: {len(header_blocks)}")
print(f"Footers: {len(footer_blocks)}")
print(f"Tables: {len(table_blocks)}")
print(f"Text/Other: {len(text_blocks)}")
