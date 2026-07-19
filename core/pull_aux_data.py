#!/usr/bin/env python
"""批量下载Tushare辅助数据 — 筹码分析增强"""
import json, sys, os, time
sys.path.insert(0, 'F:/aidanao')
from core.tushare_bridge import TushareBridge
b = TushareBridge()

CODES = ['300418.SZ', '300058.SZ']
RAW = 'data/raw/tushare'
START = '20180101'
END = '20260713'

tasks = [
    # (api_name, start_key, end_key, description, extra_params)
    ('margin_detail', START, END, '融资融券明细', {}),
    ('stk_factor', START, END, '技术因子', {}),
    ('top_list', START, END, '龙虎榜全量', {}),
    ('block_trade', START, END, '大宗交易', {}),
    ('limit_list_d', START, END, '涨跌停', {}),
]

print("=" * 70)
print(f"  批量下载 Tushare 辅助数据")
print(f"  标的: {CODES}  区间: {START}→{END}")
print("=" * 70)

total = 0
for api, start, end, desc, extra in tasks:
    for code in CODES:
        name = code.split('.')[0]
        outfile = f'{RAW}/{name}_{api}.json'
        
        # Skip if exists
        if os.path.exists(outfile):
            size = os.path.getsize(outfile) / 1024
            existing = json.load(open(outfile))
            print(f'  ⏭ {api} {name}: 已有 {len(existing)}条 ({size:.0f}KB)')
            total += len(existing)
            continue
        
        try:
            params = {'ts_code': code, 'start_date': start, 'end_date': end, **extra}
            rows = b._call(api, params)
            if rows:
                json.dump(rows, open(outfile, 'w'), ensure_ascii=False)
                print(f'  ✅ {api} {name}: {len(rows)}条')
                total += len(rows)
            else:
                print(f'  ⚠️ {api} {name}: 无数据')
            time.sleep(0.5)
        except Exception as e:
            print(f'  ❌ {api} {name}: {e}')

# Special: pull cyq_chips for latest dates
print()
for code in CODES:
    name = code.split('.')[0]
    outfile = f'{RAW}/chip_{name}_cyq_chips.json'
    existing = json.load(open(outfile))
    latest_dates = sorted(set(r[1][:10] for r in existing))[-3:]
    print(f'  cyq_chips {name}: 已到 {latest_dates[-1]} ({len(existing)}条/{len(set(r[1][:10] for r in existing))}天)')

print()
print(f"总计: {total} 条数据")
