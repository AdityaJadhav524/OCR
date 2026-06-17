"""
Check the 07.09/22 row - it appears accepted but shows as 'missing' from baseline.
The baseline key is ('07.09/22', None, 40000.0, 529850.5)
V2 accepted it. Check what key V2 produces for it.
"""
import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

PDF_PATH = r'Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
BASELINE_PATH = r'z:\CA\scratch\yes_bank_83.json'

with open(BASELINE_PATH, 'r', encoding='utf-8') as f:
    baseline = json.load(f)

full_text, pages, telemetry, page_tokens = extract_via_subprocess(PDF_PATH)
flat = []
if isinstance(page_tokens, dict):
    for _, toks in page_tokens.items():
        flat.extend(toks)
else:
    flat = page_tokens

current, tel = parse_with_coordinates(flat)

# Find baseline rows for 07.09/22 and 07/02/22
print("=== Baseline rows for these dates ===")
for t in baseline:
    if "07" in str(t.get("date","")) and ("02/22" in str(t.get("date","")) or "09/22" in str(t.get("date",""))):
        print(f"  date={t.get('date')!r}  dr={t.get('debit')}  cr={t.get('credit')}  bal={t.get('balance')}")

print("\n=== Current V2 rows for these dates ===")
for t in current:
    if "07" in str(t.get("date","")) and ("02" in str(t.get("date","")) or "09" in str(t.get("date",""))):
        print(f"  date={t.get('date')!r}  dr={t.get('debit')}  cr={t.get('credit')}  bal={t.get('balance')}  state={t.get('conservation_state')}  agree={t.get('agreement_state')}")

# Check 07.09/22 exact
print("\n=== V2 rows containing 529850 balance ===")
for t in current:
    if abs((t.get('balance') or 0) - 529850.5) < 1:
        print(f"  date={t.get('date')!r}  dr={t.get('debit')}  cr={t.get('credit')}  bal={t.get('balance')}  state={t.get('conservation_state')}")

print("\n=== Last 5 accepted rows ===")
for t in current[-5:]:
    print(f"  date={t.get('date')!r}  dr={t.get('debit')}  cr={t.get('credit')}  bal={t.get('balance')}")
