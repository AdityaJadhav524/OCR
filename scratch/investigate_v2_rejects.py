from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

pdf_path = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)

txns, tel = parse_with_coordinates(page_tokens)
print(f'Accepted: {len(txns)}')
print(f'Rejected: {len(tel.get("reject_log", []))}')

if tel.get("reject_log"):
    for rej in tel["reject_log"][:20]:
        print(f"Reject Reason: {rej.get('reject_reason')} - Date: {rej.get('date')} - Bal: {rej.get('balance')} - Dr: {rej.get('debit')}")
