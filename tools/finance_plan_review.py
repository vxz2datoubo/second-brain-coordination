"""Review actual trades against the portfolio plan.

Compares a generated portfolio plan markdown table with trade journal JSONL and
produces a discipline score. This closes the loop from plan -> execution ->
review.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.finance_trade_journal import compute_attribution, load_jsonl  # noqa: E402


def parse_plan_markdown(path: Path) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8")
    plans: dict[str, dict] = {}
    headers: list[str] = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        if "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "标的" in cells and "数量" in cells:
            headers = cells
            continue
        if not headers or len(cells) < len(headers):
            continue
        row = {header: cells[i] for i, header in enumerate(headers)}
        allowed = row.get("允许", "")
        symbol = row.get("标的", "")
        if not symbol:
            continue
        plans[symbol] = {
            "allowed": allowed == "是",
            "symbol": symbol,
            "name": row.get("名称", ""),
            "theme": row.get("题材", ""),
            "strategy": row.get("策略", ""),
            "score": to_float(row.get("分数")),
            "entry": to_float(row.get("入场")),
            "stop": to_float(row.get("止损")),
            "qty": int(to_float(row.get("数量"))),
            "position_pct": to_float(row.get("仓位")),
            "risk_pct": to_float(row.get("风险")),
            "reason": row.get("原因", ""),
        }
    return plans


def to_float(value: object, default: float = 0.0) -> float:
    try:
        text = str(value).strip().replace("%", "")
        return float(text)
    except (TypeError, ValueError):
        return default


def review_execution(plans: dict[str, dict], trades: list[dict], date: str = "") -> dict:
    by_symbol = defaultdict(list)
    for trade in trades:
        if date and str(trade.get("date", "")) > date:
            continue
        by_symbol[str(trade.get("symbol", ""))].append(trade)

    reviews = []
    total_penalty = 0
    for symbol, symbol_trades in sorted(by_symbol.items()):
        if not symbol:
            continue
        plan = plans.get(symbol)
        buys = [t for t in symbol_trades if str(t.get("side", "")).lower() == "buy"]
        sells = [t for t in symbol_trades if str(t.get("side", "")).lower() == "sell"]
        issues = []
        penalty = 0
        if not plan:
            issues.append("计划外交易")
            penalty += 35
        else:
            if not plan.get("allowed"):
                issues.append("计划不允许但发生交易")
                penalty += 30
            planned_qty = plan.get("qty", 0)
            buy_qty = sum(to_float(t.get("qty")) for t in buys)
            if planned_qty and buy_qty > planned_qty * 1.05:
                issues.append(f"买入数量超计划: {buy_qty} > {planned_qty}")
                penalty += 20
            entry = plan.get("entry", 0) if plan else 0
            for trade in buys:
                price = to_float(trade.get("price"))
                if entry and price > entry * 1.02:
                    issues.append(f"买入价高于计划入场2%以上: {price} > {round(entry * 1.02, 4)}")
                    penalty += 12
            stop = plan.get("stop", 0) if plan else 0
            if stop and buys and not sells:
                last_note = "未平仓，需持续检查止损"
                issues.append(last_note)
            for trade in sells:
                price = to_float(trade.get("price"))
                if stop and price < stop * 0.995:
                    issues.append(f"卖出价低于计划止损，可能执行滞后: {price} < {round(stop, 4)}")
                    penalty += 15
        if not issues:
            issues.append("按计划执行")
        total_penalty += penalty
        reviews.append({
            "symbol": symbol,
            "name": plan.get("name", "") if plan else symbol_trades[0].get("name", ""),
            "theme": plan.get("theme", "") if plan else symbol_trades[0].get("theme", ""),
            "planned": bool(plan),
            "buy_count": len(buys),
            "sell_count": len(sells),
            "penalty": penalty,
            "issues": issues,
        })

    planned_not_traded = [
        plan for symbol, plan in plans.items()
        if plan.get("allowed") and symbol not in by_symbol
    ]
    discipline_score = max(0, 100 - total_penalty)
    attribution = compute_attribution(trades)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "discipline_score": discipline_score,
        "total_penalty": total_penalty,
        "reviews": reviews,
        "planned_not_traded": planned_not_traded,
        "attribution": attribution,
    }


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_report(review: dict, report_date: str, plan_path: Path, journal_path: Path) -> str:
    lines = [
        f"# 计划执行复盘评分 - {report_date}",
        "",
        "用途: 对照仓位计划检查真实交易纪律，识别计划外交易、超量、追高和止损执行问题。",
        "",
        "## 总分",
        "",
        f"- 纪律分: {review['discipline_score']}",
        f"- 扣分: {review['total_penalty']}",
        f"- 已实现盈亏: {review['attribution']['total_realized_pnl']}",
        f"- 平仓笔数: {review['attribution']['closed_trades']}",
        "",
        "## 执行检查",
        "",
        "| 标的 | 名称 | 题材 | 计划内 | 买入笔数 | 卖出笔数 | 扣分 | 问题 |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    if review["reviews"]:
        for row in review["reviews"]:
            lines.append(
                f"| {md_escape(row['symbol'])} | {md_escape(row['name'])} | {md_escape(row['theme'])} | "
                f"{'是' if row['planned'] else '否'} | {row['buy_count']} | {row['sell_count']} | "
                f"{row['penalty']} | {md_escape('；'.join(row['issues']))} |"
            )
    else:
        lines.append("| - | - | - | - | 0 | 0 | 0 | 当日无交易 |")

    lines.extend(["", "## 计划内但未交易", ""])
    if review["planned_not_traded"]:
        for plan in review["planned_not_traded"]:
            lines.append(f"- {plan['symbol']} {plan['name']}：计划允许，但未交易。")
    else:
        lines.append("无。")

    lines.extend([
        "",
        "## 改进动作",
        "",
        "- 纪律分低于 80 时，下一交易日自动降低单笔风险或暂停新开仓。",
        "- 出现计划外交易时，必须写 `教训:` 节点。",
        "- 出现买入价高于计划 2% 以上时，检查是否追高。",
        "- 出现止损滞后时，复盘执行原因，不允许用补仓掩盖。",
        "",
        "## 元数据",
        "",
        f"- 计划文件: `{plan_path}`",
        f"- 账本文件: `{journal_path}`",
        f"- 生成时间: {review['generated_at']}",
    ])
    return "\n".join(lines) + "\n"


def ingest_report(report: str, title: str, brain_url: str) -> dict:
    payload = json.dumps({"title": title, "text": report, "source": "finance-plan-review"}).encode("utf-8")
    req = urllib.request.Request(
        f"{brain_url.rstrip('/')}/api/digest/text",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Review trades against portfolio plan.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--brain-url", default="http://localhost:8766")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    journal_path = Path(args.journal)
    review = review_execution(parse_plan_markdown(plan_path), load_jsonl(journal_path), args.date)
    report = render_report(review, args.date, plan_path, journal_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"finance-plan-review-{args.date}.md"
    output_path.write_text(report, encoding="utf-8")
    result = {"report_path": str(output_path), "discipline_score": review["discipline_score"], "penalty": review["total_penalty"]}
    if args.ingest:
        result["ingest"] = ingest_report(report, f"计划执行复盘评分 - {args.date}", args.brain_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
