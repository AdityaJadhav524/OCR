import json
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
with open(r'z:\CA\scratch\indusind_tokens.json', 'r') as f:
    tokens = json.load(f)

txns, tel = parse_with_coordinates(tokens)

t = txns[3]
date    = str(t.get("date") or "")
debit   = str(t.get("debit") or "")
credit  = str(t.get("credit") or "")
balance = str(t.get("balance") or "")
print(f"{date}|{debit}|{credit}|{balance}")

with open(r'Z:\CA\scratch\regression_baseline.json', 'r') as f:
    base = json.load(f)
tb = base[0]['transactions'][3]
date_b    = str(tb.get("date") or "")
debit_b   = str(tb.get("debit") or "")
credit_b  = str(tb.get("credit") or "")
balance_b = str(tb.get("balance") or "")
print(f"{date_b}|{debit_b}|{credit_b}|{balance_b}")

print("Equal?", f"{date}|{debit}|{credit}|{balance}" == f"{date_b}|{debit_b}|{credit_b}|{balance_b}")
