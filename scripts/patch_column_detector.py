import re

with open("core/layout/column_detector.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add value_date_kws and cheque_kws
kws_addition = """    date_kws      = ["DATE"]
    value_date_kws= ["VALUE DATE", "VALUE DT", "VAL DT", "VAL.DATE", "TRAN DATE", "POSTING DATE", "EFFECTIVE DATE", "TXN DATE", "DATE2"]
    cheque_kws    = ["CHQ", "CHEQUE", "REF", "REFERENCE", "INSTRUMENT"]"""

content = content.replace('    date_kws      = ["DATE"]', kws_addition)

# Add to Header detection logic
header_logic_addition = """            if matches_any(text_upper, value_date_kws) and "value_date" not in found_types:
                found_types.add("value_date"); window_header_end = i + j
            if matches_any(text_upper, cheque_kws)    and "cheque"    not in found_types:
                found_types.add("cheque");     window_header_end = i + j
            if matches_any(text_upper, date_kws)      and "date"      not in found_types and not matches_any(text_upper, value_date_kws):
                found_types.add("date");      window_header_end = i + j"""

content = content.replace('            if matches_any(text_upper, date_kws)      and "date"      not in found_types:\n                found_types.add("date");      window_header_end = i + j', header_logic_addition)

# Add to Column type assignment
type_assign_addition = """        elif matches_any(text, value_date_kws):
            cols_found.append({"type": "value_date", "x0": t["x0"], "xc": xc})
        elif matches_any(text, cheque_kws):
            cols_found.append({"type": "cheque", "x0": t["x0"], "xc": xc})
        elif matches_any(text, date_kws):
            cols_found.append({"type": "date", "x0": t["x0"], "xc": xc})"""

content = content.replace('        elif matches_any(text, date_kws):\n            cols_found.append({"type": "date", "x0": t["x0"], "xc": xc})', type_assign_addition)

# Deduplication adjustment
dedup_replacement = """        if t in ["date", "narration", "value_date", "cheque"]:"""
content = content.replace('        if t in ["date", "narration"]:', dedup_replacement)

with open("core/layout/column_detector.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched column_detector.py successfully!")
