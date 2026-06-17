"""
regression_baseline.py  —  STRENGTHENED

Captures the extraction baseline for every test PDF.
Now includes:
  - aggregate totals (transaction count, debit total, credit total, opening, closing, rejected)
  - per-transaction fingerprint hash: sha256(date|narration[:50]|debit|credit|balance|conservation_state)
  - full ordered list of (date, debit, credit, balance) for per-field comparison

Run this BEFORE any implementation changes.
Output: scratch/regression_baseline.json

Gate rule: if ANY field in ANY transaction changes, the check script exits 1.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, r"z:\CA")

from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import _parse_float

# Map of name -> token file path
# Token files must contain raw PDF tokens (list of dicts with x0, y0, x1, y1, text, page).
TOKEN_FILES = {
    "sbi_4txn": r"z:\CA\scratch\indusind_tokens.json",
    # "yes_bank": r"z:\CA\scratch\yes_bank_tokens.json",  # add when raw tokens are saved
}

# Map of name -> already-parsed transaction list (for statements where raw tokens aren't saved)
PARSED_FILES = {
    "yes_bank_83": r"z:\CA\scratch\yes_bank_83.json",
}


def _txn_hash(t: dict) -> str:
    """SHA-256 fingerprint of core fields (date|debit|credit|balance|conservation_state)."""
    date    = str(t.get("date") or "")
    narr    = str(t.get("narration") or "")[:50]
    debit   = str(round(_parse_float(t.get("debit"))   or 0.0, 2))
    credit  = str(round(_parse_float(t.get("credit"))  or 0.0, 2))
    balance = str(round(_parse_float(t.get("balance")) or 0.0, 2))
    cons    = str(t.get("conservation_state") or "")
    raw = "|".join([date, narr, debit, credit, balance, cons])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _row_hash(t: dict) -> str:
    """Minimal SHA-256 per row: date|debit|credit|balance only.
    Stored individually so a single changed row is immediately pinpointed."""
    date    = str(t.get("date") or "")
    debit   = str(round(_parse_float(t.get("debit"))   or 0.0, 2))
    credit  = str(round(_parse_float(t.get("credit"))  or 0.0, 2))
    balance = str(round(_parse_float(t.get("balance")) or 0.0, 2))
    raw = "|".join([date, debit, credit, balance])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _statement_hash(txns: list) -> str:
    """SHA-256 of the entire ordered transaction sequence (uses full _txn_hash)."""
    combined = "||".join(_txn_hash(t) for t in txns)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def capture_from_tokens(name: str, token_file: str) -> dict:
    with open(token_file, "r", encoding="utf-8") as f:
        tokens = json.load(f)
    txns, tel = parse_with_coordinates(tokens)
    return _build_record(name, txns, rejected_count=len(tel.get("reject_log", [])))


def capture_from_parsed(name: str, parsed_file: str) -> dict:
    with open(parsed_file, "r", encoding="utf-8") as f:
        txns = json.load(f)
    return _build_record(name, txns, rejected_count=None)


def _build_record(name: str, txns: list, rejected_count) -> dict:
    debit_total  = round(sum(_parse_float(t.get("debit"))  or 0.0 for t in txns), 2)
    credit_total = round(sum(_parse_float(t.get("credit")) or 0.0 for t in txns), 2)

    opening_balance = None
    closing_balance = None
    if txns:
        first = txns[0]
        b = _parse_float(first.get("balance")) or 0.0
        c = _parse_float(first.get("credit"))  or 0.0
        d = _parse_float(first.get("debit"))   or 0.0
        opening_balance = round(b - c + d, 2)
        closing_balance = round(_parse_float(txns[-1].get("balance")) or 0.0, 2)

    # Per-transaction ordered fingerprints
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
        "opening_balance":   opening_balance,
        "closing_balance":   closing_balance,
        "rejected_count":    rejected_count,
        "statement_hash":    _statement_hash(txns),
        "txn_hashes":        [_row_hash(t) for t in txns],
        "transactions":      tx_fingerprints,
    }


def main():
    baselines = []

    for name, path in TOKEN_FILES.items():
        if not os.path.exists(path):
            print(f"SKIP {name}: {path} not found")
            continue
        print(f"Capturing baseline (from tokens): {name}")
        b = capture_from_tokens(name, path)
        baselines.append(b)
        print(f"  count={b['transaction_count']}  debits={b['debit_total']}  credits={b['credit_total']}")
        print(f"  opening={b['opening_balance']}  closing={b['closing_balance']}  rejected={b['rejected_count']}")
        print(f"  statement_hash={b['statement_hash'][:16]}...")

    for name, path in PARSED_FILES.items():
        if not os.path.exists(path):
            print(f"SKIP {name}: {path} not found")
            continue
        print(f"Capturing baseline (from parsed): {name}")
        b = capture_from_parsed(name, path)
        baselines.append(b)
        print(f"  count={b['transaction_count']}  debits={b['debit_total']}  credits={b['credit_total']}")
        print(f"  opening={b['opening_balance']}  closing={b['closing_balance']}")
        print(f"  statement_hash={b['statement_hash'][:16]}...")

    out_path = r"z:\CA\scratch\regression_baseline.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(baselines, f, indent=2)
    print(f"\nBaseline written to: {out_path}")
    print(f"Total PDFs locked: {len(baselines)}")


if __name__ == "__main__":
    main()
