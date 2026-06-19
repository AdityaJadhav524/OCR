import os
import json
import glob

audit_dir = r'c:\Users\adity\Downloads\CA\tests\audit_reports'
files = glob.glob(os.path.join(audit_dir, '*_audit.json'))

print('| Bank | Top Reject Reason | % |')
print('| ---- | ----------------- | ---- |')

for fpath in files:
    with open(fpath, 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            continue
            
        bank = os.path.basename(fpath).replace('_audit.json', '')
        reasons = data.get('reject_reasons', {})
        total_rejects = data.get('rows_rejected', 0)
        
        if total_rejects == 0:
            print(f'| {bank} | NONE | 0% |')
            continue
            
        top_reason = max(reasons.items(), key=lambda x: x[1])
        pct = (top_reason[1] / total_rejects) * 100
        print(f'| {bank} | {top_reason[0]} | {pct:.1f}% |')
