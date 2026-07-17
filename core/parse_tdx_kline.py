#!/usr/bin/env python3
"""解析 tdx_kline 工具返回的持久化文本文件，抽取 Rows → 干净 JSON。

用法:
  python core/parse_tdx_kline.py <persist_txt_path> <out_json_path> [code]
"""
import json
import re
import sys
from pathlib import Path


def parse(persist_path: str):
    text = Path(persist_path).read_text(encoding="utf-8", errors="ignore")
    # 定位 JSON 块：从 "详细K线数据:" 之后第一个 { 到最后一个 }
    marker = "详细K线数据:"
    idx = text.find(marker)
    if idx == -1:
        # 退化：直接找第一个 {
        idx = text.find("{")
        if idx == -1:
            raise RuntimeError("未找到 JSON 块")
        start = idx
    else:
        start = text.find("{", idx)
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("JSON 边界解析失败")
    block = text[start : end + 1]
    # 容错：去掉可能的前缀说明行
    block = block.strip()
    data = json.loads(block)
    rows = data.get("Rows", [])
    out = []
    for r in rows:
        d = r.get("Data", "")
        if not d or len(d) != 8:
            continue
        date = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        out.append(
            {
                "date": date,
                "open": float(r.get("Open", 0) or 0),
                "high": float(r.get("High", 0) or 0),
                "low": float(r.get("Low", 0) or 0),
                "close": float(r.get("Close", 0) or 0),
                "volume": float(r.get("Volume", 0) or 0),
                "amount": float(r.get("Amount", 0) or 0),
            }
        )
    # 按日期升序
    out.sort(key=lambda x: x["date"])
    return out


if __name__ == "__main__":
    persist = sys.argv[1]
    out_path = sys.argv[2]
    code = sys.argv[3] if len(sys.argv) > 3 else ""
    bars = parse(persist)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps({"code": code, "bars": bars}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"[{code or '?'}] 解析 {len(bars)} 根K线 → {out_path}")
    if bars:
        print(f"  区间: {bars[0]['date']} ~ {bars[-1]['date']}")
        print(f"  首close={bars[0]['close']} 末close={bars[-1]['close']}")
