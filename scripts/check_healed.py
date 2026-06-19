import sys
import os
import json
sys.path.append(r'c:\Users\adity\Downloads\CA')
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth

with open(r'C:\Users\adity\Downloads\CA\scratch\yes_bank_dump.json', 'r') as f:
    data = json.load(f)

transactions, parser_telemetry = parse_with_coordinates(
    data['page_tokens'], 
    pdf_name='YESBANK.pdf', 
    bank='YES BANK',
    pdf_type='scanned'
)

for t in transactions:
    raw = t['raw_extraction']
    # Check both the raw extraction and the healed balance
    if raw.get('parsed_balance') in [285201.63, 171109.18, 208205.93, 208208.93, 171105.18, 286201.63, 250066.93, 250065.93]:
        print(f"Row Date: {t['date']} | Original: {raw.get('parsed_balance')} | Healed: {t.get('balance')} | Trust: {t.get('ledger_truth', {}).get('balance_trust')}")
