import sys
import docling
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert(r'Z:\CA\validation_lab\backend\temp\JOB_20260614_215535_7B9C_YESBANK.pdf')
doc = result.document

page = doc.pages[1]
print("Page attributes:")
print(dir(page))
if hasattr(page, 'cells'):
    print(f"Cells count: {len(page.cells)}")
if hasattr(page, 'image_cells'):
    print(f"Image cells: {len(page.image_cells)}")
if hasattr(page, 'text_cells'):
    print(f"Text cells count: {len(page.text_cells)}")
    
print("\nDocument iter items:")
count = 0
for item, level in doc.iterate_items():
    if hasattr(item, 'prov') and item.prov:
        if count < 5:
            print(f"Type: {type(item).__name__}, Text: {item.text[:30]}, bbox: {item.prov[0].bbox}")
        count += 1
print(f"Total iter items: {count}")

