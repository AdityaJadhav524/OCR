"""
scripts/corruption_audit.py
────────────────────────────
Classifies accepted transactions into:
    Financially Correct
    Financially Corrupted

Corruption types detected:
    BALANCE_AS_CREDIT  — credit value == balance value
    BALANCE_AS_DEBIT   — debit value == balance value
    DATE_AS_AMOUNT     — amount field parses as a date
    MULTIPLE_AMOUNTS   — both debit and credit non-zero
    LEDGER_FAIL        — conservation math doesn't close

Usage:
    python scripts/corruption_audit.py tests/pdfs
    python scripts/corruption_audit.py tests/pdfs --json
"""
import os
import sys
import re
import glob
import json
from collections import defaultdict

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from core.extractors.document_router import route_document
from core.layout.structural_token_protection import protect_table_header_tokens
from core.detection.header_suppression import suppress_headers_and_footers
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import _parse_float

PASSWORD = "1170AKSH"
LEDGER_TOLERANCE = 1.50

_DATE_RE = re.compile(
    r'^\s*('
    r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|'
    r'\d{2,4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|'
    r'\d{1,2}[\s\-][A-Za-z]{3,9}[\s\-]\d{2,4}'
    r')\s*$',
    re.IGNORECASE
)


def _is_date_like(val):
    """True if a numeric value when formatted as string looks like a date."""
    if val is None:
        return False
    # Check if the OCR text of a value matches a date pattern
    text = str(val)
    return bool(_DATE_RE.match(text))


def detect_corruptions(txns, zones):
    """
    Given a list of accepted transactions, detect financial corruption types.
    Returns list of (txn_index, corruption_type, evidence).
    """
    corruptions = []
    prev_balance = None
    balance_zone = zones.get("balance_zone", [0, 9999])
    credit_zone  = zones.get("credit_zone",  [0, 9999])
    debit_zone   = zones.get("debit_zone",   [0, 9999])

    for i, txn in enumerate(txns):
        credit  = txn.get("credit")
        debit   = txn.get("debit")
        balance = txn.get("balance")
        raw     = txn.get("raw_extraction", {})

        # BALANCE_AS_CREDIT: credit value equals balance value (same token misassigned)
        if credit is not None and balance is not None and abs(credit - balance) < 0.01:
            corruptions.append((i, "BALANCE_AS_CREDIT", {
                "credit": credit,
                "balance": balance,
                "ocr_credit_text": raw.get("ocr_credit_text"),
                "ocr_balance_text": raw.get("ocr_balance_text"),
                "credit_zone": credit_zone,
                "balance_zone": balance_zone,
            }))

        # BALANCE_AS_DEBIT: debit value equals balance value
        if debit is not None and balance is not None and abs(debit - balance) < 0.01:
            corruptions.append((i, "BALANCE_AS_DEBIT", {
                "debit": debit,
                "balance": balance,
                "ocr_debit_text": raw.get("ocr_debit_text"),
                "ocr_balance_text": raw.get("ocr_balance_text"),
                "debit_zone": debit_zone,
                "balance_zone": balance_zone,
            }))

        # MULTIPLE_AMOUNTS: both debit and credit populated (should never reach here — reject gate)
        if credit is not None and debit is not None:
            corruptions.append((i, "MULTIPLE_AMOUNTS", {
                "credit": credit,
                "debit": debit,
            }))

        # DATE_AS_AMOUNT: amount looks like a date
        for field, val in [("credit", credit), ("debit", debit)]:
            if val is not None:
                text_repr = raw.get(f"ocr_{field}_text", "")
                if text_repr and _DATE_RE.match(text_repr):
                    corruptions.append((i, "DATE_AS_AMOUNT", {
                        "field": field,
                        "value": val,
                        "token_text": text_repr,
                    }))

        # LEDGER_FAIL: conservation math doesn't close
        if prev_balance is not None and balance is not None:
            cr = credit or 0.0
            dr = debit  or 0.0
            expected = prev_balance + cr - dr
            residual = abs(expected - balance)
            if residual > LEDGER_TOLERANCE:
                corruptions.append((i, "LEDGER_FAIL", {
                    "prev_balance": prev_balance,
                    "credit": cr,
                    "debit": dr,
                    "expected_balance": round(expected, 2),
                    "actual_balance": balance,
                    "residual": round(residual, 2),
                }))

        if balance is not None:
            prev_balance = balance

    return corruptions


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

    try:
        protected = protect_table_header_tokens(page_tokens, {})
    except Exception:
        protected = page_tokens

    try:
        filtered = suppress_headers_and_footers(protected)
    except Exception:
        filtered = page_tokens

    try:
        txns, tel = parse_with_coordinates(filtered)
    except Exception as e:
        print(f"  [PARSE FAILED] {e}")
        return None

    zones = tel.get("zones", {})
    total = len(txns)
    corruptions = detect_corruptions(txns, zones)

    corruption_counts = defaultdict(int)
    for _, ctype, _ in corruptions:
        corruption_counts[ctype] += 1

    corrupted_rows = len(set(i for i, _, _ in corruptions))
    correct_rows   = total - corrupted_rows

    print(f"  Rows Extracted       : {total}")
    print(f"  Financially Correct  : {correct_rows}  ({correct_rows/total*100:.1f}%)" if total else "  (no rows)")
    print(f"  Financially Corrupt  : {corrupted_rows}  ({corrupted_rows/total*100:.1f}%)" if total else "")
    print(f"")
    for ctype, count in sorted(corruption_counts.items(), key=lambda x: -x[1]):
        print(f"    {ctype:<30} : {count}")

    return {
        "bank": filename,
        "total": total,
        "correct": correct_rows,
        "corrupted": corrupted_rows,
        "corruption_counts": dict(corruption_counts),
        "reject_log": tel.get("reject_log", []),
        "reject_reasons": tel.get("reject_reasons", {}),
        "warnings": tel.get("warnings", []),
    }


