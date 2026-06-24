import sys
sys.path.insert(0, '.')
from core.parsers.coordinate_parser_v2 import CONSERVATION_TOLERANCE

# Simulate the direction correction logic
txns = [
    # Row where OCR put 500 in debit, but ledger says balance went UP (credit expected)
    {
        'debit': 500.0, 'credit': None, 'balance': 10500.0,
        'ledger_truth': {'available': True, 'expected_direction': 'credit', 'expected_delta': 500.0}
    },
    # Row where OCR put 200 in credit, but ledger says balance went DOWN (debit expected)
    {
        'debit': None, 'credit': 200.0, 'balance': 10300.0,
        'ledger_truth': {'available': True, 'expected_direction': 'debit', 'expected_delta': 200.0}
    },
    # Row that is CORRECT — should NOT be changed
    {
        'debit': 300.0, 'credit': None, 'balance': 10000.0,
        'ledger_truth': {'available': True, 'expected_direction': 'debit', 'expected_delta': 300.0}
    },
    # Row with UNSEEDED (first row) — should NOT be changed
    {
        'debit': 100.0, 'credit': None, 'balance': 9900.0,
        'ledger_truth': {'available': False}
    }
]

corrections = 0
for txn in txns:
    lt = txn.get('ledger_truth', {})
    if not lt.get('available'):
        continue
    led_dir = lt.get('expected_direction')
    led_amt = lt.get('expected_delta', 0)
    ocr_dr = txn.get('debit')
    ocr_cr = txn.get('credit')
    ocr_dir = 'debit' if ocr_dr is not None else ('credit' if ocr_cr is not None else None)
    if ocr_dir is None or led_dir is None or led_dir == 'none':
        continue
    direction_match = (ocr_dir == led_dir)
    ocr_amount = ocr_dr if ocr_dr is not None else ocr_cr
    amount_match = ocr_amount is not None and abs(ocr_amount - led_amt) <= CONSERVATION_TOLERANCE
    if not direction_match and amount_match:
        if ocr_dir == 'debit':
            txn['credit'] = txn['debit']
            txn['debit'] = None
        else:
            txn['debit'] = txn['credit']
            txn['credit'] = None
        corrections += 1

print(f'Corrections made: {corrections}')
for i, t in enumerate(txns):
    d = t['debit']
    c = t['credit']
    print(f'  Row {i}: debit={d} credit={c}')

assert corrections == 2, f'Expected 2 corrections, got {corrections}'
assert txns[0]['debit'] is None and txns[0]['credit'] == 500.0, 'Row 0 should now be credit'
assert txns[1]['debit'] == 200.0 and txns[1]['credit'] is None, 'Row 1 should now be debit'
assert txns[2]['debit'] == 300.0 and txns[2]['credit'] is None, 'Row 2 should be unchanged'
assert txns[3]['debit'] == 100.0, 'Row 3 (unseeded) should be unchanged'
print('All assertions passed!')
