import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.layout.row_detector import detect_rows

pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
_, _, _, page_tokens = extract_via_subprocess(pdf_path)

date_kws = ['DATE', 'TXN DATE', 'VALUE DATE']
narration_kws = ['PARTICULARS', 'NARRATION', 'DESCRIPTION', 'DETAILS']
debit_kws = ['WITHDRAWAL', 'DEBIT', 'DR']
credit_kws = ['DEPOSIT', 'CREDIT', 'CR']
balance_kws = ['BALANCE', 'BAL']

rows = detect_rows(page_tokens)

for row in rows:
    tokens_row = row.get('tokens', [])
    text_upper = ' '.join([t['text'].upper() for t in tokens_row])
    if any(kw in text_upper for kw in date_kws) and any(kw in text_upper for kw in balance_kws):
        header_row = tokens_row
        break

cols_found = []
for t in header_row:
    text = t['text'].upper().replace('.', '').strip()
    x0 = t['x0']
    
    if any(kw in text for kw in date_kws): cols_found.append({'type': 'date', 'x0': x0})
    elif any(kw in text for kw in narration_kws): cols_found.append({'type': 'narration', 'x0': x0})
    elif any(kw in text for kw in debit_kws) or 'WITHDRAWAL' in text: cols_found.append({'type': 'debit', 'x0': x0})
    elif any(kw in text for kw in credit_kws) or 'DEPOSIT' in text: cols_found.append({'type': 'credit', 'x0': x0})
    elif any(kw in text for kw in balance_kws): cols_found.append({'type': 'balance', 'x0': x0})

cols_found.sort(key=lambda c: c['x0'])

unique_cols = []
seen = set()
for c in cols_found:
    if c['type'] not in seen:
        seen.add(c['type'])
        unique_cols.append(c)

zones = {}
for i in range(len(unique_cols)):
    col = unique_cols[i]
    if i == 0: start_x = 0.0
    else: start_x = (unique_cols[i-1]['x0'] + col['x0']) / 2.0
    
    if i < len(unique_cols) - 1: end_x = (col['x0'] + unique_cols[i+1]['x0']) / 2.0
    else: end_x = 9999.0
    
    zones[f"{col['type']}_zone"] = [start_x, end_x]

print(zones)
