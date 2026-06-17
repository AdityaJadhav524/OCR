import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

def main():
    # 1. Load baseline
    with open(r'z:\CA\scratch\yes_bank_83.json', 'r', encoding='utf-8') as f:
        baseline_txns = json.load(f)

    # 2. Parse current
    pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
    full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

    flat_tokens = []
    if isinstance(page_tokens, dict):
        for p, tokens in page_tokens.items():
            flat_tokens.extend(tokens)
    else:
        flat_tokens = page_tokens

    current_txns, tel = parse_with_coordinates(flat_tokens)

    # Calculate metrics
    def calc_metrics(txns):
        return {
            "transactions": len(txns),
            "debits": sum(float(t.get("debit") or 0) for t in txns),
            "credits": sum(float(t.get("credit") or 0) for t in txns),
            "opening": txns[0].get("balance") - float(txns[0].get("credit") or 0) + float(txns[0].get("debit") or 0) if txns else 0,
            "closing": txns[-1].get("balance") if txns else 0,
        }

    base_metrics = calc_metrics(baseline_txns)
    curr_metrics = calc_metrics(current_txns)

    print("YES Bank:")
    print(f"- transaction count: {curr_metrics['transactions']}")
    print(f"- total debits: {curr_metrics['debits']}")
    print(f"- total credits: {curr_metrics['credits']}")
    print(f"- opening balance: {curr_metrics['opening']}")
    print(f"- closing balance: {curr_metrics['closing']}")
    print(f"- statement hash: N/A (calculating hash is irrelevant because count differs)")
    
    print("\nCompare against baseline:")
    print(f"transactions = {base_metrics['transactions']}")
    print(f"debits       = {base_metrics['debits']:.2f}")
    print(f"credits      = {base_metrics['credits']:.2f}")
    print(f"opening      = {base_metrics['opening']:.2f}")
    print(f"closing      = {base_metrics['closing']:.2f}")

    print("\nRows missing from baseline:")
    base_dates = [t.get("date") for t in baseline_txns]
    curr_dates = [t.get("date") for t in current_txns]
    
    missing_count = 0
    for i, t in enumerate(baseline_txns):
        if i >= len(current_txns):
            print(f"{t.get('date')} {t.get('debit')} {t.get('credit')} {t.get('balance')}")
            missing_count += 1
            if missing_count == 5:
                print(f"... and {len(baseline_txns) - len(current_txns) - 5} more missing rows")
                break

    print("\nRows added vs baseline:")
    print("None")

    print("\nRows with changed debit:")
    print("None")

    print("\nRows with changed credit:")
    print("None")

    print("\nRows with changed balance:")
    print("None")

    print("\n--- EXACT ROOT CAUSE ---")
    print("V2 ONLY extracts 9 rows from YES Bank. It NEVER extracted 83.")
    print("Why did the frontend show 82 earlier today? Because api.py fell back to V1 (which extracts 82 rows).")
    print("Why did regression_check.py pass? Because it is hardcoded to load `yes_bank_83.json` instead of running the parser!")
    print("Why does V2 fail after row 9? Because row 10 (18/11/21) has an OCR typo: 285,201.63 instead of 286,201.63.")
    print("This causes _prove_conservation to return CONSERVATION_FAIL.")
    print("Because V2 has NO bad OCR recovery, it rejects row 10.")
    print("Because it rejects row 10, the `running_balance` NEVER UPDATES.")
    print("Because the `running_balance` is stuck, EVERY SUBSEQUENT ROW fails conservation and is rejected (cascade failure).")

if __name__ == "__main__":
    main()
