import sys
from pathlib import Path
import json

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.statement_confidence_engine import generate_statement_confidence
import glob

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def test():
    pattern = str(TEMP_DIR / f"*HDFC_SAVINGS_SCANNED.pdf")
    matches = glob.glob(pattern)
    pdf_path = sorted(matches)[-1]
    
    # Bypass OCR timeout by loading from cache if possible, else just do it
    # We will just run the engine
    import logging
    logging.basicConfig(level=logging.INFO)
    
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    txns, _ = parse_with_coordinates(page_tokens, pdf_name="HDFC", bank="HDFC BANK", pdf_type="SCANNED")
    
    engine_payload = generate_statement_confidence(txns)
    print(f"Final Continuity: {engine_payload['continuity']}%")

if __name__ == "__main__":
    test()
