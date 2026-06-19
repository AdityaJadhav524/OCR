import sqlite3
import pandas as pd
conn = sqlite3.connect('tests/benchmark.sqlite')
try:
    df_runs = pd.read_sql("SELECT * FROM benchmark_runs", conn)
    print("--- MAX TXNS BY BANK ---")
    print(df_runs.groupby('bank')['transactions'].max())
except Exception as e:
    print(e)
