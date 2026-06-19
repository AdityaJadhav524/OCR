import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
_workspace = os.path.dirname(_root)
sys.path.insert(0, _workspace)

from core.extractors.document_router import detect_document_type

test_dir = os.path.join(_workspace, "tests", "pdfs")
for f in os.listdir(test_dir):
    if "DIGITAL" in f:
        pdf_path = os.path.join(test_dir, f)
        try:
            doc_class = detect_document_type(pdf_path)
            print(f"{f}: {doc_class}")
        except Exception as e:
            print(f"{f}: Failed - {e}")
