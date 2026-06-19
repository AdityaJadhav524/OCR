import os
import time
import requests
import json
import glob

API_URL = "http://localhost:8000/api/benchmark/upload"
STATUS_URL = "http://localhost:8000/api/benchmark/status/{}"

def load_truth(truth_path):
    if not os.path.exists(truth_path):
        return None
    with open(truth_path, 'r') as f:
        return json.load(f)

def run_test(pdf_path, password=None):
    if not os.path.exists(pdf_path):
        return None
    
    data = {}
    if password:
        data["password"] = password
        
    with open(pdf_path, "rb") as f:
        res = requests.post(API_URL, files={"files": f}, data=data)
        
    if res.status_code != 200:
        return {"error": f"Upload failed: {res.text}"}
        
    job_id = res.json().get("job_id")
    if not job_id:
        return {"error": "Failed to upload"}
        
    while True:
        status_res = requests.get(STATUS_URL.format(job_id)).json()
        if status_res.get("status") in ["completed", "error"]:
            if status_res.get("results"):
                return status_res["results"][0]
            return {"error": status_res.get("error")}
        time.sleep(1)

pdf_dir = r"C:\Users\adity\Downloads\CA\tests\pdfs"
truth_dir = r"C:\Users\adity\Downloads\CA\tests\ground_truth"

# Find all PDFs in the pdf_dir
pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))

passwords = {
    "BOI_SAVINGS_DIGITAL.pdf": "11707454011"
}

results_table = []
healed_audit_log = []

print(f"Found {len(pdf_files)} PDFs in {pdf_dir}")

for pdf_path in pdf_files:
    pdf_name = os.path.basename(pdf_path)
    truth_name = pdf_name.replace('.pdf', '.truth.json')
    truth_path = os.path.join(truth_dir, truth_name)
    
    truth = load_truth(truth_path)
    if not truth:
        results_table.append(f"{pdf_name:25} | NO TRUTH FILE FOUND")
        continue
        
    pwd = passwords.get(pdf_name)
    
    print(f"Testing {pdf_name}...")
    res = run_test(pdf_path, pwd)
    
    if not res:
        results_table.append(f"{pdf_name:25} | FAILED TO RUN")
        continue
        
    if res.get("status") != "success":
        results_table.append(f"{pdf_name:25} | ERROR: {res.get('status')} {res.get('error_code', '')}")
        continue
        
    transactions = res.get("transactions", [])
    accepted_txns = [t for t in transactions if t.get('agreement_state') in ['FULL_AGREEMENT', 'PARTIAL_AGREEMENT', 'UNSEEDED']]
    
    # Actually, the truth compares ALL extracted valid transactions
    # Wait, the regression script should sum the DEBITS and CREDITS
    actual_count = len(accepted_txns)
    actual_debit = sum(t.get('debit', 0) for t in accepted_txns if t.get('debit') is not None)
    actual_credit = sum(t.get('credit', 0) for t in accepted_txns if t.get('credit') is not None)
    
    if accepted_txns:
        actual_balance = accepted_txns[-1].get('balance')
    else:
        actual_balance = 0.0
        
    healed_txns = [t for t in transactions if t.get("audit_trail", {}).get("healed")]
    actual_healed = len(healed_txns)
    
    for h in healed_txns:
        healed_audit_log.append({
            "pdf": pdf_name,
            "date": h.get("date"),
            "reason": h.get("audit_trail", {}).get("healing_reason"),
            "ocr": h.get("audit_trail", {}).get("ocr_value"),
            "corrected": h.get("audit_trail", {}).get("corrected_value")
        })

    # Compare with truth
    exp_count = truth.get('expected_transactions', 0)
    exp_debit = truth.get('expected_debit_total', 0.0)
    exp_credit = truth.get('expected_credit_total', 0.0)
    exp_balance = truth.get('closing_balance', 0.0)
    exp_healed = truth.get('expected_healed_rows', 0)
    
    # We allow small floating point differences
    def is_close(a, b, tol=0.01):
        if a is None and b is None: return True
        if a is None or b is None: return False
        return abs(float(a) - float(b)) <= tol

    pass_count = actual_count == exp_count
    pass_debit = is_close(actual_debit, exp_debit)
    pass_credit = is_close(actual_credit, exp_credit)
    pass_balance = is_close(actual_balance, exp_balance)
    pass_healed = actual_healed == exp_healed
    
    if pass_count and pass_debit and pass_credit and pass_balance and pass_healed:
        result_str = "PASS"
    else:
        result_str = "FAIL"
        
    row = f"{pdf_name:25} | C:{actual_count}/{exp_count} {'[OK]' if pass_count else '[X]'} | D:{actual_debit:.2f}/{exp_debit:.2f} {'[OK]' if pass_debit else '[X]'} | C:{actual_credit:.2f}/{exp_credit:.2f} {'[OK]' if pass_credit else '[X]'} | B:{actual_balance}/{exp_balance} {'[OK]' if pass_balance else '[X]'} | H:{actual_healed}/{exp_healed} {'[OK]' if pass_healed else '[X]'} | {result_str}"
    results_table.append(row)

print("\n\n--- REGRESSION TEST RESULTS ---")
print("PDF                       | Count       | Debit               | Credit              | Balance             | Healed  | Result")
print("-" * 120)
for r in results_table:
    print(r)

if healed_audit_log:
    print("\n--- HEALED ROWS AUDIT LOG ---")
    for log in healed_audit_log:
        print(f"{log['pdf']}: {log['date']} | {log['reason']} | {log['ocr']} -> {log['corrected']}")

# Write MD
md_content = "# Full Regression Matrix\n\n"
md_content += "| PDF | Count (Act/Exp) | Debit (Act/Exp) | Credit (Act/Exp) | Balance (Act/Exp) | Healed (Act/Exp) | Result |\n"
md_content += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
for r in results_table:
    if "ERROR" in r or "NOT FOUND" in r or "FAILED" in r:
        parts = [p.strip() for p in r.split('|')]
        md_content += f"| {parts[0]} | - | - | - | - | - | {parts[1]} |\n"
    else:
        parts = [p.strip() for p in r.split('|')]
        md_content += f"| {parts[0]} | {parts[1]} | {parts[2]} | {parts[3]} | {parts[4]} | {parts[5]} | **{parts[6]}** |\n"

with open(r'C:\Users\adity\.gemini\antigravity-ide\brain\a91c24b3-da82-413c-9098-5cc87be0fb55\REGRESSION_RESULTS.md', 'w', encoding='utf-8') as f:
    f.write(md_content)
