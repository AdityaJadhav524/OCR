import sys, os, json, logging, glob
from pathlib import Path

# Suppress debug logs from core
logging.getLogger("core.parsers.coordinate_parser_v2").setLevel(logging.WARNING)
logging.getLogger("core.extractors.document_router").setLevel(logging.WARNING)

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

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

def audit_page_boundaries():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    
    for tf in truth_files:
        truth = json.loads(tf.read_text(encoding="utf-8"))
        pdf_name = truth.get("corpus_file", "")
        bank = truth.get("bank", "Unknown")
        
        if not pdf_name: continue
        
        pdf_path = find_latest_temp_file(pdf_name)
        if not pdf_path:
            print(f"[{bank}] PDF NOT FOUND: {pdf_name}")
            continue
            
        print(f"\n{'='*90}\n[{bank}] {pdf_name}\n{'='*90}")
        
        try:
            doc_type, _ = detect_document_type(str(pdf_path))
        except ValueError as e:
            if "PASSWORD_REQUIRED" in str(e):
                print(f"[{bank}] PASSWORD REQUIRED: {pdf_name} - skipping")
                continue
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
        
        rejects = parser_tel.get("reject_log", [])
        
        all_rows = []
        for t in txns:
            t["_audit_status"] = "ACCEPTED"
            all_rows.append(t)
        for r in rejects:
            r["_audit_status"] = "REJECTED"
            all_rows.append(r)
            
        # Sort by evidence id to maintain top-to-bottom reading order as parsed
        all_rows.sort(key=lambda x: x.get("_evidence_id", ""))
        
        page_groups = {}
        for row in all_rows:
            p = row.get("_source_page", 0)
            if p not in page_groups: page_groups[p] = []
            page_groups[p].append(row)
            
        sorted_pages = sorted(page_groups.keys())
        
        def to_text(row):
            st = " ".join([tk.get("text","") for tk in row.get("_source_tokens", [])])
            bbox = row.get("_source_bbox", [0,0,0,0])
            y0 = bbox[1] if (bbox and len(bbox) >= 2) else 0
            rej = f" -> REJECT_REASON: {row.get('reject_reason')}" if row["_audit_status"] == "REJECTED" else ""
            return f"[{row['_audit_status'][:3]}] (y={y0:>6.1f}) {st[:80]}{rej}"
            
        for p in sorted_pages:
            p_rows = page_groups[p]
            accepted_rows = [r for r in p_rows if r["_audit_status"] == "ACCEPTED"]
            rejected_rows = [r for r in p_rows if r["_audit_status"] == "REJECTED"]
            
            last_3_detected = [to_text(r) for r in p_rows[-3:]]
            last_3_accepted = [to_text(r) for r in accepted_rows[-3:]]
            
            first_3_next = []
            if p + 1 in page_groups:
                first_3_next = [to_text(r) for r in page_groups[p+1][:3]]
            
            print(f"\n--- Page {p} ---")
            print(f"Detected: {len(p_rows)} | Accepted: {len(accepted_rows)} | Rejected: {len(rejected_rows)}")
            print("Last 3 Detected (any status):")
            for txt in last_3_detected: print(f"  {txt}")
            print("Last 3 Accepted:")
            for txt in last_3_accepted: print(f"  {txt}")
            if first_3_next:
                print("First 3 Detected on Page + 1:")
                for txt in first_3_next: print(f"  {txt}")
                
if __name__ == "__main__":
    audit_page_boundaries()
