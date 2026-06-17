import json
from pathlib import Path
import fitz  # PyMuPDF
from core.adapters.ocr_subprocess import extract_via_subprocess

def main():
    pdf_path = r'Z:\CA\validation_lab\backend\temp\JOB_20260614_215535_7B9C_YESBANK.pdf'
    
    # Ground truth values we are looking for:
    targets = [
        {"truth": "286,201.63", "match": "286", "page": 0},
        {"truth": "250,066.93", "match": "250", "page": 0},
        {"truth": "208,208.93", "match": "208", "page": 1},
        {"truth": "171,105.18", "match": "171", "page": 2}
    ]
    
    print(f"Running PaddleOCR on {pdf_path}...")
    full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)
    
    doc = fitz.open(pdf_path)
    out_dir = Path(r'Z:\CA\scratch\p8_crops')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # page_tokens is a list of dicts. We need to group by page.
    tokens_by_page = {}
    if isinstance(page_tokens, dict):
        tokens_by_page = page_tokens
    else:
        for t in page_tokens:
            p = t.get('page', 0)
            tokens_by_page.setdefault(p, []).append(t)
            
    # For drawing, PaddleOCR coordinates are likely in image space.
    # To handle this easily, we won't draw on the PDF directly.
    # We will just print the exact confidence and OCR text.
    
    for target in targets:
        print(f"\n======================================")
        print(f"Searching for Ground Truth: {target['truth']}")
        print(f"======================================")
        
        flat_tokens = []
        for p, toks in tokens_by_page.items():
            flat_tokens.extend(toks)
            
        candidates = [t for t in flat_tokens if target['match'] in t['text']]
        
        for c in candidates:
            # Check if it's likely a balance or amount (y-coordinate or length check)
            if len(c['text']) < 6: continue
            
            print(f"  --> FOUND OCR TEXT: '{c['text']}'")
            print(f"      Confidence : {c.get('confidence', 'Not Provided by V2 OCR')}")
            print(f"      Page Index : {c['page']}")
            print(f"      BBox       : [x0={c['x0']:.1f}, y0={c['y0']:.1f}, x1={c['x1']:.1f}, y1={c['y1']:.1f}]")
            print(f"      Source     : {c.get('source', 'Unknown')}")
            
    print("\nInvestigation Complete.")

if __name__ == '__main__':
    main()
