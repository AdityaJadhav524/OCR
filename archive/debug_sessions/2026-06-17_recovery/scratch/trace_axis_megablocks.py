import sys, os, re
sys.path.append('c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = 'c:/Users/adity/Downloads/CA/validation_lab/backend/temp/JOB_20260617_144436_EF6E_axis.pdf'
_, pages, _, page_tokens = route_document(pdf_path)
identity = classify_document_llm(pages)

rows = detect_rows(page_tokens)
zones, _ = detect_columns(rows, identity=identity)

v2_txns, v2_tel = parse_with_coordinates(page_tokens, bank=identity.get('institution_name'), identity=identity)
rejects = v2_tel.get('reject_log', [])

report = "# AXIS MEGA-BLOCK FORENSIC PROOF\n\n"

def in_zone(x, zone):
    if not zone: return False
    return zone[0] - 5 <= x <= zone[1] + 5

amount_re = re.compile(r'[\d,]*\d[\d,]*\.\d{2}')

total_merged_losses = 0

for idx, r in enumerate(rejects):
    reason = r.get('reject_reason')
    if reason != 'both_debit_and_credit':
        continue
        
    evidence_id = r.get('_evidence_id', f'rej_{idx}')
    source_tokens = r.get('_source_tokens', [])
    
    # 1. Dates found (everything in date zone)
    dates_found = [t.get("text") for t in source_tokens if in_zone(t.get("x0", -99), zones.get("date_zone"))]
    
    # 2. Debits found (amounts in debit zone)
    debits_found = [t.get("text") for t in source_tokens if in_zone(t.get("x0", -99), zones.get("debit_zone")) and amount_re.search(t.get("text", ""))]
    
    # 3. Credits found (amounts in credit zone)
    credits_found = [t.get("text") for t in source_tokens if in_zone(t.get("x0", -99), zones.get("credit_zone")) and amount_re.search(t.get("text", ""))]
    
    # 4. Estimated real txns = total amounts found (since every txn has exactly 1 amount)
    # Wait, some could be balances that spilled over? Let's just use max(dates, debits+credits)
    # Actually, a transaction is an amount movement, so Debits + Credits is a very accurate proxy for transactions.
    amounts_count = len(debits_found) + len(credits_found)
    dates_count = len(dates_found)
    
    # Let's count standalone amounts
    est_txns = amounts_count
    total_merged_losses += est_txns
    
    report += f"### BLOCK_ID: {evidence_id}\n"
    report += f"**Dates:**\n{dates_found}\n\n"
    report += f"**Debits:**\n{debits_found}\n\n"
    report += f"**Credits:**\n{credits_found}\n\n"
    report += f"**Estimated real transactions:** {est_txns}\n\n"

accepted_count = len(v2_txns)
expected_total = accepted_count + total_merged_losses

report += "---\n\n"
report += f"**TOTAL_LOST_TXNS_FROM_MERGES**: {total_merged_losses}\n"
report += f"**Accepted + Lost_From_Merges**: {accepted_count} + {total_merged_losses} = **{expected_total}**\n"

with open('C:/Users/adity/.gemini/antigravity-ide/brain/a91c24b3-da82-413c-9098-5cc87be0fb55/AXIS_MEGA_BLOCK_PROOF.md', 'w') as f:
    f.write(report)

print("Proof generated.")
