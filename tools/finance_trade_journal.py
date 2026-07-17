"""Trade journal and attribution report for the finance advisor.

Stdlib-only. Stores trades in JSONL and computes realized PnL using average
cost per symbol. The goal is disciplined review, not brokerage-grade accounting.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JOURNAL = ROOT / "qclaw-output" / "finance-trade-journal.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} invalid JSON: {exc}") from exc
    return rows


def append_trade(path: Path, trade: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trade, ensure_ascii=False) + "\n")


def to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_attribution(trades: list[dict]) -> dict:
    positions = defaultdict(lambda: {"qty": 0.0, "cost": 0.0})
    realized = []
    by_symbol = defaultdict(lambda: {"pnl": 0.0, "trades": 0, "wins": 0})
    by_theme = defaultdict(lambda: {"pnl": 0.0, "trades": 0, "wins": 0})
    by_reason = defaultdict(lambda: {"pnl": 0.0, "trades": 0, "wins": 0})

    for trade in sorted(trades, key=lambda t: (str(t.get("date", "")), str(t.get("created_at", "")))):
        symbol = str(trade.get("symbol", "")).strip()
        if not symbol:
            continue
        side = str(trade.get("side", "")).lower()
        qty = abs(to_float(trade.get("qty")))
        price = to_float(trade.get("price"))
        fee = to_float(trade.get("fee"))
        if qty <= 0 or price <= 0:
            continue
        pos = positions[symbol]
        if side == "buy":
            pos["qty"] += qty
            pos["cost"] += qty * price + fee
        elif side == "sell":
            sell_qty = min(qty, pos["qty"]) if pos["qty"] > 0 else qty
            avg_cost = pos["cost"] / pos["qty"] if pos["qty"] > 0 else price
            cost = avg_cost * sell_qty
            proceeds = sell_qty * price - fee
            pnl = proceeds - cost
            if pos["qty"] > 0:
                pos["qty"] -= sell_qty
                pos["cost"] = max(0.0, pos["cost"] - cost)
            row = {
                "date": trade.get("date", ""),
                "symbol": symbol,
                "name": trade.get("name", ""),
                "theme": trade.get("theme", ""),
                "reason": trade.get("reason", ""),
                "qty": sell_qty,
                "sell_price": price,
                "avg_cost": avg_cost,
                "pnl": pnl,
                "return": pnl / cost if cost > 0 else 0.0,
            }
            realized.append(row)
            _add_group(by_symbol[symbol], pnl)
            _add_group(by_theme[str(trade.get("theme", "未分类")) or "未分类"], pnl)
            _add_group(by_reason[str(trade.get("reason", "未记录")) or "未记录"], pnl)

    open_positions = []
    for symbol, pos in positions.items():
        if pos["qty"] > 0:
            open_positions.append({
                "symbol": symbol,
                "qty": round(pos["qty"], 4),
                "avg_cost": round(pos["cost"] / pos["qty"], 4) if pos["qty"] else 0,
                "cost": round(pos["cost"], 2),
            })

    total_pnl = sum(r["pnl"] for r in realized)
    wins = [r for r in realized if r["pnl"] > 0]
    losses = [r for r in realized if r["pnl"] <= 0]
    return {
        "total_realized_pnl": round(total_pnl, 2),
        "closed_trades": len(realized),
        "win_rate": round(len(wins) / len(realized), 4) if realized else 0,
        "avg_win": round(sum(r["pnl"] for r in wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(r["pnl"] for r in losses) / len(losses), 2) if losses else 0,
        "realized": realized,
        "open_positions": open_positions,
        "by_symbol": _sort_groups(by_symbol),
        "by_theme": _sort_groups(by_theme),
        "by_reason": _sort_groups(by_reason),
    }


def _add_group(group: dict, pnl: float) -> None:
    group["pnl"] += pnl
    group["trades"] += 1
    if pnl > 0:
        group["wins"] += 1


def _sort_groups(groups: dict) -> list[dict]:
    rows = []
    for key, value in groups.items():
        trades = value["trades"]
        rows.append({
            "name": key,
            "pnl": round(value["pnl"], 2),
            "trades": trades,
            "win_rate": round(value["wins"] / trades, 4) if trades else 0,
        })
    return sorted(rows, key=lambda r: r["pnl"], reverse=True)


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_report(stats: dict, report_date: str, journal_path: Path) -> str:
    lines = [
        f"# 交易账本绩效归因报告 - {report_date}",
        "",
        "用途: 盘后复盘、识别赚钱/亏钱来源、修正交易规则。不构成投资建议。",
        "",
        "## 总览",
        "",
        f"- 已实现盈亏: {stats['total_realized_pnl']}",
        f"- 平仓笔数: {stats['closed_trades']}",
        f"- 胜率: {stats['win_rate']}",
        f"- 平均盈利: {stats['avg_win']}",
        f"- 平均亏损: {stats['avg_loss']}",
        "",
    ]
    lines.extend(_group_table("按题材归因", stats["by_theme"]))
    lines.extend(_group_table("按标的归因", stats["by_symbol"]))
    lines.extend(_group_table("按交易理由归因", stats["by_reason"]))

    lines.extend(["", "## 当前持仓", ""])
    if stats["open_positions"]:
        lines.extend(["| 标的 | 数量 | 成本价 | 成本 |", "|---|---:|---:|---:|"])
        for row in stats["open_positions"]:
            lines.append(f"| {md_escape(row['symbol'])} | {row['qty']} | {row['avg_cost']} | {row['cost']} |")
    else:
        lines.append("无未平仓持仓。")

    lines.extend([
        "",
        "## 复盘问题",
        "",
        "- 盈利最多的题材是否来自计划内交易，还是偶然追涨？",
        "- 亏损最多的理由是否对应已有红线，如追高、补仓、消息源单一？",
        "- 下一次应该删掉哪类低胜率交易？",
        "- 是否需要降低某个题材或策略的仓位上限？",
        "",
        "## 元数据",
        "",
        f"- 账本文件: `{journal_path}`",
        f"- 生成时间: {datetime.now().isoformat(timespec='seconds')}",
    ])
    return "\n".join(lines) + "\n"


def _group_table(title: str, rows: list[dict]) -> list[str]:
    lines = ["", f"## {title}", ""]
    if not rows:
        lines.append("暂无已实现交易。")
        return lines
    lines.extend(["| 名称 | 盈亏 | 笔数 | 胜率 |", "|---|---:|---:|---:|"])
    for row in rows:
        lines.append(f"| {md_escape(row['name'])} | {row['pnl']} | {row['trades']} | {row['win_rate']} |")
    return lines


def ingest_report(report: str, title: str, brain_url: str) -> dict:
    payload = json.dumps({"title": title, "text": report, "source": "finance-trade-journal"}).encode("utf-8")
    req = urllib.request.Request(
        f"{brain_url.rstrip('/')}/api/digest/text",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def command_add(args: argparse.Namespace) -> int:
    trade = {
        "date": args.date,
        "symbol": args.symbol,
        "name": args.name,
        "theme": args.theme,
        "side": args.side,
        "qty": args.qty,
        "price": args.price,
        "fee": args.fee,
        "reason": args.reason,
        "notes": args.notes,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    append_trade(Path(args.journal), trade)
    print(json.dumps({"success": True, "trade": trade}, ensure_ascii=False, indent=2))
    return 0


def command_report(args: argparse.Namespace) -> int:
    journal = Path(args.journal)
    stats = compute_attribution(load_jsonl(journal))
    report = render_report(stats, args.date, journal)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"finance-trade-journal-report-{args.date}.md"
    output_path.write_text(report, encoding="utf-8")
    result = {"report_path": str(output_path), "closed_trades": stats["closed_trades"], "pnl": stats["total_realized_pnl"]}
    if args.ingest:
        result["ingest"] = ingest_report(report, f"交易账本绩效归因报告 - {args.date}", args.brain_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Finance trade journal.")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Append a trade")
    add.add_argument("--journal", default=str(DEFAULT_JOURNAL))
    add.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    add.add_argument("--symbol", required=True)
    add.add_argument("--name", default="")
    add.add_argument("--theme", default="")
    add.add_argument("--side", choices=["buy", "sell"], required=True)
    add.add_argument("--qty", type=float, required=True)
    add.add_argument("--price", type=float, required=True)
    add.add_argument("--fee", type=float, default=0.0)
    add.add_argument("--reason", default="")
    add.add_argument("--notes", default="")
    add.set_defaults(func=command_add)

    report = sub.add_parser("report", help="Generate attribution report")
    report.add_argument("--journal", default=str(DEFAULT_JOURNAL))
    report.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    report.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    report.add_argument("--ingest", action="store_true")
    report.add_argument("--brain-url", default="http://localhost:8766")
    report.set_defaults(func=command_report)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
