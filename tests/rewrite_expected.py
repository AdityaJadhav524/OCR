import json
import os

with open("z:/CA/tests/expected.json", "r") as f:
    old_data = json.load(f)

for pdf_name, data in old_data.items():
    transactions = data["transactions"]
    debit_total = sum(t.get("debit") or 0.0 for t in transactions)
    credit_total = sum(t.get("credit") or 0.0 for t in transactions)
    closing_balance = transactions[-1]["balance"] if transactions else 0.0

    new_data = {
        "transaction_count": len(transactions),
        "debit_total": debit_total,
        "credit_total": credit_total,
        "closing_balance": closing_balance,
        "transactions": transactions
    }

    base_name = os.path.splitext(pdf_name)[0]
    # We know it's BOI
    out_path = f"z:/CA/tests/BOI/{base_name}.expected.json"
    with open(out_path, "w") as f_out:
        json.dump(new_data, f_out, indent=2)
    print(f"Wrote {out_path}")

os.remove("z:/CA/tests/expected.json")
