"""Create a risk-controlled portfolio plan from a finance watchlist.

The plan sizes each candidate from account risk, ATR stop distance and maximum
position cap. It is a discipline tool, not investment advice.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import load_price_csv, optimize_backtests, run_backtest_strategy  # noqa: E402
from tools.finance_brain import ingest_report_once  # noqa: E402


EXECUTION_COLUMNS = {
    "adjustment": ("adjustment", "adjust", "复权", "复权方式", "复权类型"),
    "limit_up": ("limit_up", "up_limit", "涨停价", "涨停", "涨停价格"),
    "limit_down": ("limit_down", "down_limit", "跌停价", "跌停", "跌停价格"),
    "paused": ("paused", "suspended", "停牌", "是否停牌", "交易状态"),
}


def load_watchlist(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if row.get("csv_path")]


def norm_header(name: str) -> str:
    return str(name or "").strip().lower().replace("\ufeff", "")


def pick_column(headers: list[str], names: tuple[str, ...]) -> str | None:
    normalized = {norm_header(h): h for h in headers}
    for name in names:
        key = norm_header(name)
        if key in normalized:
            return normalized[key]
    return None


def to_float(value: object, default: float = 0.0) -> float:
    try:
        text = str(value if value is not None else "").strip().replace(",", "")
        return float(text) if text else default
    except (TypeError, ValueError):
        return default


def truthy(value: object) -> bool:
    text = str(value if value is not None else "").strip().lower()
    return text in {"1", "true", "yes", "y", "停牌", "suspended", "paused", "暂停"}


def load_execution_flags(csv_path: str) -> dict:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = [row for row in reader if any(str(v).strip() for v in row.values())]
    if not rows:
        return {}
    latest = rows[-1]
    columns = {key: pick_column(headers, names) for key, names in EXECUTION_COLUMNS.items()}
    adjustment_col = columns["adjustment"]
    limit_up_col = columns["limit_up"]
    limit_down_col = columns["limit_down"]
    paused_col = columns["paused"]
    return {
        "adjustment": str(latest.get(adjustment_col, "")).strip() if adjustment_col else "",
        "limit_up": to_float(latest.get(limit_up_col), 0.0) if limit_up_col else 0.0,
        "limit_down": to_float(latest.get(limit_down_col), 0.0) if limit_down_col else 0.0,
        "paused": truthy(latest.get(paused_col)) if paused_col else False,
        "has_adjustment": bool(adjustment_col),
        "has_limit_prices": bool(limit_up_col and limit_down_col),
        "has_suspension_flag": bool(paused_col),
    }


def analyze_row(row: dict) -> dict:
    bars = load_price_csv(row["csv_path"])
    strategy = row.get("strategy") or "optimize"
    if strategy == "optimize":
        result = optimize_backtests(bars)["best"] or {}
    else:
        result = run_backtest_strategy(
            bars,
            strategy=strategy,
            short_window=int(row.get("short_window") or 5),
            long_window=int(row.get("long_window") or 20),
            breakout_window=int(row.get("breakout_window") or 20),
            exit_window=int(row.get("exit_window") or 10),
            rsi_window=int(row.get("rsi_window") or 14),
            buy_below=float(row.get("buy_below") or 35),
            sell_above=float(row.get("sell_above") or 55),
        )
    result["symbol"] = row.get("symbol", "")
    result["name"] = row.get("name", "")
    result["theme"] = row.get("theme", "")
    result["csv_path"] = row.get("csv_path", "")
    result["execution_flags"] = load_execution_flags(row["csv_path"])
    return result


def build_plan(
    watchlist: list[dict],
    account_equity: float,
    risk_per_trade: float,
    max_position_pct: float,
    max_total_exposure: float,
    max_theme_exposure_pct: float,
    atr_multiple: float,
    min_score: float,
) -> dict:
    candidates = []
    for row in watchlist:
        try:
            result = analyze_row(row)
            latest = result.get("latest", {})
            entry = to_float(latest.get("close"))
            atr = to_float(latest.get("atr14"))
            stop = entry - atr_multiple * atr if entry > 0 and atr > 0 else 0
            risk_per_share = max(entry - stop, 0)
            risk_budget = account_equity * risk_per_trade
            raw_qty = int(risk_budget / risk_per_share) if risk_per_share > 0 else 0
            max_notional = account_equity * max_position_pct
            cap_qty = int(max_notional / entry) if entry > 0 else 0
            qty = max(0, min(raw_qty, cap_qty))
            notional = qty * entry
            actual_risk = qty * risk_per_share
            allowed = (
                qty > 0
                and result.get("risk_adjusted_score", -999) >= min_score
                and result.get("max_drawdown", 0) > -0.2
            )
            reason = []
            flags = result.get("execution_flags", {})
            if qty <= 0:
                reason.append("仓位为0，可能是ATR/价格数据不足或风险预算太小")
            if result.get("risk_adjusted_score", -999) < min_score:
                reason.append("策略分低于阈值")
            if result.get("max_drawdown", 0) <= -0.2:
                reason.append("历史回撤超过20%")
            if flags.get("paused"):
                allowed = False
                reason.append("最新交易日停牌，不允许新开仓")
            limit_up = to_float(flags.get("limit_up"))
            limit_down = to_float(flags.get("limit_down"))
            if limit_up > 0 and entry >= limit_up * 0.999:
                allowed = False
                reason.append("接近或触及涨停，买入可能不可成交")
            if limit_down > 0 and entry <= limit_down * 1.001:
                allowed = False
                reason.append("接近或触及跌停，流动性和止损执行风险过高")
            if not flags.get("has_adjustment"):
                reason.append("缺少复权方式，需人工确认数据口径")
            if not flags.get("has_limit_prices"):
                reason.append("缺少涨跌停价，需人工确认可成交性")
            if not flags.get("has_suspension_flag"):
                reason.append("缺少停牌标记，需人工确认交易状态")
            if not reason:
                reason.append("通过基础仓位检查，仍需交易前 consult")
            candidates.append({
                "symbol": result.get("symbol", ""),
                "name": result.get("name", ""),
                "theme": result.get("theme", ""),
                "strategy": result.get("strategy", ""),
                "score": result.get("risk_adjusted_score", 0),
                "entry": round(entry, 4),
                "stop": round(stop, 4),
                "atr": round(atr, 4),
                "qty": qty,
                "notional": round(notional, 2),
                "position_pct": round(notional / account_equity, 4) if account_equity else 0,
                "risk_amount": round(actual_risk, 2),
                "risk_pct": round(actual_risk / account_equity, 4) if account_equity else 0,
                "adjustment": flags.get("adjustment", ""),
                "limit_up": round(limit_up, 4) if limit_up else "",
                "limit_down": round(limit_down, 4) if limit_down else "",
                "paused": bool(flags.get("paused")),
                "allowed": allowed,
                "reason": "；".join(reason),
                "backtest": {
                    "total_return": result.get("total_return"),
                    "max_drawdown": result.get("max_drawdown"),
                    "win_rate": result.get("win_rate"),
                    "trades_count": result.get("trades_count"),
                },
            })
        except Exception as exc:
            candidates.append({
                "symbol": row.get("symbol", ""),
                "name": row.get("name", ""),
                "theme": row.get("theme", ""),
                "allowed": False,
                "reason": f"{type(exc).__name__}: {exc}",
            })

    candidates.sort(key=lambda x: (x.get("allowed", False), x.get("score", -999)), reverse=True)
    selected = []
    exposure = 0.0
    theme_exposure: dict[str, float] = {}
    for candidate in candidates:
        if not candidate.get("allowed"):
            continue
        if exposure + candidate.get("notional", 0) > account_equity * max_total_exposure:
            candidate["allowed"] = False
            candidate["reason"] += "；超过组合总暴露上限"
            continue
        theme = str(candidate.get("theme") or "未分类")
        next_theme_exposure = theme_exposure.get(theme, 0.0) + candidate.get("notional", 0)
        if next_theme_exposure > account_equity * max_theme_exposure_pct:
            candidate["allowed"] = False
            candidate["reason"] += "；超过单题材暴露上限"
            continue
        selected.append(candidate)
        exposure += candidate.get("notional", 0)
        theme_exposure[theme] = next_theme_exposure

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "account_equity": account_equity,
        "risk_per_trade": risk_per_trade,
        "max_position_pct": max_position_pct,
        "max_total_exposure": max_total_exposure,
        "max_theme_exposure_pct": max_theme_exposure_pct,
        "atr_multiple": atr_multiple,
        "min_score": min_score,
        "selected_count": len(selected),
        "planned_exposure": round(exposure, 2),
        "planned_exposure_pct": round(exposure / account_equity, 4) if account_equity else 0,
        "theme_exposure": {theme: round(value, 2) for theme, value in sorted(theme_exposure.items())},
        "candidates": candidates,
    }


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_report(plan: dict, report_date: str, watchlist_path: Path) -> str:
    lines = [
        f"# 组合仓位与风险计划 - {report_date}",
        "",
        "用途: 把观察池候选转换成有止损、有仓位上限、有组合暴露控制的交易计划。不构成投资建议。",
        "",
        "## 风控参数",
        "",
        f"- 账户权益: {plan['account_equity']}",
        f"- 单笔风险: {plan['risk_per_trade']}",
        f"- 单标的仓位上限: {plan['max_position_pct']}",
        f"- 组合总暴露上限: {plan['max_total_exposure']}",
        f"- 单题材暴露上限: {plan['max_theme_exposure_pct']}",
        f"- ATR 止损倍数: {plan['atr_multiple']}",
        f"- 最低策略分: {plan['min_score']}",
        f"- 计划总暴露: {plan['planned_exposure']} ({plan['planned_exposure_pct']})",
        "",
        "## 候选计划",
        "",
        "| 允许 | 标的 | 名称 | 题材 | 策略 | 分数 | 入场 | 止损 | 涨停 | 跌停 | 停牌 | 数量 | 仓位 | 风险 | 原因 |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in plan["candidates"]:
        lines.append(
            f"| {'是' if row.get('allowed') else '否'} | {md_escape(row.get('symbol'))} | {md_escape(row.get('name'))} | "
            f"{md_escape(row.get('theme'))} | {md_escape(row.get('strategy'))} | {row.get('score', '')} | "
            f"{row.get('entry', '')} | {row.get('stop', '')} | {row.get('limit_up', '')} | "
            f"{row.get('limit_down', '')} | {'是' if row.get('paused') else '否'} | {row.get('qty', '')} | "
            f"{row.get('position_pct', '')} | {row.get('risk_pct', '')} | {md_escape(row.get('reason'))} |"
        )
    lines.extend([
        "",
        "## 执行纪律",
        "",
        "- 计划外标的不交易。",
        "- 未触及计划入场条件不交易。",
        "- 跌破止损不补仓，先退出再复盘。",
        "- 最新交易日停牌、接近涨停或接近跌停的标的，不做新开仓计划。",
        "- 同一题材累计暴露超过上限时，后续同题材候选不再开新仓。",
        "- 缺少复权、涨跌停价或停牌字段时，必须人工确认可成交性。",
        "- 同一题材同时持仓过多时，优先保留分数最高且回撤更小的标的。",
        "- 下单前必须再调用 `/api/finance/consult` 做交易前红线检查。",
        "",
        "## 元数据",
        "",
        f"- 观察池文件: `{watchlist_path}`",
        f"- 生成时间: {plan['generated_at']}",
    ])
    return "\n".join(lines) + "\n"


def ingest_report(report: str, title: str, brain_url: str) -> dict:
    return ingest_report_once(report, title, "finance-portfolio-plan", brain_url)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build risk-controlled portfolio plan.")
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--account-equity", type=float, default=100000)
    parser.add_argument("--risk-per-trade", type=float, default=0.005)
    parser.add_argument("--max-position-pct", type=float, default=0.2)
    parser.add_argument("--max-total-exposure", type=float, default=0.6)
    parser.add_argument("--max-theme-exposure-pct", type=float, default=0.35)
    parser.add_argument("--atr-multiple", type=float, default=2.0)
    parser.add_argument("--min-score", type=float, default=15.0)
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--brain-url", default="http://localhost:8766")
    args = parser.parse_args()

    watchlist_path = Path(args.watchlist)
    plan = build_plan(
        load_watchlist(watchlist_path),
        account_equity=args.account_equity,
        risk_per_trade=args.risk_per_trade,
        max_position_pct=args.max_position_pct,
        max_total_exposure=args.max_total_exposure,
        max_theme_exposure_pct=args.max_theme_exposure_pct,
        atr_multiple=args.atr_multiple,
        min_score=args.min_score,
    )
    report = render_report(plan, args.date, watchlist_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"finance-portfolio-plan-{args.date}.md"
    output_path.write_text(report, encoding="utf-8")
    result = {"report_path": str(output_path), "selected_count": plan["selected_count"], "planned_exposure": plan["planned_exposure"]}
    if args.ingest:
        result["ingest"] = ingest_report(report, f"组合仓位与风险计划 - {args.date}", args.brain_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
