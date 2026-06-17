import requests, json

r = requests.get('http://localhost:8000/api/debug/cache')
data = r.json()

for sid, s in data.items():
    rb = s.get('real_benchmark', {})
    v2_count = rb.get('v2_count', 'N/A')
    v1_count = rb.get('v1_count', 'N/A')
    bank     = s.get('bank_detection', {}).get('bank', '?')
    doc_type = s.get('document_type', '?')
    diff     = rb.get('diff_rows', 'N/A')
    print(f"{sid}  bank={bank}  type={doc_type}  V1={v1_count}  V2={v2_count}  diff={diff}")

    v2_txns = rb.get('v2_output', [])
    blanks  = [t for t in v2_txns if t.get('source_statement_blank') or t.get('root_cause') == 'source_statement_blank']
    if blanks:
        print(f"  -> {len(blanks)} source_statement_blank rows in V2")
        for b in blanks[:5]:
            print(f"     {b.get('date')}  cr={b.get('credit')}  dr={b.get('debit')}  bal={b.get('balance')}")

    # Also check V1 output for comparison
    v1_txns = rb.get('v1_output', [])
    v1_blanks = [t for t in v1_txns if t.get('source_statement_blank') or t.get('root_cause') == 'source_statement_blank']
    if v1_blanks:
        print(f"  -> {len(v1_blanks)} source_statement_blank rows in V1")
