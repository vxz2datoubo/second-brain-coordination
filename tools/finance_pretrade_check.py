"""Pre-trade gate for planned stock orders.

Checks a proposed order against the generated portfolio plan before any real
trade is placed. Optional Second Brain consult adds lessons and red-line review.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.finance_plan_review import parse_plan_markdown, to_float  # noqa: E402


def consult_brain(payload: dict, brain_url: str) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{brain_url.rstrip('/')}/api/finance/consult",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def evaluate_order(
    plans: dict[str, dict],
    symbol: str,
    action: str,
    qty: float,
    price: float,
    thesis: str = "",
    horizon: str = "",
    max_loss: str = "",
    price_tolerance: float = 0.02,
) -> dict:
    symbol = symbol.strip()
    action_norm = action.strip().lower()
    plan = plans.get(symbol)
    issues = []
    warnings = []

    if not plan:
        issues.append("计划外标的，不允许下单")
        plan = {}
    elif not plan.get("allowed"):
        issues.append(f"仓位计划不允许交易: {plan.get('reason', '')}")

    planned_qty = to_float(plan.get("qty"))
    entry = to_float(plan.get("entry"))
    stop = to_float(plan.get("stop"))
    planned_risk_pct = to_float(plan.get("risk_pct"))

    if action_norm in {"buy", "买入", "b"}:
        if planned_qty and qty > planned_qty:
            issues.append(f"买入数量超过计划: {qty} > {planned_qty}")
        if entry and price > entry * (1 + price_tolerance):
            issues.append(f"买入价格高于计划入场{price_tolerance:.1%}: {price} > {round(entry * (1 + price_tolerance), 4)}")
        if entry and price < entry * 0.9:
            warnings.append("买入价显著低于计划价，确认是否基本面/题材已变化")
    elif action_norm in {"sell", "卖出", "s"}:
        if stop and price < stop * 0.995:
            warnings.append(f"卖出价低于计划止损，可能已执行滞后: {price} < {stop}")
    else:
        issues.append(f"未知方向: {action}")

    if stop and action_norm in {"buy", "买入", "b"} and price <= stop:
        issues.append("买入价已低于或等于止损价，计划失效")
    if not thesis:
        warnings.append("缺少交易理由")
    if not horizon:
        warnings.append("缺少计划周期")
    if not max_loss:
        max_loss = f"计划风险约 {planned_risk_pct}" if planned_risk_pct else ""
        if not max_loss:
            warnings.append("缺少最大可承受亏损")

    verdict = "block" if issues else ("caution" if warnings else "allow")
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "symbol": symbol,
        "action": action,
        "qty": qty,
        "price": price,
        "verdict": verdict,
        "issues": issues,
        "warnings": warnings,
        "plan": plan,
        "consult_payload": {
            "target": f"{symbol} {plan.get('name', '')}".strip(),
            "action": action,
            "thesis": thesis,
            "horizon": horizon,
            "position": f"{qty} 股，计划上限 {planned_qty}" if planned_qty else f"{qty} 股",
            "stop_loss": str(stop) if stop else "",
            "max_loss": max_loss,
        },
    }


def render_markdown(result: dict, plan_path: Path, consult: dict | None = None) -> str:
    lines = [
        f"# 交易前检查 - {result['symbol']}",
        "",
        f"- 方向: {result['action']}",
        f"- 数量: {result['qty']}",
        f"- 价格: {result['price']}",
        f"- 本地结论: {result['verdict']}",
        f"- 计划文件: `{plan_path}`",
        "",
        "## 硬检查问题",
        "",
    ]
    lines.extend([f"- {x}" for x in result["issues"]] or ["- 无。"])
    lines.extend(["", "## 提醒", ""])
    lines.extend([f"- {x}" for x in result["warnings"]] or ["- 无。"])
    plan = result.get("plan") or {}
    lines.extend([
        "",
        "## 计划摘要",
        "",
        f"- 标的: {plan.get('symbol', result['symbol'])} {plan.get('name', '')}",
        f"- 题材: {plan.get('theme', '')}",
        f"- 允许: {plan.get('allowed', False)}",
        f"- 计划入场: {plan.get('entry', '')}",
        f"- 计划止损: {plan.get('stop', '')}",
        f"- 计划数量: {plan.get('qty', '')}",
        f"- 计划风险: {plan.get('risk_pct', '')}",
        f"- 计划原因: {plan.get('reason', '')}",
    ])
    if consult:
        lines.extend([
            "",
            "## 第二大脑 Consult",
            "",
            f"- 结论: {consult.get('verdict', '')}",
            f"- 缺失项: {', '.join(consult.get('missing', [])) or '无'}",
            f"- 风险旗标: {'；'.join(consult.get('risk_flags', [])) or '无'}",
        ])
    lines.extend([
        "",
        "## 执行原则",
        "",
        "- `block` 时不下单。",
        "- `caution` 时先补齐理由、周期、最大亏损或反方证据。",
        "- 任何下单都不能超过计划数量，不能用临场情绪放大仓位。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a proposed trade against the finance portfolio plan.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--qty", type=float, required=True)
    parser.add_argument("--price", type=float, required=True)
    parser.add_argument("--thesis", default="")
    parser.add_argument("--horizon", default="")
    parser.add_argument("--max-loss", default="")
    parser.add_argument("--price-tolerance", type=float, default=0.02)
    parser.add_argument("--consult", action="store_true")
    parser.add_argument("--brain-url", default="http://localhost:8766")
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    plan_path = Path(args.plan)
    result = evaluate_order(
        parse_plan_markdown(plan_path),
        args.symbol,
        args.action,
        args.qty,
        args.price,
        args.thesis,
        args.horizon,
        args.max_loss,
        args.price_tolerance,
    )
    consult_result = None
    if args.consult:
        consult_result = consult_brain(result["consult_payload"], args.brain_url)
        result["consult"] = consult_result

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_symbol = args.symbol.replace("/", "_").replace("\\", "_")
    json_path = output_dir / f"finance-pretrade-check-{safe_symbol}.json"
    md_path = output_dir / f"finance-pretrade-check-{safe_symbol}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(result, plan_path, consult_result), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "verdict": result["verdict"],
        "issues": result["issues"],
        "warnings": result["warnings"],
        "json_path": str(json_path),
        "md_path": str(md_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
