import sys
import os
import json
import glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.transaction_order_validator import validate_and_sort_transactions
from core.validators.financial_reconciliation import run_financial_reconciliation

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

def run_reconciliation():
    truth_files = sorted(CORPUS_DIR.glob("*_digital.json"))
    report_lines = ["# FINANCIAL RECONCILIATION REPORT\n"]
    
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
        
        # Sprint 0
        sorted_txns, order_meta = validate_and_sort_transactions(txns)
        
        # Sprint 2
        recon = run_financial_reconciliation(sorted_txns)
        
        bank_stats.append({
            "bank": bank,
            "pdf_name": pdf_name,
            "reconciliation_percentage": recon["reconciliation_percentage"],
            "difference": recon["difference"],
            "total_credits": recon["total_credits"],
            "total_debits": recon["total_debits"],
            "is_reconciled": recon["is_reconciled"]
        })
        
    report_lines.append("## Summary by Bank\n")
    bank_stats.sort(key=lambda x: x["reconciliation_percentage"])
    
    for b in bank_stats:
        status = "✅" if b['is_reconciled'] else "❌"
        diff_str = f"Diff: {b['difference']}" if b['difference'] is not None else "Diff: Unknown"
        report_lines.append(f"- {status} **{b['bank']}** ({b['pdf_name']}): {b['reconciliation_percentage']}% | {diff_str} | +{b['total_credits']} / -{b['total_debits']}")
                
    with open(ROOT / "RECONCILIATION_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Audit complete. Results written to RECONCILIATION_REPORT.md")

if __name__ == "__main__":
    run_reconciliation()
