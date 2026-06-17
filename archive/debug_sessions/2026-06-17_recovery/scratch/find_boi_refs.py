import sys, json, os

files_to_check = ['c:/Users/adity/Downloads/CA/phase1_verify.py', 'c:/Users/adity/Downloads/CA/evaluate_uploads.py']
for fpath in files_to_check:
    print(f'\n--- {fpath} ---')
    if not os.path.exists(fpath):
        print("File not found")
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if 'BOI' in line or 'BANK OF INDIA' in line or 'AccountStatement' in line or 'Acct Statement' in line:
                print(f'{i+1}: {line.strip()}')

print('\n--- benchmark_export.json ---')
export_path = 'c:/Users/adity/Downloads/CA/validation_lab/backend/benchmark_export.json'
if os.path.exists(export_path):
    with open(export_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for entry in data:
            pdf = entry.get('pdf_name', '')
            bank = entry.get('bank', '')
            if 'BOI' in pdf.upper() or 'BANK OF INDIA' in bank.upper() or 'ACCOUNTSTATEMENT' in pdf.upper() or 'ACCT STATEMENT' in pdf.upper():
                print(f"File: {pdf}, Bank: {bank}, Txns: {entry.get('txns_count')}")
else:
    print("benchmark_export.json not found")
