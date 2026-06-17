import json

data = json.load(open('Z:\\CA\\scratch\\continuation_study.json'))
banks = ['HDFC', 'SBI', 'YES']
tokens_map = {}
for bank in banks:
    filename = 'latest_upload_tokens.json' if bank == 'SBI' else bank.lower() + '_tokens.json'
    tokens_map[bank] = json.load(open('Z:\\CA\\scratch\\' + filename))

def get_x0(text, bank):
    first_word = text.split()[0]
    for t in tokens_map[bank]:
        if t.get('text', '') == first_word:
            return t.get('x0', t.get('x1', 0))
    return -1

for d in data:
    if d['class'] != 'valid_continuation':
        print(f"{d['class']} | pos: {d['page_position']:>5} | x0: {get_x0(d['text'], d['bank']):>5} | {d['text']}")
