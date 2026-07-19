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

# 认知知识管理系统 (2026-07-06)
from core.cognitive_memory_system import CognitiveMemorySystem, get_cognitive_memory_system
from core.zettelkasten import Zettelkasten, get_zettelkasten
from core.para_system import PARASystem
from core.spaced_repetition import SpacedRepetition
from core.decision_tree import DecisionTreeEngine
from core.cross_domain_associator import CrossDomainAssociator
from core.meta_cognition import MetaCognitionEngine
from core.knowledge_evolver import KnowledgeEvolver

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / 'data'
APP = ROOT / 'app'

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
_health = MemoryHealthManager(_graph, _memory, DATA)
_fast_index = FastIndex(_graph, _digester, DATA)
_human = HumanThinkingEngine(_graph, _memory, _health, DATA)
_verify = SelfVerify(_graph, _memory, _health, DATA)
_actr = ACTRMemory(_graph, DATA)
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

# 认知知识管理系统实例
_cms = get_cognitive_memory_system()
_zettel = get_zettelkasten()
_para = PARASystem()
_spaced = SpacedRepetition()
_decision_tree = DecisionTreeEngine()
_cross_domain = CrossDomainAssociator()
_meta = MetaCognitionEngine()
_evolver = KnowledgeEvolver()
