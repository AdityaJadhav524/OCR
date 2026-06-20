"""
Corpus Benchmark Runner
=======================

Runs the CURRENT parser (coordinate_parser_v2) against every truth corpus entry
and reports recall, missing transactions, and any financial corruption.

This is the BASELINE. Any new parser must beat these numbers before replacing this one.

Usage:
    python tests/run_corpus_benchmark.py

Output:
    Prints a table of actual vs expected transactions for every verified PDF.
    Writes machine-readable results to tests/truth_corpus/_last_run.json
"""

import sys, os, json, logging, glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.WARNING)

# Project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

CORPUS_DIR  = ROOT / "tests" / "truth_corpus"
TEMP_DIR    = ROOT / "validation_lab" / "backend" / "temp"
RESULTS_OUT = CORPUS_DIR / "_last_run.json"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_latest_temp_file(corpus_file: str) -> Optional[Path]:
    """
    Find the most recently modified copy of `corpus_file` in the temp directory.
    Temp files are stored as JOB_<timestamp>_<original_name>.
    """
    pattern = str(TEMP_DIR / f"*{corpus_file}")
    matches = glob.glob(pattern)
    if not matches:
        # Try exact match (original name stored directly)
        exact = TEMP_DIR / corpus_file
        if exact.exists():
            return exact
        return None
    # Most recently modified
    return Path(sorted(matches, key=os.path.getmtime)[-1])


def run_parser(pdf_path: Path, bank: str, pdf_type: str) -> Dict[str, Any]:
    """Run both legacy V2 parser and Discovery Engine on a PDF and return results."""
    from core.extractors.document_router import route_document, detect_document_type
    from core.detection.bank_detector import classify_document_llm
    from core.parsers.coordinate_parser_v2 import parse_with_coordinates
    from core.discovery.transaction_discovery import discover_transactions

    doc_type, _ = detect_document_type(str(pdf_path))
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    identity = classify_document_llm(pages)

    detected_pdf_type = "SCANNED" if doc_type == "scanned" else "DIGITAL"
    
    # 1. Legacy Parser (V2)
    txns, parser_tel = parse_with_coordinates(
        page_tokens,
        pdf_name=pdf_path.name,
        statement_id="benchmark",
        job_id="benchmark",
        bank=bank,
        pdf_type=detected_pdf_type,
        identity=identity
    )

    rejects = parser_tel.get("reject_log", [])
    from collections import Counter
    reject_reasons = dict(Counter(r.get("reject_reason", "?") for r in rejects))
    
    # 2. Discovery Engine
    try:
        discovery_candidates = discover_transactions(page_tokens)
        discovery_count = len(discovery_candidates)
    except Exception as e:
        logger.error(f"Discovery Engine failed: {e}")
        discovery_count = -1

    return {
        "v2_accepted":    len(txns),
        "v2_rejected":    len(rejects),
        "v2_reasons":     reject_reasons,
        "first_date":     txns[0].get("date") if txns else None,
        "last_date":      txns[-1].get("date") if txns else None,
        "opening_balance": txns[0].get("balance") if txns else None,
        "closing_balance": txns[-1].get("balance") if txns else None,
        "total_debit":    sum(float(t.get("debit") or 0) for t in txns),
        "total_credit":   sum(float(t.get("credit") or 0) for t in txns),
        "discovery_got":  discovery_count
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    if not truth_files:
        print("No truth corpus entries found.")
        return

    results = []
    print()
    print(f"{'PDF':<40} {'Expected':>10} | {'V2 Got':>8} {'V2 Recall':>9} | {'Disc Got':>8} {'Disc Rec':>8}")
    print("-" * 92)

    for tf in truth_files:
        truth = json.loads(tf.read_text(encoding="utf-8"))
        pdf_name    = truth.get("corpus_file", "")
        bank        = truth.get("bank", "Unknown")
        pdf_type    = truth.get("type", "digital")
        expected    = truth.get("expected_transactions")
        verified    = truth.get("verified", False)

        if not pdf_name:
            continue

        pdf_path = find_latest_temp_file(pdf_name)
        if not pdf_path:
            print(f"{'[NOT FOUND] ' + pdf_name:<40} {'N/A':>10} | {'N/A':>8} {'N/A':>9} | {'N/A':>8} {'N/A':>8}")
            results.append({"corpus": tf.name, "status": "PDF_NOT_FOUND"})
            continue

        try:
            r = run_parser(pdf_path, bank, pdf_type)
            v2_got = r["v2_accepted"]
            disc_got = r["discovery_got"]

            if expected is not None:
                v2_recall = v2_got / expected if expected > 0 else 0.0
                disc_recall = disc_got / expected if expected > 0 else 0.0
                
                v2_recall_str = f"{v2_recall*100:.1f}%"
                disc_recall_str = f"{disc_recall*100:.1f}%"
                
                verified_str = f"{expected}" if verified else f"~{expected} (?)"
            else:
                v2_recall_str = "N/A"
                disc_recall_str = "N/A"
                verified_str = "TBD"

            label = (pdf_name[:37] + "...") if len(pdf_name) > 40 else pdf_name
            print(f"{label:<40} {verified_str:>10} | {v2_got:>8} {v2_recall_str:>9} | {disc_got:>8} {disc_recall_str:>8}")

            results.append({
                "corpus":       tf.name,
                "pdf_name":     pdf_name,
                "bank":         bank,
                "expected":     expected,
                "v2_got":       v2_got,
                "discovery_got": disc_got,
                "verified":     verified,
                "v2_reasons":   r["v2_reasons"],
            })

        except Exception as e:
            print(f"{pdf_name:<40} {'N/A':>10} | {'ERR':>8} {'N/A':>9} | {'ERR':>8} {'N/A':>8} ERROR: {e}")
            results.append({"corpus": tf.name, "status": f"ERROR: {e}"})

    print()

    # Write machine-readable results
    output = {
        "run_at":  datetime.utcnow().isoformat() + "Z",
        "parser":  "coordinate_parser_v2",
        "results": results
    }
    RESULTS_OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Results written to {RESULTS_OUT}")


if __name__ == "__main__":
    main()
