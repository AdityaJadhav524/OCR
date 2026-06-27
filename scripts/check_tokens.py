import sys
import os
sys.path.append(r'c:\Users\adity\Downloads\CA')
from ocr.adapters.ocr_subprocess import extract_via_subprocess

pdf_path = r'C:\Users\adity\Downloads\CA\tests\pdfs\YESBANK.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

targets = ['20820', '28520', '28620', '17110', '25006']
for p_num, p_tokens in enumerate(page_tokens):
    for t in p_tokens:
        if any(trg in t['text'] for trg in targets):
            print(f"Page {p_num}: '{t['text']}'")
