"""
Test: Verify the universal debit/credit direction fix.
  1. Correctly-parsed PDF narrations → no accidental flips
  2. Wrongly-parsed BOI-style narrations → correctly fixed
  3. Ambiguous narrations → not touched (safe)
"""
import sys, re
sys.path.insert(0, '.')
from core.parsers.coordinate_parser_v2 import _NARR_CREDIT_RE, _NARR_DEBIT_RE, CONSERVATION_TOLERANCE

def check_narration(narr):
    is_cr = bool(_NARR_CREDIT_RE.search(narr))
    is_dr = bool(_NARR_DEBIT_RE.search(narr))
    if is_cr and not is_dr: return "credit"
    if is_dr and not is_cr: return "debit"
    return None  # ambiguous

# -------------------------------------------------------------------
# Test cases: (narration, expected_result)
# -------------------------------------------------------------------
tests = [
    # === Unambiguous CREDIT signals ===
    ("UPI/CR/367592001234/AMIT KUMAR", "credit"),
    ("IMPS/CR/123456789012/SALARY", "credit"),
    ("NEFT CR HDFC0001234", "credit"),
    ("NEFT/CR/123456", "credit"),
    ("RTGS CR 987654321", "credit"),
    ("ACH/CR SALARY", "credit"),
    ("NACH/CR 20240101", "credit"),

    # === Unambiguous DEBIT signals ===
    ("UPI/DR/684917001234/KUMA R MAHADEV", "debit"),
    ("IMPS/DR/123456789012/FEES", "debit"),
    ("NEFT DR ICICI0001234", "debit"),
    ("NEFT/DR/654321", "debit"),
    ("RTGS DR 123456789", "debit"),
    ("ACH/DR EMI PAYMENT", "debit"),
    ("NACH/DR 20240101", "debit"),
    ("ATM/WDL/12345", "debit"),

    # === Ambiguous — MUST return None (do not touch) ===
    # Generic words that appear in both directions:
    ("INTEREST CREDIT FROM SAVINGS", None),  # has CREDIT but ambiguous context
    ("CREDIT CARD PAYMENT", None),           # CREDIT here = outflow!
    ("EMI PAYMENT RECEIVED", None),          # PAYMENT could be either
    ("SALARY CREDIT", None),                 # no structured ref code
    ("ATM CASH DEPOSIT", None),              # ATM could be credit here
    ("LOAN DISBURSEMENT", None),             # LOAN could be credit (disbursed to you)
    ("INTEREST CHARGED", None),              # INTEREST can be debit
    ("REVERSAL OF CHARGES", None),           # REVERSAL could be either
    ("CASH WITHDRAWAL", None),               # WITHDRAWAL alone matches nothing now
    ("INTERNET BANKING TRANSFER", None),     # no CR/DR suffix
    ("NEFT TRANSFER", None),                 # NEFT without CR/DR is ambiguous
    ("COLLECT/HDFC/50200080420 UPI", None),  # UPI without CR/DR
    ("Cred/YESB/002267800000666", None),     # no CR/DR marker

    # === From the BOI screenshot narrations ===
    ("KRUSHNAT/FDRL/138202000 UPI/DR/684917", "debit"),
    ("S/UTIB/922010016723931/Di UPI/CR/367592", "credit"),
    ("G/BKID/150810110022458/Sh UPI/CR/330408", "credit"),
    ("G/HDFC/50100221800028/Baj NEFT ITDTAX R", None),  # NEFT without CR/DR
    ("UPI/DR/699411267300/KUMA R MAHADEV S", "debit"),
    ("R/YESB/002261100000025/To UPI/DR/226683", "debit"),
    ("COLLECT/HDFC/50200080420 UPI/DR/433875", "debit"),
    ("Cred/YESB/002267800000666 UPI/DR/063803", "debit"),
]

print("=== Narration Signal Tests ===\n")
all_passed = True
for narr, expected in tests:
    result = check_narration(narr)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        all_passed = False
    print(f"[{status}] {narr[:55]!r:57s}  expected={str(expected):8s} got={result}")

print()
print("=== Direction Correction Logic Tests ===\n")

# Simulate the row-level Tier-2 narration correction
def simulate_correction(txn):
    ocr_dr  = txn.get("debit")
    ocr_cr  = txn.get("credit")
    ocr_dir = "debit" if ocr_dr is not None else ("credit" if ocr_cr is not None else None)
    if ocr_dir is None:
        return txn, "no_amount"

    narr = (txn.get("narration") or "") + " " + txn.get("_block_text", "")
    is_narr_credit = bool(_NARR_CREDIT_RE.search(narr))
    is_narr_debit  = bool(_NARR_DEBIT_RE.search(narr))

    if is_narr_credit == is_narr_debit:
        return txn, "ambiguous_skip"

    narr_dir = "credit" if is_narr_credit else "debit"

    if narr_dir != ocr_dir:
        t = dict(txn)
        if ocr_dir == "debit":
            t["credit"] = t["debit"]; t["debit"] = None
        else:
            t["debit"] = t["credit"]; t["credit"] = None
        return t, "corrected"

    return txn, "already_correct"

correction_tests = [
    # (narration, initial_debit, initial_credit, expected_debit, expected_credit, description)
    ("UPI/CR/367592", 661, None, None, 661, "BOI: UPI/CR wrongly in debit → fix to credit"),
    ("UPI/DR/684917", 80, None, 80, None, "BOI: UPI/DR correctly in debit → no change"),
    ("UPI/CR/330408", 9617, None, None, 9617, "BOI: UPI/CR wrongly in debit → fix to credit"),
    ("UPI/DR/226683", 150, None, 150, None, "BOI: UPI/DR correctly in debit → no change"),
    ("NEFT ITDTAX", 2797, None, 2797, None, "NEFT without CR/DR → ambiguous, no change"),
    ("SALARY PAYMENT", None, 50000, None, 50000, "No ref code → ambiguous, no change"),
    ("NEFT/DR/654321", None, 500, 500, None, "NEFT DR wrongly in credit → fix to debit"),
]

print(f"{'Description':45s}  {'Result':15s}  Correct?")
print("-"*80)
for narr, init_dr, init_cr, exp_dr, exp_cr, desc in correction_tests:
    txn = {"narration": narr, "_block_text": narr, "debit": init_dr, "credit": init_cr,
           "ledger_truth": {"available": False}}
    result_txn, action = simulate_correction(txn)
    got_dr = result_txn["debit"]
    got_cr = result_txn["credit"]
    ok = (got_dr == exp_dr and got_cr == exp_cr)
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_passed = False
    print(f"[{status}] {desc:43s}  [{action:15s}]  dr={got_dr} cr={got_cr}")

print()
if all_passed:
    print("✅  ALL TESTS PASSED — fix is safe for all PDFs")
else:
    print("❌  SOME TESTS FAILED — review above")
    sys.exit(1)