def main():
    as_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("Usage: python scripts/corruption_audit.py <pdf_directory> [--json]")
        sys.exit(1)

    pdf_dir = args[0]
    pdfs = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}")
        sys.exit(1)

    print(f"\nFinancial Corruption Audit — {len(pdfs)} PDFs in {pdf_dir}")

    all_results = []
    for pdf in pdfs:
        r = audit_pdf(pdf)
        if r:
            all_results.append(r)

    # Aggregate summary
    print(f"\n\n{'='*65}")
    print("FINANCIAL CORRUPTION SUMMARY")
    print(f"{'='*65}")
    print(f"{'Bank':<35} {'Total':>6} {'Correct':>8} {'Corrupt':>8} {'Rate':>6}")
    print(f"{'-'*35} {'-'*6} {'-'*8} {'-'*8} {'-'*6}")

    grand_total = grand_correct = grand_corrupt = 0
    for r in all_results:
        t = r["total"]
        c = r["correct"]
        x = r["corrupted"]
        rate = f"{x/t*100:.1f}%" if t else "N/A"
        grand_total   += t
        grand_correct += c
        grand_corrupt += x
        print(f"  {r['bank']:<33} {t:>6} {c:>8} {x:>8} {rate:>6}")

    grand_rate = f"{grand_corrupt/grand_total*100:.1f}%" if grand_total else "N/A"
    print(f"{'':->65}")
    print(f"  {'TOTAL':<33} {grand_total:>6} {grand_correct:>8} {grand_corrupt:>8} {grand_rate:>6}")

    # Corruption type breakdown
    all_types = defaultdict(int)
    for r in all_results:
        for ctype, count in r["corruption_counts"].items():
            all_types[ctype] += count

    if all_types:
        print(f"\nCORRUPTION TYPE BREAKDOWN (all banks)")
        print(f"{'Type':<35} {'Count':>6}")
        print(f"{'-'*35} {'-'*6}")
        for ctype, count in sorted(all_types.items(), key=lambda x: -x[1]):
            print(f"  {ctype:<33} {count:>6}")

    # Reject reason breakdown
    all_rejects = defaultdict(int)
    for r in all_results:
        for reason, count in r["reject_reasons"].items():
            all_rejects[reason] += count

    if all_rejects:
        print(f"\nREJECT REASON BREAKDOWN (all banks)")
        print(f"{'Reason':<35} {'Count':>6}")
        print(f"{'-'*35} {'-'*6}")
        for reason, count in sorted(all_rejects.items(), key=lambda x: -x[1]):
            print(f"  {reason:<33} {count:>6}")

    # ROW_ACCOUNTING_MISMATCH warnings
    mismatches = []
    for r in all_results:
        for w in r.get("warnings", []):
            if w.get("warning") == "ROW_ACCOUNTING_MISMATCH":
                mismatches.append((r["bank"], w))

    if mismatches:
        print(f"\nROW ACCOUNTING MISMATCHES (silent row loss detected)")
        for bank, w in mismatches:
            print(f"  {bank}: detected={w['detected']} accepted={w['accepted']} "
                  f"rejected={w['rejected']} missing={w['missing']}")

    if as_json:
        print("\n\n--- JSON OUTPUT ---")
        print(json.dumps(all_results, indent=2, default=str))

    print("\nDone.")


if __name__ == "__main__":
    main()
