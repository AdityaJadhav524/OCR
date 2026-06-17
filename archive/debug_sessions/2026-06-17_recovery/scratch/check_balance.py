import json
data = json.load(open('Z:\\CA\\scratch\\yes_bank_83.json'))
for i in [9, 18, 31, 43]:
    print(f"txn {i} balance: {data[i].get('balance')}")
