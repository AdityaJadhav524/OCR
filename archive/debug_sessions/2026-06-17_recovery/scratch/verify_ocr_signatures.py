import sys
sys.stdout.reconfigure(encoding='utf-8')
from core.validators.ocr_signature_detector import detect_ocr_signatures

tests = [
    ('2.00000 debit', '2.00000', None, '260065.93', '31/11/21', None, None, {}),
    ('260.065.93 balance', None, None, '260.065.93', None, None, None, {}),
    ('date merge', None, None, None, '07/02/22UPI-HARPREET SINGH', None, None, {}),
    ('clean row', '5000.00', None, '314919.10', '03/11/21', None, None, {}),
    ('column boundary', '1900', None, '286210.6', None, 1008.0, None,
        {'debit_zone': [1007.0, 1221.0], 'credit_zone': [1221.0, 1407.0]}),
]

for name, dr, cr, br, dt, dx, cx, zones in tests:
    r = detect_ocr_signatures(dr, cr, br, dt, dx, cx, zones)
    keys = list(r.keys()) if r else []
    reasons = {k: v.get('reason', str(v)) for k, v in r.items()} if r else {}
    result = 'CLEAN' if not r else str(reasons)
    print(f'[{name}] -> {result}')
