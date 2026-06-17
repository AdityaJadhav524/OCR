import json
from pathlib import Path
from core.adapters.ocr_subprocess import extract_via_subprocess

def main():
    pdf_path = r'Z:\CA\validation_lab\backend\temp\JOB_20260614_215535_7B9C_YESBANK.pdf'
    
    print(f"Running PaddleOCR on {pdf_path}...")
    full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)
    
    tokens_by_page = {}
    if isinstance(page_tokens, dict):
        tokens_by_page = page_tokens
    else:
        for t in page_tokens:
            p = t.get('page', 0)
            tokens_by_page.setdefault(p, []).append(t)
            
    # Page 1: target is 286,201.63 which should be right after 286,210.60
    # 286,210.60 is at y0=1127.0
    print("\n--- PAGE 1 BALANCE TOKENS (x0 > 1400) around y0=1127 ---")
    p1_tokens = [t for t in tokens_by_page.get(0, []) if t['x0'] > 1400 and 1100 < t['y0'] < 1300]
    p1_tokens.sort(key=lambda x: x['y0'])
    for t in p1_tokens:
        print(f"y0={t['y0']:.1f} : {t['text']}")

    # Wait, the log said:
    # BBox: x0=1486.0, y0=1127.0, x1=1583.0, y1=1151.0, Page=1 (this is actually page index 1, which is the 2nd page!)
    print("\n--- PAGE 2 (index 1) BALANCE TOKENS (x0 > 1400) around y0=1127 ---")
    p2_tokens = [t for t in tokens_by_page.get(1, []) if t['x0'] > 1400 and 1050 < t['y0'] < 1250]
    p2_tokens.sort(key=lambda x: x['y0'])
    for t in p2_tokens:
        print(f"y0={t['y0']:.1f} : {t['text']}")

if __name__ == '__main__':
    main()
