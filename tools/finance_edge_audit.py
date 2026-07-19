"""Audit whether the finance advisor currently shows positive edge.

This combines three evidence streams:
- real closed trades from the journal,
- paper-trade execution of generated plans,
- forward evaluation of watchlist signals.

The result is a system-level traffic light for whether to keep normal risk,
reduce risk, or pause new trades until the evidence improves.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.finance_trade_journal import compute_attribution, load_jsonl  # noqa: E402


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def discover(input_dir: Path, pattern: str) -> list[Path]:
    return sorted(input_dir.glob(pattern))


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def real_trade_evidence(journal_path: Path) -> dict:
    trades = load_jsonl(journal_path) if journal_path.exists() else []
    attribution = compute_attribution(trades)
    realized = attribution.get("realized", [])
    returns = [float(row.get("return", 0) or 0) for row in realized]
    return {
        "source": str(journal_path),
        "count": attribution.get("closed_trades", 0),
        "win_rate": attribution.get("win_rate", 0),
        "avg_return": round(avg(returns), 4),
        "net_pnl": attribution.get("total_realized_pnl", 0),
        "avg_win": attribution.get("avg_win", 0),
        "avg_loss": attribution.get("avg_loss", 0),
    }


def paper_evidence(paths: list[Path]) -> dict:
    trades = []
    reports_count = 0
    for path in paths:
        data = load_json(path)
        if not data:
            continue
        reports_count += 1
        for row in data.get("trades", []):
            if row.get("status") == "closed":
                copy = dict(row)
                copy["_report"] = str(path)
                trades.append(copy)
    returns = [float(row.get("return", 0) or 0) for row in trades]
    wins = [row for row in trades if float(row.get("net_pnl", 0) or 0) > 0]
    stop_losses = [row for row in trades if row.get("exit_reason") == "stop_loss"]
    return {
        "reports_count": reports_count,
        "count": len(trades),
        "win_rate": round(len(wins) / len(trades), 4) if trades else 0.0,
        "avg_return": round(avg(returns), 4),
        "net_pnl": round(sum(float(row.get("net_pnl", 0) or 0) for row in trades), 2),
        "stop_loss_rate": round(len(stop_losses) / len(trades), 4) if trades else 0.0,
    }


def forward_evidence(paths: list[Path], horizon: int) -> dict:
    count = 0
    hit_sum = 0.0
    return_sum = 0.0
    reports_count = 0
    for path in paths:
        data = load_json(path)
        if not data.get("summary"):
            continue
        reports_count += 1
        by_horizon = data.get("summary", {}).get("by_horizon", {})
        row = by_horizon.get(str(horizon)) or by_horizon.get(horizon)
        if not row:
            continue
        row_count = int(row.get("count", 0) or 0)
        hit_rate = float(row.get("hit_rate", 0) or 0)
        avg_return = float(row.get("avg_return", 0) or 0)
        count += row_count
        hit_sum += hit_rate * row_count
        return_sum += avg_return * row_count
    return {
        "reports_count": reports_count,
        "horizon": horizon,
        "count": count,
        "hit_rate": round(hit_sum / count, 4) if count else 0.0,
        "avg_return": round(return_sum / count, 4) if count else 0.0,
    }


def score_evidence(real: dict, paper: dict, forward: dict) -> tuple[int, list[str], list[str]]:
    score = 0
    reasons = []
    actions = []

    if real["count"] >= 3:
        if real["net_pnl"] > 0 and real["win_rate"] >= 0.45:
            score += 25
            reasons.append("真实交易已闭合样本为正")
        elif real["net_pnl"] < 0:
            score -= 30
            reasons.append("真实交易净盈亏为负")
            actions.append("降低实盘风险，复盘真实交易原因")
    elif real["count"] > 0:
        reasons.append("真实交易样本较少，暂不作为强证据")
    else:
        reasons.append("暂无真实闭合交易证据")

    if paper["count"] >= 2:
        if paper["avg_return"] > 0 and paper["win_rate"] >= 0.45:
            score += 25
            reasons.append("纸面交易显示计划执行为正")
        elif paper["avg_return"] < 0:
            score -= 30
            reasons.append("纸面交易平均收益为负，计划执行存在问题")
            actions.append("生成或更新纸面评分卡，降低亏损题材/策略排序")
        if paper["stop_loss_rate"] >= 0.5:
            score -= 10
            reasons.append("纸面交易止损率偏高")
            actions.append("检查入场条件、止损距离和市场温度")
    elif paper["count"] > 0:
        reasons.append("纸面交易样本较少，继续积累")
    else:
        reasons.append("暂无纸面交易闭合样本")

    if forward["count"] >= 2:
        if forward["avg_return"] > 0 and forward["hit_rate"] >= 0.5:
            score += 20
            reasons.append("前向评估显示观察池信号为正")
        elif forward["avg_return"] < 0:
            score -= 20
            reasons.append("前向评估收益为负")
            actions.append("降低近期失效题材/策略权重")
    elif forward["count"] > 0:
        reasons.append("前向评估样本较少，继续观察")
    else:
        reasons.append("暂无前向评估样本")

    if forward["avg_return"] > 0 and paper["avg_return"] < 0 and forward["count"] and paper["count"]:
        score -= 10
        reasons.append("信号前向为正但计划纸面为负，问题可能在入场/止损/仓位执行")
        actions.append("优先调试计划执行规则，而不是简单更换题材")

    if not actions:
        actions.append("继续小样本验证，不因单次结果放大仓位")
    return score, reasons, actions


def verdict_from_score(score: int) -> str:
    if score >= 25:
        return "positive"
    if score <= -20:
        return "negative"
    return "caution"


def build_edge_audit(journal: Path, paper_paths: list[Path], forward_paths: list[Path], horizon: int = 3) -> dict:
    real = real_trade_evidence(journal)
    paper = paper_evidence(paper_paths)
    forward = forward_evidence(forward_paths, horizon)
    score, reasons, actions = score_evidence(real, paper, forward)
    verdict = verdict_from_score(score)
    risk_action = {
        "positive": "normal_risk_after_pretrade_checks",
        "caution": "reduced_risk_or_small_sample_only",
        "negative": "pause_or_min_size_until_edge_recovers",
    }[verdict]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "verdict": verdict,
        "edge_score": score,
        "risk_action": risk_action,
        "reasons": reasons,
        "actions": actions,
        "real_trades": real,
        "paper_trades": paper,
        "forward_eval": forward,
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# 盈利边际审计 - {report['generated_at']}",
        "",
        "用途：合并真实交易、纸面交易、前向评估，判断当前系统是否有可用正期望。不构成投资建议。",
        "",
        "## 结论",
        "",
        f"- Verdict: {report['verdict']}",
        f"- Edge score: {report['edge_score']}",
        f"- Risk action: {report['risk_action']}",
        "",
        "## 理由",
        "",
    ]
    lines.extend([f"- {reason}" for reason in report["reasons"]])
    lines.extend(["", "## 下一步动作", ""])
    lines.extend([f"- {action}" for action in report["actions"]])
    lines.extend([
        "",
        "## 证据表",
        "",
        "| 证据 | 样本 | 胜率/命中率 | 平均收益 | 净盈亏 | 备注 |",
        "|---|---:|---:|---:|---:|---|",
    ])
    real = report["real_trades"]
    paper = report["paper_trades"]
    forward = report["forward_eval"]
    lines.append(f"| 真实交易 | {real['count']} | {real['win_rate']} | {real['avg_return']} | {real['net_pnl']} | closed trades |")
    lines.append(f"| 纸面交易 | {paper['count']} | {paper['win_rate']} | {paper['avg_return']} | {paper['net_pnl']} | stop rate {paper['stop_loss_rate']} |")
    lines.append(f"| 前向评估 | {forward['count']} | {forward['hit_rate']} | {forward['avg_return']} | 0 | horizon {forward['horizon']} |")
    lines.extend([
        "",
        "## 使用原则",
        "",
        "- `positive` 也不代表可以重仓，只代表证据允许按既定风控继续。",
        "- `caution` 只做小样本、低风险验证。",
        "- `negative` 时暂停或极小仓，直到纸面交易/真实交易/前向评估改善。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit finance advisor edge from real, paper, and forward evidence.")
    parser.add_argument("--journal", default=str(ROOT / "qclaw-output" / "finance-trade-journal.jsonl"))
    parser.add_argument("--input-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    report = build_edge_audit(
        Path(args.journal),
        discover(input_dir, "finance-paper-trade-*.json"),
        discover(input_dir, "finance-forward-eval-*.json"),
        args.horizon,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"finance-edge-audit-{args.date}.json"
    md_path = output_dir / f"finance-edge-audit-{args.date}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "verdict": report["verdict"],
        "edge_score": report["edge_score"],
        "risk_action": report["risk_action"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
