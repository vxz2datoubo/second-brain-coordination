"""Build a signal scorecard from forward-evaluation reports.

The scorecard converts historical forward performance into small, auditable
theme adjustments for the next daily pipeline. It is deliberately conservative:
small samples have low weight, and the output is a nudge rather than a trade
signal by itself.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_forward_reports(paths: list[Path]) -> list[dict]:
    reports = []
    for path in paths:
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("summary"):
            data["_path"] = str(path)
            reports.append(data)
    return reports


def sample_weight(count: int, min_samples: int) -> float:
    if count <= 0:
        return 0.0
    return min(1.0, math.sqrt(count / max(min_samples, 1)))


def build_scorecard(reports: list[dict], target_horizon: int = 3, min_samples: int = 5) -> dict:
    by_theme = defaultdict(lambda: {"count": 0, "hits": 0.0, "return_sum": 0.0})
    overall = {"count": 0, "hits": 0.0, "return_sum": 0.0}
    for report in reports:
        for row in report.get("summary", {}).get("by_theme", []):
            if int(row.get("horizon", 0) or 0) != target_horizon:
                continue
            count = int(row.get("count", 0) or 0)
            hit_rate = float(row.get("hit_rate", 0) or 0)
            avg_return = float(row.get("avg_return", 0) or 0)
            theme = str(row.get("theme", "") or "未分类")
            by_theme[theme]["count"] += count
            by_theme[theme]["hits"] += hit_rate * count
            by_theme[theme]["return_sum"] += avg_return * count
            overall["count"] += count
            overall["hits"] += hit_rate * count
            overall["return_sum"] += avg_return * count

    baseline_hit = overall["hits"] / overall["count"] if overall["count"] else 0.5
    baseline_return = overall["return_sum"] / overall["count"] if overall["count"] else 0.0
    themes = {}
    for theme, item in by_theme.items():
        count = item["count"]
        hit_rate = item["hits"] / count if count else 0.0
        avg_return = item["return_sum"] / count if count else 0.0
        weight = sample_weight(count, min_samples)
        edge = (hit_rate - baseline_hit) * 18 + (avg_return - baseline_return) * 220
        adjustment = round(max(-12.0, min(12.0, edge * weight)), 2)
        themes[theme] = {
            "count": count,
            "hit_rate": round(hit_rate, 4),
            "avg_return": round(avg_return, 4),
            "sample_weight": round(weight, 4),
            "score_adjustment": adjustment,
        }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target_horizon": target_horizon,
        "min_samples": min_samples,
        "reports_count": len(reports),
        "baseline": {
            "count": overall["count"],
            "hit_rate": round(baseline_hit, 4),
            "avg_return": round(baseline_return, 4),
        },
        "themes": dict(sorted(themes.items(), key=lambda kv: kv[1]["score_adjustment"], reverse=True)),
    }


def render_markdown(scorecard: dict) -> str:
    lines = [
        f"# 信号评分卡 - {scorecard['generated_at']}",
        "",
        f"- 目标周期: {scorecard['target_horizon']} 个交易日",
        f"- 前向评估报告数: {scorecard['reports_count']}",
        f"- 基线样本数: {scorecard['baseline']['count']}",
        f"- 基线命中率: {scorecard['baseline']['hit_rate']}",
        f"- 基线平均收益: {scorecard['baseline']['avg_return']}",
        "",
        "| 题材 | 样本数 | 命中率 | 平均收益 | 样本权重 | 候选分调整 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for theme, row in scorecard["themes"].items():
        lines.append(
            f"| {theme} | {row['count']} | {row['hit_rate']} | {row['avg_return']} | "
            f"{row['sample_weight']} | {row['score_adjustment']} |"
        )
    lines.extend([
        "",
        "## 使用原则",
        "",
        "- 评分卡只调整候选排序，不单独构成买卖信号。",
        "- 样本数少时调整幅度会被压低，避免过拟合。",
        "- 如果某题材长期低命中或高回撤，应降低观察优先级。",
        "- 如果某题材长期高命中且回撤小，可以提高观察优先级，但仍需仓位和止损约束。",
    ])
    return "\n".join(lines) + "\n"


def discover_reports(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("finance-forward-eval-*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build finance signal scorecard from forward evaluation JSON files.")
    parser.add_argument("--input-dir", default="qclaw-output")
    parser.add_argument("--output-dir", default="qclaw-output")
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--min-samples", type=int, default=5)
    args = parser.parse_args()

    reports = load_forward_reports(discover_reports(Path(args.input_dir)))
    scorecard = build_scorecard(reports, args.horizon, args.min_samples)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "finance-signal-scorecard.json"
    md_path = output_dir / "finance-signal-scorecard.md"
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
