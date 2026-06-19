import sys
import os
import json
sys.path.insert(0, os.path.abspath('.'))
from core.layout.column_detector import detect_columns

test_cases = [
    {
        "bank": "BOI",
        "tokens": [
            {"text": "Transactlon Date", "x0": 60, "x1": 238, "y0": 60, "y1": 80, "yc": 70, "protected": True},
            {"text": "Description", "x0": 336, "x1": 448, "y0": 60, "y1": 80, "yc": 70, "protected": True},
            {"text": "Txn Reference/Instrument", "x0": 569, "x1": 826, "y0": 60, "y1": 80, "yc": 70, "protected": True},
            {"text": "Cheque No", "x0": 881, "x1": 1014, "y0": 60, "y1": 80, "yc": 70, "protected": True},
            {"text": "Debit Amount)Credit AmountRunning Balance", "x0": 1007, "x1": 1540, "y0": 60, "y1": 80, "yc": 70, "protected": True}
        ]
    },
    {
        "bank": "HDFC",
        "tokens": [
            {"text": "Date", "x0": 10, "x1": 50, "y0": 10, "y1": 20, "yc": 15, "protected": True},
            {"text": "Narration", "x0": 100, "x1": 200, "y0": 10, "y1": 20, "yc": 15, "protected": True},
            {"text": "Withdrawal Amount", "x0": 300, "x1": 450, "y0": 10, "y1": 20, "yc": 15, "protected": True},
            {"text": "Deposit Amount", "x0": 500, "x1": 650, "y0": 10, "y1": 20, "yc": 15, "protected": True},
            {"text": "Closing Balance", "x0": 700, "x1": 850, "y0": 10, "y1": 20, "yc": 15, "protected": True}
        ]
    }
]

for tc in test_cases:
    print(f"\n--- {tc['bank']} ---")
    rows = [{"page": 1, "tokens": tc["tokens"], "y_min": 10, "y_max": 90, "protected": True}]
    telemetry = {}
    zones, headers = detect_columns(rows, telemetry=telemetry)
    print("Zones:", json.dumps(zones, indent=2))
    print("Telemetry:", json.dumps(telemetry, indent=2))

