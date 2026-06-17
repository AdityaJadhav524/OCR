"""
Inspect V1 vs V2 narration comparison for the current session.
Show which rows V1 marks as source_statement_blank and what V2 produces for same rows.
"""
import sys, requests
sys.path.insert(0, "z:/CA")

r = requests.get("http://localhost:8000/api/debug/cache")
data = r.json()

for sid, s in data.items():
    rb = s.get("real_benchmark", {})
    v1 = rb.get("v1_output", [])
    v2 = rb.get("v2_output", [])
    if not v1 or not v2:
        continue

    print(f"Session: {sid}  V1={len(v1)}  V2={len(v2)}")

    # V1 blank rows
    v1_blank = [t for t in v1 if t.get("source_statement_blank") or t.get("root_cause") == "source_statement_blank"]
    print(f"V1 source_statement_blank: {len(v1_blank)}")

    # V2 blank rows
    v2_blank = [t for t in v2 if not t.get("narration")]
    print(f"V2 narration=null: {len(v2_blank)}")

    # Side-by-side for V1 blank rows
    print()
    print("  V1 blank rows  |  V2 narration for same date+amount:")
    print("  " + "-" * 80)

    for t1 in v1_blank[:20]:
        # Match by date + balance
        date = t1.get("date", "")
        bal  = t1.get("balance")
        cr   = t1.get("credit")
        dr   = t1.get("debit")
        match = next((t for t in v2
                      if t.get("date") == date
                      and abs((t.get("balance") or 0) - (bal or 0)) < 1.0), None)
        v2_narr = match.get("narration") if match else "NO_MATCH"
        v2_blank_flag = "(blank)" if match and not match.get("narration") else ""
        print(f"  V1: {date}  cr={cr}  dr={dr}  bal={bal}")
        print(f"  V2: narration={repr(v2_narr)[:60]}  {v2_blank_flag}")
        print()

    break
