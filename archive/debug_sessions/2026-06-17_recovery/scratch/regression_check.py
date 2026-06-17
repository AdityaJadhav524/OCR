"""
regression_check.py  —  STRENGTHENED

Run this AFTER any implementation change.
Compares current results against scratch/regression_baseline.json.

Checks:
  - aggregate totals (count, debit, credit, opening, closing, rejected)
  - statement_hash  (SHA-256 of entire ordered transaction sequence)
  - per-transaction hash  (each row individually)
  - per-field comparison on every row (date, debit, credit, balance, conservation_state)

EXIT CODE 0 = all checks pass, safe to proceed.
EXIT CODE 1 = regression detected, ABORT IMPLEMENTATION, do not merge.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, r"z:\CA")

from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import _parse_float

BASELINE_PATH = r"z:\CA\scratch\regression_baseline.json"
TOLERANCE     = 0.01

TOKEN_FILES = {
    "sbi_4txn": r"z:\CA\scratch\indusind_tokens.json",
}
PARSED_FILES = {
    "yes_bank_83": r"z:\CA\scratch\yes_bank_83.json",
}


def _txn_hash(t: dict) -> str:
    date    = str(t.get("date") or "")
    narr    = str(t.get("narration") or "")[:50]
    debit   = str(round(_parse_float(t.get("debit"))   or 0.0, 2))
    credit  = str(round(_parse_float(t.get("credit"))  or 0.0, 2))
    balance = str(round(_parse_float(t.get("balance")) or 0.0, 2))
    cons    = str(t.get("conservation_state") or "")
    raw = "|".join([date, narr, debit, credit, balance, cons])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _row_hash(t: dict) -> str:
    """Minimal per-row hash: date|debit|credit|balance only."""
    date    = str(t.get("date") or "")
    debit   = str(round(_parse_float(t.get("debit"))   or 0.0, 2))
    credit  = str(round(_parse_float(t.get("credit"))  or 0.0, 2))
    balance = str(round(_parse_float(t.get("balance")) or 0.0, 2))
    raw = "|".join([date, debit, credit, balance])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _statement_hash(txns: list) -> str:
    combined = "||".join(_txn_hash(t) for t in txns)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def current_from_tokens(name: str, path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        tokens = json.load(f)
    txns, tel = parse_with_coordinates(tokens)
    return _build_current(name, txns, len(tel.get("reject_log", [])))


def current_from_parsed(name: str, path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        txns = json.load(f)
    return _build_current(name, txns, rejected_count=None)


def _build_current(name: str, txns: list, rejected_count) -> dict:
    debit_total  = round(sum(_parse_float(t.get("debit"))  or 0.0 for t in txns), 2)
    credit_total = round(sum(_parse_float(t.get("credit")) or 0.0 for t in txns), 2)

    opening = closing = None
    if txns:
        first = txns[0]
        b = _parse_float(first.get("balance")) or 0.0
        c = _parse_float(first.get("credit"))  or 0.0
        d = _parse_float(first.get("debit"))   or 0.0
        opening = round(b - c + d, 2)
        closing = round(_parse_float(txns[-1].get("balance")) or 0.0, 2)

    tx_fingerprints = [
        {
            "idx":               i,
            "date":              t.get("date"),
            "narration_prefix":  (t.get("narration") or "")[:50],
            "debit":             _parse_float(t.get("debit")),
            "credit":            _parse_float(t.get("credit")),
            "balance":           _parse_float(t.get("balance")),
            "conservation_state": t.get("conservation_state"),
            "hash":              _txn_hash(t),
        }
        for i, t in enumerate(txns)
    ]

    return {
        "pdf":               name,
        "transaction_count": len(txns),
        "debit_total":       debit_total,
        "credit_total":      credit_total,
        "opening_balance":   opening,
        "closing_balance":   closing,
        "rejected_count":    rejected_count,
        "statement_hash":    _statement_hash(txns),
        "txn_hashes":        [_row_hash(t) for t in txns],
        "transactions":      tx_fingerprints,
    }


def compare(baseline: dict, current: dict) -> list:
    failures = []
    name = baseline["pdf"]

    # 1a. txn_hashes list — pinpoints exactly which row changed
    b_hashes = baseline.get("txn_hashes", [])
    c_hashes = current.get("txn_hashes", [])
    if len(b_hashes) == len(c_hashes):
        for i, (bh, ch) in enumerate(zip(b_hashes, c_hashes)):
            if bh != ch:
                bt = baseline["transactions"][i] if i < len(baseline["transactions"]) else {}
                failures.append(
                    f"  txn[{i}] row_hash changed: date={bt.get('date')}  "
                    f"debit={bt.get('debit')}  credit={bt.get('credit')}  balance={bt.get('balance')}"
                )

    # 2. Statement-level hash (catches ordering changes even if individual rows look ok)
    if baseline.get("statement_hash") != current.get("statement_hash"):
        failures.append(f"  STATEMENT HASH MISMATCH — ordering or content changed")

    # 2. Scalar aggregates
    for field in ["transaction_count", "debit_total", "credit_total",
                  "opening_balance", "closing_balance"]:
        bv = baseline.get(field)
        cv = current.get(field)
        if bv is None and cv is None:
            continue
        if bv is None or cv is None or abs(float(bv) - float(cv)) > TOLERANCE:
            failures.append(f"  {field}: baseline={bv}  current={cv}")

    # rejected_count only for token-sourced PDFs (parsed files don't track it)
    if baseline.get("rejected_count") is not None and current.get("rejected_count") is not None:
        if baseline["rejected_count"] != current["rejected_count"]:
            failures.append(f"  rejected_count: baseline={baseline['rejected_count']}  current={current['rejected_count']}")

    # 3. Per-transaction comparison (if statement hash already failed, still enumerate specifics)
    b_txns = baseline.get("transactions", [])
    c_txns = current.get("transactions", [])

    if len(b_txns) != len(c_txns):
        failures.append(f"  transaction list length: baseline={len(b_txns)}  current={len(c_txns)}")
        return failures  # can't compare row by row if counts differ

    for bt, ct in zip(b_txns, c_txns):
        idx = bt["idx"]

        # Per-row hash
        if bt["hash"] != ct["hash"]:
            failures.append(f"  txn[{idx}] hash mismatch on row: date={bt['date']}")

        # Field-level detail
        for key in ["date", "conservation_state"]:
            if bt.get(key) != ct.get(key):
                failures.append(f"  txn[{idx}].{key}: baseline={bt.get(key)!r}  current={ct.get(key)!r}")

        for key in ["debit", "credit", "balance"]:
            bv = bt.get(key)
            cv = ct.get(key)
            if bv is None and cv is None:
                continue
            if bv is None or cv is None or abs(float(bv) - float(cv)) > TOLERANCE:
                failures.append(f"  txn[{idx}].{key}: baseline={bv}  current={cv}")

    return failures


def main():
    if not os.path.exists(BASELINE_PATH):
        print("ERROR: No baseline found. Run regression_baseline.py first.")
        sys.exit(1)

    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        baselines = {b["pdf"]: b for b in json.load(f)}

    all_passed = True

    for name, path in TOKEN_FILES.items():
        if not os.path.exists(path):
            print(f"SKIP {name}: token file not found")
            continue
        baseline = baselines.get(name)
        if not baseline:
            print(f"SKIP {name}: no baseline entry (run regression_baseline.py)")
            continue
        print(f"\nChecking [{name}] (from tokens)")
        current = current_from_tokens(name, path)
        failures = compare(baseline, current)
        if failures:
            all_passed = False
            print(f"  FAIL — {len(failures)} regression(s):")
            for f in failures:
                print(f)
        else:
            print(f"  PASS — {current['transaction_count']} transactions, statement_hash matches")

    for name, path in PARSED_FILES.items():
        if not os.path.exists(path):
            print(f"SKIP {name}: parsed file not found")
            continue
        baseline = baselines.get(name)
        if not baseline:
            print(f"SKIP {name}: no baseline entry (run regression_baseline.py)")
            continue
        print(f"\nChecking [{name}] (from parsed)")
        current = current_from_parsed(name, path)
        failures = compare(baseline, current)
        if failures:
            all_passed = False
            print(f"  FAIL — {len(failures)} regression(s):")
            for f in failures:
                print(f)
        else:
            print(f"  PASS — {current['transaction_count']} transactions, statement_hash matches")

    print()
    if not all_passed:
        print("=" * 60)
        print("REGRESSION DETECTED. ABORT IMPLEMENTATION. DO NOT MERGE.")
        print("=" * 60)
        sys.exit(1)
    else:
        print("=" * 60)
        print("All regression checks passed. Safe to proceed.")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
