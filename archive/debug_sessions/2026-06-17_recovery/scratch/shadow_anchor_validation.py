import sys, os, re
sys.path.append('c:/Users/adity/Downloads/CA')
from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns

DATE_RE = re.compile(
    r'\b('
    r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|'           
    r'\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|'           
    r'\d{1,2}[\s\-\.][A-Za-z]{3,9}[\s\-\.]\d{2,4}'  
    r')\b',
    re.IGNORECASE
)

DATE_PREFIX_RE = re.compile(
    r'^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\D',
    re.IGNORECASE
)

OCR_TOLERANT_DATE_RE = re.compile(
    r'^([OoDdl\d]{1,2}[\-\.\/\|\)][OoDdl\d]{1,2}[\-\.\/\|\)]\d{2,4}|'
    r'[OoDdl\d]{1,2}[\-\.\/\|\)]\d{2,4}|'
    r'[a-zA-Z]{3}[\-\.\/\|\)]\d{2,4})',
    re.IGNORECASE
)

import glob

temp_dir = "c:/Users/adity/Downloads/CA/validation_lab/backend/temp"

pdfs_to_test = {
    "Axis": glob.glob(f"{temp_dir}/JOB_*_axis.pdf")[0] if glob.glob(f"{temp_dir}/JOB_*_axis.pdf") else None,
    "YES": glob.glob(f"{temp_dir}/*YESBANK*.pdf")[-1] if glob.glob(f"{temp_dir}/*YESBANK*.pdf") else None,
    "HDFC": "c:/Users/adity/Downloads/CA/investigations/MINERU/output_hdfc_page12/hdfc_page12/ocr/hdfc_page12_layout.pdf", # Wait, I don't have HDFC PDF easily accessible. 
    # Actually, earlier I found: E_STATEMENT_... which is HDFC? Wait, E_STATEMENT is CC or HDFC? E-Statement is usually HDFC.
    "BOI": "c:/Users/adity/Downloads/CA/tests/BOI/BOI_01.pdf",
    "CC": glob.glob(f"{temp_dir}/*E_STATEMENT*.pdf")[-1] if glob.glob(f"{temp_dir}/*E_STATEMENT*.pdf") else None
}


report = "# SHADOW MODE ANCHOR VALIDATION\n\n"

for bank, pdf_path in pdfs_to_test.items():
    print(f"Processing {bank}...")
    if not os.path.exists(pdf_path):
        report += f"## {bank}\nFile not found.\n\n"
        continue
        
    _, pages, _, page_tokens = route_document(pdf_path)
    identity = classify_document_llm(pages)
    rows = detect_rows(page_tokens)
    zones, _ = detect_columns(rows, identity=identity)
    
    date_x_bounds = zones.get("date_zone")
    if not date_x_bounds:
        report += f"## {bank}\nNo date zone detected.\n\n"
        continue

    original_anchors = 0
    recovered_by_joining = 0
    recovered_by_tolerant = 0
    
    joining_samples = []
    tolerant_samples = []
    
    for row in rows:
        tokens = row.get("tokens", [])
        if not tokens: continue
        
        # 1. Current Logic
        is_anchor = False
        for t in tokens:
            if DATE_RE.search(t['text']) or DATE_PREFIX_RE.match(t['text']):
                if date_x_bounds[0] - 70 <= t['x0'] <= date_x_bounds[1] + 70:
                    is_anchor = True
                    break
                elif t['x0'] < 150:
                    is_anchor = True
                    break
                    
        if is_anchor:
            original_anchors += 1
            continue
            
        # 2. Token Joining Recovery
        date_col_tokens = [t for t in tokens if date_x_bounds[0] - 20 <= t['x0'] <= date_x_bounds[1] + 20]
        if not date_col_tokens:
            continue
            
        joined_text = "".join(t['text'] for t in date_col_tokens)
        
        # We also need to add word boundaries if we want to match DATE_RE, or just match strictly
        if DATE_RE.search(joined_text) or DATE_PREFIX_RE.match(joined_text):
            recovered_by_joining += 1
            joining_samples.append(joined_text)
            continue
            
        # 3. Tolerant Regex Recovery
        if OCR_TOLERANT_DATE_RE.search(joined_text):
            recovered_by_tolerant += 1
            tolerant_samples.append(joined_text)
            continue

    report += f"## {bank}\n"
    report += f"- Original Anchors: {original_anchors}\n"
    report += f"- Recovered by Token Joining: {recovered_by_joining}\n"
    report += f"- Recovered by Tolerant Regex: {recovered_by_tolerant}\n"
    
    if joining_samples:
        report += "\n**Samples (Token Joining):**\n"
        for s in joining_samples[:10]:
            report += f"- {s}\n"
            
    if tolerant_samples:
        report += "\n**Samples (Tolerant Regex):**\n"
        for s in tolerant_samples[:10]:
            report += f"- {s}\n"
            
    report += "\n---\n\n"

with open('C:/Users/adity/.gemini/antigravity-ide/brain/a91c24b3-da82-413c-9098-5cc87be0fb55/AXIS_SHADOW_RECOVERY.md', 'w') as f:
    f.write(report)
    
print("Shadow validation completed.")
