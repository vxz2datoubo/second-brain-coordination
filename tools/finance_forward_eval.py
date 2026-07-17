"""Forward performance evaluation for finance watchlists and plans.

This closes the loop from "candidate generated" to "what happened next". It
does not predict prices; it measures whether prior signals actually worked.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import Bar, load_price_csv  # noqa: E402


def parse_date(value: str) -> datetime:
    text = str(value or "").strip()[:10].replace("/", "-")
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(text)


def load_watchlist(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if row.get("csv_path")]


def first_bar_on_or_after(bars: list[Bar], signal_date: str) -> int | None:
    target = parse_date(signal_date)
    for i, bar in enumerate(bars):
        try:
            if parse_date(bar.date) >= target:
                return i
        except ValueError:
            continue
    return None


def evaluate_row(row: dict, signal_date: str, horizons: list[int]) -> dict:
    bars = load_price_csv(row["csv_path"])
    start_idx = first_bar_on_or_after(bars, signal_date)
    if start_idx is None:
        return {
            "symbol": row.get("symbol", ""),
            "name": row.get("name", ""),
            "theme": row.get("theme", ""),
            "error": "no bar on or after signal date",
        }
    entry = bars[start_idx].close
    future = bars[start_idx:]
    result = {
        "symbol": row.get("symbol", ""),
        "name": row.get("name", ""),
        "theme": row.get("theme", ""),
        "signal_date": signal_date,
        "entry_date": bars[start_idx].date,
        "entry_price": entry,
        "available_future_bars": max(0, len(future) - 1),
        "horizons": {},
    }
    lows = []
    highs = []
    for i, bar in enumerate(future[1:], 1):
        lows.append(bar.low)
        highs.append(bar.high)
        if i in horizons:
            close_return = bar.close / entry - 1 if entry > 0 else 0
            max_runup = max(highs) / entry - 1 if highs and entry > 0 else 0
            max_adverse = min(lows) / entry - 1 if lows and entry > 0 else 0
            result["horizons"][str(i)] = {
                "date": bar.date,
                "close": bar.close,
                "return": round(close_return, 4),
                "max_runup": round(max_runup, 4),
                "max_adverse": round(max_adverse, 4),
                "hit": close_return > 0,
            }
    missing = [h for h in horizons if str(h) not in result["horizons"]]
    if missing:
        result["missing_horizons"] = missing
    return result


def summarize(results: list[dict], horizons: list[int]) -> dict:
    by_horizon = {}
    by_theme = defaultdict(lambda: {"count": 0, "hits": 0, "avg_return": 0.0})
    for horizon in horizons:
        rows = [r for r in results if str(horizon) in r.get("horizons", {})]
        returns = [r["horizons"][str(horizon)]["return"] for r in rows]
        hits = [r for r in rows if r["horizons"][str(horizon)]["hit"]]
        by_horizon[str(horizon)] = {
            "count": len(rows),
            "hit_rate": round(len(hits) / len(rows), 4) if rows else 0,
            "avg_return": round(sum(returns) / len(returns), 4) if returns else 0,
        }
        for row in rows:
            theme = row.get("theme") or "未分类"
            item = by_theme[(theme, horizon)]
            item["count"] += 1
            item["hits"] += 1 if row["horizons"][str(horizon)]["hit"] else 0
            item["avg_return"] += row["horizons"][str(horizon)]["return"]
    theme_rows = []
    for (theme, horizon), item in by_theme.items():
        count = item["count"]
        theme_rows.append({
            "theme": theme,
            "horizon": horizon,
            "count": count,
            "hit_rate": round(item["hits"] / count, 4) if count else 0,
            "avg_return": round(item["avg_return"] / count, 4) if count else 0,
        })
    theme_rows.sort(key=lambda x: (x["horizon"], -x["avg_return"]))
    return {"by_horizon": by_horizon, "by_theme": theme_rows}


def evaluate_watchlist(watchlist_path: Path, signal_date: str, horizons: list[int]) -> dict:
    rows = load_watchlist(watchlist_path)
    results = [evaluate_row(row, signal_date, horizons) for row in rows]
    return {
        "watchlist_path": str(watchlist_path),
        "signal_date": signal_date,
        "horizons": horizons,
        "count": len(results),
        "evaluated": len([r for r in results if "error" not in r]),
        "errors": [r for r in results if "error" in r],
        "summary": summarize([r for r in results if "error" not in r], horizons),
        "results": results,
    }


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict) -> str:
    lines = [
        f"# 候选前向表现评估 - {report['signal_date']}",
        "",
        f"- 观察池: `{report['watchlist_path']}`",
        f"- 候选数: {report['count']}",
        f"- 可评估数: {report['evaluated']}",
        f"- 周期: {', '.join(str(h) for h in report['horizons'])} 个交易日",
        "",
        "## 汇总",
        "",
        "| 周期 | 样本数 | 命中率 | 平均收益 |",
        "|---:|---:|---:|---:|",
    ]
    for horizon, row in report["summary"]["by_horizon"].items():
        lines.append(f"| {horizon} | {row['count']} | {row['hit_rate']} | {row['avg_return']} |")
    lines.extend([
        "",
        "## 题材归因",
        "",
        "| 题材 | 周期 | 样本数 | 命中率 | 平均收益 |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in report["summary"]["by_theme"]:
        lines.append(f"| {md_escape(row['theme'])} | {row['horizon']} | {row['count']} | {row['hit_rate']} | {row['avg_return']} |")
    lines.extend([
        "",
        "## 标的明细",
        "",
        "| 标的 | 名称 | 题材 | 入场日 | 入场价 | 周期 | 收益 | 最大浮盈 | 最大不利 | 命中 |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ])
    for row in report["results"]:
        if "error" in row:
            lines.append(f"| {md_escape(row.get('symbol'))} | {md_escape(row.get('name'))} | {md_escape(row.get('theme'))} | - | - | - | - | - | - | {md_escape(row['error'])} |")
            continue
        for horizon, detail in row["horizons"].items():
            lines.append(
                f"| {md_escape(row['symbol'])} | {md_escape(row['name'])} | {md_escape(row['theme'])} | "
                f"{row['entry_date']} | {row['entry_price']} | {horizon} | {detail['return']} | "
                f"{detail['max_runup']} | {detail['max_adverse']} | {'是' if detail['hit'] else '否'} |"
            )
    lines.extend([
        "",
        "## 使用原则",
        "",
        "- 前向评估只衡量候选生成后的真实表现，不代表下一次一定复现。",
        "- 命中率、平均收益、最大不利波动要按题材和周期分开看。",
        "- 连续低命中的题材或策略应降权，连续高回撤的候选应降低仓位或剔除。",
    ])
    return "\n".join(lines) + "\n"


def parse_horizons(text: str) -> list[int]:
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate forward performance of finance watchlist candidates.")
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--signal-date", required=True)
    parser.add_argument("--horizons", default="1,3,5,10")
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    horizons = parse_horizons(args.horizons)
    report = evaluate_watchlist(Path(args.watchlist), args.signal_date, horizons)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = args.signal_date
    json_path = output_dir / f"finance-forward-eval-{suffix}.json"
    md_path = output_dir / f"finance-forward-eval-{suffix}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "count": report["count"],
        "evaluated": report["evaluated"],
        "summary": report["summary"]["by_horizon"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
