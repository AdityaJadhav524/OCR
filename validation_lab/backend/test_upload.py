import requests
import os

url = "http://127.0.0.1:8000/api/process"
filepath = r"C:\Users\adity\Downloads\DetailedStatement24-25 2.pdf"

if os.path.exists(filepath):
    print("Uploading file...")
    with open(filepath, "rb") as f:
        files = {"file": f}
        try:
            response = requests.post(url, files=files)
            print(f"Status Code: {response.status_code}")
            # print(response.json())
        except Exception as e:
            print(f"Request failed: {e}")
else:
    print("File not found")
