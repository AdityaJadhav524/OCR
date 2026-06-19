import os
import hashlib

def get_info(path):
    if not os.path.exists(path): return 'Not Found'
    with open(path, 'rb') as f: data = f.read()
    return f"size: {len(data)}, md5: {hashlib.md5(data).hexdigest()}"

print('BOI_01:', get_info(r'C:\Users\adity\Downloads\CA\tests\BOI\BOI_01.pdf'))
print('BOI_SAVINGS_DIGITAL:', get_info(r'C:\Users\adity\Downloads\CA\tests\pdfs\BOI_SAVINGS_DIGITAL.pdf'))
print('Temp 11707:', get_info(r'C:\Users\adity\Downloads\CA\validation_lab\backend\temp\JOB_20260618_122545_FC6C_11707454011-JUL-25221947 2.PDF'))
