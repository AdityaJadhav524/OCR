import os
import sys

sys.path.insert(0, os.path.abspath('core'))

# Find the YESBANK file
import glob
temp_dir = r"c:\Users\adity\Downloads\CA\validation_lab\backend\temp"
yes_files = glob.glob(os.path.join(temp_dir, "*YESBANK*")) + glob.glob(os.path.join(temp_dir, "*YES*"))
print("Found YES files:", yes_files)

if yes_files:
    pdf_path = yes_files[0]
    from core.extractors.document_router import route_document
    from core.detection.bank_detector import _detect_by_keywords, _detect_by_ocr_header, _detect_by_ifsc

    full_text, pages, merge_stats, page_tokens = route_document(pdf_path)

    print("\nFirst 500 chars of page 1:")
    print(pages[0][:500] if pages else "(no pages)")

    print("\nLayer 3 (OCR Header):", _detect_by_ocr_header(pages))
    print("Layer 1 (Keywords):", _detect_by_keywords(pages[0] if pages else ""))
    print("Layer 2 (IFSC):", _detect_by_ifsc("\n".join(pages)))

    # Check raw text for YES
    page_upper = (pages[0] if pages else "").upper()
    print("\n'YES BANK' in page:", "YES BANK" in page_upper)
    print("'YESBANK' in page:", "YESBANK" in page_upper)
    print("'YES' in page:", "YES" in page_upper)
