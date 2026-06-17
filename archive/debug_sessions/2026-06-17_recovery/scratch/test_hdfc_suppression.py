import os
import sys
import json

_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _WORKSPACE_ROOT)

from core.adapters.ocr_subprocess import extract_via_subprocess
from core.detection.header_suppression import suppress_headers_and_footers
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth

PDF_PATH = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"

print("1. Loading OCR tokens...")
full_text, pages_text, telemetry, tokens = extract_via_subprocess(PDF_PATH)
token_count_before = len(tokens)

print("2. Running Suppression...")
filtered_tokens = suppress_headers_and_footers(tokens)
token_count_after = len(filtered_tokens)

removed = [t for t in tokens if t not in filtered_tokens]
print(f"Token count BEFORE: {token_count_before}")
print(f"Token count AFTER : {token_count_after}")
print(f"Removed tokens    : {len(removed)}")

# Save removed tokens for inspection
with open(r"Z:\CA\investigations\HDFC\removed_tokens.json", "w", encoding="utf-8") as f:
    json.dump(removed, f, indent=2)

# Check specifically for the POCKIT footer strings in the removed set
target_strings = [
    "HDFC BANK LIMITED",
    "*Closing balance includes funds earmarked",
    "Registered Offce AddressHDFC Bank HouseSenapan",
    "State accou ns statement"
]

print("\n--- Checking specific leak targets in REMOVED tokens ---")
for target in target_strings:
    found = any(target.lower() in t.get("text", "").lower() for t in removed)
    print(f"Removed '{target[:20]}...'? : {found}")

print("\n--- Checking specific leak targets in REMAINING tokens ---")
for target in target_strings:
    found = any(target.lower() in t.get("text", "").lower() for t in filtered_tokens)
    print(f"Remains '{target[:20]}...'? : {found}")

print("\n3. Running V2 Parser on Filtered Tokens...")
txns_after, tel_after = parse_with_coordinates(filtered_tokens)
txns_after = annotate_ledger_truth(txns_after)

# Evaluate header leaks after
header_leaks = 0
for t in txns_after:
    if t.get("contamination_detected"):
        header_leaks += 1

print(f"\nHeader Leaks AFTER suppression: {header_leaks}")

with open(r"Z:\CA\investigations\HDFC\txns_after_suppression.json", "w", encoding="utf-8") as f:
    json.dump(txns_after, f, indent=2)
