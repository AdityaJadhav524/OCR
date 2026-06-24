import sys, os, json, glob, re
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
    report_lines = ["# RIGHTMOST BALANCE SIMULATOR REPORT\n"]
    
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
        
        # also process rejects to see if we can recover them
        rejects = parser_tel.get("reject_log", [])
        all_rows = txns + rejects
        
        recovered_balances = 0
        recovered_rejects = 0
        details = []
        
        for row in all_rows:
            raw_ex = row.get("raw_extraction", {})
            parsed_bal = raw_ex.get("parsed_balance")
            
            tokens = row.get("_source_tokens", [])
            tokens = sorted(tokens, key=lambda tk: tk.get("x0", 0))
            
            numeric_tokens = []
            for tk in tokens:
                text = tk.get("text", "").strip()
                if '/' in text or '\\' in text: continue
                if re.match(r'^\d{1,2}[A-Za-z]{3}\d{2,4}$', text): continue
                val = _parse_float(text)
                if val is not None and val > 0:
                    numeric_tokens.append(val)
                    
            is_rejected = "reject_reason" in row
            
            if parsed_bal is None and len(numeric_tokens) > 1:
                # Simulating rightmost balance
                simulated_bal = numeric_tokens[-1]
                recovered_balances += 1
                
                if is_rejected and row.get("reject_reason") == "NO_TRANSACTION_SEED":
                    # If it was rejected specifically for no seed, simulating this might recover it
                    recovered_rejects += 1
                    row_text = " ".join([t.get("text", "") for t in tokens])
                    details.append(
                        f"**Simulated Reject Recovery**\n"
                        f"- Row: `{row_text}`\n"
                        f"- Simulated Balance: {simulated_bal}\n"
                    )
                elif not is_rejected:
                    # It was accepted but with missing balance
                    row_text = " ".join([t.get("text", "") for t in tokens])
                    details.append(
                        f"**Simulated Accepted Row Balance**\n"
                        f"- Row: `{row_text}`\n"
                        f"- Simulated Balance: {simulated_bal}\n"
                    )
                    
        bank_stats.append({
            "bank": bank,
            "pdf_name": pdf_name,
            "recovered_balances": recovered_balances,
            "recovered_rejects": recovered_rejects,
            "details": details
        })
        
    bank_stats.sort(key=lambda x: x["recovered_balances"], reverse=True)
    
    report_lines.append("## Summary by Bank\n")
    for b in bank_stats:
        report_lines.append(f"- **{b['bank']}** ({b['pdf_name']}): Recovered {b['recovered_balances']} balances ({b['recovered_rejects']} were rejected rows)")
        
    report_lines.append("\n## Simulation Details\n")
    for b in bank_stats:
        if b["recovered_balances"] > 0:
            report_lines.append(f"### {b['bank']} ({b['pdf_name']})")
            for d in b["details"]:
                report_lines.append(d)
                
    with open(ROOT / "RIGHTMOST_BALANCE_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

if __name__ == "__main__":
    run_audit()
