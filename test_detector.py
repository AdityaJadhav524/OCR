import sys
import os
import json
sys.path.append(r'c:\Users\adity\Downloads\CA')
from core.layout.column_detector import detect_columns

# Let's mock a header row to see what detect_columns does.
rows = [
    {
        "tokens": [
            {"text": "Txn", "x0": 50, "x1": 80},
            {"text": "Date", "x0": 85, "x1": 120},
            {"text": "Value", "x0": 248, "x1": 280},
            {"text": "Date", "x0": 285, "x1": 320},
            {"text": "Narration", "x0": 350, "x1": 450},
            {"text": "Withdrawal", "x0": 1007, "x1": 1100},
            {"text": "Deposit", "x0": 1270, "x1": 1350},
            {"text": "Balance", "x0": 1420, "x1": 1500}
        ]
    }
]

zones, header = detect_columns(rows)
print(zones)
