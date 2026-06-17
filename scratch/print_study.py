import json
data = json.load(open('Z:\\CA\\scratch\\continuation_study.json'))
for d in data:
    if d['class'] != 'valid_continuation':
        print(f"{d['class']} | gap: {d['row_gap']:>6} | pos: {d['page_position']:>5} | text: {d['text']}")
