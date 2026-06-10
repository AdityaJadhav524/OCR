"""
extract.py — OCR Core CLI and Entry Point
"""
import argparse
import json
import logging
import os
import sys

# Ensure local imports work correctly if run from outside the directory
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from pipeline import run_pipeline
from layout_tree import asdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_document(pdf_path: str) -> dict:
    """
    Executes the standalone OCR pipeline on a PDF file.

    Returns:
        dict: A structured document containing "pages", "lines", and "words".
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    filename = os.path.basename(pdf_path)
    logger.info("Starting extraction for %s", filename)

    # run_pipeline returns a Document layout tree
    doc = run_pipeline(file_bytes=file_bytes, filename=filename)

    # Flatten the document tree into the requested structure
    out_pages = []
    out_lines = []
    out_words = []

    for page in doc.pages:
        out_pages.append({
            "page_number": page.page_number,
            "width": page.width,
            "height": page.height
        })
        
        for line in page.lines:
            line_dict = asdict(line)
            line_dict["page_number"] = page.page_number
            out_lines.append(line_dict)
            
        for word in page.words:
            word_dict = asdict(word)
            word_dict["page_number"] = page.page_number
            out_words.append(word_dict)

    result = {
        "metadata": {
            "filename": filename,
            "total_pages": len(doc.pages),
        },
        "pages": out_pages,
        "lines": out_lines,
        "words": out_words
    }

    logger.info("Extraction complete: %d pages, %d lines, %d words", 
                len(out_pages), len(out_lines), len(out_words))
    
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone OCR Extraction Core")
    parser.add_argument("file", help="Path to PDF document")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON")
    
    args = parser.parse_args()

    try:
        data = extract_document(args.file)
        print(json.dumps(data, indent=2 if args.pretty else None, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        logger.error("Extraction failed: %s", e)
        sys.exit(1)
