import os
import json
import logging
from pathlib import Path

# Adjust paths if necessary to run from CA root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.extractors.pdf_extractor import _fitz_page_text, FITZ_OK
import fitz

def find_latest_temp_file(corpus_file: str):
    TEMP_DIR = Path(__file__).resolve().parent.parent / "validation_lab" / "backend" / "temp"
    # Find matching directory
    matches = list(TEMP_DIR.glob(f"*{corpus_file}*"))
    if not matches:
        # Fallback to tests/pdfs
        fallback = Path(__file__).resolve().parent.parent / "tests" / "pdfs" / corpus_file
        if fallback.exists(): return fallback
        return None
    # Return most recently modified
    return Path(sorted(matches, key=os.path.getmtime)[-1])
logging.basicConfig(level=logging.ERROR)

def run_audit():
    pdfs_to_audit = [
        "axis.pdf",
        "24-25 -2 2.pdf",
        "YESBANK_SAVINGS_DIGITAL.pdf"
    ]
    
    bank_names = {
        "axis.pdf": "AXIS",
        "24-25 -2 2.pdf": "TJSB",
        "YESBANK_SAVINGS_DIGITAL.pdf": "YES"
    }
    
    print("# MERGE COMPRESSION AUDIT\n")
    print("| Bank | Avg Merge Ratio | Max Source Rows |")
    print("| ---- | --------------- | --------------- |")
    
    detailed_reports = []
    
    for pdf in pdfs_to_audit:
        pdf_path = find_latest_temp_file(pdf)
        if not pdf_path:
            print(f"Could not find {pdf}")
            continue
            
        doc = fitz.open(str(pdf_path))
        
        total_before = 0
        total_after = 0
        all_blocks = []
        all_block_counts = []
        
        for i in range(len(doc)):
            page = doc[i]
            t, stats, toks = _fitz_page_text(page, i)
            
            before = stats.get("before", 0)
            after = stats.get("after", 0)
            total_before += before
            total_after += after
            
            if "blocks" in stats and "block_counts" in stats:
                all_blocks.extend(stats["blocks"])
                all_block_counts.extend(stats["block_counts"])
                
        doc.close()
        
        ratio = (total_after / total_before) if total_before > 0 else 1.0
        
        if not all_block_counts:
            avg_block_rows = 1.0
            max_block_rows = 1
        else:
            avg_block_rows = sum(all_block_counts) / len(all_block_counts)
            max_block_rows = max(all_block_counts)
            
        print(f"| {bank_names[pdf].ljust(4)} | {ratio:.2f}            | {max_block_rows:<15} |")
        
        # Build detailed json for top blocks
        # Combine blocks and their counts
        paired = list(zip(all_blocks, all_block_counts)) if len(all_blocks) == len(all_block_counts) else []
        
        # Sort by source rows descending
        paired.sort(key=lambda x: x[1], reverse=True)
        top_20 = paired[:20]
        
        report = {
            "pdf": pdf,
            "rows_before": total_before,
            "rows_after": total_after,
            "ratio": round(ratio, 2),
            "largest_block_rows": max_block_rows,
            "avg_block_rows": round(avg_block_rows, 2),
            "top_20_merged_blocks": [
                {
                    "source_rows": count,
                    "merged_block": block
                }
                for block, count in top_20
            ]
        }
        detailed_reports.append(report)
        
    # Write full JSON report
    with open("MERGE_COMPRESSION_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(detailed_reports, f, indent=2)
        
    print("\nDetailed breakdown of top 20 blocks written to MERGE_COMPRESSION_REPORT.json")

if __name__ == "__main__":
    run_audit()
