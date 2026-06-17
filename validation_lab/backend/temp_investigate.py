import fitz
import pdfplumber
import json
import os
import sys
from decimal import Decimal

PDF_PATH = r"z:\CA\validation_lab\backend\temp\11707454011-JUL-25221947 2.PDF"
OUTPUT_PATH = r"C:\Users\adity\.gemini\antigravity-ide\brain\56dc278d-6771-432f-a44f-4b9b53723f34\scratch\boi_investigation.json"

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def run_investigation(password):
    results = {}

    print(f"Testing password: '{password}'")
    
    print("Extracting with pdfplumber...")
    try:
        with pdfplumber.open(PDF_PATH, password=password) as pdf:
            page2 = pdf.pages[1]
            
            tables_meta = page2.find_tables()
            results["pdfplumber_tables_count"] = len(tables_meta)
            
            tables_data = page2.extract_tables()
            if tables_data:
                results["pdfplumber_first_table_dimensions"] = f"{len(tables_data[0])} rows x {len(tables_data[0][0]) if tables_data[0] else 0} cols"
                results["pdfplumber_first_20_rows"] = tables_data[0][:20]
            else:
                results["pdfplumber_first_table_dimensions"] = "0 rows x 0 cols"
                results["pdfplumber_first_20_rows"] = []
                
            words = page2.extract_words()
            results["pdfplumber_words_count"] = len(words)
            results["pdfplumber_words_sample"] = [
                {"text": w["text"], "x0": round(w["x0"],1), "top": round(w["top"],1)} for w in words[:20]
            ]
    except Exception as e:
        results["pdfplumber_error"] = str(type(e)) + ": " + str(e)

    print("Extracting with PyMuPDF...")
    try:
        doc = fitz.open(PDF_PATH)
        if doc.needs_pass:
            auth = doc.authenticate(password)
            if not auth:
                results["fitz_error"] = "Failed to authenticate"
        
        if not doc.needs_pass or doc.authenticate(password):
            page2 = doc[1]
            words = page2.get_text("words")
            results["fitz_words_count"] = len(words)
            results["fitz_words_sample"] = [
                {"text": w[4], "bbox": [round(w[0],1), round(w[1],1), round(w[2],1), round(w[3],1)]} 
                for w in words[:20]
            ]
    except Exception as e:
        results["fitz_error"] = str(type(e)) + ": " + str(e)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, cls=DecimalEncoder)

    print("Investigation complete.")

if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else ""
    run_investigation(pwd)
