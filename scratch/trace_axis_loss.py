import sys, os, json
sys.path.append('c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import parse_with_coordinates, _extract_block

pdf_path = 'c:/Users/adity/Downloads/CA/validation_lab/backend/temp/JOB_20260617_144436_EF6E_axis.pdf'
_, pages, _, page_tokens = route_document(pdf_path)
identity = classify_document_llm(pages)

# We can just call parse_with_coordinates and get the telemetry.
# To get Rows Detected and Blocks Detected, we can just run the inner functions.
rows = detect_rows(page_tokens)
zones, _ = detect_columns(rows, identity=identity)

page_to_rows = {}
for r in rows:
    p = r.get("page", 0)
    page_to_rows.setdefault(p, []).append(r)
    
blocks = []
for p in sorted(page_to_rows.keys()):
    page_blocks = detect_transaction_blocks(page_to_rows[p], date_x_bounds=zones["date_zone"])
    blocks.extend(page_blocks)

v2_txns, v2_tel = parse_with_coordinates(page_tokens, bank=identity.get('institution_name'), identity=identity)
rejects = v2_tel.get('reject_log', [])

report = "# AXIS FORENSIC TRACE\n\n"
report += f"**STAGE 1: OCR Tokens**\n{len(page_tokens)} tokens\n\n"
report += f"**STAGE 2: Rows Detected**\n{len(rows)} rows\n\n"
report += f"**STAGE 3: Transaction Blocks**\n{len(blocks)} blocks\n\n"
report += f"**STAGE 4: Candidate Transactions**\n{len(blocks)} candidates (1 block = 1 candidate)\n\n"
report += f"**STAGE 5: Accepted Transactions**\n{len(v2_txns)} accepted\n\n"
report += f"**STAGE 6: Rejected Transactions**\n{len(rejects)} rejected\n\n"

report += "## Rejection Breakdown\n\n"
for idx, r in enumerate(rejects):
    reason = r.get('reject_reason')
    evidence_id = r.get('_evidence_id', f'rej_{idx}')
    
    report += f"### BLOCK_ID: {evidence_id}\n"
    report += f"**REJECT_REASON**: {reason}\n"
    
    source_tokens = r.get('_source_tokens', [])
    if reason == 'both_debit_and_credit':
        report += "**Dump full block tokens**:\n"
        dump = [t.get('text', '') for t in source_tokens]
        report += f"```\n{dump}\n```\n\n"
    elif reason == 'no_balance':
        # Need to dump balance-zone tokens
        bal_zone = zones.get("balance_zone", [0, 0])
        report += f"**Dump balance-zone tokens** (zone {bal_zone}):\n"
        # Find tokens that fall into the balance zone
        dump = [t.get('text', '') for t in source_tokens if bal_zone[0] - 5 <= t.get('x0', -99) and t.get('x1', 99) <= bal_zone[1] + 5]
        report += f"```\n{dump}\n```\n\n"
    elif reason == 'no_date':
        date_zone = zones.get("date_zone", [0, 0])
        report += f"**Dump date-zone tokens** (zone {date_zone}):\n"
        dump = [t.get('text', '') for t in source_tokens if date_zone[0] - 5 <= t.get('x0', -99) and t.get('x1', 99) <= date_zone[1] + 5]
        report += f"```\n{dump}\n```\n\n"
    else:
        # no_debit_or_credit
        report += f"**Snippet**: {r.get('block_text_snippet')}\n\n"

with open('C:/Users/adity/.gemini/antigravity-ide/brain/a91c24b3-da82-413c-9098-5cc87be0fb55/AXIS_LOSS_REPORT.md', 'w') as f:
    f.write(report)

print("Report generated.")
