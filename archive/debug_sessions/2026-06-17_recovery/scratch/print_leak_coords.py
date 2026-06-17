import json

data = json.load(open(r'Z:\CA\investigations\HDFC\txns_after_suppression.json', 'r', encoding='utf-8'))
leaks = [t for t in data if t.get('contamination_detected')]

print('Tokens in leaked transactions physically below 85% of page height:')
for t in leaks:
    for tok in t.get('_source_tokens', []):
        y1 = tok.get('y1', 0)
        page = tok.get('page', 0)
        # Using 2186 as an approximate page height
        if y1 / 2186.0 > 0.85:
            print(f"Page {page} Y={y1} ({y1/2186.0:.1%}) TEXT: {tok.get('text')}")
