import json, os

export_path = 'c:/Users/adity/Downloads/CA/audit_export/benchmark_export.json'
if os.path.exists(export_path):
    with open(export_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        items = data.values() if isinstance(data, dict) else data
        for entry in items:
            print(f"{entry.get('pdf_name')} | {entry.get('bank')}")
else:
    print("benchmark_export.json not found")
