import json
with open(r'z:\CA\scratch\indusind_tokens.json', 'r') as f:
    tokens = json.load(f)

# IndusInd check
cols = [{'type': 'date', 'x0': 81.0}, {'type': 'narration', 'x0': 529.0}, {'type': 'debit', 'x0': 962.0}, {'type': 'credit', 'x0': 1169.0}, {'type': 'balance', 'x0': 1385.0}]
zones = {}
for i in range(len(cols)):
    start_x = 0.0 if i == 0 else cols[i]['x0'] - 10
    end_x = cols[i+1]['x0'] - 10 if i < len(cols) - 1 else 9999.0
    zones[f"{cols[i]['type']}_zone"] = [start_x, end_x]

print('IndusInd zones:', zones)
print('3000.00 at x0=1164.0 ->', 'Debit' if zones['debit_zone'][0] <= 1164.0 <= zones['debit_zone'][1] else 'Credit' if zones['credit_zone'][0] <= 1164.0 <= zones['credit_zone'][1] else 'None')
