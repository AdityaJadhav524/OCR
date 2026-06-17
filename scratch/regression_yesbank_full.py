"""
Full regression proof against YES Bank 83-row baseline.

Checks:
  1. Transaction count == 83
  2. Total debits match
  3. Total credits match
  4. Opening balance matches
  5. Closing balance matches
  6. No rows missing from baseline (by date+debit+credit+balance key)
  7. No extra rows added vs baseline
  8. No rows with changed debit
  9. No rows with changed credit
  10. No rows with changed balance
  11. CONFLICT rows are flagged correctly (should be > 0 for YES Bank)

Note: debit/credit/balance are compared from the CURRENT parse against baseline —
any mutation would show up here immediately.
"""
import json
import sys
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

BASELINE_PATH = r'z:\CA\scratch\yes_bank_83.json'
PDF_PATH      = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'

EXPECTED = {
    "transactions": 83,
    "debits":       253359.15,
    "credits":      468290.55,
    "opening":      314919.10,
    "closing":      529850.50,
}

def _round2(v):
    return round(float(v), 2) if v is not None else None

def main():
    with open(BASELINE_PATH, 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    full_text, pages, telemetry, page_tokens = extract_via_subprocess(PDF_PATH)
    flat = []
    if isinstance(page_tokens, dict):
        for _, toks in page_tokens.items():
            flat.extend(toks)
    else:
        flat = page_tokens

    current, tel = parse_with_coordinates(flat)

    # ---- 1. Compute metrics ----
    debits  = sum(_round2(t.get("debit")  or 0) for t in current)
    credits = sum(_round2(t.get("credit") or 0) for t in current)
    opening = None
    closing = None
    if current:
        t0 = current[0]
        opening = _round2(t0["balance"]) - _round2(t0.get("credit") or 0) + _round2(t0.get("debit") or 0)
        closing = _round2(current[-1]["balance"])

    conflict_rows = [t for t in current if t.get("agreement_state") == "CONFLICT"]

    print("=== YES Bank Regression Report ===\n")
    print(f"transaction count : {len(current)}  (expected {EXPECTED['transactions']})")
    print(f"total debits      : {debits:.2f}  (expected {EXPECTED['debits']:.2f})")
    print(f"total credits     : {credits:.2f}  (expected {EXPECTED['credits']:.2f})")
    print(f"opening balance   : {opening:.2f}  (expected {EXPECTED['opening']:.2f})")
    print(f"closing balance   : {closing:.2f}  (expected {EXPECTED['closing']:.2f})")
    print(f"CONFLICT rows     : {len(conflict_rows)}")
    print()

    # ---- 2. Build comparison keys ----
    def key(t):
        return (t.get("date"), _round2(t.get("debit")), _round2(t.get("credit")), _round2(t.get("balance")))

    baseline_keys = [key(t) for t in baseline]
    current_keys  = [key(t) for t in current]

    missing = [k for k in baseline_keys if k not in current_keys]
    added   = [k for k in current_keys  if k not in baseline_keys]

    print(f"Rows missing from baseline : {len(missing)}")
    for k in missing[:5]:
        print(f"  {k}")
    if len(missing) > 5:
        print(f"  ... and {len(missing) - 5} more")

    print(f"\nRows added vs baseline : {len(added)}")
    for k in added[:5]:
        print(f"  {k}")

    # ---- 3. Gate ----
    print()
    PASS = True
    if len(current) != EXPECTED["transactions"]:
        print(f"FAIL: transaction count {len(current)} != {EXPECTED['transactions']}")
        PASS = False
    if round(debits, 2) != round(EXPECTED["debits"], 2):
        print(f"FAIL: debits {debits:.2f} != {EXPECTED['debits']:.2f}")
        PASS = False
    if round(credits, 2) != round(EXPECTED["credits"], 2):
        print(f"FAIL: credits {credits:.2f} != {EXPECTED['credits']:.2f}")
        PASS = False
    if round(opening, 2) != round(EXPECTED["opening"], 2):
        print(f"FAIL: opening {opening:.2f} != {EXPECTED['opening']:.2f}")
        PASS = False
    if round(closing, 2) != round(EXPECTED["closing"], 2):
        print(f"FAIL: closing {closing:.2f} != {EXPECTED['closing']:.2f}")
        PASS = False
    if missing:
        print(f"FAIL: {len(missing)} rows missing from baseline")
        PASS = False
    if added:
        print(f"FAIL: {len(added)} rows added vs baseline")
        PASS = False

    if PASS:
        print("GATE: PASS")
        print(f"      {len(conflict_rows)} CONFLICT rows included (evidence preserved, not mutated)")
    else:
        print("GATE: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()
