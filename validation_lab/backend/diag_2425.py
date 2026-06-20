"""
Write TJSB token/row data to a file to avoid console encoding issues.
"""
import sys, logging, json
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, 'c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'c:\Users\adity\Downloads\CA\validation_lab\backend\temp\JOB_20260619_162131_C4F0_24-25 -2 2.pdf'
_, _ = detect_document_type(pdf_path)
full_text, pages, tel, page_tokens = route_document(pdf_path)
identity = classify_document_llm(pages)
rows = detect_rows(page_tokens)
zones, header_row = detect_columns(rows, identity)

out = []
out.append(f"BANK: {identity.get('institution_name')}")
out.append(f"TOTAL ROWS: {len(rows)}")
out.append(f"ZONES: {zones}")
out.append(f"")

# Header tokens
out.append("=== HEADER TOKENS ===")
for t in header_row:
    out.append(f"  x0={t.get('x0',0):7.1f}  x1={t.get('x1',0):7.1f}  text={repr(t.get('text',''))}")

# Keyword-bearing rows
out.append("")
out.append("=== ROWS WITH KEYWORDS (first 50 matches) ===")
kws = ['DATE','BALANCE','DEBIT','CREDIT','WITHDRAWAL','DEPOSIT','NARRATION','PARTICULARS']
count = 0
for i, row in enumerate(rows):
    tokens = row.get('tokens', [])
    text_raw = ' | '.join(t.get('text','').replace('\u20b9','Rs') for t in tokens)
    text_up = text_raw.upper()
    if any(kw in text_up for kw in kws):
        xs = [round(t.get('x0',0),1) for t in tokens]
        out.append(f"Row {i:4d} (pg={row.get('page','?')}): {text_raw[:100]}")
        out.append(f"           x0s={xs[:8]}")
        count += 1
        if count >= 50:
            break

# Blocks and their reject reasons
out.append("")
out.append("=== PARSE RESULT ===")
txns, tel2 = parse_with_coordinates(page_tokens, pdf_name='test', statement_id='x', job_id='x', bank='TJSB', pdf_type='DIGITAL')
out.append(f"ACCEPTED: {len(txns)}")
rejects = tel2.get('reject_log', [])
out.append(f"REJECTED: {len(rejects)}")
from collections import Counter
reasons = Counter(r.get('reject_reason','?') for r in rejects)
out.append(f"REASONS: {dict(reasons)}")
out.append("")
out.append("FIRST 5 REJECTS:")
for r in rejects[:5]:
    raw = r.get('raw_extraction', {})
    out.append(f"  date={r.get('date')}  reason={r.get('reject_reason')}")
    out.append(f"  snippet={r.get('block_text_snippet','')[:80]}")
    out.append(f"  ocr_balance={raw.get('ocr_balance_text')} parsed={raw.get('parsed_balance')}")
    out.append(f"  ocr_debit={raw.get('ocr_debit_text')}  ocr_credit={raw.get('ocr_credit_text')}")
    out.append("")

with open('tjsb_diag.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print("Written to tjsb_diag.txt")
