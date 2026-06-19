import sys
import json
sys.path.append('C:/Users/adity/Downloads/CA')
from pipeline import run_pipeline

res = run_pipeline(r'C:\Users\adity\Downloads\CA\AccountStatement_01-DEC-2025_to_31-DEC-2025 (1).pdf', 'test_job')
print(f"Total accepted: {len(res.get('transactions', []))}")
if res.get('telemetry'):
    print(f"V2 telemetry: {res['telemetry']}")
