"""Market regime thermometer for the finance advisor.

Combines optional index trend and market breadth data into a risk multiplier.
It is a portfolio throttle: bad environments reduce exposure even when single
stocks look attractive.
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

from core.finance_advisor import load_price_csv, sma  # noqa: E402


def load_json(path: str) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def to_float(value: object, default: float = 0.0) -> float:
    try:
        text = str(value if value is not None else "").strip().replace(",", "")
        return float(text) if text else default
    except ValueError:
        return default


def index_signal(index_csv: str) -> dict:
    if not index_csv:
        return {"available": False, "score": 0, "notes": ["未提供指数CSV"]}
    try:
        bars = load_price_csv(index_csv)
    except Exception as exc:
        return {"available": False, "score": -5, "notes": [f"指数CSV读取失败: {type(exc).__name__}: {exc}"]}
    if len(bars) < 20:
        return {"available": False, "score": -3, "notes": [f"指数K线不足: {len(bars)} < 20"]}

    closes = [bar.close for bar in bars]
    ma5 = sma(closes, 5)[-1]
    ma20 = sma(closes, 20)[-1]
    last = closes[-1]
    prev = closes[-2] if len(closes) >= 2 else last
    change = last / prev - 1 if prev else 0
    score = 0
    notes = []
    if ma5 is not None and ma20 is not None and ma5 > ma20:
        score += 15
        notes.append("指数短均线在长均线上方")
    else:
        score -= 12
        notes.append("指数短均线未站上长均线")
    if ma20 is not None and last > ma20:
        score += 10
        notes.append("指数收盘在20日均线上方")
    else:
        score -= 10
        notes.append("指数收盘弱于20日均线")
    if change <= -0.02:
        score -= 15
        notes.append("指数单日跌幅超过2%")
    elif change >= 0.015:
        score += 8
        notes.append("指数单日涨幅较强")
    return {
        "available": True,
        "score": score,
        "close": last,
        "change": round(change, 4),
        "ma5": round(ma5, 4) if ma5 is not None else None,
        "ma20": round(ma20, 4) if ma20 is not None else None,
        "notes": notes,
    }


def breadth_signal(breadth: dict) -> dict:
    if not breadth:
        return {"available": False, "score": 0, "notes": ["未提供市场宽度JSON"]}
    advancers = to_float(breadth.get("advancers"))
    decliners = to_float(breadth.get("decliners"))
    limit_up = to_float(breadth.get("limit_up"))
    limit_down = to_float(breadth.get("limit_down"))
    up_amount = to_float(breadth.get("up_amount"))
    down_amount = to_float(breadth.get("down_amount"))
    total = advancers + decliners
    adv_ratio = advancers / total if total > 0 else 0
    score = 0
    notes = []
    if total > 0:
        if adv_ratio >= 0.6:
            score += 15
            notes.append("上涨家数占优")
        elif adv_ratio <= 0.4:
            score -= 18
            notes.append("下跌家数占优")
    if limit_up >= 60:
        score += 12
        notes.append("涨停家数活跃")
    elif limit_up <= 20:
        score -= 8
        notes.append("涨停家数偏少")
    if limit_down >= 20:
        score -= 20
        notes.append("跌停家数偏多")
    if up_amount > 0 and down_amount > 0:
        amount_ratio = up_amount / down_amount
        if amount_ratio >= 1.2:
            score += 8
            notes.append("上涨成交额占优")
        elif amount_ratio <= 0.8:
            score -= 8
            notes.append("下跌成交额占优")
    return {
        "available": True,
        "score": score,
        "advancers": advancers,
        "decliners": decliners,
        "advance_ratio": round(adv_ratio, 4),
        "limit_up": limit_up,
        "limit_down": limit_down,
        "notes": notes,
    }


def classify(score: float) -> tuple[str, float]:
    if score >= 35:
        return "hot", 1.1
    if score >= 15:
        return "constructive", 1.0
    if score >= -10:
        return "neutral", 0.85
    if score >= -30:
        return "weak", 0.6
    return "risk_off", 0.25


def analyze_market_regime(index_csv: str = "", breadth_path: str = "") -> dict:
    index = index_signal(index_csv)
    breadth = breadth_signal(load_json(breadth_path))
    score = index.get("score", 0) + breadth.get("score", 0)
    regime, multiplier = classify(score)
    reasons = []
    reasons.extend(index.get("notes", []))
    reasons.extend(breadth.get("notes", []))
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "index_csv": index_csv,
        "breadth_path": breadth_path,
        "score": round(score, 2),
        "regime": regime,
        "risk_multiplier": multiplier,
        "index": index,
        "breadth": breadth,
        "reasons": reasons,
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# 市场环境温度计 - {report['generated_at']}",
        "",
        f"- 环境分: {report['score']}",
        f"- 环境状态: {report['regime']}",
        f"- 风险乘数: {report['risk_multiplier']}",
        f"- 指数CSV: `{report.get('index_csv', '')}`",
        f"- 宽度JSON: `{report.get('breadth_path', '')}`",
        "",
        "## 原因",
        "",
    ]
    lines.extend([f"- {reason}" for reason in report.get("reasons", [])] or ["- 暂无。"])
    lines.extend([
        "",
        "## 使用原则",
        "",
        "- `risk_off` 或 `weak` 时，仓位计划自动降低单笔风险和总暴露。",
        "- 市场温度计只调节风险，不会绕过个股质量、可成交性和交易前 consult。",
        "- 没有指数或宽度数据时，系统会提示缺失，但不阻断日流水线。",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze market regime and produce a risk multiplier.")
    parser.add_argument("--index-csv", default="")
    parser.add_argument("--breadth", default="")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", default=str(ROOT / "qclaw-output"))
    args = parser.parse_args()

    report = analyze_market_regime(args.index_csv, args.breadth)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"finance-market-regime-{args.date}.json"
    md_path = output_dir / f"finance-market-regime-{args.date}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "success": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "regime": report["regime"],
        "score": report["score"],
        "risk_multiplier": report["risk_multiplier"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
