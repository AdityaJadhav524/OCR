import sys, os, json, glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import _parse_float

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

def run_audit():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    report_lines = ["# LEDGER DIRECTION TELEMETRY\n"]
    
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
        
        total_rows = 0
        conflicts = 0
        details = []
        
        # Sort txns by evidence_id to ensure chronological order for balance deltas
        txns.sort(key=lambda x: x.get("_evidence_id", ""))
        
        prev_balance = None
        for i, txn in enumerate(txns):
            current_balance = txn.get("balance")
            ocr_debit = txn.get("debit")
            ocr_credit = txn.get("credit")
            
            ocr_direction = "debit" if ocr_debit else ("credit" if ocr_credit else "unknown")
            
            if prev_balance is not None and current_balance is not None:
                delta = current_balance - prev_balance
                # Handle precision
                if abs(delta) > 0.05:
                    ledger_direction = "credit" if delta > 0 else "debit"
                    
                    if ledger_direction != ocr_direction:
                        conflicts += 1
                        row_text = " ".join([t.get("text", "") for t in txn.get("_source_tokens", [])])
                        details.append(
                            f"**Conflict Detected**\n"
                            f"- Row: `{row_text}`\n"
                            f"- Previous Balance: {prev_balance}, Current Balance: {current_balance}, Delta: {delta:.2f}\n"
                            f"- OCR Direction: {ocr_direction} (Dr: {ocr_debit}, Cr: {ocr_credit})\n"
                            f"- Ledger Direction: {ledger_direction}\n"
                        )
                
            prev_balance = current_balance
            total_rows += 1
            
        bank_stats.append({
            "bank": bank,
            "pdf_name": pdf_name,
            "total": total_rows,
            "conflicts": conflicts,
            "details": details
        })
        
    report_lines.append("## Summary by Bank\n")
    bank_stats.sort(key=lambda x: x["conflicts"], reverse=True)
    for b in bank_stats:
        report_lines.append(f"- **{b['bank']}** ({b['pdf_name']}): {b['conflicts']} direction conflicts out of {b['total']} rows")
        
    report_lines.append("\n## Detailed Conflicts\n")
    for b in bank_stats:
        if b["conflicts"] > 0:
            report_lines.append(f"### {b['bank']} ({b['pdf_name']})")
            for d in b["details"]:
                report_lines.append(d)
                
    with open(ROOT / "LEDGER_DIRECTION_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

if __name__ == "__main__":
    run_audit()
