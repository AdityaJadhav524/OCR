import json

d = json.load(open(r'Z:\CA\investigations\DOCLING\diagnostics\docling_document_structure.json'))
table = d.get('tables', [])[0]
cells = table['data']['table_cells'][:20]

for c in cells:
    print(f"Col {c.get('start_col_offset_idx')}: {c.get('text')}")
