import sys
import os
import requests

sys.path.insert(0, r'z:\CA')

from core.parsers.coordinate_parser_v2 import parse_with_coordinates

cache = requests.get('http://localhost:8000/api/debug/cache').json()
latest = list(cache.keys())[-1]
tokens = cache[latest].get('tokens', [])

txns, _ = parse_with_coordinates(tokens)

print('Extracted txns:', len(txns))
if txns:
    print('First Txn:', txns[0])
