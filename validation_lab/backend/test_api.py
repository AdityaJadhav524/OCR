import requests
import time

url = "http://127.0.0.1:8000/api/benchmark/upload"
files = [
    ('files', open(r'C:\Users\adity\Downloads\CA\AccountStatement_01-Feb-2026_20-Feb-2026 5.pdf', 'rb'))
]
response = requests.post(url, files=files)
print(response.json())
job_id = response.json()['job_id']

while True:
    time.sleep(2)
    res = requests.get(f"http://127.0.0.1:8000/api/benchmark/status/{job_id}")
    data = res.json()
    print(data['status'])
    if data['status'] in ('completed', 'error'):
        print("Total results:", len(data.get('results', [])))
        if data.get('results'):
            print("Transactions:", len(data['results'][0].get('transactions', [])))
        break
