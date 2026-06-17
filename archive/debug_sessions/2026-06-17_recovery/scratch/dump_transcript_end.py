import json
with open(r'C:\Users\adity\.gemini\antigravity-ide\brain\0f7ac77c-e6f8-4763-afc9-71dc0e67fdf8\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for line in lines[-50:]:
        data = json.loads(line)
        if 'content' in data:
            with open(r'Z:\CA\scratch\transcript_end.txt', 'a', encoding='utf-8') as out:
                out.write(data['content'] + '\n\n')
