import json

with open("tests/audit_reports/boi_digital_token_dump.json") as f:
    d = json.load(f)

print("=== PASSING HEADER CANDIDATES ===")
for c in d["header_candidates"]:
    if c["window_result"]["passes_3_conditions"]:
        print(f"  Anchor row {c['anchor_row']}: {c['anchor_text'][:100]}")
        print(f"    date={c['window_result']['found_date']} bal={c['window_result']['found_balance']} amt={c['window_result']['found_amount']}")

print("\n=== FIRST 5 FAILED CANDIDATES ===")
failed = [c for c in d["header_candidates"] if not c["window_result"]["passes_3_conditions"]]
for c in failed[:5]:
    print(f"  Row {c['anchor_row']}: date={c['window_result']['found_date']} bal={c['window_result']['found_balance']} amt={c['window_result']['found_amount']} | {c['anchor_text'][:80]}")

print("\n=== FINAL HEADER TOKENS (first 10) ===")
for t in d["final_header_tokens"][:10]:
    print(f"  x0={t['x0']:.1f} text={t['text']}")
