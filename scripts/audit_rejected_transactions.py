import os
import json
from pathlib import Path
from core.extractors.document_router import _extract_digital
from core.layout.row_detector import detect_transaction_blocks
from core.parsers.coordinate_parser_v2 import parse_with_coordinates, _extract_block, _qualifies, _extract_page_balance_seeds
from core.layout.column_detector import detect_columns

def run_audit(pdf_path: str):
    print(f"--- REJECTED TRANSACTION AUDIT ---")
    print(f"Document: {pdf_path}")
    
    # 1. OCR Extract
    full_text, pages, ext_stats, page_tokens = _extract_digital(pdf_path)
    
    # 2. Row Detection
    blocks = detect_transaction_blocks(page_tokens)
    
    # 3. Zones
    column_zones = detect_columns(page_tokens)
    
    # 4. We will hook into the parser by running _parse_block and _qualifies manually on the blocks
    rejected_count = 0
    missing_transactions = []
    
    prev_balance = None
    balance_zone_missing = "balance_zone" not in column_zones
    
    # First, get page seeds
    page_seeds = _extract_page_balance_seeds(blocks)
    
    for row in blocks:
        page_num = row.get("page", 1)
        if page_num in page_seeds and page_seeds[page_num] is not None:
            prev_balance = page_seeds[page_num]
            page_seeds[page_num] = None
            
        # Parse block
        candidate = _extract_block(row, column_zones)
        
        # Qualify
        passes, reason, agreement = _qualifies(candidate, prev_balance, balance_zone_missing)
        
        if passes:
            if agreement != "CONFLICT":
                prev_balance = candidate.get("balance")
            else:
                prev_balance = candidate.get("balance")
        else:
            rejected_count += 1
            if candidate.get("date"):
                missing_transactions.append({
                    "row": rejected_count, 
                    "page": page_num,
                    "ocr_tokens": " ".join([t.get("text", "") for t in row.get("tokens", [])]),
                    "parsed_debit": candidate.get("debit"),
                    "parsed_credit": candidate.get("credit"),
                    "parsed_balance": candidate.get("balance"),
                    "expected_balance": prev_balance,
                    "reject_reason": reason
                })

    for tx in missing_transactions:
        print("\n------------------------------------------------")
        print(f"Page: {tx['page']} | Reject Index: {tx['row']}")
        print(f"Tokens: {tx['ocr_tokens']}")
        print(f"Parsed Debit: {tx['parsed_debit']}")
        print(f"Parsed Credit: {tx['parsed_credit']}")
        print(f"Parsed Balance: {tx['parsed_balance']}")
        print(f"Expected Balance: {tx['expected_balance']}")
        print(f"Reject Reason: {tx['reject_reason']}")
        
    print("\n------------------------------------------------")
    print(f"Total Rejected Rows: {rejected_count}")
    print(f"Missing Date-Anchored Transactions: {len(missing_transactions)}")

if __name__ == "__main__":
    import glob
    # Target the latest PDF in temp
    pdf_files = glob.glob("validation_lab/backend/temp/*.pdf")
    if pdf_files:
        latest = max(pdf_files, key=os.path.getmtime)
        run_audit(latest)
    else:
        print("No PDF found")
