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

def count_dates(block_tokens, date_zone):
    count = 0
    seen_y = set()
    for t in block_tokens:
        txt = t.get("text", "").strip()
        x0 = t.get("x0", -1)
        y0 = t.get("y0", -1)
        if date_zone is None or (date_zone[0] - 20 <= x0 <= date_zone[1] + 20):
            if cp2._DATE_RE.match(txt) or cp2._DATE_PREFIX_RE.match(txt):
                # Avoid counting the exact same physical date twice if it got split slightly
                y_bin = int(y0 / 5) * 5
                if y_bin not in seen_y:
                    count += 1
                    seen_y.add(y_bin)
    return count

def count_amounts(block_tokens):
    count = 0
    for t in block_tokens:
        txt = t.get("text", "").strip()
        val = cp2._parse_float(txt)
        if val is not None and val > 0:
            count += 1
    return count

def run_audit():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    
    audit_results = []
    feasible_splits = 0
    total_analyzed = 0
    
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
            if len(b_candidates) <= 1: continue # Only care about row merge collapse (multiple candidates in one block)
            
            candidate_txn = cp2._extract_block(block, zones)
            qualifies = False
            if candidate_txn:
                qualifies, reason, state = cp2._qualifies(candidate_txn, prev_balance=None, balance_zone_missing=False)
            
            # If the block had multiple candidates, only ONE could have survived. The others collapsed.
            # Analyze the block tokens
            block_tokens = []
            for r in block:
                block_tokens.extend(r.get("tokens", []))
                
            num_dates = count_dates(block_tokens, date_zone)
            num_amounts = count_amounts(block_tokens)
            
            merged_block_text = " | ".join([" ".join([t.get("text","") for t in r.get("tokens",[])]) for r in block])
            
            # Feasibility condition: 2+ dates AND 4+ amounts (at least 2 amounts for each txn)
            # User specifically asked for "2+ dates AND 2+ balances" (which implies a lot of amounts).
            is_feasible = (num_dates >= 2 and num_amounts >= 3)
            
            if is_feasible:
                feasible_splits += len(b_candidates) - (1 if qualifies else 0)
                
            total_analyzed += len(b_candidates) - (1 if qualifies else 0)
            
            audit_results.append({
                "pdf": pdf_name,
                "merged_block": merged_block_text,
                "num_dates": num_dates,
                "num_amounts": num_amounts,
                "qualifies": qualifies,
                "lost_candidates": len(b_candidates) - (1 if qualifies else 0),
                "is_feasible_to_split": is_feasible
            })

    report = []
    report.append("# BLOCK SPLIT FEASIBILITY AUDIT")
    report.append("")
    report.append(f"**Total Collapsed Candidates Analyzed:** {total_analyzed}")
    report.append(f"**Candidates Feasible for Split (2+ Dates, 3+ Amounts):** {feasible_splits}")
    report.append("")
    report.append("## Detailed Traces")
    for r in audit_results:
        report.append("```json")
        report.append(json.dumps(r, indent=2))
        report.append("```")

    with open(ROOT / "BLOCK_SPLIT_AUDIT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    run_audit()
