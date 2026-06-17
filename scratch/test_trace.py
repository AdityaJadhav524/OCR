import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

target_string = '81,510.17'
ocr_token = {'text': target_string, 'x0': 500, 'y0': 150, 'page': 1, 'x1': 550, 'y1': 160}
tokens = [
    {'text': 'Date', 'x0': 50, 'y0': 100, 'page': 1, 'x1': 80, 'y1': 110},
    {'text': 'Narration', 'x0': 150, 'y0': 100, 'page': 1, 'x1': 200, 'y1': 110},
    {'text': 'Withdrawal', 'x0': 300, 'y0': 100, 'page': 1, 'x1': 350, 'y1': 110},
    {'text': 'Deposit', 'x0': 400, 'y0': 100, 'page': 1, 'x1': 450, 'y1': 110},
    {'text': 'Balance', 'x0': 500, 'y0': 100, 'page': 1, 'x1': 550, 'y1': 110},
    
    {'text': '01/01/2026', 'x0': 50, 'y0': 115, 'page': 1, 'x1': 100, 'y1': 118},
    {'text': 'Txn1', 'x0': 150, 'y0': 115, 'page': 1, 'x1': 200, 'y1': 118},
    {'text': '0.00', 'x0': 300, 'y0': 115, 'page': 1, 'x1': 330, 'y1': 118},
    {'text': '0.00', 'x0': 500, 'y0': 115, 'page': 1, 'x1': 530, 'y1': 118},
    
    {'text': '02/01/2026', 'x0': 50, 'y0': 150, 'page': 1, 'x1': 100, 'y1': 160},
    {'text': 'TestTxn', 'x0': 150, 'y0': 150, 'page': 1, 'x1': 200, 'y1': 160},
    {'text': target_string, 'x0': 400, 'y0': 150, 'page': 1, 'x1': 450, 'y1': 160},
    ocr_token
]

parsed_txns, telemetry = parse_with_coordinates(tokens, pdf_name='test.pdf', statement_id='test', job_id='test', bank='Test', pdf_type='digital', identity={'id': 'Test'})

for txn in parsed_txns:
    print(f"Date: {txn['date']}, Debit: {txn['debit']}, Credit: {txn['credit']}, Balance: {txn['balance']}")
