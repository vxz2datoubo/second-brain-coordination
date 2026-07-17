"""Batch refresh forward evaluations and the signal scorecard.

Run this weekly after enough future bars have accumulated. It scans historical
watchlists, evaluates eligible ones, and rebuilds the scorecard used by the
daily pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import load_price_csv  # noqa: E402
from tools.finance_forward_eval import evaluate_watchlist, parse_horizons, render_markdown as render_forward_markdown  # noqa: E402
from tools.finance_signal_scorecard import build_scorecard, load_forward_reports, render_markdown as render_scorecard_markdown  # noqa: E402


WATCHLIST_RE = re.compile(r"finance-watchlist-(\d{4}-\d{2}-\d{2})\.csv$")


def watchlist_date(path: Path) -> str | None:
    match = WATCHLIST_RE.match(path.name)
    return match.group(1) if match else None


def has_enough_future_bars(watchlist_path: Path, signal_date: str, max_horizon: int) -> tuple[bool, str]:
    import csv

    with watchlist_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [row for row in csv.DictReader(f) if row.get("csv_path")]
    if not rows:
        return False, "empty watchlist"
    enough = 0
    for row in rows:
        try:
            bars = load_price_csv(row["csv_path"])
            future = [bar for bar in bars if str(bar.date)[:10] >= signal_date]
            if len(future) > max_horizon:
                enough += 1
        except Exception:
            continue
    if enough <= 0:
        return False, f"no symbol has {max_horizon} future bars after {signal_date}"
    return True, f"{enough}/{len(rows)} symbols have enough future bars"


def discover_jobs(watchlist_dir: Path, max_horizon: int) -> tuple[list[dict], list[dict]]:
    jobs = []
    skipped = []
    for path in sorted(watchlist_dir.glob("finance-watchlist-*.csv")):
        signal_date = watchlist_date(path)
        if not signal_date:
            continue
        ok, reason = has_enough_future_bars(path, signal_date, max_horizon)
        row = {"watchlist": str(path), "signal_date": signal_date, "reason": reason}
        if ok:
            jobs.append(row)
        else:
            skipped.append(row)
    return jobs, skipped


def parse_extra_jobs(values: list[str]) -> list[dict]:
    jobs = []
    for value in values:
        if "=" not in value:
            raise ValueError("--extra-watchlist must be PATH=YYYY-MM-DD")
        path_text, signal_date = value.split("=", 1)
        jobs.append({"watchlist": path_text.strip(), "signal_date": signal_date.strip(), "reason": "manual"})
    return jobs


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def refresh(
    watchlist_dir: Path,
    output_dir: Path,
    horizons: list[int],
    scorecard_horizon: int,
    min_samples: int,
    extra_watchlists: list[str] | None = None,
) -> dict:
    max_horizon = max(horizons)
    jobs, skipped = discover_jobs(watchlist_dir, max_horizon)
    jobs.extend(parse_extra_jobs(extra_watchlists or []))

    generated = []
    for job in jobs:
        watchlist_path = Path(job["watchlist"])
        signal_date = job["signal_date"]
        report = evaluate_watchlist(watchlist_path, signal_date, horizons)
        json_path = output_dir / f"finance-forward-eval-{signal_date}.json"
        md_path = output_dir / f"finance-forward-eval-{signal_date}.md"
        write_json(json_path, report)
        write_text(md_path, render_forward_markdown(report))
        generated.append({
            "signal_date": signal_date,
            "watchlist": str(watchlist_path),
            "json_path": str(json_path),
            "md_path": str(md_path),
            "evaluated": report["evaluated"],
        })

    forward_paths = sorted(output_dir.glob("finance-forward-eval-*.json"))
    scorecard = build_scorecard(load_forward_reports(forward_paths), scorecard_horizon, min_samples)
    scorecard_json = output_dir / "finance-signal-scorecard.json"
    scorecard_md = output_dir / "finance-signal-scorecard.md"
    write_json(scorecard_json, scorecard)
    write_text(scorecard_md, render_scorecard_markdown(scorecard))

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "watchlist_dir": str(watchlist_dir),
        "output_dir": str(output_dir),
        "horizons": horizons,
        "scorecard_horizon": scorecard_horizon,
        "min_samples": min_samples,
        "jobs_count": len(jobs),
        "generated": generated,
        "skipped": skipped,
        "scorecard_json": str(scorecard_json),
        "scorecard_md": str(scorecard_md),
        "scorecard_themes": len(scorecard.get("themes", {})),
        "scorecard_baseline": scorecard.get("baseline", {}),
    }
    write_json(output_dir / "finance-feedback-refresh-summary.json", summary)
    write_text(output_dir / "finance-feedback-refresh-summary.md", render_summary(summary))
    return summary


def render_summary(summary: dict) -> str:
    lines = [
        f"# 金融反馈刷新摘要 - {summary['generated_at']}",
        "",
        f"- 观察池目录: `{summary['watchlist_dir']}`",
        f"- 输出目录: `{summary['output_dir']}`",
        f"- 评估周期: {', '.join(str(h) for h in summary['horizons'])}",
        f"- 评分卡周期: {summary['scorecard_horizon']}",
        f"- 生成评估数: {len(summary['generated'])}",
        f"- 跳过观察池数: {len(summary['skipped'])}",
        f"- 评分卡题材数: {summary['scorecard_themes']}",
        f"- 评分卡基线: {summary['scorecard_baseline']}",
        "",
        "## 已生成",
        "",
    ]
    if summary["generated"]:
        for row in summary["generated"]:
            lines.append(f"- {row['signal_date']}: `{row['json_path']}`，可评估 {row['evaluated']} 个")
    else:
        lines.append("- 暂无。")
    lines.extend(["", "## 已跳过", ""])
    if summary["skipped"]:
        for row in summary["skipped"]:
            lines.append(f"- {row['signal_date']}: `{row['watchlist']}`，{row['reason']}")
    else:
        lines.append("- 暂无。")
    lines.extend([
        "",
        "## 下一步",
        "",
        "- 日流水线会读取 `finance-signal-scorecard.json` 做候选分历史调整。",
        "- 样本数不足时，评分卡只作轻微排序修正，不应放大仓位。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch refresh forward evaluations and signal scorecard.")
    parser.add_argument("--watchlist-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--horizons", default="1,3,5,10")
    parser.add_argument("--scorecard-horizon", type=int, default=3)
    parser.add_argument("--min-samples", type=int, default=5)
    parser.add_argument("--extra-watchlist", action="append", default=[], help="Manual PATH=YYYY-MM-DD job")
    args = parser.parse_args()

    summary = refresh(
        Path(args.watchlist_dir),
        Path(args.output_dir),
        parse_horizons(args.horizons),
        args.scorecard_horizon,
        args.min_samples,
        args.extra_watchlist,
    )
    print(json.dumps({
        "success": True,
        "jobs_count": summary["jobs_count"],
        "generated_count": len(summary["generated"]),
        "skipped_count": len(summary["skipped"]),
        "scorecard_themes": summary["scorecard_themes"],
        "summary_json": str(Path(args.output_dir) / "finance-feedback-refresh-summary.json"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
