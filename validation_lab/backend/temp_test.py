import re

with open(r"Z:\CA\validation_lab\backend\dumps\SESSION_20260610_175231_CFE4_ocr.txt", "r", encoding="utf-8") as f:
    full_text = f.read()

pages = [
    block.strip()
    for block in re.split(r'={80}', full_text)
    if block.strip() and not re.fullmatch(r'\s*PAGE\s+\d+\s*', block.strip(), re.IGNORECASE)
]

chunk_text = "\n\n".join(pages)

with open(r"Z:\CA\validation_lab\backend\dumps\SESSION_20260610_175231_CFE4_test.txt", "w", encoding="utf-8") as f:
    f.write(chunk_text)

print(f"Pages len: {len(pages)}")
print(f"Chunk length: {len(chunk_text)}")
