# -*- coding: utf-8 -*-
"""The Second Brain - AI Knowledge System, port 8766"""

import json, math, os, sys, uuid
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from core.graph import KnowledgeGraph
from core.digest import TextDigester, FileDigester, URLDigester
from core.tfidf import SearchEngine
from core.syncer import WorkBuddySyncer
from core.memory import MemoryEngine, FeedbackLoop
from core.evolve import EvolutionEngine
from core.events import EventEngine
from core.tasks import TaskEngine
from core.emotion import EmotionEngine
from core.goals import GoalEngine
from core.agents import (
    Orchestrator, MemoryAgent, EmotionAgent, PlannerAgent,
    SimulationAgent, SafetyAgent, ReflectionAgent,
    SignalFusion, DebateSystem, AuditTrail, DecisionAudit,
)
from core.self_evolve import (
    MAPEKEngine, OpMode, ProblemCategory, RepairTicket,
    SkillHealthRecord, SelfDiagnosisRecord, RegressionTest,
    REPAIR_PERMISSION_MATRIX, CODEX_PROCEDURES,
)
from core.memory_health import MemoryHealthManager
from core.fast_index import FastIndex
from core.human_thinking import HumanThinkingEngine
from core.self_verify import SelfVerify
from core.actr_memory import ACTRMemory
from core.finance_advisor import analyze_hot_themes, load_price_csv, optimize_backtests, run_backtest_strategy
from core.trading_brain import TradingBrain, get_trading_brain
from core.cognitive_engine import CognitiveEngine
from core.reason_engine import ReasonEngine
from core.maibot_bridge import MaibotBridge
from core.game_theory_engine import GameTheoryEngine
from core.market_detective import MarketDetective
from core.news_verification import NewsVerificationEngine
from core.scenario_planner import ScenarioPlanner
from core.anti_gaming import AntiGamingEngine
from core.super_cognitive import SuperCognitiveEngine
from core.atomic_extractor import AtomicExtractor
from core.mind_models import MentalModelLibrary
from core.super_strategy import SuperStrategyEngine
from brain_core import SuperBrainV01

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / 'data'
APP = ROOT / 'app'

_v01 = SuperBrainV01(ROOT)

_graph = KnowledgeGraph(DATA)
_digester = TextDigester(_graph, DATA)
_file_digester = FileDigester(_digester)
_url_digester = URLDigester(_digester)
_search = SearchEngine(_graph, _digester)
_syncer = WorkBuddySyncer(_graph, _digester, DATA)
_memory = MemoryEngine(DATA)
_feedback = FeedbackLoop(_memory, _graph, _digester)
_evolve = EvolutionEngine(_graph, _memory, _digester, _search, DATA)
_events = EventEngine(DATA, _graph, _memory)
_tasks = TaskEngine(DATA, _graph, _memory, _events)
_emotion = EmotionEngine(DATA, _graph, _memory)
_goals = GoalEngine(DATA, _graph, _memory, _tasks, _events)
_health = MemoryHealthManager(_graph, _memory, DATA)
_fast_index = FastIndex(_graph, _digester, DATA)
_human = HumanThinkingEngine(_graph, _memory, _health, DATA)
_verify = SelfVerify(_graph, _memory, _health, DATA)

# Phase 6: Multi-Agent Orchestrator (after all engines)
_orchestrator = Orchestrator(DATA)
_orchestrator.register(MemoryAgent(_memory, _fast_index))
_orchestrator.register(EmotionAgent(_emotion))
_orchestrator.register(PlannerAgent(_goals, _tasks, _events))
_orchestrator.register(SimulationAgent(_goals))
_orchestrator.register(SafetyAgent(_events, _goals, _tasks))
_orchestrator.register(ReflectionAgent(_memory))
_actr = ACTRMemory(_graph, DATA)

# Phase 7: Self-Evolution Engine (MAPE-K)
_self_evolve = MAPEKEngine(DATA, subsystems={
    "memory": _memory, "emotion": _emotion, "tasks": _tasks,
    "events": _events, "goals": _goals, "orchestrator": _orchestrator,
    "search": _search, "graph": _graph,
})
_trading_brain = get_trading_brain(DATA)
_cognitive = CognitiveEngine(_graph, _memory, _digester, _search, _health, _human, _verify, DATA)
_reason = ReasonEngine(_graph, DATA)
_game_theory = GameTheoryEngine(_graph, DATA)
_detective = MarketDetective(_graph, DATA)
_news_verifier = NewsVerificationEngine(_graph, DATA)
_scenario = ScenarioPlanner(_graph, DATA)
_anti_gaming = AntiGamingEngine(_graph, DATA)
_super_cog = SuperCognitiveEngine(_graph, _game_theory, _detective, _news_verifier, _scenario, _anti_gaming, _cognitive, _reason, DATA)
_atomic = AtomicExtractor(DATA)
_mental_models = MentalModelLibrary(DATA)
_super_strategy = SuperStrategyEngine(_graph, _mental_models, _game_theory, _detective, _scenario, _anti_gaming, _cognitive, _reason, DATA)

def json_load(path):
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def json_save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

class SecondBrainHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP), **kwargs)

    @staticmethod
    def _coerce_bool_flag(value):
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    def send_err(self, msg, code=400):
        self.send_json({'error': True, 'message': msg}, code)
    def read_body(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0: return {}
            return json.loads(self.rfile.read(length).decode('utf-8'))
        except: return {}
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    def do_GET(self):
        p = urlparse(self.path)
        path = p.path
        if path == '/api/stats': self.stats()
        elif path == '/api/trading/stats': self.trading_stats()
        elif path == '/api/trading/rules': self.trading_rules()
        elif path == '/api/trading/lessons': self.trading_lessons()
        elif path == '/api/trading/recent-logs': self.trading_recent_logs()
        elif path == '/api/trading/regime': self.trading_regime(parse_qs(p.query))
        elif path == '/api/v0/status': self.v0_status()
        elif path == '/api/v0/board': self.v0_board_status()
        elif path == '/api/v0/evolution/log': self.v0_evolution_log(parse_qs(p.query))
        elif path == '/api/v0/learning/summary': self.v0_learning_summary(parse_qs(p.query))
        elif path == '/api/v0/feedback/summary': self.v0_feedback_summary(parse_qs(p.query))
        elif path == '/api/v0/feedback/memory-candidates': self.v0_feedback_memory_candidates(parse_qs(p.query))
        elif path == '/api/v0/review/unified-queue': self.v0_unified_memory_review_queue(parse_qs(p.query))
        elif path == '/api/v0/review/unified-confirm': self.v0_unified_memory_review_confirm(parse_qs(p.query))
        elif path == '/api/v0/review/unified-summary': self.v0_unified_memory_review_summary(parse_qs(p.query))
        elif path == '/api/v0/review/unified-signals': self.v0_unified_memory_review_signals(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-suggestions': self.v0_unified_memory_review_ranking_suggestions(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-diff': self.v0_unified_memory_review_ranking_diff(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-diff-confirm': self.v0_unified_memory_review_ranking_diff_confirm(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-diff-summary': self.v0_unified_memory_review_ranking_diff_summary(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-diff-signals': self.v0_unified_memory_review_ranking_diff_signals(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-policy-suggestions': self.v0_unified_memory_review_ranking_policy_suggestions(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-policy-approve': self.v0_unified_memory_review_ranking_policy_approve(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-policy-approval-summary': self.v0_unified_memory_review_ranking_policy_approval_summary(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-policy-approval-signals': self.v0_unified_memory_review_ranking_policy_approval_signals(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-policy-change-candidates': self.v0_unified_memory_review_ranking_policy_change_candidates(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-policy-change-candidate-approve': self.v0_unified_memory_review_ranking_policy_change_candidate_approve(parse_qs(p.query))
        elif path == '/api/v0/review/unified-ranking-policy-change-candidate-approval-summary': self.v0_unified_memory_review_ranking_policy_change_candidate_approval_summary(parse_qs(p.query))
        elif path == '/api/v0/trading/replay-history-summary': self.v0_trading_replay_history_summary(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-evidence-gaps': self.v0_trading_research_queue_evidence_gap_summary(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-consistency-diagnostics': self.v0_trading_research_queue_consistency_diagnostics_summary(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-readiness': self.v0_trading_research_queue_readiness_summary(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-approval-summary': self.v0_trading_research_queue_approval_summary(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-approval-signals': self.v0_trading_research_queue_approval_signals(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-watchlist': self.v0_trading_research_queue_watchlist(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-review-agenda': self.v0_trading_research_queue_review_agenda(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-next-validation-slice': self.v0_trading_research_queue_next_validation_slice(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-run-next-validation-slice': self.v0_trading_research_queue_run_next_validation_slice(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-latest-validation-summary': self.v0_trading_research_queue_latest_validation_summary(parse_qs(p.query))
        elif path == '/api/v0/trading/research-queue-sync-bulletin-from-latest-validation': self.v0_trading_research_queue_sync_bulletin_from_latest_validation(parse_qs(p.query))
        elif path == '/api/v0/trading/a-share/tdx-quote-snapshot': self.v0_trading_a_share_tdx_quote_snapshot(parse_qs(p.query))
        elif path == '/api/v0/trading/a-share/tencent-qt-realtime-snapshot': self.v0_trading_a_share_tencent_qt_realtime_snapshot(parse_qs(p.query))
        elif path == '/api/v0/trading/a-share/workbuddy-context-snapshot': self.v0_trading_a_share_workbuddy_context_snapshot(parse_qs(p.query))
        elif path == '/api/v0/trading/a-share/realtime-crosscheck-summary': self.v0_trading_a_share_realtime_crosscheck_summary(parse_qs(p.query))
        elif path == '/api/v0/learning/inspect': self.v0_learning_inspect(parse_qs(p.query))
        elif path == '/api/v0/learning/chains': self.v0_learning_chains(parse_qs(p.query))
        elif path == '/api/v0/learning/apply': self.v0_learning_apply(parse_qs(p.query))
        elif path == '/api/v0/legacy/lessons-map': self.v0_legacy_lessons_map(parse_qs(p.query))
        elif path == '/api/v0/legacy/decision-view': self.v0_legacy_decision_view(parse_qs(p.query))
        elif path == '/api/v0/legacy/action-summary': self.v0_legacy_action_summary(parse_qs(p.query))
        elif path == '/api/v0/atom/writeback': self.v0_atom_writeback(parse_qs(p.query))
        elif path == '/api/v0/writeback/overview': self.v0_writeback_overview(parse_qs(p.query))
        elif path == '/api/v0/writeback/compare': self.v0_writeback_compare(parse_qs(p.query))
        elif path == '/api/knowledge-graph': self.send_json(_graph.get_full_graph())
        elif path == '/api/tasks/stats': self.task_stats()
        elif path == '/api/tasks/reminders': self.get_reminders(parse_qs(p.query))
        elif path == '/api/tasks/overdue': self.overdue_tasks()
        elif path == '/api/emotion/snapshot': self.emotion_snapshot()
        elif path == '/api/emotion/relationship': self.emotion_relationship()
        elif path == '/api/emotion/policy': self.emotion_policy()
        elif path == '/api/emotion/breathing': self.emotion_breathing()
        elif path == '/api/emotion/trend': self.emotion_trend(parse_qs(p.query))
        elif path == '/api/emotion/timeline': self.emotion_timeline(parse_qs(p.query))
        elif path == '/api/goal/stats': self.goal_stats(parse_qs(p.query))
        elif path == '/api/goal/health': self.goal_health(parse_qs(p.query))
        elif path == '/api/goal/reviews-due': self.goal_reviews_due(parse_qs(p.query))
        elif path == '/api/goal/list': self.goal_list(parse_qs(p.query))
        elif path == '/api/goal/tree': self.goal_tree(parse_qs(p.query))
        elif path == '/api/goal/paths': self.goal_paths(parse_qs(p.query))
        elif path == '/api/goal/weekplan': self.goal_weekplan_get(parse_qs(p.query))
        elif path == '/api/agent/weights': self.agent_weights(parse_qs(p.query))
        elif path == '/api/agent/stats': self.agent_stats(parse_qs(p.query))
        elif path == '/api/agent/audits': self.agent_audit_list(parse_qs(p.query))
        elif path == '/api/agent/audit': self.agent_audit_get(parse_qs(p.query))
        elif path == '/api/evolve/diagnose': self.evolve_diagnose(parse_qs(p.query))
        elif path == '/api/evolve/stats': self.evolve_stats(parse_qs(p.query))
        elif path == '/api/evolve/mode': self.evolve_mode_get(parse_qs(p.query))
        elif path == '/api/evolve/tickets': self.evolve_ticket_list(parse_qs(p.query))
        elif path == '/api/evolve/ticket': self.evolve_ticket_get(parse_qs(p.query))
        elif path == '/api/evolve/regression-tests': self.evolve_regression_list(parse_qs(p.query))
        else: super().do_GET()
    def do_POST(self):
        p = urlparse(self.path)
        path = p.path
        data = self.read_body()
        self._last_data = data
        routes = self.get_routes()
        if path in routes:
            try: routes[path]()
            except Exception as e: self.send_err(str(e), 500)
        else: self.send_err('Unknown: ' + path, 404)
    def get_routes(self):
        return {
            '/api/digest/text': lambda: self.digest_text(self._last_data),
            '/api/digest/file': lambda: self.digest_file(self._last_data),
            '/api/digest/url': lambda: self.digest_url(self._last_data),
            '/api/digest/batch-text': lambda: self.digest_batch(self._last_data),
            '/api/retrieve/search': lambda: self.search(self._last_data),
            '/api/retrieve/ask': lambda: self.ask(self._last_data),
            '/api/finance/consult': lambda: self.finance_consult(self._last_data),
            '/api/finance/backtest': lambda: self.finance_backtest(self._last_data),
            '/api/finance/hot-themes': lambda: self.finance_hot_themes(self._last_data),
            '/api/sync/scan': lambda: self.sync_scan(self._last_data),
            '/api/sync/ingest': lambda: self.sync_ingest(self._last_data),
            '/api/sync/watch-memory': lambda: self.sync_memory(self._last_data),
            '/api/memory/record': lambda: self.memory_record(self._last_data),
            '/api/memory/feedback': lambda: self.memory_feedback(self._last_data),
            '/api/memory/consolidate': lambda: self.send_json(_memory.consolidate()),
            '/api/evolve/evaluate': lambda: self.send_json(_evolve.evaluate()),
            '/api/evolve/apply-rules': lambda: self.send_json(_evolve.apply_rules()),
            '/api/evolve/auto-fix': lambda: self.send_json(_evolve.auto_fix()),
            '/api/events/record': lambda: self.record_event(self._last_data),
            '/api/events/check': lambda: self.check_events(self._last_data),
            '/api/events/conflicts': lambda: self.check_conflicts(self._last_data),
            '/api/events/remind': lambda: self.remind_events(self._last_data),
            '/api/events/upcoming': lambda: self.upcoming_events(self._last_data),
            '/api/events/conflict-check': lambda: self.check_single_conflict(self._last_data),
            '/api/events/update': lambda: self.update_event_status(self._last_data),
            '/api/tasks/create': lambda: self.create_task(self._last_data),
            '/api/tasks/transition': lambda: self.transition_task(self._last_data),
            '/api/tasks/query': lambda: self.query_tasks(self._last_data),
            '/api/tasks/search': lambda: self.search_tasks(self._last_data),
            '/api/tasks/reminders': lambda: self.get_reminders(self._last_data),
            '/api/tasks/overdue': lambda: self.overdue_tasks(),
            '/api/tasks/review': lambda: self.review_task(self._last_data),
            '/api/tasks/stats': lambda: self.task_stats(),
            '/api/emotion/analyze': lambda: self.analyze_message(self._last_data),
            '/api/emotion/snapshot': lambda: self.emotion_snapshot(),
            '/api/emotion/relationship': lambda: self.emotion_relationship(),
            '/api/emotion/timeline': lambda: self.emotion_timeline(self._last_data),
            '/api/emotion/patterns': lambda: self.emotion_patterns(self._last_data),
            '/api/emotion/policy': lambda: self.emotion_policy(),
            '/api/emotion/trend': lambda: self.emotion_trend(self._last_data),
            '/api/emotion/breathing': lambda: self.emotion_breathing(),
            '/api/emotion/milestone': lambda: self.emotion_milestone(self._last_data),
            '/api/goal/create': lambda: self.goal_create(self._last_data),
            '/api/goal/list': lambda: self.goal_list(self._last_data),
            '/api/goal/tree': lambda: self.goal_tree(self._last_data),
            '/api/goal/transition': lambda: self.goal_transition(self._last_data),
            '/api/goal/milestone': lambda: self.goal_milestone(self._last_data),
            '/api/goal/review': lambda: self.goal_review(self._last_data),
            '/api/goal/delete': lambda: self.goal_delete(self._last_data),
            '/api/goal/stats': lambda: self.goal_stats(self._last_data),
            '/api/goal/health': lambda: self.goal_health(self._last_data),
            '/api/goal/reviews-due': lambda: self.goal_reviews_due(self._last_data),
            '/api/goal/simulate': lambda: self.goal_simulate(self._last_data),
            '/api/goal/paths': lambda: self.goal_paths(self._last_data),
            '/api/goal/weekplan-create': lambda: self.goal_weekplan_create(self._last_data),
            '/api/goal/weekplan': lambda: self.goal_weekplan_get(self._last_data),
            '/api/agent/orchestrate': lambda: self.agent_orchestrate(self._last_data),
            '/api/agent/outcome': lambda: self.agent_record_outcome(self._last_data),
            '/api/evolve/cycle': lambda: self.evolve_cycle(self._last_data),
            '/api/evolve/mode': lambda: self.evolve_mode_set(self._last_data),
            '/api/evolve/circuit-breaker/reset': lambda: self.evolve_circuit_breaker_reset(self._last_data),
            '/api/evolve/skill-call': lambda: self.evolve_record_skill_call(self._last_data),
            '/api/evolve/ticket/update': lambda: self.evolve_ticket_update(self._last_data),
            '/api/evolve/ticket/approve': lambda: self.evolve_ticket_approve(self._last_data),
            '/api/evolve/ticket/rollback': lambda: self.evolve_ticket_rollback(self._last_data),
            '/api/evolve/regression-tests/run': lambda: self.evolve_regression_run(self._last_data),
            '/api/evolve/regression-tests/add': lambda: self.evolve_regression_add(self._last_data),
            '/api/export/report': lambda: self.export_framework(self._last_data),
            '/api/health/prune': lambda: self.health_prune(self._last_data),
            '/api/health/reinforce': lambda: self.health_reinforce(self._last_data),
            '/api/health/detect-contradictions': lambda: self.health_detect(self._last_data),
            '/api/health/touch': lambda: self.health_touch(self._last_data),
            '/api/fast-index/rebuild': lambda: self.fast_index_rebuild(),
            '/api/fast-index/search': lambda: self.fast_search(self._last_data),
            '/api/fast-index/hybrid': lambda: self.fast_hybrid(self._last_data),
            '/api/fast-index/rerank': lambda: self.fast_rerank(self._last_data),
            '/api/human/review': lambda: self.human_review(self._last_data),
            '/api/human/search': lambda: self.human_search(self._last_data),
            '/api/verify/consistency': lambda: self.verify_consistency(self._last_data),
            '/api/verify/full': lambda: self.verify_full(self._last_data),
            '/api/verify/cross': lambda: self.verify_cross(self._last_data),
            '/api/verify/chain': lambda: self.verify_chain(self._last_data),
            '/api/verify/all': lambda: self.verify_all_nodes(self._last_data),
            '/api/verify/record-decision': lambda: self.verify_record_decision(self._last_data),
            '/api/cognitive/think': lambda: self.cognitive_think(self._last_data),
            '/api/cognitive/decision': lambda: self.cognitive_decision(self._last_data),
            '/api/cognitive/outcome': lambda: self.cognitive_outcome(self._last_data),
            '/api/cognitive/stats': lambda: self.cognitive_stats(),
            '/api/reason/cross-domain': lambda: self.reason_cross_domain(self._last_data),
            '/api/maibot/think': lambda: self.maibot_think(self._last_data),
            '/api/maibot/sync': lambda: self.maibot_sync(),
            '/api/maibot/status': lambda: self.maibot_status(),
            '/api/super/think': lambda: self.super_think(self._last_data),
            '/api/super/decision': lambda: self.super_decision(self._last_data),
            '/api/super/record-outcome': lambda: self.super_record_outcome(self._last_data),
            '/api/super/stats': lambda: self.super_stats(),
            '/api/game/analyze': lambda: self.game_analyze(self._last_data),
            '/api/game/think-enemy': lambda: self.game_think_enemy(self._last_data),
            '/api/game/multi-step': lambda: self.game_multi_step(self._last_data),
            '/api/game/advantage': lambda: self.game_advantage(self._last_data),
            '/api/game/stats': lambda: self.game_stats(),
            '/api/detective/investigate': lambda: self.detective_investigate(self._last_data),
            '/api/detective/washout-risk': lambda: self.detective_washout_risk(self._last_data),
            '/api/detective/breakout': lambda: self.detective_breakout(self._last_data),
            '/api/detective/stats': lambda: self.detective_stats(),
            '/api/news/verify': lambda: self.news_verify(self._last_data),
            '/api/news/batch': lambda: self.news_batch(self._last_data),
            '/api/news/stats': lambda: self.news_stats(),
            '/api/scenario/plan': lambda: self.scenario_plan(self._last_data),
            '/api/scenario/decision-tree': lambda: self.scenario_decision_tree(self._last_data),
            '/api/scenario/monte-carlo': lambda: self.scenario_monte_carlo(self._last_data),
            '/api/scenario/stats': lambda: self.scenario_stats(),
            '/api/anti-gaming/detect': lambda: self.anti_gaming_detect(self._last_data),
            '/api/anti-gaming/stats': lambda: self.anti_gaming_stats(),
            '/api/atomic/extract': lambda: self.atomic_extract(self._last_data),
            '/api/atomic/query': lambda: self.atomic_query(self._last_data),
            '/api/atomic/infer': lambda: self.atomic_infer(self._last_data),
            '/api/atomic/stats': lambda: self.atomic_stats(),
            '/api/mind-models/select': lambda: self.mind_models_select(self._last_data),
            '/api/mind-models/detect-bias': lambda: self.mind_models_detect_bias(self._last_data),
            '/api/mind-models/wisdom': lambda: self.mind_models_wisdom(self._last_data),
            '/api/mind-models/stats': lambda: self.mind_models_stats(),
            '/api/strategy/analyze': lambda: self.strategy_analyze(self._last_data),
            '/api/strategy/stats': lambda: self.strategy_stats(),
            '/api/trading/check': lambda: self.trading_check(self._last_data),
            '/api/trading/add-log': lambda: self.trading_add_log(self._last_data),
            '/api/trading/signal-context': lambda: self.trading_signal_context(self._last_data),
            '/api/trading/add-lesson': lambda: self.trading_add_lesson(self._last_data),
            '/api/actr/access': lambda: self.actr_access(self._last_data),
            '/api/actr/simulate-decay': lambda: self.actr_simulate_decay(self._last_data),
            '/api/v0/ingest/text': lambda: self.v0_ingest_text(self._last_data),
            '/api/v0/search': lambda: self.v0_search(self._last_data),
            '/api/v0/learning/search': lambda: self.v0_learning_search(self._last_data),
            '/api/v0/feedback/summary': lambda: self.v0_feedback_summary(self._last_data),
            '/api/v0/feedback/memory-candidates': lambda: self.v0_feedback_memory_candidates(self._last_data),
            '/api/v0/review/unified-queue': lambda: self.v0_unified_memory_review_queue(self._last_data),
            '/api/v0/review/unified-confirm': lambda: self.v0_unified_memory_review_confirm(self._last_data),
            '/api/v0/review/unified-summary': lambda: self.v0_unified_memory_review_summary(self._last_data),
            '/api/v0/review/unified-signals': lambda: self.v0_unified_memory_review_signals(self._last_data),
            '/api/v0/review/unified-ranking-suggestions': lambda: self.v0_unified_memory_review_ranking_suggestions(self._last_data),
            '/api/v0/review/unified-ranking-diff': lambda: self.v0_unified_memory_review_ranking_diff(self._last_data),
            '/api/v0/review/unified-ranking-diff-confirm': lambda: self.v0_unified_memory_review_ranking_diff_confirm(self._last_data),
            '/api/v0/review/unified-ranking-diff-summary': lambda: self.v0_unified_memory_review_ranking_diff_summary(self._last_data),
            '/api/v0/review/unified-ranking-diff-signals': lambda: self.v0_unified_memory_review_ranking_diff_signals(self._last_data),
            '/api/v0/review/unified-ranking-policy-suggestions': lambda: self.v0_unified_memory_review_ranking_policy_suggestions(self._last_data),
            '/api/v0/review/unified-ranking-policy-approve': lambda: self.v0_unified_memory_review_ranking_policy_approve(self._last_data),
            '/api/v0/review/unified-ranking-policy-approval-summary': lambda: self.v0_unified_memory_review_ranking_policy_approval_summary(self._last_data),
            '/api/v0/review/unified-ranking-policy-approval-signals': lambda: self.v0_unified_memory_review_ranking_policy_approval_signals(self._last_data),
            '/api/v0/review/unified-ranking-policy-change-candidates': lambda: self.v0_unified_memory_review_ranking_policy_change_candidates(self._last_data),
            '/api/v0/review/unified-ranking-policy-change-candidate-approve': lambda: self.v0_unified_memory_review_ranking_policy_change_candidate_approve(self._last_data),
            '/api/v0/review/unified-ranking-policy-change-candidate-approval-summary': lambda: self.v0_unified_memory_review_ranking_policy_change_candidate_approval_summary(self._last_data),
            '/api/v0/trading/replay-history-summary': lambda: self.v0_trading_replay_history_summary(self._last_data),
            '/api/v0/trading/research-queue-evidence-gaps': lambda: self.v0_trading_research_queue_evidence_gap_summary(self._last_data),
            '/api/v0/trading/research-queue-consistency-diagnostics': lambda: self.v0_trading_research_queue_consistency_diagnostics_summary(self._last_data),
            '/api/v0/trading/research-queue-readiness': lambda: self.v0_trading_research_queue_readiness_summary(self._last_data),
            '/api/v0/trading/research-queue-approval-summary': lambda: self.v0_trading_research_queue_approval_summary(self._last_data),
            '/api/v0/trading/research-queue-approval-signals': lambda: self.v0_trading_research_queue_approval_signals(self._last_data),
            '/api/v0/trading/research-queue-watchlist': lambda: self.v0_trading_research_queue_watchlist(self._last_data),
            '/api/v0/trading/research-queue-review-agenda': lambda: self.v0_trading_research_queue_review_agenda(self._last_data),
            '/api/v0/trading/research-queue-next-validation-slice': lambda: self.v0_trading_research_queue_next_validation_slice(self._last_data),
            '/api/v0/trading/research-queue-run-next-validation-slice': lambda: self.v0_trading_research_queue_run_next_validation_slice(self._last_data),
            '/api/v0/trading/research-queue-latest-validation-summary': lambda: self.v0_trading_research_queue_latest_validation_summary(self._last_data),
            '/api/v0/trading/research-queue-sync-bulletin-from-latest-validation': lambda: self.v0_trading_research_queue_sync_bulletin_from_latest_validation(self._last_data),
            '/api/v0/trading/research-queue-approve': lambda: self.v0_trading_research_queue_approve(self._last_data),
            '/api/v0/learning/inspect': lambda: self.v0_learning_inspect(self._last_data),
            '/api/v0/learning/chains': lambda: self.v0_learning_chains(self._last_data),
            '/api/v0/learning/apply': lambda: self.v0_learning_apply(self._last_data),
            '/api/v0/legacy/lessons-map': lambda: self.v0_legacy_lessons_map(self._last_data),
            '/api/v0/legacy/decision-view': lambda: self.v0_legacy_decision_view(self._last_data),
            '/api/v0/legacy/action-confirm': lambda: self.v0_legacy_action_confirm(self._last_data),
            '/api/v0/legacy/action-summary': lambda: self.v0_legacy_action_summary(self._last_data),
            '/api/v0/atom/writeback': lambda: self.v0_atom_writeback(self._last_data),
            '/api/v0/writeback/overview': lambda: self.v0_writeback_overview(self._last_data),
            '/api/v0/writeback/snapshot': lambda: self.v0_writeback_snapshot(self._last_data),
            '/api/v0/writeback/compare': lambda: self.v0_writeback_compare(self._last_data),
            '/api/v0/decision': lambda: self.v0_decision(self._last_data),
            '/api/v0/forecast': lambda: self.v0_forecast(self._last_data),
            '/api/v0/reasoning-trace': lambda: self.v0_reasoning_trace(self._last_data),
            '/api/v0/review': lambda: self.v0_review(self._last_data),
            '/api/v0/feedback': lambda: self.v0_feedback(self._last_data),
            '/api/v0/learning-entry': lambda: self.v0_learning_entry(self._last_data),
            '/api/v0/trading/replay': lambda: self.v0_trading_replay(self._last_data),
            '/api/v0/trading/a-share/tdx-quote-snapshot': lambda: self.v0_trading_a_share_tdx_quote_snapshot(self._last_data),
            '/api/v0/trading/a-share/tencent-qt-realtime-snapshot': lambda: self.v0_trading_a_share_tencent_qt_realtime_snapshot(self._last_data),
            '/api/v0/trading/a-share/workbuddy-context-snapshot': lambda: self.v0_trading_a_share_workbuddy_context_snapshot(self._last_data),
            '/api/v0/trading/a-share/realtime-crosscheck-summary': lambda: self.v0_trading_a_share_realtime_crosscheck_summary(self._last_data),
            '/api/v0/board/update': lambda: self.v0_board_update(self._last_data),
        }
    def _get_data(self): data = self.read_body(); self._last_data = data; return data

    def digest_text(self, data):
        text = data.get('text','').strip(); node = _digester.digest(text, data.get('title',''), data.get('source','manual')); _search.rebuild(); _health.register(node['id'], node.get('importance',3)); _fast_index.add_document(node['id'], node.get('title',''), node.get('content','')); self.send_json({'success':True,'node':node})

    def digest_batch(self, data):
        items = data.get('items',[]); results = [_digester.digest(i.get('text',''),i.get('title',''),i.get('source','batch')) for i in items if i.get('text')]; _search.rebuild(); self.send_json({'success':True,'count':len(results)})

    def digest_file(self, data):
        path = data.get('path',''); node = _file_digester.digest_file(path); self.send_json({'success':True,'node':node})

    def digest_url(self, data):
        url = data.get('url',''); node = _url_digester.digest_url(url); self.send_json({'success':True,'node':node})

    def stats(self, data=None):
        _graph.reload(); s = _graph.get_stats(); mem = json_load(DATA/'memory-index.json'); self.send_json({'knowledge':{'nodes':s['total_nodes'],'edges':s['total_edges']},'server':{'version':'v5-clean'}})

    def search(self, data=None):
        q = data.get('query',''); results = _search.search(q,data.get('top_k',10)); self.send_json({'results':results})

    def ask(self, data=None):
        q = data.get('query',''); results = _search.search(q,5); ctx = _cognitive.build_context(q,results) if hasattr(_cognitive,'build_context') else ''; self.send_json({'question':q,'relevant_nodes':results,'context':ctx})

    def finance_consult(self, data):
        target = data.get('target',''); missing = [k for k in ['thesis','action','horizon'] if not data.get(k)]; self.send_json({'target':target,'verdict':'reviewed','missing':missing})

    def finance_backtest(self, data):
        csv_path = data.get('csv_path',''); bars = load_price_csv(csv_path); self.send_json({'success':True,'bars':len(bars)})

    def finance_hot_themes(self, data):
        themes = analyze_hot_themes(); self.send_json({'themes':themes})

    def sync_scan(self, data):
        self.send_json(_syncer.scan())

    def sync_ingest(self, data):
        self.send_json({'success':True})

    def sync_memory(self, data):
        self.send_json({'success':True})

    def memory_record(self, data):
        result = _memory.record_interaction(data.get('content',''), data.get('type','message')); self.send_json({'success':True,'id':result})

    def memory_feedback(self, data):
        self.send_json(_memory.record_feedback(data.get('interaction_id',''), data.get('rating',0)))

    def record_event(self, data):
        """POST /api/events/record — 自然语言录入事件（自动提取日期/时间/人物/冲突检测）"""
        text = data.get('text', '')
        title = data.get('title', '')
        full_text = (title + ' ' + text) if title else text
        if not full_text or not full_text.strip():
            self.send_err('缺少 text 或 title', 400)
            return
        events = _events.record(full_text.strip())
        # 顺便跑冲突检测
        conflict_list = _events.conflicts()
        reminders = _events.remind()
        self.send_json({
            'success': True,
            'extracted': events,
            'extracted_count': len(events),
            'conflicts_today': len(conflict_list),
            'has_conflicts': len(conflict_list) > 0,
            'conflict_summary': [(c.get('date',''), c.get('type',''), c.get('severity',1)) for c in conflict_list[:5]],
            'reminders_today': reminders.get('reminders', []),
        })

    def check_events(self, data):
        """POST /api/events/check — 查询某日事件（date=YYYY-MM-DD）"""
        date = data.get('date', '')
        if not date:
            self.send_err('缺少 date', 400)
            return
        events = _events.check(date)
        self.send_json({
            'date': date,
            'events': events,
            'count': len(events),
        })

    def check_conflicts(self, data):
        """POST /api/events/conflicts — 检测所有冲突"""
        del data
        conflict_list = _events.conflicts()
        self.send_json({
            'conflicts': conflict_list,
            'count': len(conflict_list),
            'has_conflicts': len(conflict_list) > 0,
            'by_type': {
                t: len([c for c in conflict_list if c.get('type') == t])
                for t in set(c.get('type', '') for c in conflict_list)
            },
        })

    def remind_events(self, data):
        """POST /api/events/remind — 综合提醒（今日/明日/冲突/计时器）"""
        del data
        result = _events.remind()
        self.send_json(result)

    def upcoming_events(self, data):
        """POST /api/events/upcoming — 未来 N 天事件"""
        days = int(data.get('days', 7))
        events = _events.upcoming(days)
        self.send_json({
            'days': days,
            'events': events,
            'count': len(events),
        })

    def check_single_conflict(self, data):
        """POST /api/events/conflict-check — 单条文本冲突检测（返回冲突详情，含has_conflict/conflicts/max_severity/suggestion）"""
        text = (data.get('title', '') + ' ' + data.get('text', '')).strip()
        date = data.get('date', '') or data.get('target_date', '')
        if not text:
            self.send_err('缺少 text 或 title', 400)
            return
        # 提取新事件
        total_conflicts = []
        extracted = _events.extract(text)
        if date and not extracted:
            # 如果指定日期但没提取到，构造一个虚拟事件用于冲突检测
            event_type = _events._classify_event(text)
            extracted = [{
                'text': text[:200],
                'date': date,
                'type': event_type,
                'importance': _events._judge_importance(text),
                'all_day': True,
            }]
        if extracted and not date:
            # 用提取到的日期
            date = extracted[0].get('date', '')
        if date:
            existing_on_date = _events.check(date)
            if existing_on_date:
                # 检查同日是否有冲突
                for evt in extracted:
                    evt_type = evt.get('type', '')
                    evt_imp = evt.get('importance', 1)
                    for exist in existing_on_date:
                        exist_type = exist.get('type', '')
                        exist_imp = exist.get('importance', 1)
                        # 不同类型但同一天 = 软冲突
                        if evt_type != exist_type:
                            total_conflicts.append({
                                'conflict_type': 'same_day_different_type',
                                'severity': max(evt_imp, exist_imp),
                                'existing_event': exist.get('text', '')[:100],
                                'existing_date': exist.get('date', ''),
                                'existing_type': exist_type,
                                'new_event': evt.get('text', '')[:100],
                                'new_type': evt_type,
                            })
                        elif evt_type == exist_type:
                            total_conflicts.append({
                                'conflict_type': 'duplicate_same_day',
                                'severity': 1,
                                'existing_event': exist.get('text', '')[:100],
                                'existing_date': exist.get('date', ''),
                                'existing_type': exist_type,
                                'new_event': evt.get('text', '')[:100],
                                'new_type': evt_type,
                            })
        has_conflicts = len(total_conflicts) > 0
        max_severity = max((c.get('severity', 1) for c in total_conflicts), default=0)
        suggestion = '' if not has_conflicts else (
            '时间冲突，建议用户确认' if max_severity <= 2 else
            '存在重要冲突，需要优先处理'
        )
        self.send_json({
            'success': True,
            'has_conflict': has_conflicts,
            'conflicts': total_conflicts,
            'conflict_count': len(total_conflicts),
            'max_severity': max_severity,
            'suggestion': suggestion,
            'extracted_count': len(extracted),
        })

    def update_event_status(self, data):
        """POST /api/events/update — P2.8: 更新事件状态（确认→更新闭环）

        接受: {
            event_id: str,           # 事件 ID 或文本关键词
            new_status: str,         # confirmed | cancelled | rescheduled | done
            note: str = "",          # 更新原因说明
            resolve_conflicting: [str] = [],  # 同时取消的冲突事件 ID 列表
        }
        返回: {updated: [...], not_found: [...], conflict_ids_resolved: [...]}
        """
        event_id = data.get("event_id", "")
        new_status = data.get("new_status", "")
        note = data.get("note", "")
        resolve_conflicting = data.get("resolve_conflicting", [])

        if not event_id or not new_status:
            self.send_err("缺少 event_id 或 new_status", 400)
            return

        result = _events.update_status(event_id, new_status, note, resolve_conflicting)
        self.send_json({"success": True, **result})

    # ── Phase 3: Task API handlers ──

    def create_task(self, data):
        """POST /api/tasks/create — 创建任务 (自然语言或结构化)"""
        title = data.get("title", data.get("text", ""))
        if not title:
            self.send_err("缺少 title/text", 400)
            return
        desc = data.get("description", "")
        kwargs = {k: v for k, v in data.items()
                  if k in ("due_at", "priority", "energy_level", "estimated_minutes", "scheduled_start", "scheduled_end") and v}
        task = _tasks.create(title, desc, **kwargs)
        self.send_json({"success": True, "task": task})

    def transition_task(self, data):
        """POST /api/tasks/transition — 任务状态流转"""
        task_id = data.get("task_id", "")
        new_status = data.get("new_status", "")
        note = data.get("note", "")
        if not task_id or not new_status:
            self.send_err("缺少 task_id 或 new_status", 400)
            return
        result = _tasks.transition(task_id, new_status, note)
        if "error" in result:
            self.send_err(result["error"], 400, result)
        else:
            self.send_json({"success": True, "task": result})

    def query_tasks(self, data):
        """GET/POST /api/tasks/query — 按条件查询任务"""
        self.send_json({
            "tasks": _tasks.query(
                status=data.get("status", ""),
                priority=data.get("priority", ""),
                due_before=data.get("due_before", ""),
                limit=data.get("limit", 20),
            )
        })

    def search_tasks(self, data):
        """POST /api/tasks/search — 关键词搜索任务"""
        kw = data.get("keyword", data.get("query", ""))
        self.send_json({"tasks": _tasks.search(kw, data.get("limit", 10))})

    def get_reminders(self, data):
        """GET /api/tasks/reminders — 获取未来N小时内的提醒"""
        self.send_json({
            "reminders": _tasks.get_reminders(data.get("window_hours", 24)),
            "overdue": _tasks.overdue(),
        })

    def overdue_tasks(self):
        """GET /api/tasks/overdue — 超期任务"""
        self.send_json({"overdue": _tasks.overdue()})

    def review_task(self, data):
        """POST /api/tasks/review — 复盘已完成任务"""
        task_id = data.get("task_id", "")
        if not task_id:
            self.send_err("缺少 task_id", 400)
            return
        result = _tasks.review(
            task_id,
            rating=data.get("rating", 0),
            learnings=data.get("learnings", ""),
            note=data.get("note", ""),
        )
        self.send_json({"success": True, "task": result})

    def task_stats(self):
        """GET /api/tasks/stats — 任务统计"""
        self.send_json(_tasks.stats())

    # ── Phase 4: Emotion API handlers ──

    def analyze_message(self, data):
        """POST /api/emotion/analyze — 分析一条用户消息的情绪"""
        text = data.get("text", data.get("message", ""))
        if not text:
            self.send_err("缺少 text/message", 400)
            return
        result = _emotion.analyze_message(text.strip())
        self.send_json(result)

    def emotion_snapshot(self):
        """GET /api/emotion/snapshot — 当前用户情绪+关系快照"""
        self.send_json(_emotion.get_user_snapshot())

    def emotion_relationship(self):
        """GET /api/emotion/relationship — 完整关系状态"""
        self.send_json({
            "relationship": _emotion.get_relationship(),
            "health": _emotion.relationship_health(),
        })

    def emotion_timeline(self, data):
        """GET/POST /api/emotion/timeline — 情绪时间线"""
        self.send_json({"timeline": _emotion.get_emotion_timeline(data.get("hours", 24))})

    def emotion_patterns(self, data):
        """POST /api/emotion/patterns — 情感模式记忆"""
        self.send_json({"patterns": _emotion.get_patterns(data.get("keyword", ""), data.get("top_k", 10))})

    def emotion_policy(self):
        """GET /api/emotion/policy — Bot 表达策略"""
        self.send_json(_emotion.get_affective_policy())

    def emotion_trend(self, data):
        """GET/POST /api/emotion/trend — 情绪趋势分析"""
        self.send_json(_emotion.analyze_trend(data.get("days", 7)))

    def emotion_breathing(self):
        """GET /api/emotion/breathing — 呼吸感建议"""
        self.send_json(_emotion.breathing_advice())

    def emotion_milestone(self, data):
        """POST /api/emotion/milestone — 记录关系里程碑"""
        milestone = data.get("milestone", data.get("text", ""))
        if not milestone:
            self.send_err("缺少 milestone", 400)
            return
        _emotion.add_milestone(milestone.strip())
        self.send_json({"success": True, "milestone": milestone.strip()})

    def _get_param(self, data, key: str, default: str = "") -> str:
        """Extract param from GET (dict-of-lists) or POST (flat dict) data"""
        if isinstance(data, dict):
            v = data.get(key, default)
            if isinstance(v, list):
                return v[0] if v else default
            return v if v else default
        return default

    # ══════════════ Phase 5: Goals & Future Simulation ══════════════

    def goal_create(self, data):
        """POST /api/goal/create — 创建目标"""
        title = data.get('title', '').strip()
        if not title:
            self.send_err('缺少 title', 400); return
        result = _goals.create_goal(
            title=title,
            goal_type=data.get('goal_type', 'monthly'),
            description=data.get('description', ''),
            parent_goal_id=data.get('parent_goal_id', ''),
            target_date=data.get('target_date', ''),
            priority=data.get('priority', 'medium'),
            success_criteria=data.get('success_criteria', []),
            motivation=data.get('motivation', ''),
            energy_required=data.get('energy_required', 'medium'),
            review_interval_days=int(data.get('review_interval_days', 7)),
        )
        self.send_json(result)

    def goal_get(self, data):
        """GET /api/goal?id=xxx — 获取单个目标"""
        gid = self._get_param(data, 'id', '')
        if not gid:
            self.send_err('缺少 id', 400); return
        goal = _goals.get_goal(gid)
        self.send_json(goal if goal else {'error': f'Goal {gid} not found'})

    def goal_list(self, data):
        """GET/POST /api/goals — 列出目标"""
        goals = _goals.list_goals(
            goal_type=self._get_param(data, 'goal_type', ''),
            status=self._get_param(data, 'status', ''),
            parent_goal_id=self._get_param(data, 'parent_goal_id', ''),
            time_horizon=self._get_param(data, 'time_horizon', ''),
            limit=int(self._get_param(data, 'limit', '50') or '50'),
        )
        self.send_json({'goals': goals, 'count': len(goals)})

    def goal_tree(self, data):
        """GET /api/goal/tree?id=xxx — 目标树"""
        gid = self._get_param(data, 'id', '')
        self.send_json(_goals.get_goal_tree(gid))

    def goal_transition(self, data):
        """POST /api/goal/transition — 推进目标状态"""
        gid = data.get('id', '')
        new_status = data.get('status', '')
        if not gid or not new_status:
            self.send_err('缺少 id/status', 400); return
        self.send_json(_goals.transition_goal(gid, new_status))

    def goal_milestone(self, data):
        """POST /api/goal/milestone — 添加里程碑"""
        gid = data.get('id', ''); text = data.get('text', '').strip()
        if not gid or not text:
            self.send_err('缺少 id/text', 400); return
        self.send_json(_goals.add_milestone(gid, text, data.get('target_date', ''), data.get('achieved', False)))

    def goal_review(self, data):
        """POST /api/goal/review — 复盘目标"""
        gid = data.get('id', '')
        if not gid:
            self.send_err('缺少 id', 400); return
        self.send_json(_goals.review_goal(gid,
            progress_rating=int(data.get('rating', 3)),
            reflection=data.get('reflection', ''),
        ))

    def goal_delete(self, data):
        """POST /api/goal/delete — 删除目标 (级联子目标)"""
        gid = data.get('id', '')
        if not gid:
            self.send_err('缺少 id', 400); return
        self.send_json(_goals.delete_goal(gid))

    def goal_stats(self, data=None):
        """GET /api/goal/stats — 目标统计"""
        self.send_json(_goals.stats())

    def goal_health(self, data=None):
        """GET /api/goal/health — 目标健康检查"""
        self.send_json(_goals.health_check())

    def goal_reviews_due(self, data=None):
        """GET /api/goal/reviews-due — 需要复盘的 goals"""
        due = _goals.get_reviews_due()
        self.send_json({'due': due, 'count': len(due)})

    def goal_simulate(self, data):
        """POST /api/goal/simulate — 生成多路径未来推演"""
        self.send_json(_goals.simulate_future(
            goal_id=data.get('id', ''),
            description=data.get('description', ''),
            time_horizon_months=int(data.get('months', 6)),
        ))

    def goal_paths(self, data):
        """GET /api/goal/paths — 获取推演路径"""
        self.send_json({'paths': _goals.get_paths(self._get_param(data, 'id', ''))})

    def goal_weekplan_create(self, data):
        """POST /api/goal/weekplan — 生成周计划"""
        self.send_json(_goals.create_week_plan(data.get('week_start', '')))

    def goal_weekplan_get(self, data):
        """GET /api/goal/weekplan — 获取周计划"""
        self.send_json(_goals.get_week_plan(self._get_param(data, 'week_start', '')))

    # ══════════════ Phase 6: Multi-Agent Orchestrator ══════════════

    def agent_orchestrate(self, data):
        """POST /api/agent/orchestrate — 执行完整多Agent决策流程"""
        query = data.get('query', '').strip()
        if not query:
            self.send_err('缺少 query', 400); return
        agent_ids = data.get('agents', None)  # None = all
        if agent_ids and isinstance(agent_ids, str):
            agent_ids = [a.strip() for a in agent_ids.split(',')]
        context = data.get('context', {})
        auto_debate = data.get('auto_debate', True)
        result = _orchestrator.orchestrate(query, context, agent_ids, auto_debate)
        self.send_json(result)

    def agent_weights(self, data=None):
        """GET /api/agent/weights — 各Agent权重快照"""
        self.send_json(_orchestrator.get_weights())

    def agent_stats(self, data=None):
        """GET /api/agent/stats — 多Agent统计"""
        self.send_json(_orchestrator.stats())

    def agent_record_outcome(self, data):
        """POST /api/agent/outcome — 记录决策结果,更新Agent胜率"""
        audit_id = data.get('audit_id', '')
        if not audit_id:
            self.send_err('缺少 audit_id', 400); return
        outcome = data.get('outcome', '')
        was_correct = data.get('was_correct', False)
        signals = data.get('signals', None)
        _orchestrator.record_outcome(audit_id, outcome, was_correct, signals)
        self.send_json({'success': True, 'audit_id': audit_id, 'weights': _orchestrator.get_weights()})

    def agent_audit_list(self, data=None):
        """GET /api/agent/audits — 决策审计列表"""
        limit = int(self._get_param(data, 'limit', '20') or '20')
        self.send_json({'audits': _orchestrator.audit.list_recent(limit)})

    def agent_audit_get(self, data):
        """GET /api/agent/audit?id=xxx — 获取单条审计记录"""
        audit_id = self._get_param(data, 'id', '')
        if not audit_id:
            self.send_err('缺少 id', 400); return
        record = _orchestrator.audit.get(audit_id)
        self.send_json(record if record else {'error': f'Audit {audit_id} not found'})

    # ══════════════ Phase 7: Self-Evolution (MAPE-K) ══════════════

    def evolve_cycle(self, data):
        """POST /api/evolve/cycle — 执行一次 MAPE-K 循环"""
        self.send_json(_self_evolve.run_cycle())

    def evolve_diagnose(self, data=None):
        """GET /api/evolve/diagnose — 系统自诊断"""
        threshold = int(data.get('severity', 0)) if data else 0
        self.send_json(_self_evolve.diagnose(threshold).to_dict())

    def evolve_stats(self, data=None):
        """GET /api/evolve/stats — 自我进化统计"""
        self.send_json(_self_evolve.stats())

    def evolve_mode_get(self, data=None):
        """GET /api/evolve/mode — 当前运行模式"""
        self.send_json({"mode": _self_evolve.mode.name, "level": int(_self_evolve.mode)})

    def evolve_mode_set(self, data):
        """POST /api/evolve/mode — 设置运行模式"""
        mode_str = data.get('mode', '').strip()
        if not mode_str:
            self.send_err('缺少 mode (safety/observation/diagnostic/advisory/semi_auto/full_auto)', 400); return
        try:
            result = _self_evolve.set_mode(OpMode.from_str(mode_str))
            self.send_json({'success': True, **result})
        except Exception as e:
            self.send_err(str(e), 400)

    def evolve_circuit_breaker_reset(self, data=None):
        """POST /api/evolve/circuit-breaker/reset — 重置熔断器"""
        self.send_json(_self_evolve.reset_circuit_breaker())

    def evolve_record_skill_call(self, data):
        """POST /api/evolve/skill-call — 记录技能调用"""
        _self_evolve.record_skill_call(
            skill_id=data.get('skill_id', ''),
            skill_name=data.get('skill_name', ''),
            success=data.get('success', True),
            latency_ms=data.get('latency_ms', 0),
            error=data.get('error', ''),
        )
        self.send_json({'success': True})

    def evolve_ticket_list(self, data=None):
        """GET /api/evolve/tickets — 维修票据列表"""
        status = self._get_param(data, 'status', '') if data else ''
        category = self._get_param(data, 'category', '') if data else ''
        limit = int(self._get_param(data, 'limit', '50') if data else '50' or '50')
        self.send_json({'tickets': _self_evolve.list_tickets(status, category, limit)})

    def evolve_ticket_get(self, data):
        """GET /api/evolve/ticket?id=xxx — 获取单张维修票据"""
        tid = self._get_param(data, 'id', '')
        if not tid:
            self.send_err('缺少 id', 400); return
        ticket = _self_evolve.get_ticket(tid)
        self.send_json(ticket if ticket else {'error': f'Ticket {tid} not found'})

    def evolve_ticket_update(self, data):
        """POST /api/evolve/ticket/update — 更新维修票据"""
        tid = data.get('id', '')
        if not tid:
            self.send_err('缺少 id', 400); return
        updatable = {k: v for k, v in data.items()
                     if k in ('status', 'repair_result', 'verification') and k != 'id'}
        result = _self_evolve.update_ticket(tid, **updatable)
        self.send_json(result if result else {'error': 'Update failed'})

    def evolve_ticket_approve(self, data):
        """POST /api/evolve/ticket/approve — 批准维修票据"""
        tid = data.get('id', '')
        if not tid:
            self.send_err('缺少 id', 400); return
        result = _self_evolve.approve_ticket(tid)
        self.send_json(result if result else {'error': f'Ticket {tid} not found'})

    def evolve_ticket_rollback(self, data):
        """POST /api/evolve/ticket/rollback — 回滚修复"""
        tid = data.get('id', '')
        if not tid:
            self.send_err('缺少 id', 400); return
        result = _self_evolve.rollback_ticket(tid)
        self.send_json(result if result else {'error': f'Ticket {tid} not found'})

    def evolve_regression_list(self, data=None):
        """GET /api/evolve/regression-tests — 回归测试列表"""
        self.send_json({'tests': _self_evolve.list_regression_tests()})

    def evolve_regression_run(self, data):
        """POST /api/evolve/regression-tests/run — 运行回归测试"""
        test_ids = data.get('ids', [])
        self.send_json(_self_evolve.run_regression_tests(test_ids if test_ids else None))

    def evolve_regression_add(self, data):
        """POST /api/evolve/regression-tests/add — 添加回归测试用例"""
        rt = _self_evolve.add_regression_test(
            name=data.get('name', ''),
            ticket_id=data.get('ticket_id', ''),
            endpoint=data.get('endpoint', ''),
            method=data.get('method', 'GET'),
            payload=data.get('payload', {}),
            expected_status=data.get('expected_status', 'ok'),
            expected_field=data.get('expected_field', ''),
        )
        self.send_json({'success': True, 'test': rt.to_dict()})

    def export_framework(self, data):
        self.send_json({'framework':'second-brain','version':'v5-clean'})

    def health_prune(self, data):
        self.send_json({'success':True,'pruned':_health.prune(data.get('days',30))})

    def health_reinforce(self, data):
        self.send_json({'success':True})

    def health_detect(self, data):
        self.send_json({'success':True})

    def health_touch(self, data):
        self.send_json({'success':True})

    def fast_index_rebuild(self, data):
        _fast_index.rebuild(); self.send_json({'success':True})

    def fast_search(self, data):
        self.send_json({'results':_fast_index.search(data.get('query',''),data.get('top_k',10))})

    def fast_hybrid(self, data):
        self.send_json({'results':_fast_index.search_hybrid(data.get('query',''),data.get('top_k',10))})

    def fast_rerank(self, data):
        self.send_json({'results':_fast_index.rerank(data.get('query',''),data.get('results',[]))})

    def human_review(self, data):
        self.send_json({'success':True})

    def human_search(self, data):
        self.send_json({'results':_human.search(data.get('query',''),data.get('top_k',5))})

    def verify_consistency(self, data):
        self.send_json(_verify.check_consistency(data.get('node_id','')))

    def verify_full(self, data):
        self.send_json(_verify.full_verification(data.get('node_id','')))

    def verify_cross(self, data):
        self.send_json(_verify.cross_validate(data.get('node_ids',[])))

    def verify_chain(self, data):
        self.send_json(_verify.verify_chain(data.get('chain_id','')))

    def verify_all_nodes(self, data):
        self.send_json({'verified':_verify.verify_all()})

    def verify_record_decision(self, data):
        self.send_json({'success':True})

    def cognitive_think(self, data):
        sig = _cognitive.think(data.get('topic',''),data.get('context',{}),data.get('mode','deliberate'),int(data.get('depth',3))); self.send_json({'confidence':sig.confidence,'decision':sig.decision,'warnings':sig.warnings})

    def cognitive_decision(self, data):
        self.send_json(_cognitive.make_decision(data.get('type','general'),data.get('context',{}),data.get('options',[]),data.get('reasoning','')))

    def cognitive_outcome(self, data):
        self.send_json(_cognitive.record_outcome(data.get('decision_id',''),data.get('outcome',''),data.get('was_correct',False)))

    def cognitive_stats(self, data=None):
        self.send_json(_cognitive.get_cognition_stats())

    def reason_cross_domain(self, data):
        result = _reason.reason(data.get('topic',''),data.get('context_nodes',[]),int(data.get('depth',3))); self.send_json({'result':result})

    def maibot_think(self, data):
        self.send_json({'status':'active'})

    def maibot_sync(self, data):
        self.send_json({'status':'synced'})

    def maibot_status(self, data):
        self.send_json({'status':'active'})

    def super_think(self, data):
        ctx = _super_cog.MarketContext(stock=data.get('stock',''),current_price=float(data.get('current_price',0)),change_pct=float(data.get('change_pct',0)),volume=float(data.get('volume',0)),avg_volume=float(data.get('avg_volume',1)),market_trend=data.get('market_trend','neutral'),market_sentiment=data.get('market_sentiment','neutral'),volatility=data.get('volatility','medium'),recent_news=data.get('recent_news',[])); snap = _super_cog.think(data.get('situation',''),ctx,data.get('mode','deliberate'),int(data.get('depth',3))); self.send_json({'confidence':snap.confidence,'judgment':snap.final_judgment,'action':snap.recommended_action,'warnings':snap.warnings})

    def super_decision(self, data):
        did = _super_cog.record_decision(data.get('situation',''),data.get('action',''),None,data.get('reasoning','')); self.send_json({'decision_id':did})

    def super_record_outcome(self, data):
        _super_cog.record_outcome(data.get('decision_id',''),data.get('outcome',''),data.get('was_correct',False)); self.send_json({'success':True})

    def super_stats(self, data=None):
        self.send_json(_super_cog.get_stats())

    def game_analyze(self, data):
        state = _game_theory.analyze_market_game(data.get('stock',''),data.get('price_data',{}),data.get('volume_data',{}),data.get('news',[])); self.send_json({'pattern':state.detected_pattern,'confidence':state.confidence,'action':state.recommended_action})

    def game_think_enemy(self, data):
        self.send_json(_game_theory.think_like_enemy(data.get('current_position',{}),data.get('market_state',{}),data.get('my_intent','')))

    def game_multi_step(self, data):
        self.send_json(_game_theory.multi_step_prediction(data.get('current_state',{}),int(data.get('num_steps',3))))

    def game_advantage(self, data):
        self.send_json(_game_theory.analyze_advantage(data.get('my_position',{}),data.get('market',{})))

    def game_stats(self, data=None):
        self.send_json(_game_theory.get_stats())

    def detective_investigate(self, data):
        rep = _detective.investigate(data.get('stock',''),data.get('price_history',[]),data.get('volume_history',[]),data.get('minute_data',[])); self.send_json({'has_mainforce':rep.has_mainforce,'confidence':rep.confidence,'verdict':rep.verdict})

    def detective_washout_risk(self, data):
        self.send_json(_detective.analyze_washout_risk(float(data.get('current_price',0)),[float(x) for x in data.get('support_levels',[])]))

    def detective_breakout(self, data):
        self.send_json(_detective.calculate_breakout_probability(float(data.get('price',0)),float(data.get('resistance',0))))

    def detective_stats(self, data=None):
        self.send_json(_detective.get_stats())

    def news_verify(self, data):
        res = _news_verifier.verify(data.get('news',{}),data.get('stock','')); self.send_json({'authentic':res.is_authentic,'score':res.authenticity_score,'verdict':res.verdict})

    def news_batch(self, data):
        self.send_json({'count':len(data.get('news_list',[]))})

    def news_stats(self, data=None):
        self.send_json(_news_verifier.get_stats())

    def scenario_plan(self, data):
        plan = _scenario.create_scenario_plan(data.get('stock',''),float(data.get('current_price',0)),data.get('market_state',{})); self.send_json({'strategy':plan.recommended_strategy})

    def scenario_decision_tree(self, data):
        self.send_json({'best_option':_scenario.analyze_decision_tree(data.get('decision_points',[]),data.get('current_state',{})).best_option})

    def scenario_monte_carlo(self, data):
        self.send_json({'result':_scenario.monte_carlo_simulation(float(data.get('initial_capital',100000)),float(data.get('position_size',0.5)),int(data.get('num_simulations',1000)),int(data.get('time_horizon_days',20)))})

    def scenario_stats(self, data=None):
        self.send_json(_scenario.get_stats())

    def anti_gaming_detect(self, data):
        rep = _anti_gaming.detect(data.get('stock',''),data.get('price_history',[]),data.get('volume_history',[]),data.get('minute_data',[])); self.send_json({'gamed':rep.is_gamed,'score':rep.survival_score,'action':rep.recommended_action})

    def anti_gaming_stats(self, data=None):
        self.send_json(_anti_gaming.get_stats())

    def atomic_extract(self, data):
        self.send_json({'atoms':_atomic.extract(data.get('text',''),data.get('source',''))})

    def atomic_query(self, data):
        self.send_json({'results':_atomic.query(data.get('query',''),data.get('top_k',5))})

    def atomic_infer(self, data):
        self.send_json({'inferences':_atomic.infer(data.get('atom_ids',[]))})

    def atomic_stats(self, data=None):
        self.send_json(_atomic.get_stats())

    def mind_models_select(self, data):
        m = _mental_models.select_model(data.get('situation','')); self.send_json({'model':m.name,'description':m.description})

    def mind_models_detect_bias(self, data):
        b = _mental_models.detect_bias(data.get('situation','')); self.send_json({'bias':b.name if b else None})

    def mind_models_wisdom(self, data):
        self.send_json({'wisdom':_mental_models.get_wisdom(data.get('situation',''))})

    def mind_models_stats(self, data):
        self.send_json(_mental_models.get_stats())

    def strategy_analyze(self, data):
        r = _super_strategy.analyze(data.get('situation',''),data.get('context',{}),data.get('mode','comprehensive')); self.send_json({'confidence':r.confidence,'judgment':r.final_judgment})

    def strategy_stats(self, data):
        self.send_json(_super_strategy.get_stats())

    def trading_stats(self, data):
        self.send_json(_trading_brain.get_stats())

    def trading_rules(self, data):
        self.send_json(_trading_brain.get_rules())

    def trading_lessons(self, data):
        self.send_json({'lessons':_trading_brain.get_lessons(data.get('stock'))})

    def trading_recent_logs(self, data):
        self.send_json({'logs':_trading_brain.get_recent_logs(int(data.get('days',7)))})

    def trading_regime(self, data):
        params = data if isinstance(data,dict) else {}; self.send_json(_trading_brain.judge_market_regime(params))

    def trading_check(self, data):
        self.send_json(_trading_brain.pre_decision_check(data.get('decision',''),data.get('context',{})))

    def trading_add_log(self, data):
        self.send_json({'success':True})

    def trading_signal_context(self, data):
        self.send_json(_trading_brain.get_signal_context(data.get('stock','300418')))

    def trading_add_lesson(self, data):
        self.send_json({'success':True,'date':datetime.now().strftime('%Y-%m-%d')})

    def actr_access(self, data):
        self.send_json({'result':_actr.access(data.get('chunk_type',''),data.get('query',{}))})

    def actr_simulate_decay(self, data):
        self.send_json({'decayed':_actr.simulate_decay(float(data.get('time_elapsed',0)))})

    def v0_ingest_text(self, data):
        self.send_json(_v01.ingest_text(data))

    def v0_search(self, data):
        self.send_json(_v01.search(data))

    def v0_learning_search(self, data):
        self.send_json(_v01.search_learning_entries(data))

    def v0_decision(self, data):
        self.send_json(_v01.create_decision(data))

    def v0_forecast(self, data):
        self.send_json(_v01.create_forecast(data))

    def v0_reasoning_trace(self, data):
        self.send_json(_v01.create_reasoning_trace(data))

    def v0_review(self, data):
        self.send_json(_v01.review(data))

    def v0_feedback(self, data):
        self.send_json(_v01.feedback(data))

    def v0_learning_entry(self, data):
        self.send_json(_v01.learning_entry(data))

    def v0_trading_replay(self, data):
        replay_result = _v01.trading_replay(data)
        if self._coerce_bool_flag(data.get('summary_only', '')):
            self.send_json(replay_result.get("replay_summary", {}))
            return
        self.send_json(replay_result)

    def v0_trading_a_share_tdx_quote_snapshot(self, data=None):
        self.send_json(_v01.trading_a_share_tdx_quote_snapshot(data or {}))

    def v0_trading_a_share_tencent_qt_realtime_snapshot(self, data=None):
        self.send_json(_v01.trading_a_share_tencent_qt_realtime_snapshot(data or {}))

    def v0_trading_a_share_workbuddy_context_snapshot(self, data=None):
        self.send_json(_v01.trading_a_share_workbuddy_context_snapshot(data or {}))

    def v0_trading_a_share_realtime_crosscheck_summary(self, data=None):
        self.send_json(_v01.trading_a_share_realtime_crosscheck_summary(data or {}))

    def v0_trading_replay_history_summary(self, data=None):
        data = data or {}
        limit = data.get('limit', 10)
        strategy_name = data.get('strategy_name', '')
        if isinstance(limit, list):
            limit = limit[0] if limit else 10
        if isinstance(strategy_name, list):
            strategy_name = strategy_name[0] if strategy_name else ''
        self.send_json(_v01.trading_replay_history_summary({
            "limit": int(limit),
            "strategy_name": strategy_name,
        }))

    def v0_trading_research_queue_evidence_gap_summary(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        self.send_json(_v01.trading_research_queue_evidence_gap_summary({
            "candidate_slug": candidate_slug,
        }))

    def v0_trading_research_queue_consistency_diagnostics_summary(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        self.send_json(_v01.trading_research_queue_consistency_diagnostics_summary({
            "candidate_slug": candidate_slug,
        }))

    def v0_trading_research_queue_readiness_summary(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        self.send_json(_v01.trading_research_queue_readiness_summary({
            "candidate_slug": candidate_slug,
        }))

    def v0_trading_research_queue_approval_summary(self, data=None):
        data = data or {}
        limit = data.get('limit', 5)
        candidate_slug = data.get('candidate_slug', '')
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        self.send_json(_v01.trading_research_queue_approval_summary({
            "limit": int(limit),
            "candidate_slug": candidate_slug,
        }))

    def v0_trading_research_queue_approval_signals(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        min_approvals = data.get('min_approvals', 1)
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        if isinstance(min_approvals, list):
            min_approvals = min_approvals[0] if min_approvals else 1
        self.send_json(_v01.trading_research_queue_approval_signals({
            "candidate_slug": candidate_slug,
            "min_approvals": int(min_approvals),
        }))

    def v0_trading_research_queue_watchlist(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        min_approvals = data.get('min_approvals', 1)
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        if isinstance(min_approvals, list):
            min_approvals = min_approvals[0] if min_approvals else 1
        self.send_json(_v01.trading_research_queue_watchlist({
            "candidate_slug": candidate_slug,
            "min_approvals": int(min_approvals),
        }))

    def v0_trading_research_queue_review_agenda(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        min_approvals = data.get('min_approvals', 1)
        top_limit = data.get('top_limit', 3)
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        if isinstance(min_approvals, list):
            min_approvals = min_approvals[0] if min_approvals else 1
        if isinstance(top_limit, list):
            top_limit = top_limit[0] if top_limit else 3
        self.send_json(_v01.trading_research_queue_review_agenda({
            "candidate_slug": candidate_slug,
            "min_approvals": int(min_approvals),
            "top_limit": int(top_limit),
        }))

    def v0_trading_research_queue_next_validation_slice(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        min_approvals = data.get('min_approvals', 1)
        top_limit = data.get('top_limit', 3)
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        if isinstance(min_approvals, list):
            min_approvals = min_approvals[0] if min_approvals else 1
        if isinstance(top_limit, list):
            top_limit = top_limit[0] if top_limit else 3
        self.send_json(_v01.trading_research_queue_next_validation_slice({
            "candidate_slug": candidate_slug,
            "min_approvals": int(min_approvals),
            "top_limit": int(top_limit),
        }))

    def v0_trading_research_queue_run_next_validation_slice(self, data=None):
        data = data or {}
        self.send_json(_v01.trading_research_queue_run_next_validation_slice(data))

    def v0_trading_research_queue_latest_validation_summary(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        min_approvals = data.get('min_approvals', 1)
        top_limit = data.get('top_limit', 3)
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        if isinstance(min_approvals, list):
            min_approvals = min_approvals[0] if min_approvals else 1
        if isinstance(top_limit, list):
            top_limit = top_limit[0] if top_limit else 3
        self.send_json(_v01.trading_research_queue_latest_validation_summary({
            "candidate_slug": candidate_slug,
            "min_approvals": int(min_approvals),
            "top_limit": int(top_limit),
        }))

    def v0_trading_research_queue_sync_bulletin_from_latest_validation(self, data=None):
        data = data or {}
        candidate_slug = data.get('candidate_slug', '')
        min_approvals = data.get('min_approvals', 1)
        top_limit = data.get('top_limit', 3)
        if isinstance(candidate_slug, list):
            candidate_slug = candidate_slug[0] if candidate_slug else ''
        if isinstance(min_approvals, list):
            min_approvals = min_approvals[0] if min_approvals else 1
        if isinstance(top_limit, list):
            top_limit = top_limit[0] if top_limit else 3
        self.send_json(_v01.trading_research_queue_sync_bulletin_from_latest_validation({
            "candidate_slug": candidate_slug,
            "min_approvals": int(min_approvals),
            "top_limit": int(top_limit),
        }))

    def v0_trading_research_queue_approve(self, data=None):
        data = data or {}
        self.send_json(_v01.trading_confirm_research_queue_manual_approval(data))

    def v0_status(self, data=None):
        self.send_json(_v01.status())

    def v0_board_status(self, data=None):
        self.send_json(_v01.board_status())

    def v0_board_update(self, data):
        self.send_json(_v01.board_update(data))

    def v0_evolution_log(self, data=None):
        params = data or {}
        limit = params.get('limit', [20])
        if isinstance(limit, list):
            limit = limit[0] if limit else 20
        self.send_json(_v01.evolution_log(int(limit)))

    def v0_learning_summary(self, data=None):
        params = data or {}
        limit = params.get('limit', [5])
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        self.send_json(_v01.learning_summary({"limit": int(limit)}))

    def v0_feedback_summary(self, data=None):
        params = data or {}
        limit = params.get('limit', [5]) if isinstance(params, dict) else [5]
        target_type = params.get('target_type', ['']) if isinstance(params, dict) else ['']
        target_id = params.get('target_id', ['']) if isinstance(params, dict) else ['']
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        if isinstance(target_type, list):
            target_type = target_type[0] if target_type else ''
        if isinstance(target_id, list):
            target_id = target_id[0] if target_id else ''
        self.send_json(_v01.feedback_summary({
            "limit": int(limit),
            "target_type": target_type,
            "target_id": target_id,
        }))

    def v0_feedback_memory_candidates(self, data=None):
        params = data or {}
        limit = params.get('limit', [5]) if isinstance(params, dict) else [5]
        min_count = params.get('min_count', [2]) if isinstance(params, dict) else [2]
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        if isinstance(min_count, list):
            min_count = min_count[0] if min_count else 2
        self.send_json(_v01.feedback_memory_candidates({
            "limit": int(limit),
            "min_count": int(min_count),
        }))

    def v0_unified_memory_review_queue(self, data=None):
        params = data or {}
        limit = params.get('limit', [10]) if isinstance(params, dict) else [10]
        min_count = params.get('min_count', [2]) if isinstance(params, dict) else [2]
        profile = params.get('profile', ['legacy-first']) if isinstance(params, dict) else ['legacy-first']
        if isinstance(limit, list):
            limit = limit[0] if limit else 10
        if isinstance(min_count, list):
            min_count = min_count[0] if min_count else 2
        if isinstance(profile, list):
            profile = profile[0] if profile else 'legacy-first'
        self.send_json(_v01.unified_memory_review_queue({
            "limit": int(limit),
            "min_count": int(min_count),
            "profile": profile,
        }))

    def v0_unified_memory_review_confirm(self, data=None):
        self.send_json(_v01.confirm_unified_memory_review_item(data or {}))

    def v0_unified_memory_review_summary(self, data=None):
        params = data or {}
        limit = params.get('limit', [5]) if isinstance(params, dict) else [5]
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        self.send_json(_v01.unified_memory_review_summary({"limit": int(limit)}))

    def v0_unified_memory_review_signals(self, data=None):
        params = data or {}
        min_confirmations = params.get('min_confirmations', [2]) if isinstance(params, dict) else [2]
        if isinstance(min_confirmations, list):
            min_confirmations = min_confirmations[0] if min_confirmations else 2
        self.send_json(_v01.unified_memory_review_signals({"min_confirmations": int(min_confirmations)}))

    def v0_unified_memory_review_ranking_suggestions(self, data=None):
        params = data or {}
        min_confirmations = params.get('min_confirmations', [2]) if isinstance(params, dict) else [2]
        profile = params.get('profile', ['legacy-first']) if isinstance(params, dict) else ['legacy-first']
        if isinstance(min_confirmations, list):
            min_confirmations = min_confirmations[0] if min_confirmations else 2
        if isinstance(profile, list):
            profile = profile[0] if profile else 'legacy-first'
        self.send_json(_v01.unified_memory_review_ranking_suggestions({
            "min_confirmations": int(min_confirmations),
            "profile": profile,
        }))

    def v0_unified_memory_review_ranking_diff(self, data=None):
        params = data or {}
        limit = params.get('limit', [10]) if isinstance(params, dict) else [10]
        min_confirmations = params.get('min_confirmations', [2]) if isinstance(params, dict) else [2]
        profile = params.get('profile', ['legacy-first']) if isinstance(params, dict) else ['legacy-first']
        if isinstance(limit, list):
            limit = limit[0] if limit else 10
        if isinstance(min_confirmations, list):
            min_confirmations = min_confirmations[0] if min_confirmations else 2
        if isinstance(profile, list):
            profile = profile[0] if profile else 'legacy-first'
        self.send_json(_v01.unified_memory_review_ranking_diff({
            "limit": int(limit),
            "min_confirmations": int(min_confirmations),
            "profile": profile,
        }))

    def v0_unified_memory_review_ranking_diff_confirm(self, data=None):
        self.send_json(_v01.confirm_unified_memory_review_ranking_diff_item(data or {}))

    def v0_unified_memory_review_ranking_diff_summary(self, data=None):
        params = data or {}
        limit = params.get('limit', [5]) if isinstance(params, dict) else [5]
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        self.send_json(_v01.unified_memory_review_ranking_diff_summary({"limit": int(limit)}))

    def v0_unified_memory_review_ranking_diff_signals(self, data=None):
        params = data or {}
        min_confirmations = params.get('min_confirmations', [2]) if isinstance(params, dict) else [2]
        if isinstance(min_confirmations, list):
            min_confirmations = min_confirmations[0] if min_confirmations else 2
        self.send_json(_v01.unified_memory_review_ranking_diff_signals({"min_confirmations": int(min_confirmations)}))

    def v0_unified_memory_review_ranking_policy_suggestions(self, data=None):
        params = data or {}
        min_confirmations = params.get('min_confirmations', [2]) if isinstance(params, dict) else [2]
        profile = params.get('profile', ['legacy-first']) if isinstance(params, dict) else ['legacy-first']
        if isinstance(min_confirmations, list):
            min_confirmations = min_confirmations[0] if min_confirmations else 2
        if isinstance(profile, list):
            profile = profile[0] if profile else 'legacy-first'
        self.send_json(_v01.unified_memory_review_ranking_policy_suggestions({
            "min_confirmations": int(min_confirmations),
            "profile": profile,
        }))

    def v0_unified_memory_review_ranking_policy_approve(self, data=None):
        self.send_json(_v01.confirm_unified_memory_review_ranking_policy_suggestion(data or {}))

    def v0_unified_memory_review_ranking_policy_approval_summary(self, data=None):
        params = data or {}
        limit = params.get('limit', [5]) if isinstance(params, dict) else [5]
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        self.send_json(_v01.unified_memory_review_ranking_policy_approval_summary({"limit": int(limit)}))

    def v0_unified_memory_review_ranking_policy_approval_signals(self, data=None):
        params = data or {}
        min_confirmations = params.get('min_confirmations', [2]) if isinstance(params, dict) else [2]
        if isinstance(min_confirmations, list):
            min_confirmations = min_confirmations[0] if min_confirmations else 2
        self.send_json(_v01.unified_memory_review_ranking_policy_approval_signals({"min_confirmations": int(min_confirmations)}))

    def v0_unified_memory_review_ranking_policy_change_candidates(self, data=None):
        params = data or {}
        min_confirmations = params.get('min_confirmations', [2]) if isinstance(params, dict) else [2]
        profile = params.get('profile', ['legacy-first']) if isinstance(params, dict) else ['legacy-first']
        if isinstance(min_confirmations, list):
            min_confirmations = min_confirmations[0] if min_confirmations else 2
        if isinstance(profile, list):
            profile = profile[0] if profile else 'legacy-first'
        self.send_json(_v01.unified_memory_review_ranking_policy_change_candidates({
            "min_confirmations": int(min_confirmations),
            "profile": profile,
        }))

    def v0_unified_memory_review_ranking_policy_change_candidate_approve(self, data=None):
        self.send_json(_v01.confirm_unified_memory_review_ranking_policy_change_candidate(data or {}))

    def v0_unified_memory_review_ranking_policy_change_candidate_approval_summary(self, data=None):
        params = data or {}
        limit = params.get('limit', [5]) if isinstance(params, dict) else [5]
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        self.send_json(_v01.unified_memory_review_ranking_policy_change_candidate_approval_summary({"limit": int(limit)}))

    def v0_learning_inspect(self, data=None):
        params = data or {}
        learning_entry_id = params.get('learning_entry_id', [''])
        if isinstance(learning_entry_id, list):
            learning_entry_id = learning_entry_id[0] if learning_entry_id else ''
        self.send_json(_v01.inspect_learning_entry({"learning_entry_id": learning_entry_id}))

    def v0_learning_chains(self, data=None):
        params = data or {}
        limit = params.get('limit', [5])
        min_count = params.get('min_count', [2])
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        if isinstance(min_count, list):
            min_count = min_count[0] if min_count else 2
        self.send_json(_v01.learning_chains({"limit": int(limit), "min_count": int(min_count)}))

    def v0_learning_apply(self, data=None):
        params = data or {}
        limit = params.get('limit', [5])
        min_count = params.get('min_count', [2])
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        if isinstance(min_count, list):
            min_count = min_count[0] if min_count else 2
        self.send_json(_v01.apply_learning_chains({"limit": int(limit), "min_count": int(min_count)}))

    def v0_legacy_lessons_map(self, data=None):
        self.send_json(_v01.legacy_lessons_mapping(data or {}))

    def v0_legacy_decision_view(self, data=None):
        params = data or {}
        view = params.get('view', ['all']) if isinstance(params, dict) else ['all']
        if isinstance(view, list):
            view = view[0] if view else 'all'
        profile = params.get('profile', ['legacy-first']) if isinstance(params, dict) else ['legacy-first']
        if isinstance(profile, list):
            profile = profile[0] if profile else 'legacy-first'
        left_profile = params.get('left_profile', ['legacy-first']) if isinstance(params, dict) else ['legacy-first']
        right_profile = params.get('right_profile', ['pair-first']) if isinstance(params, dict) else ['pair-first']
        if isinstance(left_profile, list):
            left_profile = left_profile[0] if left_profile else 'legacy-first'
        if isinstance(right_profile, list):
            right_profile = right_profile[0] if right_profile else 'pair-first'
        self.send_json(_v01.legacy_memory_decision_view({
            "view": view,
            "profile": profile,
            "left_profile": left_profile,
            "right_profile": right_profile,
        }))

    def v0_legacy_action_confirm(self, data=None):
        self.send_json(_v01.confirm_legacy_memory_action(data or {}))

    def v0_legacy_action_summary(self, data=None):
        params = data or {}
        limit = params.get('limit', [5]) if isinstance(params, dict) else [5]
        if isinstance(limit, list):
            limit = limit[0] if limit else 5
        self.send_json(_v01.legacy_memory_action_summary({"limit": int(limit)}))

    def v0_atom_writeback(self, data=None):
        params = data or {}
        atom_id = params.get('atom_id', [''])
        if isinstance(atom_id, list):
            atom_id = atom_id[0] if atom_id else ''
        self.send_json(_v01.inspect_atom_writeback({"atom_id": atom_id}))

    def v0_writeback_overview(self, data=None):
        params = data or {}
        limit = params.get('limit', [10])
        if isinstance(limit, list):
            limit = limit[0] if limit else 10
        self.send_json(_v01.writeback_overview({"limit": int(limit)}))

    def v0_writeback_snapshot(self, data=None):
        params = data or {}
        limit = params.get('limit', [10])
        name = params.get('name', [''])
        if isinstance(limit, list):
            limit = limit[0] if limit else 10
        if isinstance(name, list):
            name = name[0] if name else ''
        self.send_json(_v01.capture_writeback_snapshot({"limit": int(limit), "name": name}))

    def v0_writeback_compare(self, data=None):
        params = data or {}
        limit = params.get('limit', [10])
        snapshot_id = params.get('snapshot_id', [''])
        if isinstance(limit, list):
            limit = limit[0] if limit else 10
        if isinstance(snapshot_id, list):
            snapshot_id = snapshot_id[0] if snapshot_id else ''
        self.send_json(_v01.compare_writeback_snapshot({"limit": int(limit), "snapshot_id": snapshot_id}))

def main():
    port = 8766
    for d in [DATA, DATA/'pending', APP, ROOT/'imports', ROOT/'exports']: d.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(('0.0.0.0', port), SecondBrainHandler)
    print(f'[Second Brain] v5-clean ready at http://localhost:{port}')
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nStopped.'); server.shutdown()

if __name__ == '__main__': main()
