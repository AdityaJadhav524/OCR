import sys, os, json, glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.layout.row_detector import detect_rows

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
    report_lines = ["# LAST ROWS AUDIT REPORT\n"]
    
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
        
        ocr_rows = detect_rows(page_tokens)
        
        report_lines.append(f"## {bank} ({pdf_name})")
        
        report_lines.append("### Last 5 OCR Rows")
        for r in ocr_rows[-5:]:
            row_text = " ".join([t.get("text", "") for t in r.get("tokens", [])])
            report_lines.append(f"- Page {r.get('page')} (y={r.get('y0', 0):.1f}): `{row_text[:120]}`")
            
        report_lines.append("\n### Last 5 Extracted (Accepted) Transactions")
        for t in txns[-5:]:
            row_text = " ".join([tk.get("text", "") for tk in t.get("_source_tokens", [])])
            report_lines.append(f"- Page {t.get('_source_page')} (y={t.get('_source_bbox', [0,0])[1]:.1f}): `{row_text[:120]}`")
            
        report_lines.append("\n---\n")

    with open(ROOT / "LAST_ROWS_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

if __name__ == "__main__":
    run_audit()
