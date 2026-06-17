import json
from core.adapters.ocr_subprocess import extract_via_subprocess

PDF_PATH = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'

full_text, pages, telemetry, page_tokens = extract_via_subprocess(PDF_PATH)
flat = []
if isinstance(page_tokens, dict):
    for _, toks in page_tokens.items():
        flat.extend(toks)
else:
    flat = page_tokens

print("Finding 31/11/21 debit row...")
for t in flat:
    if "31/11" in t.get("text", ""):
        print("Found date token:", t)
        
for p in pages:
    lines = p.split("\n")
    for l in lines:
        if "31/11" in l:
            print("Row text:", l)
