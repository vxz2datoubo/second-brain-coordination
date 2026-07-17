import json, sys

filepath = sys.argv[1]
with open(filepath, 'r') as f:
    content = f.read()

# Find Rows array
start_marker = '"Rows": ['
idx = content.index(start_marker)
# Find the actual [
bracket_pos = content.index('[', idx)
pos = bracket_pos

# Match only [... ] pairs
depth = 0
end_pos = pos
for i in range(pos, len(content)):
    c = content[i]
    if c == '[': depth += 1
    elif c == ']':
        depth -= 1
        if depth == 0:
            end_pos = i + 1
            break

rows_str = content[pos:end_pos]
print(f'Extracted {len(rows_str)} chars from pos {pos} to {end_pos}')
print(f'First 50 chars: {repr(rows_str[:50])}')
print(f'Last 50 chars: {repr(rows_str[-50:])}')

rows = json.loads(rows_str)
print(f'Parsed {len(rows)} rows')

data = []
for r in rows:
    data.append({
        'date': r['Data'],
        'open': float(r['Open']),
        'high': float(r['High']),
        'low': float(r['Low']),
        'close': float(r['Close']),
        'volume': float(r.get('Volume', 0)),
        'amount': float(r.get('Amount', 0))
    })

outpath = filepath.replace('.txt', '.json')
with open(outpath, 'w') as f:
    json.dump(data, f, ensure_ascii=False)
print(f'Saved {len(data)} rows')
print(f'Range: {data[0]["date"]} to {data[-1]["date"]}')
