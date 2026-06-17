"""
Verify source_statement_blank classification against PDF coordinates.
For each blank-narration row, check: does the narration zone actually contain tokens?
"""
import requests, json, sys
sys.path.insert(0, "z:/CA")

r = requests.get('http://localhost:8000/api/debug/cache')
data = r.json()

# Find most complete session
best = None
best_sid = None
for sid, s in data.items():
    rb = s.get('real_benchmark', {})
    if rb.get('v2_count') and rb.get('v1_count'):
        if best is None or rb.get('diff_rows', 99) <= (best.get('real_benchmark',{}).get('diff_rows',99)):
            best = s
            best_sid = sid

if not best:
    print("No session with benchmark data found")
    sys.exit(1)

rb      = best['real_benchmark']
v1_txns = rb['v1_output']
v2_txns = rb['v2_output']
tokens  = best.get('tokens', [])

print(f"Session: {best_sid}")
print(f"V1: {len(v1_txns)} txns | V2: {len(v2_txns)} txns | diff: {rb.get('diff_rows')}")
print(f"Tokens available: {len(tokens)}")
print()

# --- V1 vs V2 Financial Invariants ---
def sums(txns, label):
    debit  = sum(t.get('debit')  or 0 for t in txns)
    credit = sum(t.get('credit') or 0 for t in txns)
    close  = txns[-1].get('balance') if txns else None
    blanks = sum(1 for t in txns if not t.get('narration'))
    src_blank = sum(1 for t in txns if t.get('source_statement_blank') or t.get('root_cause') == 'source_statement_blank')
    bad = 0
    for i, t in enumerate(txns[1:], 1):
        pb = txns[i-1].get('balance') or 0
        cb = t.get('balance') or 0
        amt = (t.get('credit') or 0) - (t.get('debit') or 0)
        if abs((cb - pb) - amt) > 1.0:
            bad += 1
    print(f"{label}")
    print(f"  Transactions      : {len(txns)}")
    print(f"  Debit Sum         : {round(debit,2)}")
    print(f"  Credit Sum        : {round(credit,2)}")
    print(f"  Closing Balance   : {close}")
    print(f"  Impossible Rows   : {bad}")
    print(f"  Missing Narration : {blanks}")
    print(f"  Source Blank Rows : {src_blank}")
    print()

sums(v1_txns, "V1 (text parser)")
sums(v2_txns, "V2 (coordinate parser)")

# --- Rows only in V2 (the 3 extra) ---
def key(t):
    return (str(t.get('date','')), str(t.get('debit') or t.get('credit') or ''), str(t.get('balance','')))

v1_keys = set(key(t) for t in v1_txns)
v2_keys = set(key(t) for t in v2_txns)
only_v2 = [t for t in v2_txns if key(t) not in v1_keys]
only_v1 = [t for t in v1_txns if key(t) not in v2_keys]

print("=== Rows ONLY in V2 (V2 found, V1 missed) ===")
for t in only_v2:
    print(f"  {t.get('date')}  cr={t.get('credit')}  dr={t.get('debit')}  bal={t.get('balance')}  nar={str(t.get('narration',''))[:60]}")

print()
print("=== Rows ONLY in V1 (V1 found, V2 missed) ===")
for t in only_v1:
    print(f"  {t.get('date')}  cr={t.get('credit')}  dr={t.get('debit')}  bal={t.get('balance')}  nar={str(t.get('narration',''))[:60]}")

# --- Verify blank rows against tokens ---
if tokens:
    print()
    print("=== Verifying source_statement_blank rows against coordinate tokens ===")

    # Get narration zone from V2 telemetry (stored in v2_txns[0] if present)
    # Fall back to typical SBI narration zone
    narr_x0, narr_x1 = 100.0, 395.0  # fallback

    blank_v2 = [t for t in v2_txns if t.get('source_statement_blank') or t.get('root_cause') == 'source_statement_blank']
    print(f"Checking {len(blank_v2)} blank-narration rows from V2...")

    for txn in blank_v2[:10]:
        date  = txn.get('date', '')
        bal   = txn.get('balance')
        page  = txn.get('source_page', None)

        # Find tokens near this transaction's balance value
        bal_str = str(bal).replace('.00', '').replace('.0', '') if bal else ''
        matching_tokens = [
            tok for tok in tokens
            if bal_str and bal_str in str(tok.get('text', ''))
            and (page is None or tok.get('page') == page)
        ]

        if matching_tokens:
            # Find y-center of this row
            yc = sum(tok.get('yc', (tok.get('y0',0)+tok.get('y1',0))/2) for tok in matching_tokens) / len(matching_tokens)
            # Find tokens in narration zone at this y
            narr_tokens = [
                tok for tok in tokens
                if abs((tok.get('yc', (tok.get('y0',0)+tok.get('y1',0))/2)) - yc) < 8
                and narr_x0 <= tok.get('x0', 0) <= narr_x1
            ]
            narr_text = ' '.join(tok.get('text','') for tok in narr_tokens).strip()
            verdict = "TRULY BLANK" if not narr_text else f"MISSED TEXT: '{narr_text}'"
        else:
            verdict = "Balance token not found in token list"

        print(f"  {date}  cr={txn.get('credit')}  dr={txn.get('debit')}  bal={bal}  -> {verdict}")
else:
    print()
    print("NOTE: No tokens in session cache. Cannot verify blanks against coordinates.")
    print("Tokens are not stored in the session after processing.")
    print("To verify: use the narration_zone_token_count field in V2 output if available.")
    print()
    # Show blank V2 rows anyway
    blank_v2 = [t for t in v2_txns if t.get('source_statement_blank') or t.get('root_cause') == 'source_statement_blank']
    print(f"V2 blank rows ({len(blank_v2)}):")
    for t in blank_v2:
        print(f"  {t.get('date')}  cr={t.get('credit')}  dr={t.get('debit')}  bal={t.get('balance')}  "
              f"src_tokens={t.get('source_tokens', 'N/A')}  bbox={t.get('source_bbox', 'N/A')}")
