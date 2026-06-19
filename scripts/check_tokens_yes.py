import sys
sys.path.append(r'c:\Users\adity\Downloads\CA')
from core.adapters.ocr_subprocess import extract_via_subprocess

pdf_path = r'C:\Users\adity\Downloads\CA\tests\pdfs\YESBANK.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

targets = ['20820', '28520', '28620', '17110', '25006']
for t in page_tokens:
    for trg in targets:
        if trg in t['text']:
            print(f"OCR Token: '{t['text']}'")
