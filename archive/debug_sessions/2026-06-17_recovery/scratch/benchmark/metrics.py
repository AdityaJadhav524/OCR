import math
from .ground_truth import normalize_date, _to_float

def compute_metrics(bank_name, extracted, gt, TP, FP, FN, audit_results, runtime):
    metrics = {
        "bank": bank_name,
        "extracted": len(extracted),
        "gt": len(gt),
        "recall_pct": None,
        "precision_pct": None,
        "date_acc": None,
        "debit_acc": None,
        "credit_acc": None,
        "balance_acc": None,
        "known_errors_recovered": 0,
        "ledger_pass_pct": None,
        "runtime": runtime
    }
    
    if len(gt) > 0:
        metrics["recall_pct"] = round(len(TP) / (len(TP) + len(FN)) * 100, 1)
        if (len(TP) + len(FP)) > 0:
            metrics["precision_pct"] = round(len(TP) / (len(TP) + len(FP)) * 100, 1)
        else:
            metrics["precision_pct"] = 0.0
            
    # Field accuracy
    if len(TP) > 0:
        date_ok = 0
        deb_ok = 0
        cre_ok = 0
        bal_ok = 0
        
        for e, g in TP:
            if normalize_date(e.get("date")) == normalize_date(g.get("date")):
                date_ok += 1
                
            e_deb = _to_float(e.get("debit")); g_deb = _to_float(g.get("debit"))
            if (e_deb is None and g_deb is None) or (e_deb is not None and g_deb is not None and math.isclose(e_deb, g_deb, abs_tol=0.01)):
                deb_ok += 1
                
            e_cre = _to_float(e.get("credit")); g_cre = _to_float(g.get("credit"))
            if (e_cre is None and g_cre is None) or (e_cre is not None and g_cre is not None and math.isclose(e_cre, g_cre, abs_tol=0.01)):
                cre_ok += 1
                
            e_bal = _to_float(e.get("balance")); g_bal = _to_float(g.get("balance"))
            if (e_bal is None and g_bal is None) or (e_bal is not None and g_bal is not None and math.isclose(e_bal, g_bal, abs_tol=0.01)):
                bal_ok += 1
                
        metrics["date_acc"] = round(date_ok / len(TP) * 100, 1)
        metrics["debit_acc"] = round(deb_ok / len(TP) * 100, 1)
        metrics["credit_acc"] = round(cre_ok / len(TP) * 100, 1)
        metrics["balance_acc"] = round(bal_ok / len(TP) * 100, 1)
        
    # Known errors
    if bank_name == "YES":
        known = [286201.63, 250066.93, 208208.93, 171105.18]
        recovered = 0
        for e in extracted:
            e_deb = _to_float(e.get("debit"))
            e_cre = _to_float(e.get("credit"))
            e_bal = _to_float(e.get("balance"))
            for k in known:
                if (e_deb and math.isclose(e_deb, k)) or (e_cre and math.isclose(e_cre, k)) or (e_bal and math.isclose(e_bal, k)):
                    recovered += 1
        metrics["known_errors_recovered"] = recovered
        
    # Ledger
    if audit_results and len(extracted) > 0:
        issues = audit_results.get("running_balance_issues", 0)
        metrics["ledger_pass_pct"] = round(max(0, len(extracted) - issues) / len(extracted) * 100, 1)
        
    return metrics
