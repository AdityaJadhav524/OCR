import sys
import os
import json
import glob
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_transaction_blocks, detect_rows
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

def score_raw_row(row, date_zone=None) -> int:
    score = 0
    tokens = row.get("tokens", [])
    row_text = " ".join([t.get("text", "") for t in tokens])
    row_text_lower = row_text.lower()
    
    has_date = False
    for t in tokens:
        txt = t.get("text", "").strip()
        x0 = t.get("x0", -1)
        if date_zone is None or (date_zone[0] <= x0 <= date_zone[1]):
            if cp2._DATE_RE.match(txt) or cp2._DATE_PREFIX_RE.match(txt):
                has_date = True
                break
    if has_date:
        score += 5

    amount_matches = re.findall(r'\b\d{1,3}(?:,\d{2,3})*\.\d{2}\b', row_text)
    if len(amount_matches) >= 1:
        score += 4
    if len(amount_matches) >= 2:
        score += 4

    if re.search(r'\b(upi|neft|imps|rtgs)\b', row_text_lower):
        score += 3
        
    if re.search(r'\b\d{10,20}\b', row_text) or re.search(r'\b[A-Z0-9]{10,15}\b', row_text):
        score += 2
        
    if re.search(r'\b(statement|summary|closing|opening|brought forward|carried forward|total|page)\b', row_text_lower):
        score -= 10
        
    if re.search(r'\b(branch|ifsc|micr|open date|account no|customer id|address|email)\b', row_text_lower):
        score -= 10

    return score

def classify_rejection(block, b_candidates, candidate_txn, reason):
    if len(b_candidates) > 1:
        return "ROW_MERGE_COLLAPSE"
        
    block_text = " ".join([" ".join([t.get("text","") for t in r.get("tokens",[])]) for r in block]).lower()
    
    # Check for header/footer tokens that merged into transaction
    if re.search(r'\b(brought forward|carried forward|opening balance|closing balance|statement summary|total)\b', block_text):
        return "PAGE_BOUNDARY_COLLAPSE"
        
    if len(block) >= 3 and reason in ("both_debit_and_credit", "no_debit_or_credit"):
        return "MULTILINE_NARRATION_COLLAPSE"
        
    if not candidate_txn:
        return "TRUE_OCR_FAILURE"
        
    has_date = bool(candidate_txn.get("date"))
    has_amount = bool(candidate_txn.get("debit")) or bool(candidate_txn.get("credit"))
    
    if not has_date or not has_amount:
        return "TRUE_OCR_FAILURE"
        
    return "POLICY_REJECT"

