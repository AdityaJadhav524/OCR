import sqlite3
import os
import hashlib
from datetime import datetime

def get_db_path():
    return os.path.join(os.path.dirname(__file__), "benchmark.sqlite")

def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            id TEXT PRIMARY KEY,
            pdf_hash TEXT,
            bank TEXT,
            parser TEXT,
            transactions INTEGER,
            date_accuracy REAL,
            narration_accuracy REAL,
            debit_accuracy REAL,
            credit_accuracy REAL,
            balance_accuracy REAL,
            audit_score REAL,
            ocr_time REAL,
            fallback_used BOOLEAN,
            created_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_run(pdf_path, bank, parser, txns_count, metrics, merge_stats, fallback_used):
    with open(pdf_path, 'rb') as f:
        pdf_hash = hashlib.md5(f.read()).hexdigest()
        
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    # ensure new columns exist if DB was created previously
    try:
        cursor.execute("ALTER TABLE benchmark_runs ADD COLUMN ocr_time REAL")
        cursor.execute("ALTER TABLE benchmark_runs ADD COLUMN fallback_used BOOLEAN")
    except sqlite3.OperationalError:
        pass # Columns already exist
    
    run_id = f"{pdf_hash}_{parser}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # We expect ocr_time to be passed through merge_stats or metrics. Let's get it from merge_stats telemetry
    ocr_time = merge_stats.get("total_ocr_time", 0.0) if merge_stats else 0.0
    
    cursor.execute("""
        INSERT INTO benchmark_runs (
            id, pdf_hash, bank, parser, transactions, 
            date_accuracy, narration_accuracy, debit_accuracy, credit_accuracy, balance_accuracy, 
            audit_score, ocr_time, fallback_used, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id, pdf_hash, bank, parser, txns_count,
        metrics.get("date_accuracy", 0.0),
        metrics.get("narration_accuracy", 0.0),
        metrics.get("debit_accuracy", 0.0),
        metrics.get("credit_accuracy", 0.0),
        metrics.get("balance_accuracy", 0.0),
        metrics.get("audit_score", 0.0),
        ocr_time,
        fallback_used,
        datetime.now()
    ))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Benchmark Database Initialized.")
