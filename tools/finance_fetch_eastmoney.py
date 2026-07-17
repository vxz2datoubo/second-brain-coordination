"""Fetch Eastmoney board/concept snapshots into daily-report JSONL.

This is an optional adapter. Eastmoney public endpoints may change or block
some environments, so the script fails loudly and leaves the core local
workflow untouched.
"""
from __future__ import annotations

import argparse
import http.client
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


ENDPOINT = "https://push2.eastmoney.com/api/qt/clist/get"
FIELDS = "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87"
BOARD_FS = {
    "industry": "m:90+t:2",
    "concept": "m:90+t:3",
}


def fetch_json(url: str, timeout: int = 15, retries: int = 2) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://quote.eastmoney.com/",
    }
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "ignore"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, http.client.HTTPException) as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"fetch failed after {retries + 1} attempts: {last_error}")


def build_url(kind: str, page_size: int, sort_field: str) -> str:
    params = {
        "pn": "1",
        "pz": str(page_size),
        "po": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": sort_field,
        "fs": BOARD_FS[kind],
        "fields": FIELDS,
    }
    return f"{ENDPOINT}?{urllib.parse.urlencode(params)}"


def row_to_item(row: dict, kind: str, report_date: str) -> dict:
    name = row.get("f14", "")
    code = row.get("f12", "")
    change_pct = row.get("f3", "-")
    main_inflow = row.get("f62", "-")
    inflow_pct = row.get("f184", "-")
    super_inflow = row.get("f66", "-")
    large_inflow = row.get("f72", "-")
    medium_inflow = row.get("f78", "-")
    small_inflow = row.get("f84", "-")
    title = f"东方财富{kind}板块: {name} 涨跌幅{change_pct}% 主力净流入{main_inflow}"
    text = (
        f"板块代码 {code}，板块名称 {name}，涨跌幅 {change_pct}%，"
        f"主力净流入 {main_inflow}，主力净占比 {inflow_pct}%，"
        f"超大单净流入 {super_inflow}，大单净流入 {large_inflow}，"
        f"中单净流入 {medium_inflow}，小单净流入 {small_inflow}。"
        "用于每日题材热度和资金方向观察，仍需结合成交量、指数环境和个股结构。"
    )
    return {
        "title": title,
        "text": text,
        "date": report_date,
        "source": f"eastmoney-{kind}",
        "metadata": row,
    }


def fetch_items(kind: str, page_size: int, sort_field: str, report_date: str) -> list[dict]:
    url = build_url(kind, page_size, sort_field)
    payload = fetch_json(url)
    rows = (((payload or {}).get("data") or {}).get("diff") or [])
    if not rows:
        raise RuntimeError(f"no rows returned from Eastmoney endpoint: {url}")
    return [row_to_item(row, kind, report_date) for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Eastmoney board data into JSONL.")
    parser.add_argument("--kind", choices=sorted(BOARD_FS), default="concept")
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--sort-field", default="f62", help="Eastmoney sort field, default f62 main inflow")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    try:
        items = fetch_items(args.kind, args.page_size, args.sort_field, args.date)
    except Exception as exc:
        print(json.dumps({
            "error": True,
            "message": f"{type(exc).__name__}: {exc}",
            "hint": "Eastmoney public endpoints may block this environment. Use manual JSONL input or retry later.",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    output = Path(args.output) if args.output else ROOT / "qclaw-output" / f"finance-eastmoney-{args.kind}-{args.date}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output), "count": len(items), "kind": args.kind}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
