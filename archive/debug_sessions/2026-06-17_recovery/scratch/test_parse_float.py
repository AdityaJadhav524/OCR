import re

def _parse_float(val):
    if val is None:
        return None

    if isinstance(val, (int, float)):
        return float(val)

    text = str(val).strip()
    
    # Strip everything except digits, comma, period, minus
    text = re.sub(r'[^\d.,-]', '', text)

    # Apply OCR comma-as-decimal fix
    if '.' not in text and ',' in text:
        last_comma_idx = text.rfind(',')
        if len(text) - last_comma_idx - 1 == 2:
            text = text[:last_comma_idx] + '.' + text[last_comma_idx+1:]

    text = text.replace(',', '')

    if text.count('.') > 1:
        parts = text.rsplit('.', 1)
        text = parts[0].replace('.', '') + '.' + parts[1]
    elif text.count('.') == 1:
        parts = text.split('.')
        if len(parts[1]) == 3:
            text = text.replace('.', '')
        elif len(parts[1]) == 5:
            text = parts[0] + parts[1][:3] + '.' + parts[1][3:]

    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return None

    return float(match.group())

test_cases = [
    "81,510,17 Cr",
    "81,510,17*",
    "1,000,000",
    "1,234",
    "50,00",
    "50.00",
    "81,510.17",
    "Rs 81,510,17",
    "-12,345,67",
    "2.000"
]

for t in test_cases:
    print(f"{t} -> {_parse_float(t)}")
