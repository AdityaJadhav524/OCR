from core.adapters.ocr_subprocess import extract_via_subprocess

pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

print("--- 03/11/21 Y-BAND TOKENS ---")
for t in page_tokens:
    y_mid = (t['y0'] + t['y1']) / 2
    if 680 < y_mid < 735 and t['page'] == 1:
        print(f"{t['text']:20s} x0={t['x0']:.1f} x1={t['x1']:.1f} y0={t['y0']:.1f} y1={t['y1']:.1f}")
