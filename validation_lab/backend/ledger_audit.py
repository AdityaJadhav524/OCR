"""
Ledger-First Corpus Audit
=========================
For each unique PDF in the temp directory (by base name, deduped), run
the full pipeline and compare:
  - OCR-assigned debit/credit (from column geometry)
  - Ledger-derived debit/credit (from balance delta math)

Reports per-bank MATCH / MISMATCH / UNSEEDED rates.
"""
import sys, os, logging, json, hashlib
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.WARNING)  # suppress noise
sys.path.insert(0, 'c:/Users/adity/Downloads/CA')

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth

TEMP_DIR = Path(r'c:\Users\adity\Downloads\CA\validation_lab\backend\temp')

# --- select unique PDFs by original filename (ignore JOB_ prefixed copies) ---
seen_names = set()
pdf_paths = []
for p in sorted(TEMP_DIR.glob("*.pdf")) + sorted(TEMP_DIR.glob("*.PDF")):
    name = p.name
    # skip JOB_ prefixed duplicates
    if name.startswith("JOB_"):
        continue
    if name not in seen_names:
        seen_names.add(name)
        pdf_paths.append(p)

# Also grab one copy of each JOB-prefixed name if no plain copy exists
job_seen = set()
for p in sorted(TEMP_DIR.glob("JOB_*.pdf")) + sorted(TEMP_DIR.glob("JOB_*.PDF")):
    # strip the JOB_YYYYMMDD_HHMMSS_XXXX_ prefix
    parts = p.name.split("_", 4)
    if len(parts) == 5:
        base = parts[4]
    else:
        base = p.name
    if base not in seen_names and base not in job_seen:
        job_seen.add(base)
        pdf_paths.append(p)

print(f"Total unique PDFs to audit: {len(pdf_paths)}")
print()

stats = defaultdict(lambda: {"match": 0, "mismatch": 0, "direction_flip": 0, "unseeded": 0, "total": 0})
rows = []

for pdf_path in pdf_paths:
    try:
        doc_type, _ = detect_document_type(str(pdf_path))
        full_text, pages, telemetry, page_tokens = route_document(str(pdf_path))
        identity = classify_document_llm(pages)
        bank = identity.get("institution_name", "Unknown")
        
        pdf_type = "SCANNED" if doc_type.upper() == "SCANNED" else "DIGITAL"
        txns, tel = parse_with_coordinates(
            page_tokens,
            pdf_name=pdf_path.name,
            statement_id="audit",
            job_id="audit",
            bank=bank,
            pdf_type=pdf_type,
            identity=identity
        )
        final_txns = annotate_ledger_truth(txns)
        
        for t in final_txns:
            lt = t.get("ledger_truth", {})
            ocr_dr = t.get("debit")
            ocr_cr = t.get("credit")
            
            if not lt.get("available"):
                stats[bank]["unseeded"] += 1
                stats[bank]["total"] += 1
                continue

            led_dir = lt.get("expected_direction")
            led_amt = lt.get("expected_delta", 0)
            
            # OCR direction
            if ocr_dr is not None:
                ocr_dir = "debit"
                ocr_amt = float(ocr_dr)
            elif ocr_cr is not None:
                ocr_dir = "credit"
                ocr_amt = float(ocr_cr)
            else:
                stats[bank]["unseeded"] += 1
                stats[bank]["total"] += 1
                continue

            amt_match = abs(ocr_amt - led_amt) <= 1.50
            dir_match = ocr_dir == led_dir

            if amt_match and dir_match:
                outcome = "MATCH"
                stats[bank]["match"] += 1
            elif dir_match and not amt_match:
                outcome = "AMT_MISMATCH"
                stats[bank]["mismatch"] += 1
            elif not dir_match:
                outcome = "DIR_FLIP"
                stats[bank]["direction_flip"] += 1
            else:
                outcome = "MISMATCH"
                stats[bank]["mismatch"] += 1
            
            stats[bank]["total"] += 1
            rows.append({
                "bank": bank,
                "pdf": pdf_path.name[:50],
                "date": t.get("date"),
                "ocr_dir": ocr_dir,
                "ocr_amt": ocr_amt,
                "led_dir": led_dir,
                "led_amt": led_amt,
                "outcome": outcome
            })
    except Exception as e:
        print(f"  ERROR {pdf_path.name[:50]}: {e}")

# --- Print report ---
print("=" * 70)
print(f"{'Bank':<30} {'Total':>6} {'MATCH':>7} {'DIR_FLIP':>9} {'AMT_MISM':>9} {'UNSEED':>7} {'MATCH%':>8}")
print("-" * 70)

grand = {"match": 0, "direction_flip": 0, "mismatch": 0, "unseeded": 0, "total": 0}
for bank, s in sorted(stats.items()):
    pct = (s["match"] / s["total"] * 100) if s["total"] > 0 else 0
    print(f"{bank[:30]:<30} {s['total']:>6} {s['match']:>7} {s['direction_flip']:>9} {s['mismatch']:>9} {s['unseeded']:>7} {pct:>7.1f}%")
    for k in grand:
        grand[k] += s[k]

print("-" * 70)
total = grand["total"]
pct = (grand["match"] / total * 100) if total > 0 else 0
print(f"{'GRAND TOTAL':<30} {total:>6} {grand['match']:>7} {grand['direction_flip']:>9} {grand['mismatch']:>9} {grand['unseeded']:>7} {pct:>7.1f}%")
print()

# Show some DIR_FLIP examples
flips = [r for r in rows if r["outcome"] == "DIR_FLIP"]
if flips:
    print(f"\n--- Direction Flips (first 10 of {len(flips)}) ---")
    for r in flips[:10]:
        print(f"  {r['bank'][:20]:<20} {r['date']} | OCR={r['ocr_dir']:6} {r['ocr_amt']:10.2f} | LED={r['led_dir']:6} {r['led_amt']:10.2f}")
