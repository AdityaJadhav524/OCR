import sys
import os
import json
import glob
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.transaction_order_validator import validate_and_sort_transactions
from core.validators.running_balance_audit import run_running_balance_audit

CORPUS_DIR  = ROOT / "tests" / "truth_corpus"
TEMP_DIR    = ROOT / "validation_lab" / "backend" / "temp"

def find_latest_temp_file(corpus_file: str):
    pattern = str(TEMP_DIR / f"*{corpus_file}")
    matches = glob.glob(pattern)
    if not matches:
        exact = TEMP_DIR / corpus_file
        if exact.exists(): return exact
        return None
    return Path(sorted(matches, key=os.path.getmtime)[-1])

def measure_continuity():
    truth_files = sorted(CORPUS_DIR.glob("*_digital.json"))
    report_lines = ["# RUNNING BALANCE CONTINUITY REPORT\n"]
    
    bank_stats = []
    
    for tf in truth_files:
        truth = json.loads(tf.read_text(encoding="utf-8"))
        pdf_name = truth.get("corpus_file", "")
        bank = truth.get("bank", "Unknown")
        if not pdf_name: continue
        
        pdf_path = find_latest_temp_file(pdf_name)
        if not pdf_path: continue
        
        try:
            doc_type, _ = detect_document_type(str(pdf_path))
        except ValueError as e:
            if "PASSWORD_REQUIRED" in str(e): continue
            raise
            
        full_text, pages, tel, page_tokens = route_document(str(pdf_path))
        identity = classify_document_llm(pages)
        detected_pdf_type = "SCANNED" if doc_type == "scanned" else "DIGITAL"
        
        txns, parser_tel = parse_with_coordinates(
            page_tokens,
            pdf_name=pdf_name,
            statement_id="audit",
            job_id="audit",
            bank=bank,
            pdf_type=detected_pdf_type,
            identity=identity
        )
        
        # Sprint 0: Order Validation
        sorted_txns, order_meta = validate_and_sort_transactions(txns)
        
        # Sprint 1: Running Balance Audit
        rb_audit = run_running_balance_audit(sorted_txns)
        
        bank_stats.append({
            "bank": bank,
            "pdf_name": pdf_name,
            "continuity": rb_audit["continuity_percentage"],
            "total_transitions": rb_audit["total_transitions"],
            "breaks": rb_audit["ledger_breaks"]
        })
        
    report_lines.append("## Summary by Bank\n")
    # Sort by continuity (lowest first to highlight issues)
    bank_stats.sort(key=lambda x: x["continuity"])
    
    for b in bank_stats:
        report_lines.append(f"- **{b['bank']}** ({b['pdf_name']}): {b['continuity']}% ({b['total_transitions'] - len(b['breaks'])}/{b['total_transitions']} valid)")
        
    report_lines.append("\n## Ledger Breaks\n")
    for b in bank_stats:
        if b["breaks"]:
            report_lines.append(f"### {b['bank']} ({b['pdf_name']})")
            for br in b["breaks"]:
                reason = br.get('reason', 'UNKNOWN')
                report_lines.append(
                    f"- Row {br['row_index']} [{reason}]: Prev Balance: {br['prev_balance']}, "
                    f"Credit: {br['credit']}, Debit: {br['debit']} -> "
                    f"Expected: {br['expected_balance']:.2f}, Got: {br['current_balance']}, Diff: {br['difference']:.2f}"
                )
                
    with open(ROOT / "CONTINUITY_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Audit complete. Results written to CONTINUITY_REPORT.md")

if __name__ == "__main__":
    measure_continuity()
