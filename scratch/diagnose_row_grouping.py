import json
import os
import sys

_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _WORKSPACE_ROOT)

from core.adapters.ocr_subprocess import extract_via_subprocess
from core.layout.row_detector import detect_rows, detect_transaction_blocks

PDF_PATH = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"

print("1. Extracting OCR tokens...")
full_text, pages_text, telemetry, tokens = extract_via_subprocess(PDF_PATH)

print("2. Running row_detector.detect_rows...")
rows = detect_rows(tokens)

# The leak we care about is on Page 5 or 9 (page index depends on what leaked).
# The leaked text contains: "t is that ou secord with the Bank as at the day of requesting"
# Let's find the exact row that contains this text.

target_row = None
for row in rows:
    row_text = " ".join(t.get("text", "") for t in row.get("tokens", []))
    if "secord with the Bank" in row_text or "t branchGSTN27AAACH2702HZ0" in row_text:
        target_row = row
        print(f"\n--- FOUND LEAKED FOOTER ROW (Page {row.get('page')}) ---")
        print(f"Row Text: {row_text}")
        print(f"Row Y bounds: {row.get('y0')} -> {row.get('y1')}")
        
        # Check transaction evidence
        import re
        _DATE_RE = re.compile(
            r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|\d{1,2}[\s\-\.][A-Za-z]{3,9}[\s\-\.]\d{2,4})\b',
            re.IGNORECASE
        )
        has_date = bool(_DATE_RE.search(row_text))
        
        # Check for numbers that could be amounts (debit/credit/balance)
        amounts = [t.get("text") for t in row.get("tokens", []) if re.fullmatch(r'[\d,\.]+', t.get("text", "").strip())]
        
        print(f"Date present? : {has_date}")
        print(f"Amounts found? : {amounts}")
        
        print("\nRaw Tokens in Row:")
        for t in row.get("tokens", []):
            print(f"  - '{t.get('text')}' (x0={t.get('x0')}, y1={t.get('y1')})")
        print("-" * 50)

print("\nWhy did row_detector allow it?")
print("In core.layout.row_detector.detect_transaction_blocks:")
print("    if is_anchor:")
print("        if current_block:")
print("            blocks.append(current_block)")
print("        current_block = [row]")
print("    else:")
print("        if current_block:")
print("            current_block.append(row)   <--- HERE")
print("\nThe logic blindly appends ANY row that does not contain an anchor date to the last seen transaction block, without verifying if the row is actually a narration continuation row vs. a completely unrelated footer row.")
