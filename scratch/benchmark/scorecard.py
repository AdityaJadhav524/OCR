import json
import os

def render_scorecard():
    paddle_path = r"Z:\CA\scratch\benchmark\benchmark_current.json"
    docling_path = r"Z:\CA\scratch\benchmark\benchmark_docling.json"
    mineru_path = r"Z:\CA\scratch\benchmark\benchmark_mineru.json"
    
    paddle = json.load(open(paddle_path)) if os.path.exists(paddle_path) else {}
    docling = json.load(open(docling_path)) if os.path.exists(docling_path) else {}
    mineru = json.load(open(mineru_path)) if os.path.exists(mineru_path) else {}
    
    # Helper to get metric
    def get_val(engine_data, bank, key, suffix=""):
        if not engine_data: return "?"
        bank_data = engine_data.get(bank)
        if not bank_data: return "?"
        val = bank_data.get(key)
        if val is None: return "?"
        return f"{val}{suffix}"
        
    md = f"""# P7 Transaction Extraction Benchmark Scorecard

┌──────────────────────────┬──────────────┬─────────────┬──────────────┐
│ Metric                   │ PaddleOCR    │ Docling OCR │ MinerU OCR   │
├──────────────────────────┼──────────────┼─────────────┼──────────────┤
│ YES Recall               │ {get_val(paddle, 'YES', 'recall_pct', '%'):<12} │ {get_val(docling, 'YES', 'recall_pct', '%'):<11} │ {get_val(mineru, 'YES', 'recall_pct', '%'):<12} │
│ YES Precision            │ {get_val(paddle, 'YES', 'precision_pct', '%'):<12} │ {get_val(docling, 'YES', 'precision_pct', '%'):<11} │ {get_val(mineru, 'YES', 'precision_pct', '%'):<12} │
│ YES Date Accuracy        │ {get_val(paddle, 'YES', 'date_acc', '%'):<12} │ {get_val(docling, 'YES', 'date_acc', '%'):<11} │ {get_val(mineru, 'YES', 'date_acc', '%'):<12} │
│ YES Debit Accuracy       │ {get_val(paddle, 'YES', 'debit_acc', '%'):<12} │ {get_val(docling, 'YES', 'debit_acc', '%'):<11} │ {get_val(mineru, 'YES', 'debit_acc', '%'):<12} │
│ YES Credit Accuracy      │ {get_val(paddle, 'YES', 'credit_acc', '%'):<12} │ {get_val(docling, 'YES', 'credit_acc', '%'):<11} │ {get_val(mineru, 'YES', 'credit_acc', '%'):<12} │
│ YES Balance Accuracy     │ {get_val(paddle, 'YES', 'balance_acc', '%'):<12} │ {get_val(docling, 'YES', 'balance_acc', '%'):<11} │ {get_val(mineru, 'YES', 'balance_acc', '%'):<12} │
│ YES Known Error Recovery │ {get_val(paddle, 'YES', 'known_errors_recovered', '/4'):<12} │ {get_val(docling, 'YES', 'known_errors_recovered', '/4'):<11} │ {get_val(mineru, 'YES', 'known_errors_recovered', '/4'):<12} │
│ YES Ledger Pass %        │ {get_val(paddle, 'YES', 'ledger_pass_pct', '%'):<12} │ {get_val(docling, 'YES', 'ledger_pass_pct', '%'):<11} │ {get_val(mineru, 'YES', 'ledger_pass_pct', '%'):<12} │
├──────────────────────────┼──────────────┼─────────────┼──────────────┤
│ SBI Recall               │ {get_val(paddle, 'SBI', 'recall_pct', '%'):<12} │ {get_val(docling, 'SBI', 'recall_pct', '%'):<11} │ {get_val(mineru, 'SBI', 'recall_pct', '%'):<12} │
├──────────────────────────┼──────────────┼─────────────┼──────────────┤
│ HDFC Ledger Pass %       │ {get_val(paddle, 'HDFC', 'ledger_pass_pct', '%'):<12} │ {get_val(docling, 'HDFC', 'ledger_pass_pct', '%'):<11} │ {get_val(mineru, 'HDFC', 'ledger_pass_pct', '%'):<12} │
├──────────────────────────┼──────────────┼─────────────┼──────────────┤
│ Runtime — YES            │ {get_val(paddle, 'YES', 'runtime', 's'):<12} │ {get_val(docling, 'YES', 'runtime', 's'):<11} │ {get_val(mineru, 'YES', 'runtime', 's'):<12} │
│ Runtime — HDFC           │ {get_val(paddle, 'HDFC', 'runtime', 's'):<12} │ {get_val(docling, 'HDFC', 'runtime', 's'):<11} │ {get_val(mineru, 'HDFC', 'runtime', 's'):<12} │
└──────────────────────────┴──────────────┴─────────────┴──────────────┘
"""
    with open(r"Z:\CA\scratch\benchmark\benchmark_scorecard.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("Scorecard written to scratch/benchmark/benchmark_scorecard.md")

if __name__ == "__main__":
    render_scorecard()
