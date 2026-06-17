import sys
import docling
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert(r'Z:\CA\validation_lab\backend\temp\JOB_20260614_215535_7B9C_YESBANK.pdf')
doc = result.document
print('Pages:', len(doc.pages))
for page_no, page in doc.pages.items():
    print(f"Page {page_no}")
    if hasattr(page, 'cells'):
        for cell in page.cells[:5]:
            print(cell.text, cell.bbox)
    break
