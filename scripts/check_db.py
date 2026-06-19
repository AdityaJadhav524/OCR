import sqlite3
import json
conn = sqlite3.connect(r'c:\Users\adity\Downloads\CA\tests\benchmark.sqlite')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print('Tables:', tables)
for t in tables:
    cols = conn.execute(f"PRAGMA table_info({t[0]});").fetchall()
    print(t[0], ':', cols)
