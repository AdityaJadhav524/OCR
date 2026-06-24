import sys, os, json, glob, re
from pathlib import Path
from collections import Counter

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
    report_lines = ["# BALANCE OWNERSHIP FORENSIC AUDIT\n"]
    
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
        
        stolen_count = 0
        total_txns = len(txns)
        bank_details = []
        
        for txn in txns:
            # We want to identify if a balance token was stolen by amount zones
            # First, find all numeric tokens in the row
            tokens = txn.get("_source_tokens", [])
            tokens = sorted(tokens, key=lambda tk: tk.get("x0", 0))
            
            raw_ex = txn.get("raw_extraction", {})
            parsed_bal = raw_ex.get("parsed_balance")
            parsed_dr = raw_ex.get("parsed_debit")
            parsed_cr = raw_ex.get("parsed_credit")
            
            ocr_bal = raw_ex.get("ocr_balance_text")
            ocr_dr = raw_ex.get("ocr_debit_text")
            ocr_cr = raw_ex.get("ocr_credit_text")
            
            numeric_tokens = []
            for tk in tokens:
                text = tk.get("text", "").strip()
                if '/' in text or '\\' in text: continue
                if re.match(r'^\d{1,2}[A-Za-z]{3}\d{2,4}$', text): continue
                val = _parse_float(text)
                if val is not None and val > 0:
                    numeric_tokens.append(text)
                    
            if not numeric_tokens: continue
            
            row_text = " ".join([tk.get("text", "") for tk in tokens])
            
            # If balance is NOT parsed, but there are multiple numeric tokens,
            # or if the rightmost numeric token ended up in credit/debit
            
            rightmost = numeric_tokens[-1]
            stolen_by = None
            
            if parsed_bal is None:
                if rightmost == ocr_dr:
                    stolen_by = "debit_zone"
                elif rightmost == ocr_cr:
                    stolen_by = "credit_zone"
                    
            if stolen_by:
                stolen_count += 1
                bank_details.append(
                    f"**Stolen by {stolen_by}**\n"
                    f"- Row: `{row_text}`\n"
                    f"- Numeric Tokens: `{numeric_tokens}`\n"
                    f"- Debit={ocr_dr}, Credit={ocr_cr}, Balance={ocr_bal}\n"
                )
                
        bank_stats.append({
            "bank": bank,
            "pdf_name": pdf_name,
            "total": total_txns,
            "stolen": stolen_count,
            "details": bank_details
        })
        
    bank_stats.sort(key=lambda x: x["stolen"], reverse=True)
    
    report_lines.append("## Summary by Bank\n")
    for b in bank_stats:
        report_lines.append(f"- **{b['bank']}** ({b['pdf_name']}): {b['stolen']} stolen balances out of {b['total']} accepted rows")
        
    report_lines.append("\n## Stolen Balance Details\n")
    for b in bank_stats:
        if b["stolen"] > 0:
            report_lines.append(f"### {b['bank']} ({b['pdf_name']})")
            for d in b["details"]:
                report_lines.append(d)
                
    with open(ROOT / "BALANCE_OWNERSHIP_FORENSIC.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

if __name__ == "__main__":
    run_audit()
