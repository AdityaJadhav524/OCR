import requests

url = "http://127.0.0.1:8000/api/process"
pdf_path = r"Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf"

try:
    with open(pdf_path, 'rb') as f:
        files = {'file': ('YESBANK_page-0001.pdf', f, 'application/pdf')}
        print("Sending request to API...")
        response = requests.post(url, files=files)
        response.raise_for_status()
        data = response.json()
        
        txns = data.get("transactions", [])
        print(f"API Returned {len(txns)} transactions")
        
        if len(txns) > 0:
            print(f"First transaction: {txns[0].get('date')} - {txns[0].get('balance')}")
            print(f"Last transaction: {txns[-1].get('date')} - {txns[-1].get('balance')}")
            
except Exception as e:
    print(f"Error: {e}")
