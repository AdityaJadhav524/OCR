"""
scripts/header_truth_audit.py
─────────────────────────────
Runs header detection across every PDF in a directory.
Prints header_keyword_score, transaction_like_score, account_info_score,
and HEADER_SELECTION_SUSPECT warning for each bank without running the full pipeline.

Usage:
    python scripts/header_truth_audit.py tests/pdfs
"""
import os
import sys
import glob

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from core.extractors.document_router import route_document
from core.layout.structural_token_protection import protect_table_header_tokens
from core.detection.header_suppression import suppress_headers_and_footers
from core.layout.row_detector import detect_rows
from core.layout.column_detector import detect_columns

PASSWORD = "1170AKSH"

def audit_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    print(f"\n{'='*65}")
    print(f"  {filename}")
    print(f"{'='*65}")

    try:
        full_text, pages, _telemetry, page_tokens = route_document(pdf_path, password=PASSWORD)
    except Exception as e:
        print(f"  [EXTRACTION FAILED] {e}")
        return None

    print(f"  Tokens (raw)        : {len(page_tokens)}")

    try:
        protected = protect_table_header_tokens(page_tokens, {})
    except Exception:
        protected = page_tokens

    try:
        filtered = suppress_headers_and_footers(protected)
    except Exception:
        filtered = page_tokens

    print(f"  Tokens (filtered)   : {len(filtered)}")

    rows = detect_rows(filtered)
    print(f"  Rows detected       : {len(rows)}")

    tel = {}
    zones, headers = detect_columns(rows, telemetry=tel)

    audit = tel.get("header_audit")
    if not audit:
        print("  [NO HEADER FOUND]")
        return {"bank": filename, "header": None, "warning": "NO_HEADER"}

    print(f"  Selected Header     : {audit['selected_header_text'][:80]!r}")
    print(f"  header_keyword_score: {audit['header_keyword_score']}")
    print(f"  transaction_like    : {audit['transaction_like_score']}")
    print(f"  account_info        : {audit['account_info_score']}")
    print(f"  Warning             : {audit['warning']}")
    print(f"  Zones               : {list(zones.keys())}")

    return {
        "bank": filename,
        "header": audit["selected_header_text"][:80],
        "header_keyword_score": audit["header_keyword_score"],
        "transaction_like_score": audit["transaction_like_score"],
        "account_info_score": audit["account_info_score"],
        "warning": audit["warning"],
        "zones": list(zones.keys()),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/header_truth_audit.py <pdf_directory>")
        sys.exit(1)

    pdf_dir = sys.argv[1]
    pdfs = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}")
        sys.exit(1)

    print(f"\nHeader Truth Audit — {len(pdfs)} PDFs in {pdf_dir}")

    results = []
    for pdf in pdfs:
        r = audit_pdf(pdf)
        if r:
            results.append(r)

    # Summary table
    print(f"\n\n{'='*65}")
    print("HEADER TRUTH AUDIT SUMMARY")
    print(f"{'='*65}")
    print(f"{'Bank':<35} {'KW':>4} {'TXN':>4} {'ACCT':>5} {'Warning':<28}")
    print(f"{'-'*35} {'-'*4} {'-'*4} {'-'*5} {'-'*28}")
    suspects = 0
    for r in results:
        kw   = r.get("header_keyword_score", "?")
        txn  = r.get("transaction_like_score", "?")
        acct = r.get("account_info_score", "?")
        warn = r.get("warning", "NO_HEADER")
        if warn != "OK":
            suspects += 1
        flag = " <--" if warn != "OK" else ""
        print(f"  {r['bank']:<33} {kw:>4} {txn:>4} {acct:>5} {warn:<28}{flag}")

    print(f"\n{suspects}/{len(results)} banks have HEADER_SELECTION_SUSPECT or NO_HEADER")
    print("\nDone.")


if __name__ == "__main__":
    main()
