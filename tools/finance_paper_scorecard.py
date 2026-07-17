"""Build candidate score adjustments from paper-trade validation reports.

Forward evaluation checks whether watchlist signals worked. Paper-trade
validation checks whether the generated plan itself would have made money.
This scorecard converts recent paper-trade PnL into conservative theme nudges.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_paper_reports(paths: list[Path]) -> list[dict]:
    reports = []
    for path in paths:
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("trades") is not None:
            data["_path"] = str(path)
            reports.append(data)
    return reports


def discover_reports(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("finance-paper-trade-*.json"))


def sample_weight(count: int, min_samples: int) -> float:
    if count <= 0:
        return 0.0
    return min(1.0, math.sqrt(count / max(min_samples, 1)))


def build_paper_scorecard(reports: list[dict], min_samples: int = 5, max_adjustment: float = 10.0) -> dict:
    by_theme = defaultdict(lambda: {"count": 0, "wins": 0, "return_sum": 0.0, "pnl": 0.0, "stop_losses": 0})
    overall = {"count": 0, "wins": 0, "return_sum": 0.0, "pnl": 0.0}
    for report in reports:
        for trade in report.get("trades", []):
            if trade.get("status") != "closed":
                continue
            theme = str(trade.get("theme", "") or "未分类")
            ret = float(trade.get("return", 0) or 0)
            pnl = float(trade.get("net_pnl", 0) or 0)
            win = 1 if pnl > 0 else 0
            by_theme[theme]["count"] += 1
            by_theme[theme]["wins"] += win
            by_theme[theme]["return_sum"] += ret
            by_theme[theme]["pnl"] += pnl
            if trade.get("exit_reason") == "stop_loss":
                by_theme[theme]["stop_losses"] += 1
            overall["count"] += 1
            overall["wins"] += win
            overall["return_sum"] += ret
            overall["pnl"] += pnl

    baseline_win = overall["wins"] / overall["count"] if overall["count"] else 0.5
    baseline_return = overall["return_sum"] / overall["count"] if overall["count"] else 0.0
    themes = {}
    for theme, item in by_theme.items():
        count = item["count"]
        win_rate = item["wins"] / count if count else 0.0
        avg_return = item["return_sum"] / count if count else 0.0
        stop_rate = item["stop_losses"] / count if count else 0.0
        weight = sample_weight(count, min_samples)
        edge = (win_rate - baseline_win) * 12 + (avg_return - baseline_return) * 180 - max(0.0, stop_rate - 0.5) * 4
        adjustment = round(max(-max_adjustment, min(max_adjustment, edge * weight)), 2)
        themes[theme] = {
            "count": count,
            "win_rate": round(win_rate, 4),
            "avg_return": round(avg_return, 4),
            "net_pnl": round(item["pnl"], 2),
            "stop_loss_rate": round(stop_rate, 4),
            "sample_weight": round(weight, 4),
            "score_adjustment": adjustment,
        }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "min_samples": min_samples,
        "max_adjustment": max_adjustment,
        "reports_count": len(reports),
        "baseline": {
            "count": overall["count"],
            "win_rate": round(baseline_win, 4),
            "avg_return": round(baseline_return, 4),
            "net_pnl": round(overall["pnl"], 2),
        },
        "themes": dict(sorted(themes.items(), key=lambda kv: kv[1]["score_adjustment"], reverse=True)),
    }


def render_markdown(scorecard: dict) -> str:
    lines = [
        f"# 纸面交易反馈评分卡 - {scorecard['generated_at']}",
        "",
        "用途：把计划级纸面交易表现转成后续候选排序的保守加减分。",
        "",
        f"- 报告数: {scorecard['reports_count']}",
        f"- 样本门槛: {scorecard['min_samples']}",
        f"- 单题材最大调整: {scorecard['max_adjustment']}",
        f"- 基线样本数: {scorecard['baseline']['count']}",
        f"- 基线胜率: {scorecard['baseline']['win_rate']}",
        f"- 基线平均收益: {scorecard['baseline']['avg_return']}",
        f"- 基线净盈亏: {scorecard['baseline']['net_pnl']}",
        "",
        "| 题材 | 样本数 | 胜率 | 平均收益 | 净盈亏 | 止损率 | 样本权重 | 候选分调整 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for theme, row in scorecard["themes"].items():
        lines.append(
            f"| {theme} | {row['count']} | {row['win_rate']} | {row['avg_return']} | {row['net_pnl']} | "
            f"{row['stop_loss_rate']} | {row['sample_weight']} | {row['score_adjustment']} |"
        )
    lines.extend([
        "",
        "## 使用原则",
        "",
        "- 这是计划级反馈，专门惩罚“生成了计划但模拟执行亏损”的题材。",
        "- 样本少时自动降低权重，避免过拟合。",
        "- 连续纸面亏损的题材应降低候选排序，不应扩大实盘仓位。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build scorecard from finance paper-trade reports.")
    parser.add_argument("--input-dir", default="qclaw-output")
    parser.add_argument("--output-dir", default="qclaw-output")
    parser.add_argument("--min-samples", type=int, default=5)
    parser.add_argument("--max-adjustment", type=float, default=10.0)
    args = parser.parse_args()

    reports = load_paper_reports(discover_reports(Path(args.input_dir)))
    scorecard = build_paper_scorecard(reports, args.min_samples, args.max_adjustment)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "finance-paper-scorecard.json"
    md_path = output_dir / "finance-paper-scorecard.md"
    json_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(scorecard), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "reports_count": scorecard["reports_count"],
        "themes": len(scorecard["themes"]),
        "baseline": scorecard["baseline"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
