"""Analyze multi-day finance theme trends.

Daily hot-theme reports are useful, but trading decisions also need continuity:
is a theme warming up, fading, or only a one-day spike? This tool reads recent
daily-items JSONL files and/or generated daily reports, then builds a recent
theme trend report.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import analyze_hot_themes  # noqa: E402
from tools.finance_daily_report import load_jsonl  # noqa: E402


def parse_date_from_name(path: Path) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return match.group(1) if match else ""


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_daily_report(path: Path) -> dict:
    date = parse_date_from_name(path)
    rows = []
    in_hot_table = False
    headers: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_hot_table = ("题材" in line and "热" in line) or ("棰樻潗" in line and "鐑" in line)
            headers = []
            continue
        if not in_hot_table or not line.startswith("|"):
            continue
        if "---" in line:
            continue
        cells = split_table_row(line)
        if not headers:
            headers = cells
            continue
        if len(cells) < len(headers):
            continue
        row = {headers[i]: cells[i] for i in range(len(headers))}
        rows.append(normalize_theme_row(row, date, str(path)))
    return {"date": date, "source_path": str(path), "themes": [row for row in rows if row.get("theme")]}


def normalize_theme_row(row: dict, date: str, source_path: str) -> dict:
    theme = row.get("题材") or row.get("棰樻潗") or row.get("theme") or ""
    lifecycle = row.get("阶段") or row.get("闃舵") or row.get("lifecycle") or ""
    risk = row.get("风险") or row.get("椋庨櫓") or row.get("risk_level") or ""
    priority = row.get("优先级") or row.get("浼樺厛绾") or row.get("action_priority") or 0
    score = row.get("热度分") or row.get("鐑害鍒") or row.get("score") or 0
    mentions = row.get("提及") or row.get("鎻愬強") or row.get("mentions") or 0
    suggestion = row.get("建议") or row.get("寤鸿") or row.get("suggestion") or ""
    return {
        "date": date,
        "theme": theme,
        "lifecycle": lifecycle,
        "risk_level": risk,
        "action_priority": parse_float(priority),
        "score": parse_float(score),
        "mentions": int(parse_float(mentions)),
        "suggestion": suggestion,
        "source_path": source_path,
    }


def daily_from_items(path: Path) -> dict:
    date = parse_date_from_name(path)
    items = load_jsonl(path)
    trends = analyze_hot_themes(items, top_k=20)
    rows = []
    for row in trends.get("themes", []):
        rows.append({
            "date": date or str(row.get("date", "")),
            "theme": row.get("theme", ""),
            "lifecycle": row.get("lifecycle", ""),
            "risk_level": row.get("risk_level", ""),
            "action_priority": parse_float(row.get("action_priority")),
            "score": parse_float(row.get("score")),
            "mentions": int(parse_float(row.get("mentions"))),
            "suggestion": row.get("suggestion", ""),
            "source_path": str(path),
        })
    return {"date": date, "source_path": str(path), "themes": rows}


def load_daily_series(input_dir: Path, pattern: str, reports_pattern: str, days: int) -> list[dict]:
    by_date: dict[str, dict] = {}
    for path in sorted(input_dir.glob(pattern)):
        date = parse_date_from_name(path)
        if not date:
            continue
        try:
            by_date[date] = daily_from_items(path)
        except Exception:
            continue
    for path in sorted(input_dir.glob(reports_pattern)):
        date = parse_date_from_name(path)
        if not date or date in by_date:
            continue
        try:
            by_date[date] = parse_daily_report(path)
        except Exception:
            continue
    series = [by_date[date] for date in sorted(by_date)]
    return series[-days:] if days > 0 else series


def classify_trend(scores: list[float], lifecycles: list[str]) -> str:
    nonzero = [score for score in scores if score > 0]
    if not nonzero:
        return "无热度"
    first = scores[0]
    last = scores[-1]
    peak = max(scores)
    active_days = len(nonzero)
    if lifecycles and lifecycles[-1] in {"退潮", "閫€娼?"}:
        return "退潮风险"
    if active_days == 1 and last > 0:
        return "单日脉冲"
    if last >= first * 1.5 and last >= 3:
        return "升温"
    if first > 0 and last <= first * 0.5:
        return "降温"
    if active_days >= max(2, len(scores) // 2) and last >= peak * 0.65:
        return "持续热门"
    return "观察"


def analyze_theme_trends(series: list[dict]) -> dict:
    dates = [day["date"] for day in series]
    all_themes = sorted({row["theme"] for day in series for row in day.get("themes", []) if row.get("theme")})
    rows = []
    for theme in all_themes:
        by_date = {day["date"]: None for day in series}
        for day in series:
            for row in day.get("themes", []):
                if row.get("theme") == theme:
                    by_date[day["date"]] = row
        scores = [parse_float((by_date[date] or {}).get("score")) for date in dates]
        mentions = [int(parse_float((by_date[date] or {}).get("mentions"))) for date in dates]
        lifecycles = [str((by_date[date] or {}).get("lifecycle", "")) for date in dates if by_date[date]]
        latest = next((by_date[date] for date in reversed(dates) if by_date[date]), {})
        active_days = sum(1 for score in scores if score > 0)
        score_change = round(scores[-1] - scores[0], 3) if scores else 0
        momentum = round((scores[-1] if scores else 0) + score_change + active_days * 0.75, 3)
        rows.append({
            "theme": theme,
            "trend": classify_trend(scores, lifecycles),
            "active_days": active_days,
            "latest_score": scores[-1] if scores else 0,
            "score_change": score_change,
            "total_score": round(sum(scores), 3),
            "total_mentions": sum(mentions),
            "momentum_score": momentum,
            "latest_lifecycle": latest.get("lifecycle", ""),
            "latest_risk": latest.get("risk_level", ""),
            "latest_suggestion": latest.get("suggestion", ""),
            "scores": {date: scores[i] for i, date in enumerate(dates)},
            "mentions": {date: mentions[i] for i, date in enumerate(dates)},
        })
    rows.sort(key=lambda row: (row["momentum_score"], row["latest_score"], row["total_score"]), reverse=True)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dates": dates,
        "days": len(dates),
        "themes": rows,
        "rising": [row for row in rows if row["trend"] == "升温"],
        "persistent": [row for row in rows if row["trend"] == "持续热门"],
        "fading": [row for row in rows if row["trend"] in {"降温", "退潮风险"}],
        "spikes": [row for row in rows if row["trend"] == "单日脉冲"],
    }


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict, output_json: Path) -> str:
    dates = report.get("dates", [])
    lines = [
        f"# 最近题材趋势报告 - {dates[0] if dates else ''} ~ {dates[-1] if dates else ''}",
        "",
        "用途：判断题材是连续升温、持续热门、降温退潮，还是单日脉冲。不构成投资建议。",
        "",
        "## 总览",
        "",
        f"- 覆盖天数: {report.get('days', 0)}",
        f"- 题材数: {len(report.get('themes', []))}",
        f"- 升温: {len(report.get('rising', []))}",
        f"- 持续热门: {len(report.get('persistent', []))}",
        f"- 降温/退潮: {len(report.get('fading', []))}",
        f"- 单日脉冲: {len(report.get('spikes', []))}",
        f"- JSON: `{output_json}`",
        "",
        "## 趋势排名",
        "",
        "| 排名 | 题材 | 趋势 | 活跃天数 | 最新热度 | 热度变化 | 总热度 | 最新阶段 | 最新风险 | 建议 |",
        "|---:|---|---|---:|---:|---:|---:|---|---|---|",
    ]
    for rank, row in enumerate(report.get("themes", [])[:20], 1):
        lines.append(
            f"| {rank} | {md_escape(row['theme'])} | {row['trend']} | {row['active_days']} | "
            f"{row['latest_score']} | {row['score_change']} | {row['total_score']} | "
            f"{md_escape(row['latest_lifecycle'])} | {md_escape(row['latest_risk'])} | "
            f"{md_escape(row['latest_suggestion'])} |"
        )
    lines.extend(["", "## 操作含义", ""])
    lines.extend([
        "- `升温`: 可以进入重点观察，但仍要等价格、量能和仓位计划确认。",
        "- `持续热门`: 只做核心分歧低吸或计划内回踩，不因连续热度追高。",
        "- `降温/退潮`: 降低权重，已有持仓先看止损和减仓纪律。",
        "- `单日脉冲`: 先观察第二天是否延续，不直接放大仓位。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze recent multi-day finance theme trends.")
    parser.add_argument("--input-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--pattern", default="finance-daily-items-*.jsonl")
    parser.add_argument("--reports-pattern", default="finance-daily-report-*.md")
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    series = load_daily_series(Path(args.input_dir), args.pattern, args.reports_pattern, args.days)
    if not series:
        print(json.dumps({"success": False, "error": "no daily items or reports found"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    report = analyze_theme_trends(series)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"finance-theme-trends-{args.date}.json"
    md_path = output_dir / f"finance-theme-trends-{args.date}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, json_path), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "days": report["days"],
        "themes": len(report["themes"]),
        "rising": [row["theme"] for row in report["rising"][:5]],
        "fading": [row["theme"] for row in report["fading"][:5]],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
