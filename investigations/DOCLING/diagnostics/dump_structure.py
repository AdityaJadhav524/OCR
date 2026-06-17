import sys
import json
import os
from docling.document_converter import DocumentConverter

print("Converting page12_test.pdf...")
converter = DocumentConverter()
pdf_path = r"Z:\CA\investigations\DOCLING\HDFC\page12_test.pdf"

result = converter.convert(pdf_path)
doc = result.document

print("Exporting to dict...")
doc_dict = doc.export_to_dict()

out_path = r"Z:\CA\investigations\DOCLING\diagnostics\docling_document_structure.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(doc_dict, f, indent=2)

print(f"Dumped to {out_path}")

# Print basic dir
print("\ndir(doc):")
print(dir(doc))

print("\nPages:")
for p_no, page in doc.pages.items():
    print(f"Page {p_no}:")
    print(f"  dir(page): {dir(page)}")
    if hasattr(page, 'cells'):
        print(f"  Cells length: {len(page.cells)}")
    if hasattr(page, 'text_cells'):
        print(f"  Text cells length: {len(page.text_cells)}")
    if hasattr(page, 'image_cells'):
        print(f"  Image cells length: {len(page.image_cells)}")

