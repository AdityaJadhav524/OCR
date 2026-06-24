import sys, os, json, glob, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_transaction_blocks
import core.layout.row_detector as row_detector
import core.parsers.coordinate_parser_v2 as cp2
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

_orig_dtb = row_detector.detect_transaction_blocks
_block_lengths = {} # _evidence_id -> int

def _audit_detect_transaction_blocks(rows, date_x_bounds=None):
    blocks = _orig_dtb(rows, date_x_bounds=date_x_bounds)
    global _block_lengths
    
    # We don't have evidence_id yet, it's assigned in cp2.
    # Instead, we will monkeypatch the block extraction inside cp2? No.
    # We can just store the block lengths by their text to match them later,
    # or just monkeypatch cp2._extract_block
    return blocks

cp2_extract_block = cp2._extract_block
def _mock_extract_block(block, zones):
    res = cp2_extract_block(block, zones)
    if res:
        res["_source_rows_count"] = len(block)
    return res
cp2._extract_block = _mock_extract_block

def run_audit():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    report_lines = ["# FIX IMPACT RANKING REPORT\n"]
    
    total_row_merge_recovery = 0
    total_balance_ownership_recovery = 0
    total_ledger_overlay_recovery = 0
    
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
        
        txns, parser_tel = cp2.parse_with_coordinates(
            page_tokens,
            pdf_name=pdf_name,
            statement_id="audit",
            job_id="audit",
            bank=bank,
            pdf_type=detected_pdf_type,
            identity=identity
        )
        
        # 1. Row Merge Recovery
        rejects = parser_tel.get("reject_log", [])
        row_merge_recovered = 0
        for r in rejects:
            source_rows = len(r.get("_source_tokens", [])) # rough proxy, not perfect
            # Better: we patched _extract_block which might not put _source_rows_count in reject_log easily 
            # if it was rejected in _qualifies. Let's look at the tokens length. Usually > 10 tokens if merged.
            # Wait, NO_TRANSACTION_SEED or both_debit_and_credit with many tokens.
            # Actually, let's use bounding box height > 35px as proxy for merged rows on scanned, or > 20px on digital.
            # Or just check if the text contains multiple dates/headers.
            text = " ".join([t.get("text", "") for t in r.get("_source_tokens", [])])
            if r.get("reject_reason") in ["NO_TRANSACTION_SEED", "both_debit_and_credit", "conservation_conflict"]:
                # If it's a massive block, it's a merge
                bbox = r.get("_source_bbox", [0,0,0,0])
                if bbox and (bbox[3] - bbox[1]) > 30:
                    row_merge_recovered += 1
                elif len(r.get("_source_tokens", [])) > 15:
                    row_merge_recovered += 1
                    
        # 2. Balance Ownership Recovery
        balance_ownership_recovered = 0
        for txn in txns:
            if txn.get("raw_extraction", {}).get("parsed_balance") is None:
                numeric_tokens = 0
                for tk in txn.get("_source_tokens", []):
                    text = tk.get("text", "").strip()
                    if '/' in text or '\\' in text: continue
                    if re.match(r'^\d{1,2}[A-Za-z]{3}\d{2,4}$', text): continue
                    val = _parse_float(text)
                    if val is not None and val > 0:
                        numeric_tokens += 1
                if numeric_tokens > 1:
                    balance_ownership_recovered += 1
                    
        # 3. Ledger Direction Corrections
        ledger_direction_corrections = 0
        txns.sort(key=lambda x: x.get("_evidence_id", ""))
        prev_balance = None
        for txn in txns:
            current_balance = txn.get("balance")
            ocr_debit = txn.get("debit")
            ocr_credit = txn.get("credit")
            ocr_direction = "debit" if ocr_debit else ("credit" if ocr_credit else "unknown")
            
            if prev_balance is not None and current_balance is not None:
                delta = current_balance - prev_balance
                if abs(delta) > 0.05:
                    ledger_direction = "credit" if delta > 0 else "debit"
                    if ledger_direction != ocr_direction:
                        ledger_direction_corrections += 1
            prev_balance = current_balance
            
        total_row_merge_recovery += row_merge_recovered
        total_balance_ownership_recovery += balance_ownership_recovered
        total_ledger_overlay_recovery += ledger_direction_corrections
        
        bank_stats.append({
            "bank": bank,
            "pdf_name": pdf_name,
            "row_merge": row_merge_recovered,
            "balance_own": balance_ownership_recovered,
            "ledger_dir": ledger_direction_corrections
        })
        
    report_lines.append(f"## Global Impact Summary\n")
    report_lines.append(f"- **Row Merge Fix:** +{total_row_merge_recovery} rows recovered")
    report_lines.append(f"- **Balance Ownership Fix:** +{total_balance_ownership_recovery} balances recovered")
    report_lines.append(f"- **Ledger Overlay Fix:** +{total_ledger_overlay_recovery} direction corrections\n")
    
    report_lines.append("## Impact by Bank\n")
    report_lines.append("| Bank | PDF | Row Merge (+Rows) | Balance Own (+Bal) | Ledger Dir (+Dir) |")
    report_lines.append("|---|---|---|---|---|")
    for b in bank_stats:
        report_lines.append(f"| {b['bank']} | {b['pdf_name']} | {b['row_merge']} | {b['balance_own']} | {b['ledger_dir']} |")
        
    with open(ROOT / "FIX_IMPACT_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

if __name__ == "__main__":
    run_audit()
