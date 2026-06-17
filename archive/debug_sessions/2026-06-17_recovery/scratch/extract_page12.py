import fitz
import os

PDF_PATH = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"
OUT_PATH = r"Z:\CA\investigations\DOCLING\HDFC\page12_test.pdf"

doc = fitz.open(PDF_PATH)
# Page 12 is index 11
doc_new = fitz.open()
doc_new.insert_pdf(doc, from_page=11, to_page=11)
doc_new.save(OUT_PATH)
print(f"Saved {OUT_PATH}")
