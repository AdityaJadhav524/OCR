import re

DATE_RE = re.compile(
    r'\b('
    r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|'           
    r'\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|'           
    r'\d{1,2}[\s\-\.][A-Za-z]{3,9}[\s\-\.]\d{2,4}'  
    r')\b',
    re.IGNORECASE
)

_DATE_ZONE_COLS = 30
_MIN_LEADING = 1

def _has_date_at_left(line: str) -> bool:
    return bool(DATE_RE.search(line[:_DATE_ZONE_COLS]))

def _is_cont_line(line: str) -> bool:
    if not line.strip(): return False
    leading = len(line) - len(line.lstrip(' '))
    return leading >= _MIN_LEADING and not _has_date_at_left(line)

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
            pre = []
            while i < n and _is_cont_line(lines[i]):
                pre.append(lines[i])
                i += 1
            if i < n and _has_date_at_left(lines[i]):
                anchor = lines[i]
                i += 1
                post = []
                while i < n and _is_cont_line(lines[i]):
                    post.append(lines[i])
                    i += 1
                result.append(_overlay_lines([anchor] + pre + post))
            else:
                merged_pre = _overlay_lines(pre)
                if result and not _has_date_at_left(result[-1]):
                    result[-1] = _overlay_lines([result[-1], merged_pre])
                else:
                    result.append(merged_pre)
        elif _has_date_at_left(line):
            anchor = line
            i += 1
            post = []
            while i < n and _is_cont_line(lines[i]):
                post.append(lines[i])
                i += 1
            if post: result.append(_overlay_lines([anchor] + post))
            else: result.append(anchor)
        else:
            if result and not _has_date_at_left(result[-1]) and line.strip() and not _has_date_at_left(line):
                result[-1] = _overlay_lines([result[-1], line])
            else:
                result.append(line)
            i += 1
    return [l for l in result if l.strip()]

def test_no_date_format():
    # Simulated bank statement where transactions are grouped under a date
    lines = [
        "Transactions for 01/10/2024",
        "ATM WITHDRAWAL                     1000.00           5000.00",
        "POS RETAIL                         2000.00           3000.00",
        "Transactions for 05/10/2024",
        "IMPS TRANSFER                      500.00            2500.00",
    ]
    merged = _merge_continuation_rows(lines)
    print("No Date Left Format Test:")
    for l in merged: print(l)
    print(f"Transactions before: 3, after: {len(merged) - 2}")

if __name__ == "__main__":
    test_no_date_format()
