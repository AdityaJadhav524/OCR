import os
import sys

sys.path.insert(0, r"Z:\CA")
import pdfplumber

with pdfplumber.open(r"Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf") as pdf:
    for page in pdf.pages[:1]:
        print("Page 1 Layout:")
        print(page.extract_text(layout=True)[:1000])
