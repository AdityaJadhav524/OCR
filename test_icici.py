import sys
import os
from pprint import pprint

sys.path.insert(0, os.path.abspath('.'))

from ledgerai.identifier_service import parse_document

if __name__ == "__main__":
    file_path = r'C:\Users\adity\Downloads\DetailedStatement24-25 2.pdf'
    res = parse_document(file_path)
    print(f"Total Transactions: {len(res['transactions'])}")
    if '_debug' in res:
        print("Debug Reject Reasons:")
        pprint(res['_debug'].get('reject_reasons', {}))
