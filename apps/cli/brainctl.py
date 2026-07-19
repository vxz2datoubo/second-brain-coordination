"""Command line interface for the super second brain v0.1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from brain_core import SuperBrainV01


def emit(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brainctl", description="Super second brain v0.1 CLI")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]), help="Project root")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest-text")
    ingest.add_argument("--text", required=True)
    ingest.add_argument("--title", default="")
    ingest.add_argument("--source-type", default="manual")
    ingest.add_argument("--uri", default="")
    ingest.add_argument("--reliability", type=float, default=0.6)

    search = sub.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--top-k", type=int, default=5)

    learning_search = sub.add_parser("learning-search")
    learning_search.add_argument("--query", required=True)
    learning_search.add_argument("--top-k", type=int, default=5)

    learning_summary = sub.add_parser("learning-summary")
    learning_summary.add_argument("--limit", type=int, default=5)

    feedback_summary = sub.add_parser("feedback-summary")
    feedback_summary.add_argument("--limit", type=int, default=5)
    feedback_summary.add_argument("--target-type", default="")
    feedback_summary.add_argument("--target-id", default="")
    feedback_memory_candidates = sub.add_parser("feedback-memory-candidates")
    feedback_memory_candidates.add_argument("--limit", type=int, default=5)
    feedback_memory_candidates.add_argument("--min-count", type=int, default=2)
    unified_memory_review_queue = sub.add_parser("unified-memory-review-queue")
    unified_memory_review_queue.add_argument("--limit", type=int, default=10)
    unified_memory_review_queue.add_argument("--min-count", type=int, default=2)
    unified_memory_review_queue.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    unified_memory_review_confirm = sub.add_parser("unified-memory-review-confirm")
    unified_memory_review_confirm.add_argument("--source-view", required=True)
    unified_memory_review_confirm.add_argument("--candidate-type", required=True)
    unified_memory_review_confirm.add_argument("--label", required=True)
    unified_memory_review_confirm.add_argument("--queue-bucket", choices=["review_now", "watchlist", "observe"], default="review_now")
    unified_memory_review_confirm.add_argument("--decision", choices=["accepted", "deferred", "rejected"], default="accepted")
    unified_memory_review_confirm.add_argument("--summary", default="")
    unified_memory_review_confirm.add_argument("--profile", default="")
    unified_memory_review_confirm.add_argument("--min-count", type=int, default=0)
    unified_memory_review_confirm.add_argument("--lesson", action="append", default=[])
    unified_memory_review_confirm.add_argument("--improvement-item", action="append", default=[])
    unified_memory_review_summary = sub.add_parser("unified-memory-review-summary")
    unified_memory_review_summary.add_argument("--limit", type=int, default=5)
    unified_memory_review_signals = sub.add_parser("unified-memory-review-signals")
    unified_memory_review_signals.add_argument("--min-confirmations", type=int, default=2)
    unified_memory_review_ranking_suggestions = sub.add_parser("unified-memory-review-ranking-suggestions")
    unified_memory_review_ranking_suggestions.add_argument("--min-confirmations", type=int, default=2)
    unified_memory_review_ranking_suggestions.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    unified_memory_review_ranking_diff = sub.add_parser("unified-memory-review-ranking-diff")
    unified_memory_review_ranking_diff.add_argument("--limit", type=int, default=10)
    unified_memory_review_ranking_diff.add_argument("--min-confirmations", type=int, default=2)
    unified_memory_review_ranking_diff.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    unified_memory_review_ranking_diff_confirm = sub.add_parser("unified-memory-review-ranking-diff-confirm")
    unified_memory_review_ranking_diff_confirm.add_argument("--label", required=True)
    unified_memory_review_ranking_diff_confirm.add_argument("--source-view", required=True)
    unified_memory_review_ranking_diff_confirm.add_argument("--candidate-type", required=True)
    unified_memory_review_ranking_diff_confirm.add_argument("--decision", choices=["accepted", "deferred", "rejected"], default="accepted")
    unified_memory_review_ranking_diff_confirm.add_argument("--summary", default="")
    unified_memory_review_ranking_diff_confirm.add_argument("--profile", default="")
    unified_memory_review_ranking_diff_confirm.add_argument("--current-rank", type=int, default=0)
    unified_memory_review_ranking_diff_confirm.add_argument("--suggested-rank", type=int, default=0)
    unified_memory_review_ranking_diff_confirm.add_argument("--score-delta", type=float, default=0.0)
    unified_memory_review_ranking_diff_confirm.add_argument("--lesson", action="append", default=[])
    unified_memory_review_ranking_diff_confirm.add_argument("--improvement-item", action="append", default=[])
    unified_memory_review_ranking_diff_summary = sub.add_parser("unified-memory-review-ranking-diff-summary")
    unified_memory_review_ranking_diff_summary.add_argument("--limit", type=int, default=5)
    unified_memory_review_ranking_diff_signals = sub.add_parser("unified-memory-review-ranking-diff-signals")
    unified_memory_review_ranking_diff_signals.add_argument("--min-confirmations", type=int, default=2)
    unified_memory_review_ranking_policy_suggestions = sub.add_parser("unified-memory-review-ranking-policy-suggestions")
    unified_memory_review_ranking_policy_suggestions.add_argument("--min-confirmations", type=int, default=2)
    unified_memory_review_ranking_policy_suggestions.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    unified_memory_review_ranking_policy_approve = sub.add_parser("unified-memory-review-ranking-policy-approve")
    unified_memory_review_ranking_policy_approve.add_argument("--dimension", choices=["profile", "source_view", "candidate_type"], required=True)
    unified_memory_review_ranking_policy_approve.add_argument("--key", required=True)
    unified_memory_review_ranking_policy_approve.add_argument("--decision", choices=["accepted", "deferred", "rejected"], default="accepted")
    unified_memory_review_ranking_policy_approve.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    unified_memory_review_ranking_policy_approve.add_argument("--weight-signal", default="observe")
    unified_memory_review_ranking_policy_approve.add_argument("--suggested-weight-delta", type=int, default=0)
    unified_memory_review_ranking_policy_approve.add_argument("--summary", default="")
    unified_memory_review_ranking_policy_approve.add_argument("--lesson", action="append", default=[])
    unified_memory_review_ranking_policy_approve.add_argument("--improvement-item", action="append", default=[])
    unified_memory_review_ranking_policy_approval_summary = sub.add_parser("unified-memory-review-ranking-policy-approval-summary")
    unified_memory_review_ranking_policy_approval_summary.add_argument("--limit", type=int, default=5)
    unified_memory_review_ranking_policy_approval_signals = sub.add_parser("unified-memory-review-ranking-policy-approval-signals")
    unified_memory_review_ranking_policy_approval_signals.add_argument("--min-confirmations", type=int, default=2)
    unified_memory_review_ranking_policy_change_candidates = sub.add_parser("unified-memory-review-ranking-policy-change-candidates")
    unified_memory_review_ranking_policy_change_candidates.add_argument("--min-confirmations", type=int, default=2)
    unified_memory_review_ranking_policy_change_candidates.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    unified_memory_review_ranking_policy_change_candidate_approve = sub.add_parser("unified-memory-review-ranking-policy-change-candidate-approve")
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--dimension", choices=["dimension", "key", "profile"], required=True)
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--key", required=True)
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--decision", choices=["accepted", "deferred", "rejected"], default="accepted")
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--change-bucket", choices=["promote_candidate", "downgrade_candidate", "observe_only"], default="observe_only")
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--weight-signal", default="observe")
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--suggested-weight-delta", type=int, default=0)
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--summary", default="")
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--lesson", action="append", default=[])
    unified_memory_review_ranking_policy_change_candidate_approve.add_argument("--improvement-item", action="append", default=[])
    unified_memory_review_ranking_policy_change_candidate_approval_summary = sub.add_parser("unified-memory-review-ranking-policy-change-candidate-approval-summary")
    unified_memory_review_ranking_policy_change_candidate_approval_summary.add_argument("--limit", type=int, default=5)

    learning_inspect = sub.add_parser("learning-inspect")
    learning_inspect.add_argument("--learning-entry-id", required=True)

    atom_writeback_inspect = sub.add_parser("atom-writeback-inspect")
    atom_writeback_inspect.add_argument("--atom-id", required=True)

    writeback_overview = sub.add_parser("writeback-overview")
    writeback_overview.add_argument("--limit", type=int, default=10)

    writeback_snapshot = sub.add_parser("writeback-snapshot")
    writeback_snapshot.add_argument("--limit", type=int, default=10)
    writeback_snapshot.add_argument("--name", default="")

    writeback_compare = sub.add_parser("writeback-compare")
    writeback_compare.add_argument("--limit", type=int, default=10)
    writeback_compare.add_argument("--snapshot-id", default="")

    legacy_lessons_map = sub.add_parser("legacy-lessons-map")
    legacy_lessons_map.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    legacy_decision_view = sub.add_parser("legacy-decision-view")
    legacy_decision_view.add_argument("--view", choices=["all", "promote-now", "watchlist", "profile-diff"], default="all")
    legacy_decision_view.add_argument("--profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    legacy_decision_view.add_argument("--left-profile", choices=["legacy-first", "pair-first", "balanced"], default="legacy-first")
    legacy_decision_view.add_argument("--right-profile", choices=["legacy-first", "pair-first", "balanced"], default="pair-first")
    legacy_action_confirm = sub.add_parser("legacy-action-confirm")
    legacy_action_confirm.add_argument("--candidate-label", required=True)
    legacy_action_confirm.add_argument("--candidate-type", required=True)
    legacy_action_confirm.add_argument("--action-bucket", choices=["promote_earlier", "defer_or_watch"], default="promote_earlier")
    legacy_action_confirm.add_argument("--accepted", choices=["true", "false"], default="true")
    legacy_action_confirm.add_argument("--summary", default="")
    legacy_action_confirm.add_argument("--left-profile", default="")
    legacy_action_confirm.add_argument("--right-profile", default="")
    legacy_action_confirm.add_argument("--lesson", action="append", default=[])
    legacy_action_confirm.add_argument("--improvement-item", action="append", default=[])
    legacy_action_summary = sub.add_parser("legacy-action-summary")
    legacy_action_summary.add_argument("--limit", type=int, default=5)

    learning_chains = sub.add_parser("learning-chains")
    learning_chains.add_argument("--limit", type=int, default=5)
    learning_chains.add_argument("--min-count", type=int, default=2)

    learning_apply = sub.add_parser("learning-apply")
    learning_apply.add_argument("--limit", type=int, default=5)
    learning_apply.add_argument("--min-count", type=int, default=2)

    decision = sub.add_parser("decision")
    decision.add_argument("--type", default="general")
    decision.add_argument("--question", required=True)
    decision.add_argument("--chosen", default="")
    decision.add_argument("--action", default="")
    decision.add_argument("--confidence", type=float, default=0.5)
    decision.add_argument("--evidence-id", action="append", default=[])
    decision.add_argument("--rationale", default="")

    forecast = sub.add_parser("forecast")
    forecast.add_argument("--question", required=True)
    forecast.add_argument("--horizon", required=True)
    forecast.add_argument("--probability", type=float, required=True)
    forecast.add_argument("--confidence", type=float, default=0.5)
    forecast.add_argument("--evidence-id", action="append", default=[])
    forecast.add_argument("--review-at", default="")

    trace = sub.add_parser("reasoning-trace")
    trace.add_argument("--question", required=True)
    trace.add_argument("--trace-type", default="analysis")
    trace.add_argument("--step", action="append", default=[])
    trace.add_argument("--evidence-id", action="append", default=[])
    trace.add_argument("--counter-evidence-id", action="append", default=[])
    trace.add_argument("--conclusion", default="")
    trace.add_argument("--confidence", type=float, default=0.5)
    trace.add_argument("--uncertainty", default="")
    trace.add_argument("--next-action", default="wait")

    review = sub.add_parser("review")
    review.add_argument("--target-type", choices=["decision", "forecast"], required=True)
    review.add_argument("--target-id", required=True)
    review.add_argument("--actual-outcome", required=True)
    review.add_argument("--actual-score", type=float)
    review.add_argument("--notes", default="")
    review.add_argument("--lesson", action="append", default=[])

    feedback = sub.add_parser("feedback")
    feedback.add_argument("--target-type", default="atom")
    feedback.add_argument("--target-id", action="append", required=True)
    feedback.add_argument("--feedback-text", default="")
    feedback.add_argument("--tag-add", action="append", default=[])
    feedback.add_argument("--tag-remove", action="append", default=[])
    feedback.add_argument("--confidence-delta", type=float, default=0.0)
    feedback.add_argument("--related-atom-id", action="append", default=[])
    feedback.add_argument("--support-id", action="append", default=[])
    feedback.add_argument("--refute-id", action="append", default=[])
    feedback.add_argument("--improvement-item", action="append", default=[])

    learning = sub.add_parser("learning-entry")
    learning.add_argument("--entry-type", default="manual_learning")
    learning.add_argument("--target-type", required=True)
    learning.add_argument("--target-id", action="append", required=True)
    learning.add_argument("--summary", default="")
    learning.add_argument("--source-record-id", default="")
    learning.add_argument("--evidence-id", action="append", default=[])
    learning.add_argument("--counter-evidence-id", action="append", default=[])
    learning.add_argument("--lesson", action="append", default=[])
    learning.add_argument("--improvement-item", action="append", default=[])
    learning.add_argument("--confidence-delta", type=float, default=0.0)

    sub.add_parser("status")
    foundation_report = sub.add_parser("foundation-data-governance-report")
    foundation_report.add_argument("--symbol", default="300418")
    foundation_report.add_argument("--timeframe", default="1d")
    foundation_report.add_argument("--data-path", default="")
    foundation_report.add_argument("--no-writeback", action="store_true")
    log = sub.add_parser("evolution-log")
    log.add_argument("--limit", type=int, default=20)
    sub.add_parser("board-status")
    board_update = sub.add_parser("board-update")
    board_update.add_argument("--completed", action="append", default=None)
    board_update.add_argument("--in-progress", action="append", default=None)
    board_update.add_argument("--next-step", default=None)
    board_update.add_argument("--status", default=None)
    board_update.add_argument("--event-type", default="progress_update")
    board_update.add_argument("--summary", default="")

    trading_replay = sub.add_parser("trading-replay")
    trading_replay.add_argument("--data-path", default="")
    trading_replay.add_argument("--symbol", default="")
    trading_replay.add_argument("--timeframe", default="1d")
    trading_replay.add_argument("--short-window", type=int, default=5)
    trading_replay.add_argument("--long-window", type=int, default=20)
    trading_replay.add_argument("--initial-cash", type=float, default=100000.0)
    trading_replay.add_argument("--commission-pct", type=float, default=0.00025)
    trading_replay.add_argument("--slippage-pct", type=float, default=0.001)
    trading_replay.add_argument("--position-pct", type=float, default=0.05)
    trading_replay.add_argument("--max-loss-pct", type=float, default=0.02)
    trading_replay.add_argument("--ddx", type=float)
    trading_replay.add_argument("--ddy", type=float)
    trading_replay.add_argument("--change-pct", type=float)
    trading_replay.add_argument("--volume-ratio", type=float)
    trading_replay.add_argument("--price", type=float, default=0.0)
    trading_replay.add_argument("--turnover-rate", type=float, default=0.0)
    trading_replay.add_argument("--quote-ts", default="")
    trading_replay.add_argument("--requested-action", choices=["trade", "wait", "no_trade"], default="")
    trading_replay.add_argument("--market-trend", default="")
    trading_replay.add_argument("--has-base-position", action="store_true")
    trading_replay.add_argument("--is-t-trade", action="store_true")
    trading_replay.add_argument("--day-loss-pct", type=float)
    trading_replay.add_argument("--holding-day-change-pct", type=float)
    trading_replay.add_argument("--summary-only", action="store_true")
    trading_next_slice = sub.add_parser("trading-research-queue-next-validation-slice")
    trading_next_slice.add_argument("--candidate-slug", default="")
    trading_next_slice.add_argument("--min-approvals", type=int, default=1)
    trading_next_slice.add_argument("--top-limit", type=int, default=3)
    trading_run_next_slice = sub.add_parser("trading-research-queue-run-next-validation-slice")
    trading_run_next_slice.add_argument("--candidate-slug", default="")
    trading_run_next_slice.add_argument("--min-approvals", type=int, default=1)
    trading_run_next_slice.add_argument("--top-limit", type=int, default=3)
    trading_run_next_slice.add_argument("--data-path", default="")
    trading_run_next_slice.add_argument("--symbol", default="")
    trading_run_next_slice.add_argument("--timeframe", default="")
    trading_run_next_slice.add_argument("--train-ratio", type=float, default=0.7)
    trading_run_next_slice.add_argument("--short-window", type=int, default=5)
    trading_run_next_slice.add_argument("--long-window", type=int, default=20)
    trading_run_next_slice.add_argument("--initial-cash", type=float, default=100000.0)
    trading_run_next_slice.add_argument("--commission-pct", type=float, default=0.00025)
    trading_run_next_slice.add_argument("--slippage-pct", type=float, default=0.001)
    trading_run_next_slice.add_argument("--position-pct", type=float, default=0.05)
    trading_run_next_slice.add_argument("--max-loss-pct", type=float, default=0.02)
    trading_run_next_slice.add_argument("--variant-key", default="")
    trading_latest_summary = sub.add_parser("trading-research-queue-latest-validation-summary")
    trading_latest_summary.add_argument("--candidate-slug", default="")
    trading_latest_summary.add_argument("--min-approvals", type=int, default=1)
    trading_latest_summary.add_argument("--top-limit", type=int, default=3)
    trading_sync_bulletin = sub.add_parser("trading-research-queue-sync-bulletin-from-latest-validation")
    trading_sync_bulletin.add_argument("--candidate-slug", default="")
    trading_sync_bulletin.add_argument("--min-approvals", type=int, default=1)
    trading_sync_bulletin.add_argument("--top-limit", type=int, default=3)
    trading_manual_approval = sub.add_parser("trading-confirm-research-queue-manual-approval")
    trading_manual_approval.add_argument("--candidate-slug", required=True)
    trading_manual_approval.add_argument("--decision", required=True, choices=["approved", "deferred", "rejected"])
    trading_manual_approval.add_argument("--reviewer", required=True)
    trading_manual_approval.add_argument("--rationale", required=True)
    trading_manual_approval.add_argument("--summary", default="")
    trading_manual_approval.add_argument("--approved-at", default="")
    trading_manual_approval.add_argument("--source-record-id", default="")
    trading_manual_approval.add_argument("--confidence-delta", type=float, default=0.0)
    trading_manual_approval.add_argument("--limit", type=int, default=5)
    trading_manual_approval.add_argument("--follow-up-item", action="append", default=[])
    trading_manual_approval.add_argument("--evidence-note", action="append", default=[])
    trading_manual_approval.add_argument("--lesson", action="append", default=[])
    trading_manual_approval.add_argument("--improvement-item", action="append", default=[])
    trading_manual_approval.add_argument("--evidence-id", action="append", default=[])
    trading_manual_approval.add_argument("--counter-evidence-id", action="append", default=[])
    trading_reconcile_authority = sub.add_parser("trading-reconcile-a-share-authority")
    trading_reconcile_authority.add_argument("--doc-path", default="")
    trading_authority_snapshot = sub.add_parser("trading-a-share-authority-constraints-snapshot")
    trading_authority_snapshot.add_argument("--symbol", default="300418")
    trading_authority_snapshot.add_argument("--timeframe", default="1d")
    trading_tdx_quote_snapshot = sub.add_parser("trading-a-share-tdx-quote-snapshot")
    trading_tdx_quote_snapshot.add_argument("--symbol", default="300418")
    trading_tdx_quote_snapshot.add_argument("--timeframe", default="1d")
    trading_tdx_quote_snapshot.add_argument("--ddx", type=float, required=True)
    trading_tdx_quote_snapshot.add_argument("--ddy", type=float, required=True)
    trading_tdx_quote_snapshot.add_argument("--change-pct", type=float, required=True)
    trading_tdx_quote_snapshot.add_argument("--volume-ratio", type=float, required=True)
    trading_tdx_quote_snapshot.add_argument("--price", type=float, default=0.0)
    trading_tdx_quote_snapshot.add_argument("--turnover-rate", type=float, default=0.0)
    trading_tdx_quote_snapshot.add_argument("--quote-ts", default="")
    trading_tdx_quote_snapshot.add_argument("--candidate-slug", default="")
    trading_tencent_qt_snapshot = sub.add_parser("trading-a-share-tencent-qt-snapshot")
    trading_tencent_qt_snapshot.add_argument("--symbol", default="300418")
    trading_tencent_qt_snapshot.add_argument("--timeframe", default="1d")
    trading_tencent_qt_snapshot.add_argument("--price", type=float, required=True)
    trading_tencent_qt_snapshot.add_argument("--change-pct", type=float, required=True)
    trading_tencent_qt_snapshot.add_argument("--volume", type=float, default=0.0)
    trading_tencent_qt_snapshot.add_argument("--amount", type=float, default=0.0)
    trading_tencent_qt_snapshot.add_argument("--northbound-flow", type=float, default=0.0)
    trading_tencent_qt_snapshot.add_argument("--quote-crosscheck", default="not_verified")
    trading_tencent_qt_snapshot.add_argument("--bids-json", required=True)
    trading_tencent_qt_snapshot.add_argument("--asks-json", required=True)
    trading_tencent_qt_snapshot.add_argument("--quote-ts", default="")
    trading_tencent_qt_snapshot.add_argument("--candidate-slug", default="")
    trading_workbuddy_context_snapshot = sub.add_parser("trading-a-share-workbuddy-context-snapshot")
    trading_workbuddy_context_snapshot.add_argument("--symbol", default="300418")
    trading_workbuddy_context_snapshot.add_argument("--timeframe", default="1d")
    trading_workbuddy_context_snapshot.add_argument("--snapshot-path", default="")
    trading_workbuddy_context_snapshot.add_argument("--quote-ts", default="")
    trading_workbuddy_context_snapshot.add_argument("--candidate-slug", default="")
    trading_proxy_guard_coverage = sub.add_parser("trading-a-share-proxy-guard-source-coverage")
    trading_proxy_guard_coverage.add_argument("--symbol", default="300418")
    trading_proxy_guard_coverage.add_argument("--timeframe", default="1d")
    trading_proxy_guard_coverage.add_argument("--candidate-slug", default="")
    trading_proxy_guard_coverage.add_argument("--min-approvals", type=int, default=1)
    trading_proxy_guard_coverage.add_argument("--top-limit", type=int, default=3)
    trading_true_money_flow = sub.add_parser("trading-a-share-true-money-flow-readiness")
    trading_true_money_flow.add_argument("--symbol", default="300418")
    trading_true_money_flow.add_argument("--timeframe", default="1d")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    brain = SuperBrainV01(args.root)
    if args.command == "ingest-text":
        emit(brain.ingest_text({
            "text": args.text,
            "title": args.title,
            "source_type": args.source_type,
            "uri": args.uri,
            "reliability": args.reliability,
        }))
    elif args.command == "search":
        emit(brain.search({"query": args.query, "top_k": args.top_k}))
    elif args.command == "learning-search":
        emit(brain.search_learning_entries({"query": args.query, "top_k": args.top_k}))
    elif args.command == "learning-summary":
        emit(brain.learning_summary({"limit": args.limit}))
    elif args.command == "feedback-summary":
        emit(brain.feedback_summary({
            "limit": args.limit,
            "target_type": args.target_type,
            "target_id": args.target_id,
        }))
    elif args.command == "feedback-memory-candidates":
        emit(brain.feedback_memory_candidates({
            "limit": args.limit,
            "min_count": args.min_count,
        }))
    elif args.command == "unified-memory-review-queue":
        emit(brain.unified_memory_review_queue({
            "limit": args.limit,
            "min_count": args.min_count,
            "profile": args.profile,
        }))
    elif args.command == "unified-memory-review-confirm":
        emit(brain.confirm_unified_memory_review_item({
            "source_view": args.source_view,
            "candidate_type": args.candidate_type,
            "label": args.label,
            "queue_bucket": args.queue_bucket,
            "decision": args.decision,
            "summary": args.summary,
            "profile": args.profile,
            "min_count": args.min_count,
            "lessons": args.lesson,
            "improvement_items": args.improvement_item,
        }))
    elif args.command == "unified-memory-review-summary":
        emit(brain.unified_memory_review_summary({"limit": args.limit}))
    elif args.command == "unified-memory-review-signals":
        emit(brain.unified_memory_review_signals({"min_confirmations": args.min_confirmations}))
    elif args.command == "unified-memory-review-ranking-suggestions":
        emit(brain.unified_memory_review_ranking_suggestions({
            "min_confirmations": args.min_confirmations,
            "profile": args.profile,
        }))
    elif args.command == "unified-memory-review-ranking-diff":
        emit(brain.unified_memory_review_ranking_diff({
            "limit": args.limit,
            "min_confirmations": args.min_confirmations,
            "profile": args.profile,
        }))
    elif args.command == "unified-memory-review-ranking-diff-confirm":
        emit(brain.confirm_unified_memory_review_ranking_diff_item({
            "label": args.label,
            "source_view": args.source_view,
            "candidate_type": args.candidate_type,
            "decision": args.decision,
            "summary": args.summary,
            "profile": args.profile,
            "current_rank": args.current_rank,
            "suggested_rank": args.suggested_rank,
            "score_delta": args.score_delta,
            "lessons": args.lesson,
            "improvement_items": args.improvement_item,
        }))
    elif args.command == "unified-memory-review-ranking-diff-summary":
        emit(brain.unified_memory_review_ranking_diff_summary({"limit": args.limit}))
    elif args.command == "unified-memory-review-ranking-diff-signals":
        emit(brain.unified_memory_review_ranking_diff_signals({"min_confirmations": args.min_confirmations}))
    elif args.command == "unified-memory-review-ranking-policy-suggestions":
        emit(brain.unified_memory_review_ranking_policy_suggestions({
            "min_confirmations": args.min_confirmations,
            "profile": args.profile,
        }))
    elif args.command == "unified-memory-review-ranking-policy-approve":
        emit(brain.confirm_unified_memory_review_ranking_policy_suggestion({
            "dimension": args.dimension,
            "key": args.key,
            "decision": args.decision,
            "profile": args.profile,
            "weight_signal": args.weight_signal,
            "suggested_weight_delta": args.suggested_weight_delta,
            "summary": args.summary,
            "lessons": args.lesson,
            "improvement_items": args.improvement_item,
        }))
    elif args.command == "unified-memory-review-ranking-policy-approval-summary":
        emit(brain.unified_memory_review_ranking_policy_approval_summary({"limit": args.limit}))
    elif args.command == "unified-memory-review-ranking-policy-approval-signals":
        emit(brain.unified_memory_review_ranking_policy_approval_signals({"min_confirmations": args.min_confirmations}))
    elif args.command == "unified-memory-review-ranking-policy-change-candidates":
        emit(brain.unified_memory_review_ranking_policy_change_candidates({
            "min_confirmations": args.min_confirmations,
            "profile": args.profile,
        }))
    elif args.command == "unified-memory-review-ranking-policy-change-candidate-approve":
        emit(brain.confirm_unified_memory_review_ranking_policy_change_candidate({
            "dimension": args.dimension,
            "key": args.key,
            "decision": args.decision,
            "profile": args.profile,
            "change_bucket": args.change_bucket,
            "weight_signal": args.weight_signal,
            "suggested_weight_delta": args.suggested_weight_delta,
            "summary": args.summary,
            "lessons": args.lesson,
            "improvement_items": args.improvement_item,
        }))
    elif args.command == "unified-memory-review-ranking-policy-change-candidate-approval-summary":
        emit(brain.unified_memory_review_ranking_policy_change_candidate_approval_summary({"limit": args.limit}))
    elif args.command == "learning-inspect":
        emit(brain.inspect_learning_entry({"learning_entry_id": args.learning_entry_id}))
    elif args.command == "atom-writeback-inspect":
        emit(brain.inspect_atom_writeback({"atom_id": args.atom_id}))
    elif args.command == "writeback-overview":
        emit(brain.writeback_overview({"limit": args.limit}))
    elif args.command == "writeback-snapshot":
        emit(brain.capture_writeback_snapshot({"limit": args.limit, "name": args.name}))
    elif args.command == "writeback-compare":
        emit(brain.compare_writeback_snapshot({"limit": args.limit, "snapshot_id": args.snapshot_id}))
    elif args.command == "legacy-lessons-map":
        emit(brain.legacy_lessons_mapping({"profile": args.profile}))
    elif args.command == "legacy-decision-view":
        emit(brain.legacy_memory_decision_view({
            "view": args.view,
            "profile": args.profile,
            "left_profile": args.left_profile,
            "right_profile": args.right_profile,
        }))
    elif args.command == "legacy-action-confirm":
        emit(brain.confirm_legacy_memory_action({
            "candidate_label": args.candidate_label,
            "candidate_type": args.candidate_type,
            "action_bucket": args.action_bucket,
            "accepted": args.accepted == "true",
            "summary": args.summary,
            "left_profile": args.left_profile,
            "right_profile": args.right_profile,
            "lessons": args.lesson,
            "improvement_items": args.improvement_item,
        }))
    elif args.command == "legacy-action-summary":
        emit(brain.legacy_memory_action_summary({"limit": args.limit}))
    elif args.command == "learning-chains":
        emit(brain.learning_chains({"limit": args.limit, "min_count": args.min_count}))
    elif args.command == "learning-apply":
        emit(brain.apply_learning_chains({"limit": args.limit, "min_count": args.min_count}))
    elif args.command == "decision":
        emit(brain.create_decision({
            "decision_type": args.type,
            "question": args.question,
            "chosen": args.chosen,
            "action": args.action,
            "confidence": args.confidence,
            "evidence_ids": args.evidence_id,
            "rationale": args.rationale,
        }))
    elif args.command == "forecast":
        emit(brain.create_forecast({
            "question": args.question,
            "horizon": args.horizon,
            "probability": args.probability,
            "confidence": args.confidence,
            "evidence_ids": args.evidence_id,
            "review_at": args.review_at,
        }))
    elif args.command == "reasoning-trace":
        emit(brain.create_reasoning_trace({
            "question": args.question,
            "trace_type": args.trace_type,
            "steps": [{"index": i + 1, "content": step} for i, step in enumerate(args.step)],
            "evidence_ids": args.evidence_id,
            "counter_evidence_ids": args.counter_evidence_id,
            "conclusion": args.conclusion,
            "confidence": args.confidence,
            "uncertainty": args.uncertainty,
            "next_action": args.next_action,
        }))
    elif args.command == "review":
        emit(brain.review({
            "target_type": args.target_type,
            "target_id": args.target_id,
            "actual_outcome": args.actual_outcome,
            "actual_score": args.actual_score,
            "notes": args.notes,
            "lessons": args.lesson,
        }))
    elif args.command == "feedback":
        emit(brain.feedback({
            "target_type": args.target_type,
            "target_ids": args.target_id,
            "feedback_text": args.feedback_text,
            "tags_to_add": args.tag_add,
            "tags_to_remove": args.tag_remove,
            "confidence_delta": args.confidence_delta,
            "related_atom_ids": args.related_atom_id,
            "support_ids": args.support_id,
            "refute_ids": args.refute_id,
            "improvement_items": args.improvement_item,
        }))
    elif args.command == "learning-entry":
        emit(brain.learning_entry({
            "entry_type": args.entry_type,
            "target_type": args.target_type,
            "target_ids": args.target_id,
            "summary": args.summary,
            "source_record_id": args.source_record_id,
            "evidence_ids": args.evidence_id,
            "counter_evidence_ids": args.counter_evidence_id,
            "lessons": args.lesson,
            "improvement_items": args.improvement_item,
            "confidence_delta": args.confidence_delta,
        }))
    elif args.command == "status":
        emit(brain.status())
    elif args.command == "foundation-data-governance-report":
        emit(brain.foundation_data_governance_report({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "data_path": args.data_path,
            "writeback": not args.no_writeback,
        }))
    elif args.command == "evolution-log":
        emit(brain.evolution_log(args.limit))
    elif args.command == "board-status":
        emit(brain.board_status())
    elif args.command == "board-update":
        emit(brain.board_update({
            "completed": args.completed,
            "in_progress": args.in_progress,
            "next_step": args.next_step,
            "status": args.status,
            "event_type": args.event_type,
            "summary": args.summary,
        }))
    elif args.command == "trading-replay":
        replay_payload = {
            "data_path": args.data_path,
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "short_window": args.short_window,
            "long_window": args.long_window,
            "initial_cash": args.initial_cash,
            "commission_pct": args.commission_pct,
            "slippage_pct": args.slippage_pct,
            "position_pct": args.position_pct,
            "max_loss_pct": args.max_loss_pct,
        }
        if args.requested_action:
            replay_payload["requested_action"] = args.requested_action
        if args.market_trend:
            replay_payload["market_trend"] = args.market_trend
        if args.has_base_position:
            replay_payload["has_base_position"] = True
        if args.is_t_trade:
            replay_payload["is_t_trade"] = True
        if args.day_loss_pct is not None:
            replay_payload["day_loss_pct"] = args.day_loss_pct
        if args.holding_day_change_pct is not None:
            replay_payload["holding_day_change_pct"] = args.holding_day_change_pct
        if None not in (args.ddx, args.ddy, args.change_pct, args.volume_ratio):
            replay_payload.update({
                "ddx": args.ddx,
                "ddy": args.ddy,
                "change_pct": args.change_pct,
                "volume_ratio": args.volume_ratio,
                "price": args.price,
                "turnover_rate": args.turnover_rate,
                "quote_ts": args.quote_ts,
            })
        elif args.quote_ts:
            replay_payload["quote_ts"] = args.quote_ts
        replay_result = brain.trading_replay(replay_payload)
        emit(replay_result.get("replay_summary", {}) if args.summary_only else replay_result)
    elif args.command == "trading-research-queue-next-validation-slice":
        emit(brain.trading_research_queue_next_validation_slice({
            "candidate_slug": args.candidate_slug,
            "min_approvals": args.min_approvals,
            "top_limit": args.top_limit,
        }))
    elif args.command == "trading-research-queue-run-next-validation-slice":
        emit(brain.trading_research_queue_run_next_validation_slice({
            "candidate_slug": args.candidate_slug,
            "min_approvals": args.min_approvals,
            "top_limit": args.top_limit,
            "data_path": args.data_path,
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "train_ratio": args.train_ratio,
            "short_window": args.short_window,
            "long_window": args.long_window,
            "initial_cash": args.initial_cash,
            "commission_pct": args.commission_pct,
            "slippage_pct": args.slippage_pct,
            "position_pct": args.position_pct,
            "max_loss_pct": args.max_loss_pct,
            "variant_key": args.variant_key,
        }))
    elif args.command == "trading-research-queue-latest-validation-summary":
        emit(brain.trading_research_queue_latest_validation_summary({
            "candidate_slug": args.candidate_slug,
            "min_approvals": args.min_approvals,
            "top_limit": args.top_limit,
        }))
    elif args.command == "trading-research-queue-sync-bulletin-from-latest-validation":
        emit(brain.trading_research_queue_sync_bulletin_from_latest_validation({
            "candidate_slug": args.candidate_slug,
            "min_approvals": args.min_approvals,
            "top_limit": args.top_limit,
        }))
    elif args.command == "trading-confirm-research-queue-manual-approval":
        emit(brain.trading_confirm_research_queue_manual_approval({
            "candidate_slug": args.candidate_slug,
            "decision": args.decision,
            "reviewer": args.reviewer,
            "rationale": args.rationale,
            "summary": args.summary,
            "approved_at": args.approved_at,
            "source_record_id": args.source_record_id,
            "confidence_delta": args.confidence_delta,
            "limit": args.limit,
            "follow_up_items": args.follow_up_item,
            "evidence_notes": args.evidence_note,
            "lessons": args.lesson,
            "improvement_items": args.improvement_item,
            "evidence_ids": args.evidence_id,
            "counter_evidence_ids": args.counter_evidence_id,
        }))
    elif args.command == "trading-reconcile-a-share-authority":
        emit(brain.trading_reconcile_a_share_authority({
            "doc_path": args.doc_path,
        }))
    elif args.command == "trading-a-share-authority-constraints-snapshot":
        emit(brain.trading_a_share_authority_constraints_snapshot({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
        }))
    elif args.command == "trading-a-share-tdx-quote-snapshot":
        emit(brain.trading_a_share_tdx_quote_snapshot({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "ddx": args.ddx,
            "ddy": args.ddy,
            "change_pct": args.change_pct,
            "volume_ratio": args.volume_ratio,
            "price": args.price,
            "turnover_rate": args.turnover_rate,
            "quote_ts": args.quote_ts,
            "candidate_slug": args.candidate_slug,
        }))
    elif args.command == "trading-a-share-tencent-qt-snapshot":
        emit(brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "price": args.price,
            "change_pct": args.change_pct,
            "volume": args.volume,
            "amount": args.amount,
            "northbound_flow": args.northbound_flow,
            "quote_crosscheck": args.quote_crosscheck,
            "bids": json.loads(args.bids_json),
            "asks": json.loads(args.asks_json),
            "quote_ts": args.quote_ts,
            "candidate_slug": args.candidate_slug,
        }))
    elif args.command == "trading-a-share-workbuddy-context-snapshot":
        payload = {
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "quote_ts": args.quote_ts,
            "candidate_slug": args.candidate_slug,
        }
        if args.snapshot_path:
            payload["source_path"] = args.snapshot_path
        emit(brain.trading_a_share_workbuddy_context_snapshot(payload))
    elif args.command == "trading-a-share-proxy-guard-source-coverage":
        emit(brain.trading_a_share_proxy_guard_source_coverage({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "candidate_slug": args.candidate_slug,
            "min_approvals": args.min_approvals,
            "top_limit": args.top_limit,
        }))
    elif args.command == "trading-a-share-true-money-flow-readiness":
        emit(brain.trading_a_share_true_money_flow_readiness({
            "symbol": args.symbol,
            "timeframe": args.timeframe,
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
