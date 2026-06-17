import sys, os, re
sys.path.append('c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_rows
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = 'c:/Users/adity/Downloads/CA/validation_lab/backend/temp/JOB_20260617_144436_EF6E_axis.pdf'
_, pages, _, page_tokens = route_document(pdf_path)
identity = classify_document_llm(pages)
rows = detect_rows(page_tokens)
zones, _ = detect_columns(rows, identity=identity)

v2_txns, v2_tel = parse_with_coordinates(page_tokens, bank=identity.get('institution_name'), identity=identity)
rejects = v2_tel.get('reject_log', [])

report = "# AXIS FULL LOSS ACCOUNTING AUDIT\n\n"

def in_zone(x, zone):
    if not zone: return False
    return zone[0] - 5 <= x <= zone[1] + 5

amount_re = re.compile(r'[\d,]*\d[\d,]*\.\d{2}')
loose_date_re = re.compile(r'[\dOod]{1,2}[\-\.\|][a-zA-Z\d]{2,3}[\-\.\|]?\d{2,4}')

accounting = {
    "both_debit_and_credit": {"blocks": 0, "txns_lost": 0, "samples": []},
    "no_balance": {"blocks": 0, "txns_lost": 0, "samples": []},
    "no_date": {"blocks": 0, "txns_lost": 0, "samples": []},
    "no_debit_or_credit": {"blocks": 0, "txns_lost": 0, "samples": []},
    "other": {"blocks": 0, "txns_lost": 0, "samples": []}
}

for r in rejects:
    reason = r.get('reject_reason')
    if reason not in accounting:
        reason = "other"
        
    source_tokens = r.get('_source_tokens', [])
    
    dates_found = [t.get("text") for t in source_tokens if loose_date_re.search(t.get("text", "")) or "2021" in t.get("text", "") or "11-2021" in t.get("text", "")]
    debits_found = [t.get("text") for t in source_tokens if in_zone(t.get("x0", -99), zones.get("debit_zone")) and amount_re.search(t.get("text", ""))]
    credits_found = [t.get("text") for t in source_tokens if in_zone(t.get("x0", -99), zones.get("credit_zone")) and amount_re.search(t.get("text", ""))]
    
    # Logic: a logical txn has either a debit or credit. 
    # If it has neither, but has a date, it might just be a header or garbage.
    # We will estimate txns by taking the max of valid dates or (debits + credits)
    est_txns = max(len(dates_found), len(debits_found) + len(credits_found))
    if est_txns == 0:
        est_txns = 1 # At least 1 block was rejected, it might have been a txn that lost all structural data
        
    accounting[reason]["blocks"] += 1
    accounting[reason]["txns_lost"] += est_txns
    
    if len(accounting[reason]["samples"]) < 3:
        accounting[reason]["samples"].append({
            "dates": dates_found,
            "debits": debits_found,
            "credits": credits_found,
            "tokens": [t.get("text") for t in source_tokens][:15],
            "est_txns": est_txns
        })

# Check for silent merges in ACCEPTED transactions!
silent_merges_txns_lost = 0
silent_samples = []

for txn in v2_txns:
    source_tokens = txn.get("_source_tokens", [])
    dates_found = [t.get("text") for t in source_tokens if loose_date_re.search(t.get("text", "")) or "2021" in t.get("text", "") or "11-2021" in t.get("text", "")]
    debits_found = [t.get("text") for t in source_tokens if in_zone(t.get("x0", -99), zones.get("debit_zone")) and amount_re.search(t.get("text", ""))]
    credits_found = [t.get("text") for t in source_tokens if in_zone(t.get("x0", -99), zones.get("credit_zone")) and amount_re.search(t.get("text", ""))]
    
    est_txns = max(len(dates_found), len(debits_found) + len(credits_found))
    if est_txns > 1:
        silent_merges_txns_lost += (est_txns - 1) # We accepted 1, but there were actually est_txns inside
        if len(silent_samples) < 3:
            silent_samples.append({
                "dates": dates_found,
                "debits": debits_found,
                "credits": credits_found,
                "tokens": [t.get("text") for t in source_tokens][:15],
                "est_txns": est_txns
            })

report += "## Rejection Category Audit\n\n"

for reason, data in accounting.items():
    if data["blocks"] == 0: continue
    report += f"### {reason}\n"
    report += f"- **Blocks:** {data['blocks']}\n"
    report += f"- **Estimated Txns Lost:** {data['txns_lost']}\n"
    report += "- **Samples:**\n"
    for s in data["samples"]:
        report += f"  - Dates: {s['dates']} | Debits: {s['debits']} | Credits: {s['credits']} -> Est: {s['est_txns']}\n"
        report += f"  - Tokens: {s['tokens']}...\n"
    report += "\n"

report += f"### silent_merges (Accepted blocks hiding multiple txns)\n"
report += f"- **Estimated Txns Lost:** {silent_merges_txns_lost}\n"
report += "- **Samples:**\n"
for s in silent_samples:
    report += f"  - Dates: {s['dates']} | Debits: {s['debits']} | Credits: {s['credits']} -> Est: {s['est_txns']}\n"
    report += f"  - Tokens: {s['tokens']}...\n"
report += "\n"

report += "## Final Accounting Equation\n\n"
report += f"- **Accepted Transactions:** {len(v2_txns)}\n"
report += f"- **Lost from both_debit_and_credit:** {accounting['both_debit_and_credit']['txns_lost']}\n"
report += f"- **Lost from no_balance:** {accounting['no_balance']['txns_lost']}\n"
report += f"- **Lost from no_date:** {accounting['no_date']['txns_lost']}\n"
report += f"- **Lost from no_debit_or_credit:** {accounting['no_debit_or_credit']['txns_lost']}\n"
report += f"- **Lost from other:** {accounting['other']['txns_lost']}\n"
report += f"- **Lost from silent_merges:** {silent_merges_txns_lost}\n"
report += "---\n"
projected_total = len(v2_txns) + sum(d["txns_lost"] for d in accounting.values()) + silent_merges_txns_lost
report += f"**PROJECTED TOTAL = {projected_total}**\n\n"

with open('C:/Users/adity/.gemini/antigravity-ide/brain/a91c24b3-da82-413c-9098-5cc87be0fb55/AXIS_FULL_LOSS_ACCOUNTING.md', 'w') as f:
    f.write(report)

print(f"Audit completed. Projected total: {projected_total}")
