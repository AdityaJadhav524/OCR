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

def run_audit():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    
    total_rejected = 0
    classifications = defaultdict(int)
    audit_results = []
    
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
        for r in raw_rows:
            if score_raw_row(r, date_zone) >= 8:
                candidate_ids.add(id(r))
                
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
            if not candidate_txn: continue
            
            qualifies, reason, state = cp2._qualifies(candidate_txn, prev_balance=None, balance_zone_missing=False)
            
            if not qualifies and reason == "both_debit_and_credit":
                total_rejected += 1
                
                raw_extracted = candidate_txn.get("raw_extraction", {})
                debit_candidate = raw_extracted.get("parsed_debit")
                credit_candidate = raw_extracted.get("parsed_credit")
                balance_candidate = raw_extracted.get("parsed_balance")
                
                # Get all numerical tokens in the block
                all_tokens = candidate_txn.get("_source_tokens", [])
                
                # Find all numbers
                numbers = []
                rightmost_numeric_val = None
                rightmost_x = -1
                balance_suffix = "null"
                
                for i, tok in enumerate(all_tokens):
                    txt = tok.get("text", "").strip()
                    val = cp2._parse_float(txt)
                    if val is not None and val > 0:
                        numbers.append(val)
                        if tok.get("x0", -1) > rightmost_x:
                            rightmost_x = tok.get("x0", -1)
                            rightmost_numeric_val = val
                            
                            # Check next token for CR/DR
                            if i + 1 < len(all_tokens):
                                nxt = all_tokens[i+1].get("text", "").strip().upper()
                                if nxt in ("CR", "DR"):
                                    balance_suffix = nxt
                            # Or check inside the same token (e.g. 210.78CR)
                            if "CR" in txt.upper(): balance_suffix = "CR"
                            if "DR" in txt.upper(): balance_suffix = "DR"
                            
                # Classification logic
                would_recover = False
                recovered_balance = None
                
                if rightmost_numeric_val is not None and balance_suffix in ("CR", "DR"):
                    if balance_candidate is None and rightmost_numeric_val in (debit_candidate, credit_candidate):
                        would_recover = True
                        recovered_balance = rightmost_numeric_val
                        if rightmost_numeric_val == credit_candidate:
                            category = "BALANCE_STOLEN_BY_CREDIT"
                        else:
                            category = "BALANCE_STOLEN_BY_DEBIT"
                            
                if not would_recover:
                    if debit_candidate and credit_candidate:
                        category = "TRUE_DOUBLE_AMOUNT"
                    else:
                        category = "OTHER"
                    
                classifications[category] += 1
                
                audit_results.append({
                    "pdf": pdf_name,
                    "date": candidate_txn.get("date"),
                    "current_debit": debit_candidate,
                    "current_credit": credit_candidate,
                    "current_balance": balance_candidate,
                    "rightmost_numeric": rightmost_numeric_val,
                    "suffix": balance_suffix,
                    "recovered_balance": recovered_balance,
                    "would_recover": would_recover
                })

    report = []
    report.append("# PRE_FIX_RECOVERY_ESTIMATE")
    report.append("")
    recoverable_rows = sum(1 for r in audit_results if r["would_recover"])
    non_recoverable_rows = len(audit_results) - recoverable_rows
    report.append(f"**Total Rejects Analysed:** {total_rejected}")
    report.append(f"**Recoverable Rows:** {recoverable_rows}")
    report.append(f"**Non-Recoverable Rows:** {non_recoverable_rows}")
    report.append("")
    report.append("## Classification Results")
    for cat, count in sorted(classifications.items(), key=lambda x: x[1], reverse=True):
        report.append(f"- **{cat}**: {count}")
        
    report.append("")
    report.append("## Detailed Traces (Sample of 50)")
    for r in audit_results[:50]:
        report.append("```json")
        report.append(json.dumps(r, indent=2))
        report.append("```")

    with open(ROOT / "PRE_FIX_RECOVERY_ESTIMATE.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    run_audit()
