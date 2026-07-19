"""Market CSV quality checks for the finance advisor pipeline.

Backtests are only useful when the input bars are sane. This tool checks local
OHLCV CSV files before they enter the watchlist and portfolio plan.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import Bar, load_price_csv  # noqa: E402
from tools.finance_build_watchlist import infer_symbol_name  # noqa: E402


OPTIONAL_COLUMNS = {
    "adjustment": ("adjustment", "adjust", "复权", "复权方式", "复权类型"),
    "limit_up": ("limit_up", "up_limit", "涨停价", "涨停", "涨停价格"),
    "limit_down": ("limit_down", "down_limit", "跌停价", "跌停", "跌停价格"),
    "paused": ("paused", "suspended", "停牌", "是否停牌", "交易状态"),
}


def _norm_header(name: str) -> str:
    return str(name or "").strip().lower().replace("\ufeff", "")


def _pick_column(headers: list[str], names: tuple[str, ...]) -> str | None:
    normalized = {_norm_header(h): h for h in headers}
    for name in names:
        key = _norm_header(name)
        if key in normalized:
            return normalized[key]
    return None


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        text = str(value if value is not None else "").strip().replace(",", "")
        return float(text) if text else default
    except ValueError:
        return default


def _truthy(value: object) -> bool:
    text = str(value if value is not None else "").strip().lower()
    return text in {"1", "true", "yes", "y", "停牌", "suspended", "paused", "暂停"}


def inspect_optional_columns(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    columns = {key: _pick_column(headers, names) for key, names in OPTIONAL_COLUMNS.items()}
    adjustment_values = []
    if columns["adjustment"]:
        adjustment_values = sorted({
            str(row.get(columns["adjustment"], "")).strip()
            for row in rows
            if str(row.get(columns["adjustment"], "")).strip()
        })

    limit_up_hits = 0
    limit_down_hits = 0
    if columns["limit_up"]:
        limit_up_hits = sum(1 for row in rows if _to_float(row.get(columns["limit_up"])) > 0)
    if columns["limit_down"]:
        limit_down_hits = sum(1 for row in rows if _to_float(row.get(columns["limit_down"])) > 0)

    paused_rows = 0
    if columns["paused"]:
        paused_rows = sum(1 for row in rows if _truthy(row.get(columns["paused"])))

    return {
        "columns": columns,
        "has_adjustment": bool(columns["adjustment"] and adjustment_values),
        "adjustment_values": adjustment_values,
        "has_limit_prices": bool(columns["limit_up"] and columns["limit_down"] and (limit_up_hits or limit_down_hits)),
        "limit_up_rows": limit_up_hits,
        "limit_down_rows": limit_down_hits,
        "has_suspension_flag": bool(columns["paused"]),
        "paused_rows": paused_rows,
    }


def parse_date(value: str) -> datetime | None:
    text = str(value or "").strip()[:10].replace("/", "-")
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def business_days_between(start: datetime, end: datetime) -> int:
    if end <= start:
        return 0
    days = 0
    current = start + timedelta(days=1)
    while current < end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


def _finite(value: float) -> bool:
    return math.isfinite(value)


def check_bars(
    bars: list[Bar],
    min_bars: int = 120,
    max_gap_business_days: int = 10,
    max_abs_return: float = 0.35,
    metadata: dict | None = None,
) -> dict:
    issues: list[dict] = []
    warnings: list[dict] = []
    metadata = metadata or {}

    if len(bars) < min_bars:
        issues.append({"code": "too_few_bars", "message": f"bars {len(bars)} < min_bars {min_bars}", "severity": "error"})

    dates = [parse_date(bar.date) for bar in bars]
    invalid_dates = [bar.date for bar, dt in zip(bars, dates) if dt is None]
    if invalid_dates:
        issues.append({"code": "invalid_date", "message": f"invalid dates: {invalid_dates[:5]}", "severity": "error"})

    valid_pairs = [(bar, dt) for bar, dt in zip(bars, dates) if dt is not None]
    valid_dates = [dt for _, dt in valid_pairs]
    counts = Counter(dt.date().isoformat() for dt in valid_dates)
    duplicates = [date for date, count in counts.items() if count > 1]
    if duplicates:
        issues.append({"code": "duplicate_date", "message": f"duplicate dates: {duplicates[:5]}", "severity": "error"})

    if valid_dates and valid_dates != sorted(valid_dates):
        issues.append({"code": "unsorted_dates", "message": "bars are not sorted ascending by date", "severity": "error"})

    zero_volume = 0
    bad_ohlc = 0
    nonfinite = 0
    jumps: list[str] = []
    gaps: list[str] = []
    prev_bar: Bar | None = None
    prev_dt: datetime | None = None
    for bar, dt in valid_pairs:
        values = [bar.open, bar.high, bar.low, bar.close, bar.volume]
        if any(not _finite(v) for v in values):
            nonfinite += 1
        if bar.low <= 0 or bar.high <= 0 or bar.close <= 0 or bar.open <= 0:
            bad_ohlc += 1
        if not (bar.low <= bar.open <= bar.high and bar.low <= bar.close <= bar.high):
            bad_ohlc += 1
        if bar.volume <= 0:
            zero_volume += 1
        if prev_bar and prev_bar.close > 0:
            daily_return = bar.close / prev_bar.close - 1
            if abs(daily_return) > max_abs_return:
                jumps.append(f"{bar.date}: {daily_return:.2%}")
        if prev_dt:
            gap = business_days_between(prev_dt, dt)
            if gap > max_gap_business_days:
                gaps.append(f"{prev_dt.date().isoformat()} -> {dt.date().isoformat()}: {gap} business days")
        prev_bar = bar
        prev_dt = dt

    if nonfinite:
        issues.append({"code": "nonfinite_value", "message": f"{nonfinite} rows contain non-finite values", "severity": "error"})
    if bad_ohlc:
        issues.append({"code": "bad_ohlc", "message": f"{bad_ohlc} rows violate OHLC bounds", "severity": "error"})
    if zero_volume:
        ratio = zero_volume / max(len(bars), 1)
        target = issues if ratio > 0.2 else warnings
        target.append({"code": "zero_volume", "message": f"{zero_volume} rows have non-positive volume ({ratio:.1%})", "severity": "error" if ratio > 0.2 else "warning"})
    if jumps:
        warnings.append({"code": "large_jump", "message": f"large close-to-close jumps: {jumps[:5]}", "severity": "warning"})
    if gaps:
        warnings.append({"code": "large_gap", "message": f"large date gaps: {gaps[:5]}", "severity": "warning"})

    if not metadata.get("has_adjustment"):
        warnings.append({
            "code": "missing_adjustment_flag",
            "message": "CSV does not declare adjustment mode; confirm qfq/hfq/raw before trusting backtests",
            "severity": "warning",
        })
    if not metadata.get("has_limit_prices"):
        warnings.append({
            "code": "missing_limit_prices",
            "message": "CSV does not include limit-up/limit-down prices; A-share execution feasibility is not verified",
            "severity": "warning",
        })
    if not metadata.get("has_suspension_flag"):
        warnings.append({
            "code": "missing_suspension_flag",
            "message": "CSV does not include suspension/trading-status flag; gaps require manual review",
            "severity": "warning",
        })

    penalty = len(issues) * 25 + len(warnings) * 8
    score = max(0, 100 - penalty)
    status = "pass" if score >= 70 and not issues else "fail"
    return {
        "status": status,
        "score": score,
        "bars": len(bars),
        "start_date": valid_dates[0].date().isoformat() if valid_dates else "",
        "end_date": valid_dates[-1].date().isoformat() if valid_dates else "",
        "metadata": metadata,
        "issues": issues,
        "warnings": warnings,
    }


def check_csv(path: Path, min_bars: int = 120, max_gap_business_days: int = 10, max_abs_return: float = 0.35) -> dict:
    symbol, name = infer_symbol_name(path)
    try:
        bars = load_price_csv(path)
        metadata = inspect_optional_columns(path)
        result = check_bars(bars, min_bars, max_gap_business_days, max_abs_return, metadata)
    except Exception as exc:
        result = {
            "status": "fail",
            "score": 0,
            "bars": 0,
            "start_date": "",
            "end_date": "",
            "metadata": {},
            "issues": [{"code": "load_error", "message": f"{type(exc).__name__}: {exc}", "severity": "error"}],
            "warnings": [],
        }
    result.update({"symbol": symbol, "name": name, "path": str(path).replace("\\", "/")})
    return result


def check_market_dir(
    market_dir: Path,
    min_bars: int = 120,
    max_gap_business_days: int = 10,
    max_abs_return: float = 0.35,
) -> dict:
    files = [
        check_csv(path, min_bars, max_gap_business_days, max_abs_return)
        for path in sorted(market_dir.rglob("*.csv"))
    ]
    failed = [item for item in files if item["status"] != "pass"]
    warned = [item for item in files if item["warnings"]]
    return {
        "market_dir": str(market_dir).replace("\\", "/"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(files),
        "passed": len(files) - len(failed),
        "failed": len(failed),
        "warned": len(warned),
        "files": files,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# 行情 CSV 质量检查",
        "",
        f"- 目录: `{report['market_dir']}`",
        f"- 文件数: {report['count']}",
        f"- 通过: {report['passed']}",
        f"- 失败: {report['failed']}",
        f"- 有警告: {report['warned']}",
        f"- 生成时间: {report['generated_at']}",
        "",
        "| 状态 | 分数 | 标的 | 名称 | K线数 | 起始 | 结束 | 复权 | 涨跌停价 | 停牌标记 | 问题 | 警告 |",
        "|---|---:|---|---|---:|---|---|---|---|---|---|---|",
    ]
    for item in report["files"]:
        issues = "; ".join(i["code"] for i in item["issues"]) or "-"
        warnings = "; ".join(w["code"] for w in item["warnings"]) or "-"
        meta = item.get("metadata", {})
        adjustment = ",".join(meta.get("adjustment_values", [])[:3]) if meta.get("has_adjustment") else "缺失"
        limit_prices = "有" if meta.get("has_limit_prices") else "缺失"
        suspension = f"有({meta.get('paused_rows', 0)})" if meta.get("has_suspension_flag") else "缺失"
        lines.append(
            f"| {item['status']} | {item['score']} | {item['symbol']} | {item['name']} | "
            f"{item['bars']} | {item['start_date']} | {item['end_date']} | {adjustment} | "
            f"{limit_prices} | {suspension} | {issues} | {warnings} |"
        )
    lines.extend([
        "",
        "## 使用原则",
        "",
        "- `fail` 标的不进入实盘候选，只能先修数据。",
        "- `large_jump` 可能是未复权、除权除息、错误价格或真实涨跌停，需要人工确认。",
        "- `large_gap` 可能是停牌、缺失数据或新上市，需要人工确认。",
        "- 缺少复权字段时，至少要人工确认 CSV 是前复权、后复权还是原始不复权。",
        "- 缺少涨跌停价时，系统不能判断计划买卖是否真实可成交。",
        "- 缺少停牌字段时，长时间缺口只能提示风险，不能区分停牌和数据缺失。",
        "- 回测结果必须和本报告一起看；数据质量不合格时，收益率和胜率没有决策价值。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local market CSV quality.")
    parser.add_argument("--market-dir", required=True)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    parser.add_argument("--min-bars", type=int, default=120)
    parser.add_argument("--max-gap-business-days", type=int, default=10)
    parser.add_argument("--max-abs-return", type=float, default=0.35)
    args = parser.parse_args()

    report = check_market_dir(Path(args.market_dir), args.min_bars, args.max_gap_business_days, args.max_abs_return)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"finance-data-quality-{args.date}.json"
    md_path = output_dir / f"finance-data-quality-{args.date}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "count": report["count"],
        "passed": report["passed"],
        "failed": report["failed"],
        "warned": report["warned"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
