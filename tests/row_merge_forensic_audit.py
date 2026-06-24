import sys, os, json, glob
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_transaction_blocks
import core.layout.row_detector as row_detector
import core.parsers.coordinate_parser_v2 as cp2

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

# Monkeypatch detect_transaction_blocks to capture audit data
_orig_dtb = row_detector.detect_transaction_blocks
_audit_blocks_data = []

def _audit_detect_transaction_blocks(rows, date_x_bounds=None):
    blocks = _orig_dtb(rows, date_x_bounds=date_x_bounds)
    if not rows: return blocks
    page_num = rows[0].get("page", 0)
    
    for b in blocks:
        if len(b) > 1:
            merged_row_text = " | ".join([" ".join([t.get("text", "") for t in r.get("tokens", [])]) for r in b])
            y_positions = [r.get("y0", 0) for r in b]
            
            # Determine merge reason based on the gap logic
            reason = "block_continuation"
            
            _audit_blocks_data.append({
                "page": page_num,
                "merged_row_text": merged_row_text,
                "source_rows_count": len(b),
                "source_row_y_positions": y_positions,
                "merge_reason": reason
            })
            
    return blocks

row_detector.detect_transaction_blocks = _audit_detect_transaction_blocks
cp2.detect_transaction_blocks = _audit_detect_transaction_blocks

def run_audit():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    report_lines = ["# ROW MERGE FORENSIC AUDIT\n"]
    
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
        
        global _audit_blocks_data
        _audit_blocks_data = []
        
        # We need to run parse_with_coordinates to trigger detect_transaction_blocks
        txns, parser_tel = cp2.parse_with_coordinates(
            page_tokens,
            pdf_name=pdf_name,
            statement_id="audit",
            job_id="audit",
            bank=bank,
            pdf_type=detected_pdf_type,
            identity=identity
        )
        
        # We also need rows_before and rows_after
        # Let's get them from row_detector
        rows = row_detector.detect_rows(page_tokens)
        page_to_rows = {}
        for r in rows:
            p = r.get("page", 0)
            page_to_rows.setdefault(p, []).append(r)
            
        total_rows_before = len(rows)
        total_rows_after = 0
        for p in sorted(page_to_rows.keys()):
            # count blocks per page without re-triggering audit
            p_blocks = _orig_dtb(page_to_rows[p], date_x_bounds=None)
            total_rows_after += len(p_blocks)
            
        loss_pct = 0.0
        if total_rows_before > 0:
            loss_pct = ((total_rows_before - total_rows_after) / total_rows_before) * 100
            
        bank_stats.append({
            "bank": bank,
            "pdf_name": pdf_name,
            "before": total_rows_before,
            "after": total_rows_after,
            "loss_pct": loss_pct,
            "merges": list(_audit_blocks_data)
        })
        
    bank_stats.sort(key=lambda x: x["loss_pct"], reverse=True)
    
    report_lines.append("## Rank by Merge Loss Percentage\n")
    for b in bank_stats:
        report_lines.append(f"- **{b['bank']}** ({b['pdf_name']}): {b['before']} -> {b['after']} ({b['loss_pct']:.1f}% loss)")
        
    report_lines.append("\n## Detailed Merge Analysis\n")
    for b in bank_stats:
        if not b["merges"]: continue
        report_lines.append(f"### {b['bank']} - {b['pdf_name']}")
        for m in b["merges"]:
            # Only show highly suspicious merges (>= 3 rows, or spanning large gap)
            if m['source_rows_count'] > 1:
                # Calculate gap
                y_pos = m['source_row_y_positions']
                max_gap = 0
                for i in range(1, len(y_pos)):
                    gap = y_pos[i] - y_pos[i-1]
                    if gap > max_gap: max_gap = gap
                    
                report_lines.append(f"**Page {m['page']} | {m['source_rows_count']} rows merged | Max Gap: {max_gap:.1f}**")
                report_lines.append(f"```text\n{m['merged_row_text']}\n```")
                report_lines.append(f"Y-positions: {[round(y, 1) for y in m['source_row_y_positions']]}\n")

    with open(ROOT / "ROW_MERGE_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

if __name__ == "__main__":
    run_audit()
