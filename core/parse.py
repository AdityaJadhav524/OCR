"""
parse.py — Core CLI entry point.
────────────────────────────────────────────────────────────────────────────
Usage:
    python parse.py <statement.pdf>
    python parse.py <statement.pdf> --password "pass"
    python parse.py <statement.csv>
    python parse.py <statement.pdf> --pretty

Output (JSON to stdout):
    [
      {
        "date": "2024-03-01",
        "narration": "NEFT CR-SALARY COMPANY XYZ",
        "debit": null,
        "credit": 85000.0,
        "balance": 91200.5
      },
      ...
    ]

Pipeline:
    PDF (digital)  → document_router → pdf_extractor → bank_detector → statement_parser → validation → JSON
    PDF (scanned)  → document_router → ocr_core → ocr_adapter → bank_detector → statement_parser → validation → JSON
    CSV            → pandas → bank_detector → statement_parser → validation → JSON

Environment (.env):
    GEMINI_API_KEY             — required
    CLASSIFIER_MODEL           — optional (default: models/gemini-2.5-flash)
    LLM_PARSER_MODEL           — optional (default: models/gemini-2.5-flash)
    OPENROUTER_API_KEY         — optional fallback
    NINEROUTER_API_KEY         — optional fallback
────────────────────────────────────────────────────────────────────────────
"""

import argparse
import json
import logging
import os
import re
import sys

# ── Ensure core root is on sys.path ──────────────────────────────────────────
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# ── Logging (stderr so JSON output on stdout stays clean) ─────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-38s  %(levelname)-7s  %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("core.parse")


def _split_pages(full_text: str) -> list:
    """Split full_text on the page separators inserted by pdf_extractor."""
    pages = [
        block.strip()
        for block in re.split(r'={80}', full_text)
        if block.strip() and not re.fullmatch(r'\s*PAGE\s+\d+\s*', block.strip(), re.IGNORECASE)
    ]
    return pages if pages else [full_text]


def parse_statement(file_path: str, password: str = None) -> list:
    """
    Run the four-step parsing pipeline.

    Step 1  document_router.route_document()      PDF → (full_text, pages)
              ├─ digital PDF → pdf_extractor (unchanged)
              └─ scanned PDF → ocr_core → ocr_adapter
    Step 2  bank_detector.classify_document_llm() LLM → institution + family
    Step 3  statement_parser.parse_with_llm()     LLM → transaction JSON
    Step 4  validation helpers                    normalize dates

    Steps 2, 3, 4 and the CSV path are completely unchanged.

    Args:
        file_path : Path to PDF, CSV, or Excel file.
        password  : PDF password (None if not encrypted).

    Returns:
        List of dicts: [{date, narration, debit, credit, balance}, ...]
    """
    from core.extractors.document_router import route_document
    from core.detection.bank_detector import classify_document_llm
    from core.parsers.statement_parser import parse_with_llm
    from core.parsers.validation import extract_json_from_response, normalize_date
    from core.validators.financial_audit import run_financial_audit

    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    ext = os.path.splitext(abs_path)[1].lower()

    # ── STEP 1: Extract raw text ──────────────────────────────────────────────
    # PDFs: document_router detects digital vs scanned and routes accordingly.
    # Both paths return identical (full_text, pages) — downstream is unchanged.
    # CSV/Excel: pandas path is untouched.
    logger.info("STEP 1 — Extracting text from: %s", abs_path)

    if ext == ".pdf":
        full_text, pages, merge_stats, page_tokens = route_document(abs_path, password=password)
        if not full_text or not full_text.strip():
            raise ValueError("PDF text extraction returned empty content.")
    elif ext in (".csv", ".xlsx", ".xls"):
        import pandas as pd
        df = pd.read_csv(abs_path) if ext == ".csv" else pd.read_excel(abs_path)
        full_text = df.to_string(index=False)
        pages = _split_pages(full_text)
    else:
        raise ValueError(
            f"Unsupported file type: {ext!r}. Supported: .pdf  .csv  .xlsx  .xls"
        )

    logger.info("STEP 1 — Done: %d pages, %d chars", len(pages), len(full_text))

    # ── STEP 2: Classify document ─────────────────────────────────────────────
    logger.info("STEP 2 — Detecting bank / document family...")
    identity_json = classify_document_llm(pages)
    logger.info(
        "STEP 2 — Done: family=%s  institution=%s",
        identity_json.get("document_family"),
        identity_json.get("institution_name"),
    )

    # ── STEP 3: Extract transactions ──────────────────────────────────────────
    logger.info("STEP 3 — Parsing transactions...")
    
    from core.parsers.deterministic_parser import parse_deterministic_transactions
    transactions, telemetry = parse_deterministic_transactions(full_text)
    
    if transactions:
        logger.info("STEP 3 — Done: %d transactions extracted (Deterministic)", len(transactions))
    else:
        logger.info("STEP 3 — Deterministic failed/empty, falling back to LLM...")
        raw_response  = parse_with_llm(full_text, identity_json)
        transactions  = extract_json_from_response(raw_response)
        logger.info("STEP 3 — Done: %d transactions extracted (LLM)", len(transactions))

    # ── STEP 4: Normalize dates + unify field names ───────────────────────────
    normalized = []
    for txn in transactions:
        txn["date"] = normalize_date(txn.get("date"))
        # Unify narration field (LLM may return "details" or "narration")
        if "details" in txn and "narration" not in txn:
            txn["narration"] = txn.pop("details")
        normalized.append(txn)

    logger.info("STEP 4 — Done: dates normalized.")
    
    # ── STEP 5: Financial Audit ───────────────────────────────────────────────
    logger.info("STEP 5 — Running Financial Audit...")
    audit_results = run_financial_audit(normalized)
    
    return {
        "transactions": normalized,
        "audit": audit_results
    }


def main():
    parser = argparse.ArgumentParser(
        description="Core — Parse a bank statement PDF/CSV into structured JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parse.py hdfc_march_2024.pdf
  python parse.py encrypted.pdf --password mypassword
  python parse.py statement.csv
  python parse.py statement.pdf --pretty
  python parse.py statement.pdf --pretty > transactions.json
        """,
    )
    parser.add_argument("file",       help="Path to PDF or CSV/Excel statement")
    parser.add_argument("--password", default=None, help="PDF password (if encrypted)")
    parser.add_argument("--pretty",   action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    try:
        result = parse_statement(file_path=args.file, password=args.password)
        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent, ensure_ascii=False))
        sys.exit(0)

    except FileNotFoundError as e:
        logger.error("%s", e)
        sys.exit(1)
    except ValueError as e:
        logger.error("%s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
