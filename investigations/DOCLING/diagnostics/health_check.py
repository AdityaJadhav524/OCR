import sys
import time

print("--- Docling Diagnostic ---")
print(f"Python: {sys.version}")

try:
    import torch
    print(f"Torch: {torch.__version__}")
except ImportError:
    print("Torch: not installed")

print("1. Importing Docling...")
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    print("   Success")
except Exception as e:
    print(f"   Failed: {e}")
    sys.exit(1)

print("2. Initializing converter...")
try:
    converter = DocumentConverter()
    print("   Success")
except Exception as e:
    print(f"   Failed: {e}")
    sys.exit(1)

print("3. Converting simple single page PDF (HDFC page 12)...")
try:
    pdf_path = r"Z:\CA\investigations\DOCLING\HDFC\page12_test.pdf"
    result = converter.convert(pdf_path)
    doc = result.document
    print(f"   Success! Extracted {len(doc.pages)} pages")
except Exception as e:
    print(f"   Failed: {e}")
    sys.exit(1)

print("\nAll docling diagnostics passed successfully.")
