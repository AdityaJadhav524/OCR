import urllib.request, json
resp = urllib.request.urlopen('http://localhost:8000/api/debug/cache').read().decode('utf-8')
cache = json.loads(resp)
if not cache: print('Cache empty')
for sid, sdata in cache.items():
    print(f'Session ID: {sid}')
    for stage in sdata.get('stages', []):
        print(f'{stage[\
name\]}: {stage[\time_ms\]}ms')
