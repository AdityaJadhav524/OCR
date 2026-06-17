import json, os, glob

dirs = [
    r"C:\Users\adity\.gemini\antigravity-ide\brain\0f7ac77c-e6f8-4763-afc9-71dc0e67fdf8",
    r"C:\Users\adity\.gemini\antigravity-ide\brain\68beee24-0bb4-4a23-a49b-924b2fadd524",
    r"C:\Users\adity\.gemini\antigravity-ide\brain\a91c24b3-da82-413c-9098-5cc87be0fb55",
    r"C:\Users\adity\.gemini\antigravity-ide\brain\e084ae69-7698-469b-9758-84d185b90bf4",
    r"C:\Users\adity\.gemini\antigravity-ide\brain\056e3290-b9b7-4b93-81bc-ccf07e7cb18c",
]

for d in dirs:
    path = os.path.join(d, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(path):
        print(f"MISSING: {d}")
        continue
    print(f"\n=== {os.path.basename(d)} ===")
    with open(path, encoding='utf-8') as f:
        for line in f:
            try:
                obj = json.loads(line)
                if obj.get('type') == 'USER_INPUT':
                    c = obj.get('content','')
                    for tag in ['<USER_REQUEST>', '</USER_REQUEST>', '<ADDITIONAL_METADATA>', '</ADDITIONAL_METADATA>']:
                        c = c.replace(tag, '')
                    c = c.strip()[:200]
                    if c:
                        print(f"  s{obj['step_index']}: {c}")
            except:
                pass
