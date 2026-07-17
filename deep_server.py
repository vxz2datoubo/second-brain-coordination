# -*- coding: utf-8 -*-
"""
deep_server.py - Deep Learning Enhanced Second Brain Server v6.1
==============================================================
Enhanced with:
1. Episodic Memory System - Experience-based trading memory
2. Continual Learning Engine - Overcome catastrophic forgetting
3. Trading Deep Bridge - Intelligent trading signal generation

Port: 8767

Usage:
  python deep_server.py
"""

import json, math, os, sys, uuid
from collections import deque
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Core modules
from core.graph import KnowledgeGraph
from core.digest import TextDigester
from core.tfidf import SearchEngine
from core.memory import MemoryEngine
from core.evolve import EvolutionEngine
from core.cognitive_engine import CognitiveEngine
from core.reason_engine import ReasonEngine
from core.super_cognitive import SuperCognitiveEngine

# Deep Learning modules
from core.neural_memory import NeuralMemoryNetwork, get_neural_memory
from core.differentiable_reasoner import DifferentiableReasoner, get_differentiable_reasoner
from core.meta_learning import MetaLearningDecision, get_meta_learner
from core.deep_memory_integration import UnifiedBrain, get_unified_brain
from core.episodic_memory import EpisodicMemory, get_episodic_memory, Episode
from core.continual_learning import ContinualLearningEngine, get_continual_learner, LearningTask
from core.trading_deep_bridge import TradingDeepBridge, MarketContext, get_trading_bridge

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / 'data'
APP = ROOT / 'app'

# Initialize all modules
_graph = KnowledgeGraph(DATA)
_digester = TextDigester(_graph, DATA)
_search = SearchEngine(_graph, _digester)
_memory = MemoryEngine(DATA)
_evolve = EvolutionEngine(_graph, _memory, _digester, _search, DATA)
_cognitive = CognitiveEngine(_graph, _memory, _digester, _search, None, None, None, DATA)
_reason = ReasonEngine(_graph, DATA)
_game_theory = None
_detective = None
_news_verifier = None
_scenario = None
_anti_gaming = None
_super_cog = SuperCognitiveEngine(_graph, _game_theory, _detective, _news_verifier, _scenario, _anti_gaming, _cognitive, _reason, DATA)

# Deep Learning modules
_neural_memory = get_neural_memory(DATA)
_differentiable_reasoner = get_differentiable_reasoner(_graph, DATA)
_meta_learner = get_meta_learner(DATA)
_unified_brain = get_unified_brain(_graph, DATA)
_episodic_memory = get_episodic_memory(DATA)
_continual_learner = get_continual_learner(DATA)
_trading_bridge = get_trading_bridge(_graph, DATA)


def json_load(path):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}


