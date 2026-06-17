"""
Row Fragmentation Diagnostic

For every transaction block where narration is None:
  - Show ALL tokens in the block with their x, y, text
  - Show which tokens were claimed as date/debit/credit/balance
  - Show how many tokens were left for narration (should be > 0 if narration exists)

This proves: is the bug row fragmentation (tokens never arrive together)
             or narration zone clipping (tokens arrive but are discarded)?
"""
import sys, requests
sys.path.insert(0, "z:/CA")

from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import (
    _prove_date, _prove_balance, _prove_amount, _in_zone
)

r = requests.get("http://localhost:8000/api/debug/cache")
data = r.json()

# Find the session with tokens
session_tokens = None
session_id     = None
for sid, s in data.items():
    toks = s.get("tokens", [])
    if len(toks) > 100:
        session_tokens = toks
        session_id     = sid
        v1_count = s.get("real_benchmark", {}).get("v1_count", "?")
        v2_count = s.get("real_benchmark", {}).get("v2_count", "?")
        break

if not session_tokens:
    print("No session with tokens found. Upload a PDF first.")
    sys.exit(1)

print(f"Session: {session_id}  tokens={len(session_tokens)}  V1={v1_count} V2={v2_count}")

rows  = detect_rows(session_tokens)
zones, headers = detect_columns(rows)
blocks = detect_transaction_blocks(rows, date_x_bounds=zones["date_zone"])

print(f"Detected {len(blocks)} blocks")
print(f"Zones: {zones}")
print()

date_zone    = zones.get("date_zone")
debit_zone   = zones.get("debit_zone")
credit_zone  = zones.get("credit_zone")
balance_zone = zones.get("balance_zone")

null_narr_blocks  = []
has_narr_blocks   = []
token_count_dist  = []

for block_idx, block in enumerate(blocks):
    # Flatten all tokens in the block
    all_toks = []
    for row in block:
        for tok in row.get("tokens", []):
            text = tok.get("text", "").strip()
            if text:
                all_toks.append(tok)

    # Run Pass 1: claim structural tokens
    date = bal = debit = credit = None
    claimed = set()

    for i, tok in enumerate(all_toks):
        if date is None and date_zone:
            d = _prove_date(tok, date_zone)
            if d:
                date = d; claimed.add(i); continue
        if balance_zone:
            b = _prove_balance(tok, balance_zone)
            if b is not None:
                bal = b; claimed.add(i); continue
        if debit_zone:
            v = _prove_amount(tok, debit_zone)
            if v is not None:
                debit = v; claimed.add(i); continue
        if credit_zone:
            v = _prove_amount(tok, credit_zone)
            if v is not None:
                credit = v; claimed.add(i); continue

    narr_toks = [all_toks[i] for i in range(len(all_toks)) if i not in claimed]
    narr_text  = " ".join(t["text"].strip() for t in sorted(narr_toks, key=lambda t: t.get("x0", 0))
                          if not __import__("re").fullmatch(r"[\d,\.]+", t["text"].strip()))

    token_count_dist.append(len(all_toks))

    info = {
        "block": block_idx,
        "total_tokens": len(all_toks),
        "date": date, "debit": debit, "credit": credit, "balance": bal,
        "narr_token_count": len(narr_toks),
        "narr_text": narr_text.strip() or None,
        "all_toks": all_toks,
        "claimed": claimed,
    }

    if not narr_text.strip() and date and (debit or credit) and bal:
        null_narr_blocks.append(info)
    elif date and (debit or credit) and bal:
        has_narr_blocks.append(info)

print(f"Accepted blocks with narration:    {len(has_narr_blocks)}")
print(f"Accepted blocks WITHOUT narration: {len(null_narr_blocks)}")
print()

# Token count distribution for null-narration blocks
null_counts = [b["total_tokens"] for b in null_narr_blocks]
has_counts  = [b["total_tokens"] for b in has_narr_blocks]
print(f"Token counts (null narration blocks): min={min(null_counts) if null_counts else 0}  "
      f"max={max(null_counts) if null_counts else 0}  "
      f"avg={round(sum(null_counts)/len(null_counts),1) if null_counts else 0}")
print(f"Token counts (with narration blocks): min={min(has_counts) if has_counts else 0}  "
      f"max={max(has_counts) if has_counts else 0}  "
      f"avg={round(sum(has_counts)/len(has_counts),1) if has_counts else 0}")
print()

print("=" * 70)
print("NULL NARRATION BLOCKS — Full Token Dump")
print("=" * 70)

for info in null_narr_blocks[:15]:
    b = info["block"]
    print(f"\n  Block[{b}]  date={info['date']}  cr={info['credit']}  dr={info['debit']}  bal={info['balance']}")
    print(f"  total_tokens={info['total_tokens']}  narr_tokens={info['narr_token_count']}")
    print(f"  All tokens:")
    for i, tok in enumerate(info["all_toks"]):
        role = "DATE" if i in {j for j in info["claimed"] if info["date"] and _prove_date(tok, date_zone)} else \
               "BAL"  if i in info["claimed"] and balance_zone and _prove_balance(tok, balance_zone) is not None else \
               "DR"   if i in info["claimed"] and debit_zone   and _prove_amount(tok, debit_zone)   is not None else \
               "CR"   if i in info["claimed"] and credit_zone  and _prove_amount(tok, credit_zone)  is not None else \
               "CLAIMED" if i in info["claimed"] else \
               "NARR"
        y = tok.get("y0", tok.get("yc", "?"))
        print(f"    [{role:7}] x={tok.get('x0',0):6.1f}  y={y}  text={tok.get('text','')!r}")
