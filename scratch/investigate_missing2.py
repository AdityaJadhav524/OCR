"""
Investigate the two specific rows still missing from YES Bank after the CONFLICT fix.

Missing:
  07/02/22  None  25000.0  489850.5
  07.09/22  None  40000.0  529850.5

Check what the parser sees for those dates.
"""
import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

PDF_PATH = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'

full_text, pages, telemetry, page_tokens = extract_via_subprocess(PDF_PATH)
flat = []
if isinstance(page_tokens, dict):
    for _, toks in page_tokens.items():
        flat.extend(toks)
else:
    flat = page_tokens

current, tel = parse_with_coordinates(flat)
rejects = tel.get('reject_log', [])

TARGET_DATES = {"07/02/22", "07.09/22"}

print("=== Accepted rows near the missing dates ===")
for t in current:
    d = t.get("date", "")
    if "02/22" in d or "09/22" in d:
        print(f"  ACCEPTED  {d:20s}  dr={t.get('debit')}  cr={t.get('credit')}  bal={t.get('balance')}  state={t.get('conservation_state')}  agree={t.get('agreement_state')}")

print("\n=== Rejected rows near the missing dates ===")
for r in rejects:
    d = r.get("date", "")
    if "02/22" in str(d) or "09/22" in str(d) or d in TARGET_DATES:
        print(f"  REJECTED  {str(d):20s}  dr={r.get('debit')}  cr={r.get('credit')}  bal={r.get('balance')}  prev={r.get('prev_balance')}  reason={r.get('reject_reason')}")

print("\n=== All rejected row dates (last 10) ===")
for r in rejects[-10:]:
    print(f"  {r.get('date')}  dr={r.get('debit')}  cr={r.get('credit')}  bal={r.get('balance')}  reason={r.get('reject_reason')}")
