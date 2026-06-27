"""
Benchmark Script: Validate Structural Token Protection
------------------------------------------------------
Runs the full extraction pipeline (routing -> protection -> suppression -> parsing)
on the specified benchmark PDFs and reports the Before/After matrix.
"""

import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ocr.adapters.ocr_subprocess import extract_via_subprocess
from core.detection.bank_detector import classify_document_llm
from core.layout.structural_token_protection import protect_table_header_tokens
from core.detection.header_suppression import suppress_headers_and_footers
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.parsers.credit_card_parser import parse_credit_card_transactions

TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "validation_lab", "backend", "temp")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "audit_reports", "protection_benchmark.json")

# The required benchmarks
BENCHMARKS = [
    ("BOI Digital", "JOB_20260618_121804_8C99_BOI_SAVINGS_DIGITAL.pdf", "1170AKSH"),
    ("BOI Scanned", "JOB_20260618_121808_497C_BOI_SAVINGS_SCANNED.pdf",  None),
    ("YES Bank",    "JOB_20260618_122213_4B2B_YESBANK_SAVINGS_DIGITAL.pdf", None),
    ("HDFC",        "JOB_20260618_115001_5E18_HDFC_SAVINGS_SCANNED.pdf",    None),
    ("ICICI CC",    "JOB_20260618_102941_061C_ICICI_1.pdf",                 None)
]

# Baseline known rows before protection was added
BASELINE_ROWS = {
    "BOI Digital": 0,
    "BOI Scanned": 259,
    "YES Bank": 83,
    "HDFC": 110,
    "ICICI CC": 32  # Known prior baseline for ICICI
}

def run_benchmark():
    results = []

    print(f"{'PDF':<20} | {'Before':<8} | {'After':<8} | {'Change':<10} | {'Protected Tokens'}")
    print("-" * 80)

    for label, filename, password in BENCHMARKS:
        pdf_path = os.path.join(TEMP_DIR, filename)
        if not os.path.exists(pdf_path):
            print(f"{label:<20} | FILE NOT FOUND")
            continue

        try:
            # Pipeline: Route & Extract via cached subprocess
            full_text, pages, merge_stats, page_tokens = extract_via_subprocess(pdf_path, password=password)
            
            # Pipeline: Classify
            identity = classify_document_llm(pages)
            bank_name = identity.get("institution_name", "Unknown")
            doc_family = identity.get("document_family", "BANK_STATEMENT")

            # Pipeline: Protect
            telemetry = {}
            page_tokens = protect_table_header_tokens(page_tokens, telemetry)
            protected_count = telemetry.get("protected_token_count", 0)
            
            protected_words = []
            for ev in telemetry.get("protection_events", []):
                protected_words.extend(ev.get("matched_keywords", []))
                
            # Pipeline: Suppress
            page_tokens = suppress_headers_and_footers(page_tokens)

            # Pipeline: Parse
            if doc_family == "CREDIT_CARD":
                txns, _ = parse_credit_card_transactions(page_tokens)
            else:
                txns, _ = parse_with_coordinates(page_tokens, bank=bank_name, identity=identity)

            extracted_rows = len(txns)
            before_rows = BASELINE_ROWS.get(label, 0)
            
            if before_rows == 0 and extracted_rows > 0:
                change = "Expected"
            elif before_rows == extracted_rows:
                change = "0"
            else:
                change = f"ERR: {extracted_rows - before_rows}"
                
            prot_str = f"{protected_count} tkns: {list(set(protected_words))}" if protected_count > 0 else "None"
            
            print(f"{label:<20} | {before_rows:<8} | {extracted_rows:<8} | {change:<10} | {prot_str}")
            
            results.append({
                "label": label,
                "before_rows": before_rows,
                "after_rows": extracted_rows,
                "change": change,
                "protected_token_count": protected_count,
                "protection_events": telemetry.get("protection_events", [])
            })

        except Exception as e:
            print(f"{label:<20} | ERROR: {e}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    run_benchmark()
