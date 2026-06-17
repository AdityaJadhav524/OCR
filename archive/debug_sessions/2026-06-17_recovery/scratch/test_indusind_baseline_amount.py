import json
from core.validators.financial_audit import _prove_amount

tok = {'text': '3,000.00', 'x0': 1164.0, 'y0': 1424.0, 'x1': 1265.0, 'y1': 1463.0, 'page': 1, 'source': 'paddleocr', 'yc': 1443.5}

debit_zone = [952.0, 1167.0]
credit_zone = [1159.0, 1383.0]

print("Debit:", _prove_amount(tok, debit_zone))
print("Credit:", _prove_amount(tok, credit_zone))
