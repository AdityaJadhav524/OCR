import sys, os, difflib
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

TEMP_DIR = ROOT / "validation_lab" / "backend" / "temp"

def find_file(name_substring: str) -> Path:
    import glob
    pattern = str(TEMP_DIR / f"*{name_substring}*")
    matches = glob.glob(pattern)
    if not matches:
        raise FileNotFoundError(f"No temp files matching {name_substring}")
    return Path(sorted(matches, key=os.path.getmtime)[-1])

def main():
    if len(sys.argv) < 2:
        print("Usage: python discovery_diff.py <pdf_filename_substring>")
        sys.exit(1)
        
    pdf_substring = sys.argv[1]
    pdf_path = find_file(pdf_substring)
    print(f"Comparing on: {pdf_path.name}\n")
    
    from core.extractors.document_router import route_document, detect_document_type
    from core.detection.bank_detector import classify_document_llm
    from core.parsers.coordinate_parser_v2 import parse_with_coordinates
    from core.discovery.transaction_discovery import discover_transactions
    
    doc_type, _ = detect_document_type(str(pdf_path))
    full_text, pages, tel, page_tokens = route_document(str(pdf_path))
    identity = classify_document_llm(pages)
    bank = identity.get("bank", "UNKNOWN")
    detected_pdf_type = "SCANNED" if doc_type == "scanned" else "DIGITAL"
    
    print("Running V2 Legacy Parser...")
    v2_txns, _ = parse_with_coordinates(
        page_tokens,
        pdf_name=pdf_path.name,
        statement_id="diff",
        job_id="diff",
        bank=bank,
        pdf_type=detected_pdf_type,
        identity=identity
    )
    
    print("Running Discovery Engine...")
    disc_candidates = discover_transactions(page_tokens)
    
    # Matching
    matched_v2 = set()
    matched_disc = set()
    shared = []
    
    for i, d in enumerate(disc_candidates):
        best_match_j = -1
        best_ratio = 0
        d_clean = "".join(d.raw_text.lower().split())
        
        for j, v in enumerate(v2_txns):
            if j in matched_v2: continue
            v_text = v.get("raw_text", "")
            
            if not v_text:
                # Fallback to checking date + amount
                date = str(v.get("date", "")).lower()
                amt_float = float(v.get("credit") or v.get("debit") or 0.0)
                
                # Check if date is in text
                date_in_text = date in d.raw_text.lower()
                
                # Check if amount is in text (by extracting all numbers from text)
                import re
                numbers_in_text = re.findall(r'[\d,]+\.\d+|\d+', d.raw_text)
                floats_in_text = []
                for n in numbers_in_text:
                    try: floats_in_text.append(float(n.replace(',', '')))
                    except: pass
                    
                amt_in_text = any(abs(f - amt_float) < 0.01 for f in floats_in_text)
                
                if date and amt_float > 0 and date_in_text and amt_in_text:
                    best_match_j = j
                    best_ratio = 1.0
                    break
                continue
                
            v_clean = "".join(v_text.lower().split())
            ratio = difflib.SequenceMatcher(None, v_clean, d_clean).ratio()
            
            if v_clean in d_clean or d_clean in v_clean:
                ratio = max(ratio, 0.8)
                
            if ratio > 0.6 and ratio > best_ratio:
                best_ratio = ratio
                best_match_j = j
                
        if best_match_j != -1:
            matched_disc.add(i)
            matched_v2.add(best_match_j)
            shared.append((d, v2_txns[best_match_j]))
            
    disc_only = [d for i, d in enumerate(disc_candidates) if i not in matched_disc]
    v2_only = [v for j, v in enumerate(v2_txns) if j not in matched_v2]
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"V2 Transactions : {len(v2_txns)}")
    print(f"Discovery Cand  : {len(disc_candidates)}")
    print(f"Shared          : {len(shared)}")
    print(f"Discovery-only  : {len(disc_only)}")
    print(f"V2-only         : {len(v2_only)}")
    print("="*50 + "\n")
    
    if disc_only:
        import json
        print("=== DISCOVERY ONLY ===")
        for d in disc_only:
            # Reconstruct the classification dictionary
            output = {
                "source": "DISCOVERY_ONLY",
                "page": d.page,
                "raw_text": d.raw_text,
                "scores": {
                    "transaction": getattr(d, 'transaction_score', 0),
                    "header": getattr(d, 'header_score', 0),
                    "footer": getattr(d, 'footer_score', 0)
                },
                "signals": getattr(d, 'signals', {}),
                "classification": "FALSE_POSITIVE" # Default to false positive for now, will manual review
            }
            print(json.dumps(output, indent=2))
            print("-" * 50)
            
    if v2_only:
        print("\n=== V2 ONLY ===")
        for v in v2_only:
            print(f"[Date: {v.get('date')} | Amount: {v.get('credit') or v.get('debit')}]")
            print(f"Text: {v.get('raw_text', '')}")
            print("-" * 50)

if __name__ == "__main__":
    main()