def run_audit():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    
    lost_transactions = []
    classifications = defaultdict(int)
    pdf_breakdown = defaultdict(int)
    
    for tf in truth_files:
        truth = json.loads(tf.read_text(encoding="utf-8"))
        pdf_name = truth.get("corpus_file", "")
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
        
        raw_rows = detect_rows(page_tokens)
        from core.layout.column_detector import detect_columns
        zones, _ = detect_columns(raw_rows, identity=identity)
        if not zones or "date_zone" not in zones:
            continue
            
        date_zone = zones.get("date_zone")
        
        candidate_ids = set()
        row_scores = {}
        for r in raw_rows:
            score = score_raw_row(r, date_zone)
            if score >= 8:
                candidate_ids.add(id(r))
                row_scores[id(r)] = score
                
        page_to_rows = {}
        for r in raw_rows:
            page_to_rows.setdefault(r.get("page", 0), []).append(r)
            
        blocks = []
        for p in sorted(page_to_rows.keys()):
            blocks.extend(detect_transaction_blocks(page_to_rows[p], date_x_bounds=date_zone))
            
        for block in blocks:
            b_candidates = [r for r in block if id(r) in candidate_ids]
            if not b_candidates: continue
            
            candidate_txn = cp2._extract_block(block, zones)
            qualifies = False
            reason = ""
            
            if candidate_txn:
                qualifies, reason, state = cp2._qualifies(candidate_txn, prev_balance=None, balance_zone_missing=False)
            
            # Merged block text
            merged_block_text = " | ".join([" ".join([t.get("text","") for t in r.get("tokens",[])]) for r in block])
            
            if qualifies:
                # The first candidate was accepted. Any additional candidates in this block were merged and lost.
                for lost_cand in b_candidates[1:]:
                    raw_text = " ".join([t.get("text","") for t in lost_cand.get("tokens",[])])
                    cat = "ROW_MERGE_COLLAPSE"
                    classifications[cat] += 1
                    pdf_breakdown[pdf_name] += 1
                    
                    lost_transactions.append({
                        "pdf": pdf_name,
                        "raw_row": raw_text,
                        "merged_block": merged_block_text,
                        "candidate_score": row_scores[id(lost_cand)],
                        "reject_reason": "swallowed_by_accepted_candidate",
                        "date_detected": bool(candidate_txn.get("date")),
                        "amount_detected": bool(candidate_txn.get("debit")) or bool(candidate_txn.get("credit")),
                        "balance_detected": bool(candidate_txn.get("balance")),
                        "lost_stage": "detect_transaction_blocks",
                        "category": cat
                    })
            else:
                # The entire block was rejected. All candidates inside are lost.
                cat = classify_rejection(block, b_candidates, candidate_txn, reason)
                for lost_cand in b_candidates:
                    raw_text = " ".join([t.get("text","") for t in lost_cand.get("tokens",[])])
                    classifications[cat] += 1
                    pdf_breakdown[pdf_name] += 1
                    
                    lost_transactions.append({
                        "pdf": pdf_name,
                        "raw_row": raw_text,
                        "merged_block": merged_block_text,
                        "candidate_score": row_scores[id(lost_cand)],
                        "reject_reason": reason or "extract_failed",
                        "date_detected": bool(candidate_txn.get("date")) if candidate_txn else False,
                        "amount_detected": (bool(candidate_txn.get("debit")) or bool(candidate_txn.get("credit"))) if candidate_txn else False,
                        "balance_detected": bool(candidate_txn.get("balance")) if candidate_txn else False,
                        "lost_stage": "_qualifies" if candidate_txn else "_extract_block",
                        "category": cat
                    })

    # Generate Deliverable
    report = []
    report.append("# FINAL 18 MISSING TRANSACTIONS REPORT")
    report.append("")
    report.append(f"**Total Lost Transactions Identified:** {len(lost_transactions)}")
    report.append("")
    report.append("## Global Counts")
    for cat in ["ROW_MERGE_COLLAPSE", "PAGE_BOUNDARY_COLLAPSE", "MULTILINE_NARRATION_COLLAPSE", "TRUE_OCR_FAILURE", "POLICY_REJECT"]:
        report.append(f"- **{cat}**: {classifications.get(cat, 0)}")
        
    report.append("")
    report.append("## Per-PDF Breakdown")
    for pdf, count in sorted(pdf_breakdown.items(), key=lambda x: x[1], reverse=True):
        report.append(f"- **{pdf}**: {count} missing")
        
    report.append("")
    report.append("## Complete Forensic Traces")
    for r in lost_transactions:
        report.append("```json")
        report.append(json.dumps(r, indent=2))
        report.append("```")
        
    report.append("")
    report.append("## Engineering Recommendation")
    report.append("*(Auto-generated based on highest classifications)*")
    
    top_cat = max(classifications.items(), key=lambda x: x[1], default=("None", 0))[0]
    report.append(f"\n**Primary Remaining Defect**: {top_cat}")
    
    if top_cat == "ROW_MERGE_COLLAPSE":
        report.append("\n**Recommendation**: Fixing row merge logic is HIGH RISK. Row merge keeps multiline narrations together. Tuning it to split merged rows might fracture hundreds of valid transactions. Given this affects extremely few rows, it is likely NOT worth the engineering effort to redesign `detect_transaction_blocks`.")
    elif top_cat == "TRUE_OCR_FAILURE":
        report.append("\n**Recommendation**: True OCR failure means the text is physically absent or unreadable. Do NOT fix. It is impossible to safely guess missing dates/amounts without hallucination.")
    elif top_cat == "POLICY_REJECT":
        report.append("\n**Recommendation**: Policy rejects can be safely relaxed if the candidate score is extremely high (e.g., has date, has amount, but is missing balance). LOW RISK, HIGH REWARD.")
    elif top_cat == "PAGE_BOUNDARY_COLLAPSE":
        report.append("\n**Recommendation**: Enhance header suppression logic to aggressively strip header/footer keywords from the token stream BEFORE row merge. MEDIUM RISK.")

    with open(ROOT / "FINAL_18_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    run_audit()
