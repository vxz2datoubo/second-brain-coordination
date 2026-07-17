import json, os, glob
SF = 'data/raw/tushare/_pull_state.json'
d = json.load(open(SF))
print('updated:', d['meta'].get('updated'))
print('total pulls:', len(d['pulls']), 'done:', sum(1 for v in d['pulls'].values() if v.get('status')=='done'))
print('failed:', sum(1 for v in d['pulls'].values() if v.get('status')=='failed'))
for label, pat in [('index', 'index_'), ('stock_daily', 'stock_0'), ('chip', 'chip_'), ('north', 'north_')]:
    fs = [f for f in os.listdir('data/raw/tushare') if f.startswith(pat) and f.endswith('.json')]
    print(f'{label}: {len(fs)} files')
    for f in sorted(fs)[:3]:
        p = os.path.join('data/raw/tushare', f)
        try:
            n = len(json.load(open(p)))
            print(f'   {f} -> {n} rows')
        except Exception as e:
            print(f'   {f} -> ERR {e}')
