import json

# Load Docling JSON
json_path = r"Z:\CA\investigations\DOCLING\diagnostics\docling_document_structure.json"
with open(json_path, 'r', encoding='utf-8') as f:
    d = json.load(f)

for t in d.get("texts", [])[:3]:
    bbox = t.get("prov", [{}])[0].get("bbox", {})
    print(f"Text: {t.get('text')} Bbox: {bbox}")

for table in d.get("tables", [])[:1]:
    for c in table.get("data", {}).get("table_cells", [])[:3]:
        print(f"Cell: {c.get('text')} Bbox: {c.get('bbox')}")
