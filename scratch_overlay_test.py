import re

DATE_RE = re.compile(
    r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b'
)
_DATE_ZONE_COLS = 30
_MIN_LEADING = 1

def _has_date_at_left(line: str) -> bool:
    return bool(DATE_RE.search(line[:_DATE_ZONE_COLS]))

def _overlay_lines(group: list) -> str:
    if not group: return ''
    if len(group) == 1: return group[0]
    max_w = max(len(l) for l in group)
    grid = [' '] * max_w
    for line in group:
        for col, ch in enumerate(line):
            if col < max_w and ch != ' ' and grid[col] == ' ':
                grid[col] = ch
    return ''.join(grid).rstrip()

def _is_cont_line(line: str) -> bool:
    if not line.strip(): return False
    leading = len(line) - len(line.lstrip(' '))
    return leading >= _MIN_LEADING and not _has_date_at_left(line)

def _merge_continuation_rows(lines: list) -> list:
    if not lines: return lines
    result = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if 'PAGE' in line or 'Opening Balance' in line or 'TOTAL' in line:
            result.append(line)
            i += 1
            continue
            
        if _is_cont_line(line):
            # ... abbreviated for simple test
            result.append(line)
            i += 1
        elif _has_date_at_left(line):
            result.append(line)
            i += 1
        else:
            if result and not _has_date_at_left(result[-1]) and line.strip() and not _has_date_at_left(line):
                result[-1] = _overlay_lines([result[-1], line])
            else:
                result.append(line)
            i += 1
    return [l for l in result if l.strip()]

# Test with Bank of India dates
lines = [
    "01 OCT 2024   CHQ1234   10,000.00          10,000.00",
    "05 OCT 2024   ATM       5,000.00           5,000.00",
    "10 OCT 2024   POS       1,000.00           4,000.00",
    "15 OCT 2024   NEFT      500.00             3,500.00"
]

merged = _merge_continuation_rows(lines)
print(f"Original lines: {len(lines)}")
print(f"Merged lines: {len(merged)}")
print(f"Merged output:")
for m in merged:
    print(m)
