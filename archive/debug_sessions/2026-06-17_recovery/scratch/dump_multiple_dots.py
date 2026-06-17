import json
data = json.load(open(r'Z:\CA\investigations\HDFC\raw_output.json', encoding='utf-8'))
for t in data:
    if t.get('suspicious_fields', {}).get('balance', {}).get('reason') == 'MULTIPLE_DOTS':
        print(f"{t.get('date')} | {t.get('raw_extraction', {}).get('ocr_balance_text')} | {t.get('narration', '')[:30]}")
