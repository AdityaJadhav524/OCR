"""
MinerU Adapter
Parses MinerU's middle.json output into V2 Tokens.
"""
import json
from bs4 import BeautifulSoup

def parse_mineru_json(json_path: str):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    tokens = []
    
    for page in data.get('pdf_info', []):
        page_idx = page.get('page_idx', 0)
        
        for block in page.get('preproc_blocks', []):
            b_type = block.get('type')
            
            if b_type == 'text':
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        text = span.get('content', '').strip()
                        if not text:
                            continue
                        bbox = span.get('bbox', [0,0,0,0])
                        tokens.append({
                            'text': text,
                            'x0': float(bbox[0]),
                            'y0': float(bbox[1]),
                            'x1': float(bbox[2]),
                            'y1': float(bbox[3]),
                            'page': page_idx,
                            'source': 'mineru_text'
                        })
                        
            elif b_type == 'table':
                # Parse HTML table into fake coordinate tokens
                bbox = block.get('bbox', [0,0,1000,1000])
                tx0, ty0, tx1, ty1 = bbox
                
                # Get HTML string
                html_str = ""
                for b in block.get('blocks', []):
                    for l in b.get('lines', []):
                        for s in l.get('spans', []):
                            if 'html' in s:
                                html_str += s['html']
                                
                if not html_str:
                    continue
                    
                soup = BeautifulSoup(html_str, 'html.parser')
                rows = soup.find_all('tr')
                
                for r_idx, row in enumerate(rows):
                    c_idx = 0
                    for cell in row.find_all(['td', 'th']):
                        text = cell.get_text(separator=' ', strip=True)
                        if not text:
                            c_idx += 1
                            continue
                            
                        colspan = int(cell.get('colspan', 1))
                        rowspan = int(cell.get('rowspan', 1))
                        
                        # Fake grid coordinates
                        cell_x0 = tx0 + (c_idx * 150)
                        cell_x1 = cell_x0 + (colspan * 140)
                        
                        cell_y0 = ty0 + (r_idx * 30)
                        cell_y1 = cell_y0 + (rowspan * 20)
                        
                        tokens.append({
                            'text': text,
                            'x0': float(cell_x0),
                            'y0': float(cell_y0),
                            'x1': float(cell_x1),
                            'y1': float(cell_y1),
                            'page': page_idx,
                            'source': 'mineru_table'
                        })
                        
                        c_idx += colspan

    return tokens
