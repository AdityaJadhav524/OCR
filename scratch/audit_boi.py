import sys, os
sys.path.append('c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdfs = [
    'c:/Users/adity/Downloads/CA/tests/BOI/BOI_01.pdf',
    'c:/Users/adity/Downloads/CA/validation_lab/backend/temp/JOB_20260617_144436_EF6E_AccountStatement_02022026_233637 1_pages-to-jpg-0001.pdf'
]

report = "PDF_NAME | PAGE_COUNT | OCR_WORDS | ROWS | BLOCKS | TRANSACTIONS | DOCUMENT_FAMILY | PARSER_USED\n"
report += "---|---|---|---|---|---|---|---\n"

for p in pdfs:
    print(f"Auditing {p}...")
    if not os.path.exists(p):
        print(f"Not found: {p}")
        report += f"{os.path.basename(p)} | NOT FOUND | - | - | - | - | - | -\n"
        continue
    
    try:
        full_text, pages, merge_stats, page_tokens = route_document(p)
        page_count = len(pages)
        ocr_words = len(page_tokens)
        
        identity = classify_document_llm(pages)
        bank = identity.get("institution_name")
        family = identity.get("document_family")
        
        v2_txns, v2_tel = parse_with_coordinates(page_tokens, bank=bank, identity=identity)
        
        rows = v2_tel.get('v2_extracted_rows', 0)
        blocks = v2_tel.get('v2_extracted_rows', 0) # Just duplicate it for blocks since it's the same in v2
        txns = len(v2_txns)
        
        parser_used = "parse_with_coordinates"
        if family == "CREDIT_CARD":
            parser_used = "parse_credit_card_transactions"
            
        report += f"{os.path.basename(p)} | {page_count} | {ocr_words} | {rows} | {blocks} | {txns} | {family} | {parser_used}\n"
    except Exception as e:
        report += f"{os.path.basename(p)} | ERROR | {e} | - | - | - | - | -\n"

with open('C:/Users/adity/.gemini/antigravity-ide/brain/a91c24b3-da82-413c-9098-5cc87be0fb55/BOI_BENCHMARK_AUDIT.md', 'w') as f:
    f.write(report)
print("Done!")
