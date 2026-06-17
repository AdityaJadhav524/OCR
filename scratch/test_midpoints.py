import json
from core.layout.column_detector import detect_columns
from core.layout.row_detector import detect_rows

with open(r'z:\CA\scratch\indusind_tokens.json', 'r') as f:
    tokens = json.load(f)

# Mock detect_columns to use MIDPOINTS!
def mock_detect_columns(rows):
    cols_found = [{'type': 'date', 'x0': 81.0}, {'type': 'narration', 'x0': 529.0}, {'type': 'debit', 'x0': 962.0}, {'type': 'credit', 'x0': 1169.0}, {'type': 'balance', 'x0': 1385.0}]
    zones = {}
    for i in range(len(cols_found)):
        col = cols_found[i]
        if i == 0: start_x = 0.0
        else: start_x = (cols_found[i-1]['x0'] + col['x0']) / 2.0
        if i < len(cols_found) - 1: end_x = (col['x0'] + cols_found[i+1]['x0']) / 2.0
        else: end_x = 9999.0
        zones[f"{col['type']}_zone"] = [start_x, end_x]
    return zones, None

import core.parsers.coordinate_parser_v2 as cpv2
cpv2.detect_columns = mock_detect_columns

txns, tel = cpv2.parse_with_coordinates(tokens)
print('First txn with midpoints:', txns[0]['debit'], txns[0]['credit'])
