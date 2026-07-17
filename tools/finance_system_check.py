"""Regression/smoke checks for the stock AI advisor toolchain."""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import analyze_hot_themes, load_price_csv, optimize_backtests  # noqa: E402
from tools.finance_build_watchlist import build_watchlist, load_meta  # noqa: E402
from tools.finance_data_quality import check_market_dir  # noqa: E402
from tools.finance_daily_report import load_jsonl, load_watchlist, run_watchlist_backtests  # noqa: E402
from tools.finance_decision_dashboard import build_dashboard, parse_markdown_tables  # noqa: E402
from tools.finance_edge_audit import build_edge_audit  # noqa: E402
from tools.finance_execution_tuner import run_sweep  # noqa: E402
from tools.finance_forward_eval import evaluate_watchlist  # noqa: E402
from tools.finance_signal_scorecard import build_scorecard  # noqa: E402
from tools.finance_daily_pipeline import apply_paper_scorecard, apply_signal_scorecard  # noqa: E402
from tools.finance_feedback_refresh import refresh as refresh_feedback  # noqa: E402
from tools.finance_market_regime import analyze_market_regime  # noqa: E402
from tools.finance_paper_trade import simulate_plan  # noqa: E402
from tools.finance_paper_scorecard import build_paper_scorecard  # noqa: E402
from tools.finance_plan_review import parse_plan_markdown, review_execution  # noqa: E402
from tools.finance_position_monitor import load_watchlist_csvs, monitor_positions  # noqa: E402
from tools.finance_pretrade_check import evaluate_order  # noqa: E402
from tools.finance_portfolio_plan import build_plan, load_watchlist as load_plan_watchlist  # noqa: E402
from tools.finance_risk_state import compute_risk_state, parse_review_report  # noqa: E402
from tools.finance_theme_ingest import parse_text_blob  # noqa: E402
from tools.finance_theme_trends import analyze_theme_trends, load_daily_series  # noqa: E402
from tools.finance_trade_journal import compute_attribution, load_jsonl as load_trades  # noqa: E402
from tools.finance_walk_forward import walk_forward_validate  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_http() -> dict:
    try:
        with urllib.request.urlopen("http://localhost:8766/api/stats", timeout=5) as resp:
            return {"ok": True, "stats": json.loads(resp.read().decode("utf-8"))}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def write_limit_gate_sample(path: Path, bars: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["date", "open", "high", "low", "close", "volume", "adjustment", "limit_up", "limit_down", "paused"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, bar in enumerate(bars):
            limit_up = bar.close if i == len(bars) - 1 else round(bar.close * 1.1, 4)
            writer.writerow({
                "date": bar.date,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "adjustment": "qfq",
                "limit_up": limit_up,
                "limit_down": round(bar.close * 0.9, 4),
                "paused": 0,
            })


def main() -> int:
    sample_bars = ROOT / "qclaw-output" / "market-sample" / "SEMI-半导体样例.csv"
    items_path = ROOT / "qclaw-output" / "finance-daily-items-sample-2026-06-20.jsonl"
    market_dir = ROOT / "qclaw-output" / "market-sample"
    market_meta = ROOT / "qclaw-output" / "market-sample-meta.json"
    market_index = ROOT / "qclaw-output" / "finance-market-index-sample.csv"
    market_breadth = ROOT / "qclaw-output" / "finance-market-breadth-sample.json"
    watchlist_path = ROOT / "qclaw-output" / "_finance-system-check-watchlist.csv"
    plan_path = ROOT / "qclaw-output" / "finance-portfolio-plan-2026-06-20.md"
    journal_path = ROOT / "qclaw-output" / "finance-trade-journal-sample.jsonl"
    review_path = ROOT / "qclaw-output" / "finance-plan-review-2026-06-20.md"

    bars = load_price_csv(sample_bars)
    check(len(bars) >= 30, "sample bars should load")
    optimized = optimize_backtests(bars)
    check(optimized.get("best") is not None, "optimizer should return a best strategy")
    check(optimized["best"].get("risk_adjusted_score", -999) > -999, "best strategy should have score")
    walk_forward = walk_forward_validate(bars, train_bars=18, test_bars=12, step_bars=6)
    check(walk_forward["valid_windows"] >= 1, "walk-forward should produce at least one valid window")

    items = load_jsonl(items_path)
    themes = analyze_hot_themes(items).get("themes", [])
    check(any(t["theme"] == "半导体" for t in themes), "theme analysis should find 半导体")

    ingested_items = parse_text_blob(
        "AI算力、服务器、光模块方向放量分歧。半导体、芯片、封测方向确认走强。消费方向继续退潮。",
        "2026-06-20",
        "system-check",
        8,
    )
    check(len(ingested_items) == 3, "theme ingest should split multi-theme notes into sentence events")
    ingested_themes = analyze_hot_themes(ingested_items).get("themes", [])
    check(len(ingested_themes) >= 3, "theme ingest output should feed hot-theme analysis")
    theme_series = load_daily_series(ROOT / "qclaw-output", "finance-daily-items-*.jsonl", "finance-daily-report-*.md", 10)
    theme_trends = analyze_theme_trends(theme_series)
    check(theme_trends["days"] >= 1, "theme trends should load at least one daily source")
    check(len(theme_trends["themes"]) >= 1, "theme trends should produce ranked themes")
    check(any(row["trend"] for row in theme_trends["themes"]), "theme trends should classify trend state")

    quality = check_market_dir(market_dir, min_bars=30)
    check(quality["count"] == 2, "quality check should scan 2 sample symbols")
    check(quality["failed"] == 0, "sample market data should pass quality checks")
    regime = analyze_market_regime(str(market_index), str(market_breadth))
    check(regime["risk_multiplier"] < 1.0, "weak sample market should reduce risk")

    watchlist_result = build_watchlist(market_dir, watchlist_path, load_meta(str(market_meta)), min_bars=30)
    check(watchlist_result["count"] == 2, "watchlist should contain 2 sample symbols")
    raw_backtests = run_watchlist_backtests(load_watchlist(watchlist_path))
    check(len(raw_backtests) == 2, "watchlist backtests should run for 2 symbols")

    forward = evaluate_watchlist(watchlist_path, "2026-06-02", [1, 3, 5])
    check(forward["evaluated"] == 2, "forward evaluation should evaluate 2 symbols")
    check(forward["summary"]["by_horizon"]["3"]["count"] == 2, "forward 3-day summary should have 2 samples")
    scorecard = build_scorecard([forward], target_horizon=3, min_samples=1)
    adjusted_backtests = apply_signal_scorecard(raw_backtests, scorecard)
    check(any("candidate_score_raw" in row for row in adjusted_backtests), "scorecard should annotate adjusted candidates")
    refresh_summary = refresh_feedback(
        market_dir.parent,
        ROOT / "qclaw-output",
        [1, 3],
        3,
        1,
        [f"{watchlist_path}=2026-06-02"],
    )
    check(refresh_summary["scorecard_themes"] >= 1, "feedback refresh should rebuild a scorecard")

    plan = build_plan(load_plan_watchlist(watchlist_path), 100000, 0.005, 0.2, 0.6, 0.35, 2.0, 15)
    check(plan["selected_count"] >= 1, "portfolio plan should select at least one candidate")
    check(plan["planned_exposure"] > 0, "portfolio exposure should be positive")

    same_theme_rows = load_plan_watchlist(watchlist_path)
    for row in same_theme_rows:
        row["theme"] = "同题材压力测试"
    theme_cap_plan = build_plan(same_theme_rows, 100000, 0.005, 0.2, 0.6, 0.07, 2.0, 15)
    check(theme_cap_plan["selected_count"] < len(same_theme_rows), "theme cap should block at least one same-theme candidate")
    check(any("单题材" in c.get("reason", "") for c in theme_cap_plan["candidates"] if not c.get("allowed")), "theme cap reason should mention 单题材")

    limit_gate_path = ROOT / "qclaw-output" / "_finance-system-check-limit-gate.csv"
    write_limit_gate_sample(limit_gate_path, bars)
    limit_plan = build_plan([{
        "symbol": "LIMIT",
        "name": "limit gate sample",
        "theme": "execution",
        "csv_path": str(limit_gate_path),
        "strategy": "optimize",
    }], 100000, 0.005, 0.2, 0.6, 0.35, 2.0, 15)
    check(limit_plan["selected_count"] == 0, "limit-up candidate should not be selected")
    check("涨停" in limit_plan["candidates"][0]["reason"], "limit-up reason should mention 涨停")

    trades = load_trades(journal_path)
    attribution = compute_attribution(trades)
    check(attribution["closed_trades"] == 1, "sample journal should have one closed trade")
    check(attribution["total_realized_pnl"] == 490.0, "sample pnl should be 490.0")

    parsed_plan = parse_plan_markdown(plan_path)
    pretrade_ok = evaluate_order(parsed_plan, "SAMPLE", "buy", 100, 13.3, "按计划试错", "短线", "账户0.5%")
    check(pretrade_ok["verdict"] != "block", "planned pretrade order should not be blocked")
    pretrade_bad = evaluate_order(parsed_plan, "SAMPLE", "buy", 99999, 20.0, "追高买入", "短线", "账户0.5%")
    check(pretrade_bad["verdict"] == "block", "oversized/chasing order should be blocked")
    monitor_ok = monitor_positions(
        parsed_plan,
        [{
            "date": "2026-06-18",
            "symbol": "SAMPLE",
            "name": "sample open",
            "theme": "AI",
            "side": "buy",
            "qty": 100,
            "price": 12.8,
            "fee": 1,
        }],
        load_watchlist_csvs(watchlist_path),
        market_dir,
        "2026-06-20",
    )
    check(monitor_ok["open_count"] == 1, "position monitor should see one open position")
    check(monitor_ok["action_required"] == 0, "valid open position should not require action")
    monitor_bad = monitor_positions(
        parsed_plan,
        [{
            "date": "2026-06-18",
            "symbol": "SAMPLE",
            "name": "sample open",
            "theme": "AI",
            "side": "buy",
            "qty": 99999,
            "price": 12.8,
            "fee": 1,
        }],
        {},
        None,
        "2026-06-20",
    )
    check(monitor_bad["action_required"] == 1, "position monitor should flag oversized risk")
    paper = simulate_plan(parsed_plan, load_watchlist_csvs(watchlist_path), "2026-06-02", 10)
    check(paper["planned"] >= 1, "paper trade should see planned candidates")
    check(paper["closed"] >= 1, "paper trade should close simulated trades when future bars exist")
    check("total_net_pnl" in paper, "paper trade should report net pnl")
    check(len(paper["by_theme"]) >= 1, "paper trade should attribute pnl by theme")
    paper_scorecard = build_paper_scorecard([paper], min_samples=1)
    paper_adjusted = apply_paper_scorecard(adjusted_backtests, paper_scorecard)
    check(any("paper_score_adjustment" in row for row in paper_adjusted), "paper scorecard should annotate candidates")
    check(len(paper_scorecard["themes"]) >= 1, "paper scorecard should include theme adjustments")
    edge_audit = build_edge_audit(
        journal_path,
        [ROOT / "qclaw-output" / "finance-paper-trade-2026-06-02.json"],
        [ROOT / "qclaw-output" / "finance-forward-eval-2026-06-02.json"],
        3,
    )
    check(edge_audit["verdict"] in {"positive", "caution", "negative"}, "edge audit should produce a verdict")
    check(edge_audit["risk_action"], "edge audit should produce a risk action")
    execution_tune = run_sweep(
        parsed_plan,
        load_watchlist_csvs(watchlist_path),
        "2026-06-02",
        [3, 5],
        [0.0, 0.01],
        [0.0, 0.02],
    )
    check(execution_tune["tested"] == 8, "execution tuner should test parameter grid")
    check("total_net_pnl" in execution_tune["best"], "execution tuner should report best pnl")
    check(execution_tune["diagnosis"], "execution tuner should provide diagnosis")
    pipeline_summary_path = ROOT / "qclaw-output" / "finance-daily-pipeline-2026-06-20.json"
    with pipeline_summary_path.open("r", encoding="utf-8-sig") as f:
        pipeline_summary = json.load(f)
    pipeline_summary["pipeline_path"] = str(pipeline_summary_path)
    dashboard = build_dashboard(
        pipeline_summary,
        parse_markdown_tables(ROOT / "qclaw-output" / "finance-daily-report-2026-06-20.md"),
        parsed_plan,
        monitor_ok,
        {},
        edge_audit,
    )
    check(dashboard["counts"]["selected"] >= 1, "decision dashboard should include planned candidates")
    check(len(dashboard["hot_themes"]) >= 1, "decision dashboard should include hot themes")
    check(any("consult" in gate for gate in dashboard["gates"]), "decision dashboard should keep pretrade consult gate")
    review = review_execution(parsed_plan, trades, "2026-06-20")
    check(review["discipline_score"] == 80, "sample discipline score should be 80")

    review_state = parse_review_report(review_path)
    risk_state = compute_risk_state(review_state, 0.005, 0.2, 0.6)
    check(risk_state["mode"] == "cautious", "sample risk state should be cautious")
    check(risk_state["risk_per_trade"] == 0.00375, "risk per trade should be throttled")

    http = check_http()
    result = {
        "ok": True,
        "bars": len(bars),
        "best_strategy": optimized["best"].get("strategy"),
        "walk_forward": walk_forward["summary"],
        "themes": [t["theme"] for t in themes[:5]],
        "quality_failed": quality["failed"],
        "market_regime": {"regime": regime["regime"], "risk_multiplier": regime["risk_multiplier"]},
        "watchlist_count": watchlist_result["count"],
        "forward_eval_3d": forward["summary"]["by_horizon"]["3"],
        "scorecard_themes": len(scorecard["themes"]),
        "feedback_refresh_themes": refresh_summary["scorecard_themes"],
        "selected_count": plan["selected_count"],
        "theme_cap_selected": theme_cap_plan["selected_count"],
        "execution_gate_selected": limit_plan["selected_count"],
        "pretrade_bad_verdict": pretrade_bad["verdict"],
        "position_monitor_action_required": monitor_bad["action_required"],
        "dashboard_candidates": dashboard["counts"]["selected"],
        "dashboard_hot_themes": len(dashboard["hot_themes"]),
        "paper_trade_closed": paper["closed"],
        "paper_trade_pnl": paper["total_net_pnl"],
        "paper_scorecard_themes": len(paper_scorecard["themes"]),
        "edge_verdict": edge_audit["verdict"],
        "edge_score": edge_audit["edge_score"],
        "execution_tuner_best_pnl": execution_tune["best"]["total_net_pnl"],
        "sample_pnl": attribution["total_realized_pnl"],
        "discipline_score": review["discipline_score"],
        "risk_mode": risk_state["mode"],
        "http": http,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
