"""
V1 vs V2 Financial Invariants Comparison
Reads a session's real_benchmark export and prints the comparison table.

Usage:
  python compare_invariants.py <export.json>

Or pipe the exported JSON:
  python compare_invariants.py  (reads from stdin if no arg)
"""
import sys, os, json

sys.path.insert(0, "z:/CA")
from core.validators.financial_audit import run_financial_audit


def compute_invariants(txns, label):
    if not txns:
        return {"label": label, "count": 0, "debit_sum": 0, "credit_sum": 0,
                "closing_balance": None, "conservation_pass": False,
                "balance_graph_pass": False, "missing_narrations": 0,
                "source_blank_rows": 0, "impossible_rows": 0, "error": "empty"}

    debit_sum  = sum(t.get("debit")  or 0 for t in txns)
    credit_sum = sum(t.get("credit") or 0 for t in txns)
    closing    = txns[-1].get("balance")
    opening    = txns[0].get("balance") or 0

    # Conservation
    # Try to find opening from first txn's prior balance
    first = txns[0]
    if first.get("debit"):
        opening = (first.get("balance") or 0) + (first.get("debit") or 0)
    elif first.get("credit"):
        opening = (first.get("balance") or 0) - (first.get("credit") or 0)

    expected_close = opening + credit_sum - debit_sum
    conservation_pass = closing is not None and abs(expected_close - closing) < 1.0

    # Balance graph
    impossible_rows = 0
    for i, t in enumerate(txns[1:], 1):
        prev_bal = txns[i-1].get("balance") or 0
        cur_bal  = t.get("balance") or 0
        delta    = cur_bal - prev_bal
        amount   = (t.get("credit") or 0) - (t.get("debit") or 0)
        if abs(delta - amount) > 1.0:
            impossible_rows += 1

    balance_graph_pass = impossible_rows == 0

    # Narration / blank stats
    missing_narrations = sum(1 for t in txns if not t.get("narration"))
    source_blank_rows  = sum(1 for t in txns if t.get("source_statement_blank") or t.get("root_cause") == "source_statement_blank")

    return {
        "label":              label,
        "count":              len(txns),
        "debit_sum":          round(debit_sum, 2),
        "credit_sum":         round(credit_sum, 2),
        "closing_balance":    closing,
        "conservation_pass":  conservation_pass,
        "balance_graph_pass": balance_graph_pass,
        "missing_narrations": missing_narrations,
        "source_blank_rows":  source_blank_rows,
        "impossible_rows":    impossible_rows,
    }


def print_table(v1, v2):
    def flag(val): return "PASS" if val else "FAIL"
    def val(x):    return str(x) if x is not None else "?"

    rows = [
        ("Check",               "V1",                             "V2",                             "Winner"),
        ("Transaction Count",   val(v1["count"]),                 val(v2["count"]),                 "?" ),
        ("Debit Sum",           val(v1["debit_sum"]),             val(v2["debit_sum"]),             "?" ),
        ("Credit Sum",          val(v1["credit_sum"]),            val(v2["credit_sum"]),            "?" ),
        ("Closing Balance",     val(v1["closing_balance"]),       val(v2["closing_balance"]),       "?" ),
        ("Conservation",        flag(v1["conservation_pass"]),    flag(v2["conservation_pass"]),    "?" ),
        ("Balance Graph",       flag(v1["balance_graph_pass"]),   flag(v2["balance_graph_pass"]),   "?" ),
        ("Missing Narrations",  val(v1["missing_narrations"]),    val(v2["missing_narrations"]),    "?" ),
        ("Source Blank Rows",   val(v1["source_blank_rows"]),     val(v2["source_blank_rows"]),     "?" ),
        ("Impossible Rows",     val(v1["impossible_rows"]),       val(v2["impossible_rows"]),       "?" ),
    ]

    # Compute winners
    def winner_count(a, b):
        try: return "V2" if int(b) > int(a) else ("V1" if int(a) > int(b) else "TIE")
        except: return "?"

    def winner_lower(a, b):
        try: return "V2" if int(b) < int(a) else ("V1" if int(a) < int(b) else "TIE")
        except: return "?"

    def winner_flag(a, b):
        if a == b: return "TIE"
        return "V2" if b == "PASS" else "V1"

    rows[1]  = rows[1][:3] + (winner_count(v1["count"],             v2["count"]),)
    rows[2]  = rows[2][:3] + ("?",)   # debit sum: difference is informational
    rows[3]  = rows[3][:3] + ("?",)
    rows[4]  = rows[4][:3] + ("?",)
    rows[5]  = rows[5][:3] + (winner_flag(rows[5][1], rows[5][2]),)
    rows[6]  = rows[6][:3] + (winner_flag(rows[6][1], rows[6][2]),)
    rows[7]  = rows[7][:3] + (winner_lower(v1["missing_narrations"], v2["missing_narrations"]),)
    rows[8]  = rows[8][:3] + (winner_lower(v1["source_blank_rows"],  v2["source_blank_rows"]),)
    rows[9]  = rows[9][:3] + (winner_lower(v1["impossible_rows"],    v2["impossible_rows"]),)

    col_w = [24, 14, 14, 8]
    sep = "+" + "+".join("-" * (w + 2) for w in col_w) + "+"
    print(sep)
    for i, row in enumerate(rows):
        line = "| " + " | ".join(str(row[j]).ljust(col_w[j]) for j in range(4)) + " |"
        print(line)
        if i == 0:
            print(sep)
    print(sep)

    # Score
    v1_wins = sum(1 for r in rows[1:] if r[3] == "V1")
    v2_wins = sum(1 for r in rows[1:] if r[3] == "V2")
    ties    = sum(1 for r in rows[1:] if r[3] == "TIE")
    print(f"\n  V1 wins: {v1_wins}  |  V2 wins: {v2_wins}  |  Ties: {ties}")
    if v2_wins > v1_wins:
        print("  --> V2 is the better parser for this statement.")
    elif v1_wins > v2_wins:
        print("  --> V1 is the better parser for this statement.")
    else:
        print("  --> Draw — examine diff rows manually.")


