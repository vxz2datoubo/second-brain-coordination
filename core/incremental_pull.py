#!/usr/bin/env python3
"""增量数据拉取——只拉 20260613 至今的数据，追加到已有文件。"""
import sys, os, json, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.tushare_bridge import TushareBridge

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "tushare")
START = "20260613"
END = datetime.now().strftime("%Y%m%d")

bridge = TushareBridge()
print(f"[增量] {START} → {END}")

def append_new(filepath, new_data, dedup_key_idx=1):
    existing = []
    if os.path.exists(filepath):
        try:
            existing = json.load(open(filepath, encoding="utf-8"))
        except Exception:
            existing = []
    existing_dates = set()
    for row in existing:
        if isinstance(row, list) and len(row) > dedup_key_idx:
            existing_dates.add(str(row[dedup_key_idx])[:8])
    added = 0
    for row in new_data:
        if isinstance(row, list) and len(row) > dedup_key_idx:
            date_str = str(row[dedup_key_idx])[:8]
            if date_str not in existing_dates:
                existing.append(row)
                existing_dates.add(date_str)
                added += 1
    existing.sort(key=lambda r: str(r[dedup_key_idx])[:8] if isinstance(r, list) and len(r) > dedup_key_idx else "")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False)
    return added, len(existing)

total_added = 0

# ── 持仓 daily + daily_basic + moneyflow ──
for code, name in [("300418.SZ", "昆仑"), ("300058.SZ", "蓝标")]:
    short = code.split('.')[0]
    print(f"\n📊 {name}({code})")
    
    try:
        data = bridge.daily(code, START, END)
        added, n = append_new(os.path.join(RAW, f"{short}_daily.json"), data, 1)
        print(f"  daily: +{added} → {n}")
        total_added += added
        time.sleep(0.3)
    except Exception as e:
        print(f"  daily: 失败 {e}")
    
    try:
        data = bridge.daily_basic(code, START, END)
        added, n = append_new(os.path.join(RAW, f"{short}_daily_basic.json"), data, 1)
        print(f"  daily_basic: +{added} → {n}")
        total_added += added
        time.sleep(0.3)
    except Exception as e:
        print(f"  daily_basic: 失败 {e}")
    
    try:
        data = bridge.moneyflow(code, START, END)
        added, n = append_new(os.path.join(RAW, f"{short}_moneyflow.json"), data, 0)
        print(f"  moneyflow: +{added} → {n}")
        total_added += added
        time.sleep(0.3)
    except Exception as e:
        print(f"  moneyflow: 失败 {e}")

# ── 指数 daily ──
for idx_code, idx_name in [("000001.SH","上证"), ("000300.SH","沪深300"),
                            ("399001.SZ","深证"), ("399006.SZ","创业板"),
                            ("000905.SH","中证500"), ("000688.SH","科创50")]:
    short = idx_code.split('.')[0]
    print(f"\n📈 {idx_name}({idx_code})")
    try:
        data = bridge._call("index_daily", {"ts_code": idx_code, "start_date": START, "end_date": END})
        added, n = append_new(os.path.join(RAW, f"index_{short}_daily.json"), data, 1)
        print(f"  index_daily: +{added} → {n}")
        total_added += added
        time.sleep(0.3)
    except Exception as e:
        print(f"  index_daily: 失败 {e}")

print(f"\n{'='*40}")
print(f"✅ 增量完成: 共 +{total_added} 条")
