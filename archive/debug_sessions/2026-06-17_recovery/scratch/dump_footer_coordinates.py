import os
import sys
import json

_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _WORKSPACE_ROOT)

from core.adapters.ocr_subprocess import extract_via_subprocess
from core.detection.header_suppression import suppress_headers_and_footers
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

PDF_PATH = r"Z:\CA\validation_lab\backend\temp\JOB_20260614_233121_48AC_Acct Statement_3644_14032026_13.08.12 1 (1)_page-0006.pdf"

print("1. Extracting OCR tokens...")
full_text, pages_text, telemetry, tokens = extract_via_subprocess(PDF_PATH)

# Determine page height proxy (max y1 per page)
page_heights = {}
for t in tokens:
    p = t.get("page", 0)
    if "y1" in t:
        if p not in page_heights or t["y1"] > page_heights[p]:
            page_heights[p] = t["y1"]

print("2. Running Suppression and Parsing...")
filtered_tokens = suppress_headers_and_footers(tokens)
txns_after, tel_after = parse_with_coordinates(filtered_tokens)

print("3. Analyzing Leaked Footer Coordinates...")
footer_vocab = ["statemen", "receipt", "address", "secord", "requestig", "statement", "carrectif", "correct", "tbranch", "gstn"]

leak_coordinates = []

for txn in txns_after:
    narration = str(txn.get("narration", "")).lower()
    # Check if this txn has the leaked footer
    if any(v in narration for v in footer_vocab):
        # Examine its source tokens
        source_tokens = txn.get("_source_tokens", [])
        for t in source_tokens:
            text = t.get("text", "").strip()
            text_lower = text.lower()
            if any(v in text_lower for v in footer_vocab) or len(text) > 20:
                if "upi" in text_lower or "pay" in text_lower:
                    if len(text) < 40:
                        continue
                p = t.get("page", 0)
                leak_coordinates.append({
                    "text": text,
                    "page": p,
                    "x0": t.get("x0"),
                    "y0": t.get("y0"),
                    "x1": t.get("x1"),
                    "y1": t.get("y1"),
                    "page_height": page_heights.get(p, 0)
                })

with open(r"Z:\CA\investigations\HDFC\footer_leak_coordinates.json", "w", encoding="utf-8") as f:
    json.dump(leak_coordinates, f, indent=2)

print(f"Dumped {len(leak_coordinates)} leaked footer tokens to investigations/HDFC/footer_leak_coordinates.json")