def find_rows_only_in(a_txns, b_txns):
    """Return rows in a that have no match in b (by date+amount)."""
    def key(t):
        return (str(t.get("date", "")),
                str(t.get("debit") or t.get("credit") or ""),
                str(t.get("balance", "")))
    b_keys = set(key(t) for t in b_txns)
    return [t for t in a_txns if key(t) not in b_keys]


def main():
    if len(sys.argv) > 1:
        data = json.load(open(sys.argv[1], encoding="utf-8"))
    else:
        print("Reading JSON from stdin...")
        data = json.load(sys.stdin)

    # Handle both direct export and session cache format
    rb = None
    if isinstance(data, dict):
        # Try real_benchmark at top level
        if "real_benchmark" in data:
            rb = data["real_benchmark"]
        # Try stages/session format
        elif "stages" in data or "transactions" in data:
            # Direct V1 only export — run V2 is not available
            print("This is a direct V1 export (no real_benchmark). Re-upload with new backend.")
            txns = data.get("transactions", [])
            v1 = compute_invariants(txns, "V1")
            v2 = compute_invariants([], "V2 (not run)")
            print_table(v1, v2)
            return

    if rb is None:
        print("ERROR: Could not find real_benchmark in export. Upload with the new backend.")
        return

    v1_txns = rb.get("v1_output", [])
    v2_txns = rb.get("v2_output", [])

    v1 = compute_invariants(v1_txns, "V1 (text)")
    v2 = compute_invariants(v2_txns, "V2 (coord)")

    print(f"\n  Benchmark: {v1['count']} V1 txns vs {v2['count']} V2 txns  |  diff_rows={rb.get('diff_rows', '?')}")
    print(f"  V1 score={rb.get('v1_score', '?')}  V2 score={rb.get('v2_score', '?')}\n")
    print_table(v1, v2)

    # Diff rows
    only_v1 = find_rows_only_in(v1_txns, v2_txns)
    only_v2 = find_rows_only_in(v2_txns, v1_txns)

    if only_v1:
        print(f"\n  Rows in V1 only ({len(only_v1)}):")
        for t in only_v1[:10]:
            print(f"    {t.get('date')}  debit={t.get('debit')}  credit={t.get('credit')}  "
                  f"bal={t.get('balance')}  nar={str(t.get('narration',''))[:40]}")

    if only_v2:
        print(f"\n  Rows in V2 only ({len(only_v2)}):")
        for t in only_v2[:10]:
            print(f"    {t.get('date')}  debit={t.get('debit')}  credit={t.get('credit')}  "
                  f"bal={t.get('balance')}  nar={str(t.get('narration',''))[:40]}")

    print()


if __name__ == "__main__":
    main()
