import requests, json

pdf_path = r'z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf'
print('Testing:', pdf_path)
with open(pdf_path, 'rb') as f:
    resp = requests.post('http://127.0.0.1:8000/api/process', files={'file': f}, timeout=600)

print('HTTP STATUS:', resp.status_code)
try:
    data = resp.json()
    with open(r'z:\CA\debug\last_api_response.json', 'w') as out_f:
        json.dump(data, out_f, indent=2)
    print('Response saved to debug/last_api_response.json')
    
    print('SUCCESS:', data.get('success'))
    for stage in data.get('stages', []):
        name = stage['name']
        status = stage['status']
        time = stage.get('time_taken_ms', 0)
        print(f"  - {name}: {status} ({time}ms)")
        if status == 'ERROR':
            print('    ERROR:', stage.get('error'))
            
except Exception as e:
    print('Failed to parse JSON:', e)
    print('RAW Response:', resp.text[:1000])
