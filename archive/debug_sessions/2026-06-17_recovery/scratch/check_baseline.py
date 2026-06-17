import json

data = json.load(open('Z:\\CA\\scratch\\regression_baseline.json'))
print(f'Total entries in baseline: {len(data)}')
for item in data:
    pdf = item.get("pdf", "?")
    n = item.get("transaction_count", "?")
    dbt = item.get("debit_total", "?")
    crd = item.get("credit_total", "?")
    ob = item.get("opening_balance", "?")
    cb = item.get("closing_balance", "?")
    print(f"  {pdf:<40} txns={n} debit={dbt} credit={crd} OB={ob} CB={cb}")
