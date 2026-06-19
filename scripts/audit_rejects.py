import os
import json
import glob
from collections import defaultdict
from core.adapters.ocr_subprocess import extract_via_subprocess

from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.detection.header_suppression import suppress_headers_and_footers
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns

def audit_pdf(pdf_path):
    print(f"Auditing {os.path.basename(pdf_path)}...")
    full_text, image_paths, ocr_tree, pages = extract_via_subprocess(pdf_path, password="1170AKSH")
    
    # Flatten tokens
    page_tokens = []
    for page in pages:
        p_num = page.get("page", 1)
        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                for word in line.get("words", []):
                    word["page"] = p_num
                    page_tokens.append(word)
    
    # Standard pipeline
    filtered_tokens = suppress_headers_and_footers(page_tokens)
    rows = detect_rows(filtered_tokens)
    zones, headers = detect_columns(rows)
    blocks = detect_transaction_blocks(rows, zones.get("date_zone"))
    
    # Run parser
    txns, telemetry = parse_with_coordinates(blocks, zones)
    
    reject_log = telemetry.get("reject_log", [])
    reject_reasons = defaultdict(int)
    for r in reject_log:
        reject_reasons[r.get("reason", "UNKNOWN")] += 1
        
    return {
        "detected": len(blocks),
        "parsed": len(blocks),  # Coordinate parser processes all detected blocks
        "accepted": len(txns),
        "rejected": len(reject_log),
        "reject_reasons": dict(reject_reasons)
    }

def main():
    pdf_dir = r"C:\Users\adity\Downloads\CA\tests\pdfs"
    pdfs = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    
    results = {}
    
    for pdf_path in pdfs:
        bank_name = os.path.basename(pdf_path).split('_')[0]
        try:
            stats = audit_pdf(pdf_path)
            results[bank_name] = stats
        except Exception as e:
            print(f"Error on {bank_name}: {e}")
            
    print("\n--- REJECT HISTOGRAM ACROSS ALL BANKS ---")
    print(f"{'Bank':<10} | {'Detected':>8} | {'Parsed':>8} | {'Accepted':>8} | {'Rejected':>8} | {'Top Reject Reason'}")
    print("-" * 80)
    for bank, stats in results.items():
        top_reason = "NONE"
        if stats["reject_reasons"]:
            top_reason = max(stats["reject_reasons"].items(), key=lambda x: x[1])[0]
        print(f"{bank:<10} | {stats['detected']:>8} | {stats['parsed']:>8} | {stats['accepted']:>8} | {stats['rejected']:>8} | {top_reason}")

    # Specific audit for the BOI file
    print("\n\n--- DETAILED REJECT HISTOGRAM FOR BOI ---")
    boi_file = os.path.join(pdf_dir, "BOI_SAVINGS_SCANNED.pdf")
    if os.path.exists(boi_file):
        stats = audit_pdf(boi_file)
        print(f"PDF: {os.path.basename(boi_file)}")
        print(f"rows_detected: {stats['detected']}")
        print(f"rows_accepted: {stats['accepted']}")
        print(f"rows_rejected: {stats['rejected']}")
        print("top_reject_reasons:")
        for reason, count in sorted(stats["reject_reasons"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {reason} = {count}")

if __name__ == "__main__":
    main()
