import sys
import os
import json
import glob
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.statement_confidence_engine import generate_statement_confidence

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

def run_confidence_benchmark():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    report_lines = ["# STATEMENT CONFIDENCE BENCHMARK\n"]
    
    bank_stats = []
    
    for tf in truth_files:
        truth = json.loads(tf.read_text(encoding="utf-8"))
        pdf_name = truth.get("corpus_file", "")
        bank = truth.get("bank", "Unknown")
        expected_count = len(truth.get("transactions", []))
        
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
        
        # Sprint 4
        conf = generate_statement_confidence(txns, expected_transaction_count=expected_count)
        
        # Telemetry
        from telemetry.logger import log_telemetry
        log_telemetry("confidence", pdf_name.replace(".pdf", ""), conf)
        
        bank_stats.append({
            "bank": bank,
            "pdf_name": pdf_name,
            "confidence": conf["confidence"],
            "status": conf["status"],
            "continuity": conf["continuity"],
            "reconciliation": conf["reconciliation"],
            "direction": conf["direction"],
            "completeness": conf["transaction_completeness"],
            "corrected_directions": conf["details"]["corrected_directions"]
        })
        
    report_lines.append("## Benchmark Results\n")
    bank_stats.sort(key=lambda x: x["confidence"], reverse=True)
    
    for b in bank_stats:
        status_icon = "🟢" if b["status"] == "AUTO_APPROVE" else ("🟡" if b["status"] == "REVIEW" else "🔴")
        report_lines.append(
            f"### {status_icon} {b['bank']} ({b['pdf_name']})\n"
            f"- **Confidence**: {b['confidence']} ({b['status']})\n"
            f"- Continuity: {b['continuity']}%\n"
            f"- Reconciliation: {b['reconciliation']}%\n"
            f"- Direction Accuracy: {b['direction']}% (Healed: {b['corrected_directions']})\n"
            f"- Completeness: {b['completeness']:.1f}%\n"
        )
                
    with open(ROOT / "CONFIDENCE_BENCHMARK.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    with open(ROOT / "CONFIDENCE_BENCHMARK.json", "w", encoding="utf-8") as f:
        json.dump(bank_stats, f, indent=2)
        
    print(f"Benchmark complete. Results written to CONFIDENCE_BENCHMARK.md and CONFIDENCE_BENCHMARK.json")
    return bank_stats

if __name__ == "__main__":
    run_confidence_benchmark()