class DeepSecondBrainHandler(SimpleHTTPRequestHandler):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP), **kwargs)
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    
    def send_err(self, msg, code=400):
        self.send_json({"error": True, "message": msg}, code)
    
    def read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0: return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except: return {}
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/api/stats": self.stats()
        elif p.path == "/api/deep/stats": self.deep_stats()
        elif p.path == "/api/deep/memory/stats": self.neural_memory_stats()
        elif p.path == "/api/deep/reasoner/stats": self.reasoner_stats()
        elif p.path == "/api/deep/meta/stats": self.meta_stats()
        elif p.path == "/api/deep/episodic/stats": self.episodic_stats()
        elif p.path == "/api/deep/continual/stats": self.continual_stats()
        elif p.path == "/api/deep/trading/insights": self.trading_insights()
        else: super().do_GET()
    
    def do_POST(self):
        p = urlparse(self.path)
        data = self.read_body()
        self._last_data = data
        routes = self.get_routes()
        if p.path in routes:
            try: routes[p.path]()
            except Exception as e: self.send_err(str(e), 500)
        else: self.send_err("Unknown: " + p.path, 404)
    
    def get_routes(self):
        return {
            # ===== Deep Brain Core =====
            "/api/deep/think": lambda: self.deep_think(self._last_data),
            "/api/deep/decide": lambda: self.deep_decide(self._last_data),
            "/api/deep/learn": lambda: self.deep_learn(self._last_data),
            "/api/deep/consolidate": lambda: self.deep_consolidate(self._last_data),
            
            # ===== Neural Memory =====
            "/api/deep/memory/write": lambda: self.neural_write(self._last_data),
            "/api/deep/memory/read": lambda: self.neural_read(self._last_data),
            "/api/deep/memory/associate": lambda: self.neural_associate(self._last_data),
            
            # ===== Differentiable Reasoner =====
            "/api/deep/reason": lambda: self.dl_reason(self._last_data),
            "/api/deep/reason/add-rule": lambda: self.add_rule(self._last_data),
            
            # ===== Meta Learning =====
            "/api/deep/meta/record": lambda: self.meta_record(self._last_data),
            "/api/deep/meta/decide": lambda: self.meta_decide(self._last_data),
            
            # ===== Episodic Memory =====
            "/api/deep/episodic/record": lambda: self.episodic_record(self._last_data),
            "/api/deep/episodic/retrieve": lambda: self.episodic_retrieve(self._last_data),
            "/api/deep/episodic/advice": lambda: self.episodic_advice(self._last_data),
            "/api/deep/episodic/update-outcome": lambda: self.episodic_update_outcome(self._last_data),
            
            # ===== Continual Learning =====
            "/api/deep/continual/learn": lambda: self.continual_learn(self._last_data),
            "/api/deep/continual/consolidate": lambda: self.continual_consolidate(self._last_data),
            "/api/deep/continual/report": lambda: self.continual_report(self._last_data),
            
            # ===== Trading Bridge =====
            "/api/deep/trading/signal": lambda: self.trading_signal(self._last_data),
            "/api/deep/trading/record": lambda: self.trading_record(self._last_data),
            
            # ===== Original APIs =====
            "/api/retrieve/search": lambda: self.search(self._last_data),
            "/api/cognitive/think": lambda: self.cognitive_think(self._last_data),
        }
    
    # ===== Deep Brain Core =====
    
    def deep_think(self, data):
        result = _unified_brain.think(data.get("query", ""), data.get("context"))
        self.send_json(result)
    
    def deep_decide(self, data):
        decision = _meta_learner.adapt_to_context(data)
        self.send_json(decision)
    
    def deep_learn(self, data):
        result = _unified_brain.learn_from_feedback(
            data.get("chain_id", ""),
            data.get("outcome", 0),
            data.get("correct", False)
        )
        self.send_json(result)
    
    def deep_consolidate(self, data):
        result = _unified_brain.consolidate()
        self.send_json(result)
    
    # ===== Neural Memory =====
    
    def neural_write(self, data):
        memory_id = _neural_memory.write(
            content=data.get("content", ""),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            source=data.get("source", "api")
        )
        self.send_json({"success": True, "memory_id": memory_id})
    
    def neural_read(self, data):
        results = _neural_memory.read(data.get("query", ""), data.get("top_k", 5))
        self.send_json({"results": results})
    
    def neural_associate(self, data):
        _neural_memory.associate(data.get("memory_id1", ""), data.get("memory_id2", ""))
        self.send_json({"success": True})
    
    def neural_memory_stats(self, data=None):
        self.send_json(_neural_memory.get_stats())
    
    # ===== Differentiable Reasoner =====
    
    def dl_reason(self, data):
        result = _differentiable_reasoner.infer(
            facts=data.get("facts", {}),
            target=data.get("target"),
            mode=data.get("mode", "forward")
        )
        self.send_json(result)
    
    def add_rule(self, data):
        from core.differentiable_reasoner import Rule
        rule = Rule(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            antecedent=data.get("antecedent", []),
            consequent=data.get("consequent", ""),
            confidence=data.get("confidence", 0.8)
        )
        _differentiable_reasoner.add_rule(rule)
        self.send_json({"success": True, "rule_id": rule.id})
    
    def reasoner_stats(self, data=None):
        self.send_json(_differentiable_reasoner.get_stats())
    
    # ===== Meta Learning =====
    
    def meta_record(self, data):
        task_id = _meta_learner.record_task(
            market_condition=data.get("market_condition", "range"),
            stock_type=data.get("stock_type", "tech"),
            action=data.get("action", "hold"),
            outcome=data.get("outcome", 0)
        )
        self.send_json({"success": True, "task_id": task_id})
    
    def meta_decide(self, data):
        decision = _meta_learner.decide(
            market_condition=data.get("market_condition", "range"),
            stock_type=data.get("stock_type", "tech"),
            context=data.get("context")
        )
        self.send_json(decision)
    
    def meta_stats(self, data=None):
        self.send_json(_meta_learner.get_stats())
    
    # ===== Episodic Memory =====
    
    def episodic_record(self, data):
        episode = Episode(
            id="",
            timestamp=datetime.now().isoformat(),
            situation_type=data.get("situation_type", "range"),
            market_trend=data.get("market_trend", "neutral"),
            volatility=data.get("volatility", "medium"),
            price_change=data.get("price_change", 0.0),
            volume_ratio=data.get("volume_ratio", 1.0),
            sector_performance=data.get("sector_performance", 0.0),
            action=data.get("action", "hold"),
            position_size=data.get("position_size", 0.5),
            confidence=data.get("confidence", 0.5),
            stock_code=data.get("stock_code", ""),
            stock_name=data.get("stock_name", ""),
            tags=data.get("tags", [])
        )
        episode_id = _episodic_memory.record(episode)
        self.send_json({"success": True, "episode_id": episode_id})
    
    def episodic_retrieve(self, data):
        results = _episodic_memory.retrieve(data.get("situation", {}), data.get("top_k", 5))
        self.send_json({"results": results})
    
    def episodic_advice(self, data):
        advice = _episodic_memory.get_action_advice(data.get("situation", {}))
        self.send_json(advice)
    
    def episodic_update_outcome(self, data):
        _episodic_memory.update_outcome(
            data.get("episode_id", ""),
            data.get("outcome", 0),
            data.get("reflection", ""),
            data.get("lessons", [])
        )
        self.send_json({"success": True})
    
    def episodic_stats(self, data=None):
        self.send_json(_episodic_memory.get_stats())
    
    # ===== Continual Learning =====
    
    def continual_learn(self, data):
        task = LearningTask(
            id="",
            name=data.get("name", "task_" + datetime.now().strftime("%Y%m%d%H%M%S")),
            timestamp=datetime.now().isoformat(),
            category=data.get("category", "general"),
            samples=data.get("samples", []),
            labels=data.get("labels", []),
            before_performance=0.5,
            after_performance=0.5
        )
        result = _continual_learner.learn_task(task)
        self.send_json(result)
    
    def continual_consolidate(self, data):
        result = _continual_learner.consolidate_knowledge()
        self.send_json(result)
    
    def continual_report(self, data):
        report = _continual_learner.generate_report()
        self.send_json({"report": report})
    
    def continual_stats(self, data=None):
        self.send_json(_continual_learner.get_stats())
    
    # ===== Trading Bridge =====
    
    def trading_signal(self, data):
        context = MarketContext(
            stock_code=data.get("stock_code", ""),
            stock_name=data.get("stock_name", ""),
            current_price=float(data.get("current_price", 0)),
            change_pct=float(data.get("change_pct", 0)),
            volume_ratio=float(data.get("volume_ratio", 1.0)),
            avg_volume=float(data.get("avg_volume", 1)),
            market_trend=data.get("market_trend", "neutral"),
            volatility=data.get("volatility", "medium"),
            market_sentiment=data.get("market_sentiment", "neutral"),
            time_window=data.get("time_window", "T2"),
            recent_news=data.get("recent_news", []),
            position=data.get("position")
        )
        signal = _trading_bridge.generate_signal(context)
        self.send_json({
            "action": signal.action,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "risk_level": signal.risk_level,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "signal_sources": signal.signal_sources,
            "historical_win_rate": signal.historical_win_rate
        })
    
    def trading_record(self, data):
        context = MarketContext(
            stock_code=data.get("stock_code", ""),
            stock_name=data.get("stock_name", ""),
            current_price=float(data.get("current_price", 0)),
            change_pct=float(data.get("change_pct", 0)),
            volume_ratio=float(data.get("volume_ratio", 1.0)),
            avg_volume=float(data.get("avg_volume", 1)),
            market_trend=data.get("market_trend", "neutral"),
            volatility=data.get("volatility", "medium"),
            time_window=data.get("time_window", "T2"),
            position=data.get("position")
        )
        episode_id = _trading_bridge.record_decision(
            context,
            None,
            data.get("outcome"),
            data.get("reflection", "")
        )
        self.send_json({"success": True, "episode_id": episode_id})
    
    def trading_insights(self, data=None):
        self.send_json(_trading_bridge.get_trading_insights())
    
    # ===== Original APIs =====
    
    def search(self, data):
        results = _search.search(data.get("query", ""), data.get("top_k", 10))
        self.send_json({"results": results})
    
    def cognitive_think(self, data):
        sig = _cognitive.think(
            data.get("topic", ""),
            data.get("context", {}),
            data.get("mode", "deliberate"),
            int(data.get("depth", 3))
        )
        self.send_json({"confidence": sig.confidence, "decision": sig.decision, "warnings": sig.warnings})
    
    def stats(self, data=None):
        _graph.reload()
        s = _graph.get_stats()
        self.send_json({"knowledge": {"nodes": s["total_nodes"], "edges": s["total_edges"]}, "server": {"version": "v6.1-deep-learning"}})


def main():
    port = 8767
    for d in [DATA, APP]: d.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("0.0.0.0", port), DeepSecondBrainHandler)
    print(f"[Deep Second Brain] v6.1 ready at http://localhost:{port}")
    print("=" * 60)
    print("Deep Learning APIs:")
    print("  /api/deep/think         - Unified deep thinking")
    print("  /api/deep/trading/signal - Trading signal generation")
    print("  /api/deep/episodic/*    - Episodic memory")
    print("  /api/deep/continual/*  - Continual learning")
    print("=" * 60)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStopped."); server.shutdown()


if __name__ == "__main__": main()
