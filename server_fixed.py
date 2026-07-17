"""
第二大脑 (The Second Brain) - 个人 AI 知识库系统
本地 HTTP 服务器 - Python stdlib only, port 8766

核心模块: core/graph.py (知识图谱) / core/digest.py (知识消化)
"""
import json
import math
import os
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---- 核心模块 ----
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
from core.mind_models import MentalModelLibrary\r\nfrom core.super_strategy import SuperStrategyEngine\r\n
# ---- 路径配置 ----
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"
APP = ROOT / "app"

# ---- 核心实例 ----
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
_mental_models = MentalModelLibrary(DATA)\n_super_strategy = SuperStrategyEngine(_graph, _mental_models, _game_theory, _detective, _scenario, _anti_gaming, _cognitive, _reason, DATA)\n

def json_load(path: Path) -> dict:

    try:
with open(path, "r", encoding="utf-8") as f:
return json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
return {}


def json_save(path: Path, data: dict):

    path.parent.mkdir(parents=True, exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
json.dump(data, f, ensure_ascii=False, indent=2)


# ---- HTTP 请求处理器 ----
class SecondBrainHandler(SimpleHTTPRequestHandler):
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

def read_body(self) -> dict:

        try:
length = int(self.headers.get("Content-Length", 0))
if length == 0:
return {}
body = self.rfile.read(length).decode("utf-8")
return json.loads(body) if body else {}
except (json.JSONDecodeError, ValueError):
return {}

def log_message(self, format, *args):

        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

def do_OPTIONS(self):

        self.send_response(200)
self.send_header("Access-Control-Allow-Origin", "*")
self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
self.send_header("Access-Control-Allow-Headers", "Content-Type")
self.end_headers()

    # ========== GET ==========
def do_GET(self):

         import sys
sys.stderr.write("do_GET called\n")
sys.stderr.flush()
p = urlparse(self.path)
path = p.path
sys.stderr.write(f"path={path}\n")
sys.stderr.flush()
        
        # Trading Brain API
if path == "/api/trading/stats":
sys.stderr.write("MATCH: /api/trading/stats\n")
sys.stderr.flush()
self.trading_stats()
elif path == "/api/trading/rules":
self.trading_rules()
elif path == "/api/trading/lessons":
self.trading_lessons()
elif path == "/api/trading/recent-logs":
self.trading_recent_logs()
elif path == "/api/trading/regime":
params = parse_qs(p.query)
self.trading_regime(params)
elif path == "/api/stats":
self.stats()
elif path == "/api/knowledge-graph":
self.send_json(_graph.get_full_graph())
else:
super().do_GET()

def do_POST(self):

        p = urlparse(self.path)
path, data = p.path, self.read_body()
r = {
"/api/digest/text": lambda: self.digest_text(data),
"/api/digest/file": lambda: self.digest_file(data),
"/api/digest/url": lambda: self.digest_url(data),
"/api/digest/batch-text": lambda: self.digest_batch(data),
"/api/retrieve/search": lambda: self.search(data),
"/api/retrieve/ask": lambda: self.ask(data),
"/api/finance/consult": lambda: self.finance_consult(data),
"/api/finance/backtest": lambda: self.finance_backtest(data),
"/api/finance/hot-themes": lambda: self.finance_hot_themes(data),
"/api/sync/scan": lambda: self.sync_scan(data),
"/api/sync/ingest": lambda: self.sync_ingest(data),
"/api/sync/watch-memory": lambda: self.sync_memory(data),
"/api/memory/record": lambda: self.memory_record(data),
"/api/memory/feedback": lambda: self.memory_feedback(data),
"/api/memory/consolidate": lambda: self.send_json(_memory.consolidate()),
"/api/evolve/evaluate": lambda: self.send_json(_evolve.evaluate()),
"/api/evolve/apply-rules": lambda: self.send_json(_evolve.apply_rules()),
"/api/evolve/auto-fix": lambda: self.send_json(_evolve.auto_fix()),
"/api/events/record": lambda: self.record_event(data),
"/api/export/report": lambda: self.export_framework(data),
"/api/export/framework": lambda: self.export_framework(data),
"/api/health/prune": lambda: self.health_prune(data),
"/api/health/reinforce": lambda: self.health_reinforce(data),
"/api/health/detect-contradictions": lambda: self.health_detect(data),
"/api/health/touch": lambda: self.health_touch(data),
"/api/fast-index/rebuild": lambda: self.fast_index_rebuild(),
"/api/fast-index/search": lambda: self.fast_search(data),
"/api/fast-index/hybrid": lambda: self.fast_hybrid(data),
"/api/fast-index/rerank": lambda: self.fast_rerank(data),
"/api/human/review": lambda: self.human_review(data),
"/api/human/detect-chunks": lambda: self.human_detect_chunks(),
"/api/human/search": lambda: self.human_search(data),
"/api/human/associate": lambda: self.human_associate(data),
"/api/human/tag-emotion": lambda: self.human_tag_emotion(data),
"/api/verify/consistency": lambda: self.verify_consistency(data),
"/api/verify/full": lambda: self.verify_full(data),
"/api/verify/cross": lambda: self.verify_cross(data),
"/api/verify/chain": lambda: self.verify_chain(data),
"/api/verify/all": lambda: self.verify_all_nodes(data),
"/api/verify/record-decision": lambda: self.verify_record_decision(data),
"/api/cognitive/think": lambda: self.cognitive_think(data),
"/api/cognitive/decision": lambda: self.cognitive_decision(data),
"/api/cognitive/outcome": lambda: self.cognitive_outcome(data),
"/api/cognitive/stats": lambda: self.cognitive_stats(),
"/api/reason/cross-domain": lambda: self.reason_cross_domain(data),
"/api/reason/knowledge": lambda: self.reason_knowledge(data),
"/api/maibot/think": lambda: self.maibot_think(data),
"/api/maibot/sync": lambda: self.maibot_sync(),
"/api/maibot/feedback": lambda: self.maibot_feedback(data),
"/api/maibot/status": lambda: self.maibot_status(),
"/api/super/think": lambda: self.super_think(data),
"/api/super/decision": lambda: self.super_decision(data),
"/api/super/record-outcome": lambda: self.super_record_outcome(data),
"/api/super/stats": lambda: self.super_stats(),
"/api/game/analyze": lambda: self.game_analyze(data),
"/api/game/think-enemy": lambda: self.game_think_enemy(data),
"/api/game/multi-step": lambda: self.game_multi_step(data),
"/api/game/advantage": lambda: self.game_advantage(data),
"/api/game/stats": lambda: self.game_stats(),
"/api/detective/investigate": lambda: self.detective_investigate(data),
"/api/detective/washout-risk": lambda: self.detective_washout_risk(data),
"/api/detective/breakout": lambda: self.detective_breakout(data),
"/api/detective/stats": lambda: self.detective_stats(),
"/api/news/verify": lambda: self.news_verify(data),
"/api/news/batch": lambda: self.news_batch(data),
"/api/news/stats": lambda: self.news_stats(),
"/api/scenario/plan": lambda: self.scenario_plan(data),
"/api/scenario/decision-tree": lambda: self.scenario_decision_tree(data),
"/api/scenario/monte-carlo": lambda: self.scenario_monte_carlo(data),
"/api/scenario/stats": lambda: self.scenario_stats(),
"/api/anti-gaming/detect": lambda: self.anti_gaming_detect(data),
"/api/atomic/extract": lambda: self.atomic_extract(data),
"/api/atomic/query": lambda: self.atomic_query(data),
"/api/atomic/infer": lambda: self.atomic_infer(data),
"/api/atomic/stats": lambda: self.atomic_stats(),
"/api/anti-gaming/stats": lambda: self.anti_gaming_stats(),

"/api/super/think": lambda: self.super_think(data),
"/api/super/decision": lambda: self.super_decision(data),
"/api/super/record-outcome": lambda: self.super_record_outcome(data),
"/api/super/stats": lambda: self.super_stats(),

            # ========== Game Theory API ==========
"/api/game/analyze": lambda: self.game_analyze(data),
"/api/game/think-enemy": lambda: self.game_think_enemy(data),
"/api/game/multi-step": lambda: self.game_multi_step(data),
"/api/game/advantage": lambda: self.game_advantage(data),
"/api/game/stats": lambda: self.game_stats(),

            # ========== Market Detective API ==========
"/api/detective/investigate": lambda: self.detective_investigate(data),
"/api/detective/washout-risk": lambda: self.detective_washout_risk(data),
"/api/detective/breakout": lambda: self.detective_breakout(data),
"/api/detective/stats": lambda: self.detective_stats(),

            # ========== News Verification API ==========
"/api/news/verify": lambda: self.news_verify(data),
"/api/news/batch": lambda: self.news_batch(data),
"/api/news/stats": lambda: self.news_stats(),

            # ========== Scenario Planner API ==========
"/api/scenario/plan": lambda: self.scenario_plan(data),
"/api/scenario/decision-tree": lambda: self.scenario_decision_tree(data),
"/api/scenario/monte-carlo": lambda: self.scenario_monte_carlo(data),
"/api/scenario/stats": lambda: self.scenario_stats(),

            # ========== Anti Gaming API ==========
"/api/anti-gaming/detect": lambda: self.anti_gaming_detect(data),
"/api/atomic/extract": lambda: self.atomic_extract(data),
"/api/atomic/query": lambda: self.atomic_query(data),
"/api/atomic/infer": lambda: self.atomic_infer(data),
"/api/atomic/stats": lambda: self.atomic_stats(),
"/api/anti-gaming/stats": lambda: self.anti_gaming_stats(),"/api/verify/audit-decision": lambda: self.verify_audit_decision(data),
"/api/verify/truth-discovery": lambda: self.verify_truth_discovery(),
"/api/trading/check": lambda: self.trading_check(data),
"/api/trading/add-log": lambda: self.trading_add_log(data),
"/api/trading/signal-context": lambda: self.trading_signal_context(data),
"/api/trading/add-lesson": lambda: self.trading_add_lesson(data),
"/api/actr/access": lambda: self.actr_access(data),
"/api/actr/simulate-decay": lambda: self.actr_simulate_decay(data),
}

print(f"[DEBUG] path={path}, r_keys={list(r.keys())}")
if path in r:
try: r[path]()
except Exception as e: self.send_err(str(e), 500)
else:
self.send_err(f"Unknown: {path}", 404)

    # ---------- Digest ----------
def digest_text(self, data):

        text = data.get("text", "").strip()
if not text: return self.send_err("text required")
node = _digester.digest(text, data.get("title", ""), data.get("source", "manual"))
_search.rebuild()
_health.register(node["id"], node.get("importance", 3))
_fast_index.add_document(node["id"], node.get("title", ""), node.get("content", ""))
self.send_json({"success": True, "node": node})

def digest_batch(self, data):

        items = data.get("items", [])
if not items: return self.send_err("items required")
results = []
for item in items:
t = item.get("text", "").strip()
if not t: continue
node = _digester.digest(t, item.get("title", ""), item.get("source", "batch"))
results.append(node)
_health.register(node["id"], node.get("importance", 3))
_fast_index.add_document(node["id"], node.get("title", ""), node.get("content", ""))
_search.rebuild()
self.send_json({"success": True, "nodes": results, "count": len(results)})

def digest_file(self, data):

        file_path = data.get("path", "").strip()
if not file_path: return self.send_err("path required")
node = _file_digester.digest_file(file_path)
if not node: return self.send_err("unsupported or missing file", 400)
_search.rebuild()
_health.register(node["id"], node.get("importance", 3))
_fast_index.add_document(node["id"], node.get("title", ""), node.get("content", ""))
self.send_json({"success": True, "node": node})

def digest_url(self, data):

        url = data.get("url", "").strip()
if not url: return self.send_err("url required")
node = _url_digester.digest_url(url)
_search.rebuild()
_health.register(node["id"], node.get("importance", 3))
_fast_index.add_document(node["id"], node.get("title", ""), node.get("content", ""))
self.send_json({"success": True, "node": node})

def stats(self):

        _graph.reload()
s = _graph.get_stats()
mem = json_load(DATA / "memory-index.json")
sync = json_load(DATA / "sync-state.json")
self.send_json({
"knowledge": {"total_nodes": s["total_nodes"], "total_edges": s["total_edges"], "last_updated": s["last_updated"]},
"memory": {"total_interactions": mem["meta"]["total_interactions"], "total_feedback": mem["meta"]["total_feedback"], "good_rate": mem["meta"]["good_rate"]},
"sync": {"total_synced": sync.get("total_nodes_synced", 0), "last_sync": sync.get("last_session_sync", "")},
"server": {"uptime": datetime.now().isoformat(), "version": "MVP-0.1.0"}
})

def categories(self):

        ci = json_load(DATA / "category-index.json")
_graph.reload()
sd = _graph.get_stats().get("categories", {})
cats = {}
for k, v in ci.get("categories", {}).items():
cats[k] = {"name": v["name"], "keywords": v["keywords"], "count": sd.get(k, 0)}
self.send_json({"categories": cats, "default": ci.get("default_category", "life")})

def get_graph(self, params):

        nid = params.get("node_id", [None])[0]
depth = int(params.get("depth", [1])[0])
cat = params.get("category", [None])[0]
tag = params.get("tag", [None])[0]
_graph.reload()
if nid: self.send_json(_graph.get_neighbors(nid, depth))
elif cat: self.send_json(_graph.filter_by_category(cat))
elif tag: self.send_json(_graph.filter_by_tag(tag))
else: self.send_json(_graph.get_full_graph())

def associate(self, params):

        nid = params.get("node_id", [None])[0]
if not nid: return self.send_err("node_id required")
_graph.reload()
self.send_json(_graph.get_neighbors(nid, 2))

    # ---------- Search ----------
def search(self, data):

        q = data.get("query", "").strip()
if not q: return self.send_err("query required")
cat = data.get("category") or None  # 空串当 None 处理
results = _search.search(q, data.get("top_k", 10), category=cat)
self.send_json({"query": q, "category": cat, "results": results, "count": len(results)})

def ask(self, data):

        q = data.get("question", "").strip()
if not q: return self.send_err("question required")
results = _search.search(q, 5)
ctx = "\n\n".join(f"[{i+1}] {r['title']}\n{r['summary']}" for i, r in enumerate(results))
up = load_user_profile()
self.send_json({
"question": q, "relevant_nodes": results, "context": ctx,
"user_profile": {"output_style": up.get("preferences", {}).get("output_style", "structured_table"), "preferred_categories": up.get("preferences", {}).get("preferred_categories", [])},
"suggested_prompt": f"基于以下知识库内容回答问题:\n\n{ctx}\n\n用户问题: {q}\n\n请用简洁直接的方式回答。"
})

    # ---------- Finance ----------
def finance_consult(self, data):

        """股票/金融交易前检查。只做概率与风控辅助，不做确定性预测。"""
target = data.get("target", "").strip()
thesis = data.get("thesis", "").strip()
action = data.get("action", "").strip()
horizon = data.get("horizon", "").strip()
stop_loss = data.get("stop_loss", "").strip()
max_loss = data.get("max_loss", "").strip()
position = data.get("position", "").strip()

if not target:
return self.send_err("target required")

query = " ".join(x for x in [target, thesis, action, horizon, stop_loss, max_loss, position] if x)
finance_hits = []
for cat in ("finance-market", "finance-a-share", "finance-macro", "finance-sector",
"finance-company", "finance-technical", "finance-risk", "finance-review"):
finance_hits.extend(_search.search(query, 3, category=cat))

lesson_query = f"{query} 红线 教训 追高 补仓 满仓 止损 仓位"
raw_lessons = _search.search(lesson_query, 12, category="decision-lessons")
finance_lesson_terms = [
"交易", "股票", "股市", "A股", "买入", "卖出", "仓位", "止损",
"止盈", "追高", "补仓", "满仓", "重仓", "回撤", "消息源", "小作文"
]
lesson_hits = [
hit for hit in raw_lessons
if hit.get("source") == "finance-seed-2026-06-20"
or any(term in (hit.get("title", "") + hit.get("summary", "")) for term in finance_lesson_terms)
][:6]

missing = []
if not thesis:
missing.append("买入/卖出理由")
if not horizon:
missing.append("计划周期")
if not stop_loss:
missing.append("止损或失效条件")
if not max_loss:
missing.append("最大可承受亏损")
if not position:
missing.append("仓位计划")

risk_flags = []
text = query.lower()
flag_words = [
("追高", "出现追高/FOMO风险"),
("补仓", "补仓必须基于新证据，不能只为摊低成本"),
("满仓", "满仓/重仓前必须通过极端情景检查"),
("重仓", "重仓前必须确认回撤可承受"),
("小作文", "单一消息源风险"),
("消息", "消息驱动交易需要交叉验证"),
]
for word, flag in flag_words:
if word.lower() in text and flag not in risk_flags:
risk_flags.append(flag)

if lesson_hits:
risk_flags.append(f"命中 {len(lesson_hits)} 条决策教训，交易前必须阅读")
if missing:
verdict = "先补计划"
elif len(risk_flags) >= 3:
verdict = "回避或只观察"
elif len(risk_flags) >= 1:
verdict = "小仓试错"
else:
verdict = "观察，按触发条件执行"

checklist = [
"至少写出三条反方证据",
"确认买入理由、止损条件、卖出条件彼此一致",
"用最大可承受亏损反推仓位，不用信心决定仓位",
"把乐观、中性、悲观三种剧本写清楚",
"交易后用 /api/verify/audit-decision 或复盘节点记录结果",
]

decision_id = None
if data.get("record", False):
decision_id = _verify.record_decision(
"stock-trade-consult",
{
"target": target,
"thesis": thesis,
"action": action,
"horizon": horizon,
"stop_loss": stop_loss,
"max_loss": max_loss,
"position": position,
"missing": missing,
"risk_flags": risk_flags,
},
["回避", "观察", "小仓试错", "按计划执行"],
verdict,
"第二大脑金融专题交易前检查"
)

self.send_json({
"target": target,
"verdict": verdict,
"missing": missing,
"risk_flags": risk_flags,
"checklist": checklist,
"related_finance": finance_hits[:8],
"matched_lessons": lesson_hits[:6],
"decision_id": decision_id,
"disclaimer": "仅作为个人知识库与风控辅助，不构成投资建议或确定性预测。"
})

def finance_backtest(self, data):

        """POST /api/finance/backtest — CSV 行情回测。"""
csv_path = data.get("csv_path", "").strip()
if not csv_path:
return self.send_err("csv_path required")
try:
bars = load_price_csv(csv_path)
strategy = data.get("strategy", "sma_cross")
initial_cash = float(data.get("initial_cash", 100000))
fee_rate = float(data.get("fee_rate", 0.0003))
if strategy == "optimize":
result = optimize_backtests(bars, initial_cash=initial_cash, fee_rate=fee_rate)
else:
result = run_backtest_strategy(bars, strategy=strategy, initial_cash=initial_cash, fee_rate=fee_rate, **data)
except Exception as e:
return self.send_err(f"{type(e).__name__}: {e}", 400)
self.send_json(result)

def finance_hot_themes(self, data):

        """POST /api/finance/hot-themes — 从文本/知识库估算题材热度。"""
items = data.get("items", [])
if not items:
_graph.reload()
finance_categories = {
"finance-market", "finance-a-share", "finance-macro", "finance-sector",
"finance-company", "finance-technical", "finance-risk", "finance-review",
}
items = []
for node in _graph.data.get("nodes", {}).values():
if node.get("category") in finance_categories:
items.append({
"title": node.get("title", ""),
"text": node.get("content", "") or node.get("summary", ""),
"date": node.get("created_at", ""),
"source": node.get("source", "knowledge-graph"),
})
if not isinstance(items, list):
return self.send_err("items must be a list")
result = analyze_hot_themes(items, top_k=int(data.get("top_k", 10)))
self.send_json(result)

    # ---------- Sync ----------
def sync_scan(self, data):

        new = _syncer.scan(data.get("since", None))
self.send_json({"new_sessions": new, "count": len(new)})

def sync_ingest(self, data):

        ids = data.get("session_ids", [])
if not ids: return self.send_err("session_ids required")
added = _syncer.ingest_sessions(ids)
_search.rebuild()
self.send_json({"success": True, "nodes_added": added})

def sync_memory(self, data):

        added = _syncer.sync_memory_files()
_search.rebuild()
self.send_json({"success": True, "nodes_added": added})

def sync_sources(self):

        self.send_json(_syncer.get_sources())

    # ---------- Memory ----------
def memory_record(self, data):

        iid = _memory.record(
data.get("user_input", ""), data.get("response", ""),
data.get("context_ids", []), data.get("session_id", "")
)
self.send_json({"success": True, "interaction_id": iid})

def memory_feedback(self, data):

        iid = data.get("interaction_id", "")
if not iid: return self.send_err("interaction_id required")
result = _memory.record_feedback(
iid, data.get("rating", "neutral"),
data.get("accepted", True), data.get("correction", ""),
data.get("chosen", ""), data.get("rejected", []),
data.get("feedback_text", "")
)
if result:
self.send_json({"success": True, "interaction": result["id"]})
else:
self.send_err("interaction not found", 404)

def memory_recent(self, params):

        limit = int(params.get("limit", [20])[0])
mem = json_load(DATA / "memory-index.json")
recent = mem.get("interactions", [])[-limit:]
recent.reverse()
self.send_json({"interactions": recent, "total": len(mem.get("interactions", []))})

def memory_context(self, params):

        query = params.get("query", [""])[0]
limit = int(params.get("limit", [5])[0])
ctx = _memory.get_context(query, limit)
self.send_json({"context": ctx})

    # ---------- Events ----------
def record_event(self, data):

        text = data.get("text", "").strip()
if not text: return self.send_err("text required")
events = _events.record(text)
self.send_json({"success": True, "events": events, "count": len(events)})

def serve_event_check(self, params):

        date = params.get("date", [None])[0]
events = _events.check(date)
conflicts = _events.conflicts()
self.send_json({"date": date or datetime.now().strftime("%Y-%m-%d"), "events": events, "conflicts": conflicts})

def serve_event_upcoming(self, params):

        days = int(params.get("days", [7])[0])
self.send_json({"upcoming": _events.upcoming(days), "conflicts": _events.conflicts()})

    # ---------- Memory Health ----------
def health_prune(self, data):

        dry_run = data.get("dry_run", True)
result = _health.prune(dry_run=dry_run)
self.send_json(result)

def health_reinforce(self, data):

        nid = data.get("node_id", "")
if not nid: return self.send_err("node_id required")
_health.reinforce(nid, data.get("positive", True))
self.send_json({"success": True, "node_id": nid})

def health_detect(self, data):

        sim = float(data.get("min_similarity", 0.4))
contras = _health.detect_contradictions(sim)
self.send_json({"contradictions": contras, "count": len(contras)})

def health_touch(self, data):

        node_ids = data.get("node_ids", [])
_health.touch_by_query(node_ids)
self.send_json({"success": True, "touched": len(node_ids)})

    # ---------- Fast Index ----------
def fast_index_rebuild(self):

        _fast_index.rebuild()
self.send_json({"success": True, "stats": _fast_index.stats()})

def fast_search(self, data):

        q = data.get("query", "").strip()
if not q: return self.send_err("query required")
results = _fast_index.search(q, data.get("top_k", 10), data.get("category"))
        # 记录访问
_health.touch_by_query([r["id"] for r in results])
self.send_json({"query": q, "results": results, "count": len(results)})

def autocomplete(self, params):

        prefix = params.get("prefix", [""])[0]
limit = int(params.get("limit", [10])[0])
words = _fast_index.autocomplete(prefix, limit)
self.send_json({"prefix": prefix, "suggestions": words})

def fast_hybrid(self, data):

        """v2.1: 4路信号 RRF 混合检索"""
q = data.get("query", "").strip()
if not q: return self.send_err("query required")
results = _fast_index.search_hybrid(q, data.get("top_k", 10), data.get("category"))
_health.touch_by_query([r["id"] for r in results])
self.send_json({"query": q, "expanded_tokens": _fast_index.expand_query(q), "results": results, "count": len(results), "mode": "hybrid-rrf"})

def fast_rerank(self, data):

        """v2.1: 交叉信号重排序"""
candidates = data.get("candidates", [])
query = data.get("query", "")
top_k = data.get("top_k", 5)
if not candidates:
results = _fast_index.search_hybrid(query, top_k=20)
results = _fast_index.rerank(query, results, top_k=top_k)
else:
results = _fast_index.rerank(query, candidates, top_k=top_k)
self.send_json({"query": query, "results": results, "count": len(results), "mode": "rerank"})

    # ---------- Human Thinking ----------
def human_review(self, data):

        nid = data.get("node_id", "")
quality = int(data.get("quality", 3))
if not nid: return self.send_err("node_id required")
card = _human.sm2_review(nid, quality)
self.send_json({"success": True, "node_id": nid, "card": card})

def human_detect_chunks(self):

        chunks = _human.detect_chunks()
self.send_json({"chunks": chunks, "count": len(chunks)})

def human_search(self, data):

        q = data.get("query", "").strip()
if not q: return self.send_err("query required")
        # 先基础检索
base = _fast_index.search(q, data.get("top_k", 15), data.get("category"))
        # 注入人类认知层
seed = [_human.data["session_memory"][-1]] if _human.data["session_memory"] else []
results = _human.human_like_search(q, base, seed_nodes=seed)
        # 记录访问
_health.touch_by_query([r["id"] for r in results])
        # 加入当前会话
if results:
_human.add_to_session(results[0]["id"])
self.send_json({"query": q, "results": results, "count": len(results), "mode": "human_like"})

def human_associate(self, data):

        node_ids = data.get("node_ids", [])
if not node_ids: return self.send_err("node_ids required")
results = _human.associative_recall(node_ids, data.get("max_depth", 3))
self.send_json({"seed": node_ids, "associations": results, "count": len(results)})

def human_tag_emotion(self, data):

        nid = data.get("node_id", "")
text = data.get("text", "")
if not nid or not text: return self.send_err("node_id and text required")
_human.tag_emotion(nid, text)
self.send_json({"success": True, "emotion": _human.data["emotion_tags"].get(nid, {})})

    # ---------- Self Verify ----------
def verify_consistency(self, data):

        claim = data.get("claim", "")
context_ids = data.get("context_node_ids", [])
if not claim: return self.send_err("claim required")
result = _verify.check_consistency(claim, context_ids)
self.send_json(result)

def verify_full(self, data):

        claim = data.get("claim", "")
context_ids = data.get("context_node_ids", [])
report = _verify.full_verify(claim, context_ids)
self.send_json(report)

def verify_cross(self, data):

        nid = data.get("node_id", "")
if not nid: return self.send_err("node_id required")
result = _verify.cross_validate(nid)
self.send_json(result)

def verify_chain(self, data):

        chain = data.get("chain", [])
if not chain: return self.send_err("chain required")
result = _verify.verify_reasoning_chain(chain)
self.send_json(result)

def verify_all_nodes(self, data):

        report = _verify.verify_all_nodes()
self.send_json(report)

def verify_record_decision(self, data):

        did = _verify.record_decision(
data.get("decision_type", "general"),
data.get("context", {}),
data.get("options", []),
data.get("chosen", ""),
data.get("reasoning", "")
)
self.send_json({"success": True, "decision_id": did})

def verify_audit_decision(self, data):

        did = data.get("decision_id", "")
if not did: return self.send_err("decision_id required")
_verify.audit_decision(did, data.get("outcome", ""), data.get("was_correct", False))
self.send_json({"success": True, "decision_id": did})

def verify_truth_discovery(self):

        """POST /api/verify/truth-discovery — 迭代式真相发现"""
report = _verify.iterative_truth_discovery()
self.send_json(report)

def actr_access(self, data):

        """POST /api/actr/access — 记录记忆访问"""
nids = data.get("node_ids", [])
if not nids:
return self.send_err("node_ids required")
_actr.batch_access(nids)
self.send_json({"accessed": len(nids)})

def actr_simulate_decay(self, data):

        """POST /api/actr/simulate-decay — 模拟未来衰减"""
nid = data.get("node_id", "")
if not nid:
return self.send_err("node_id required")
days = data.get("days", [1, 7, 30, 90])
result = _actr.simulate_decay(nid, days)
self.send_json({"node_id": nid, "decay": result})

    # ---------- Schema ----------
def serve_schema(self):

        """返回 Schema 约束文件 (Karpathy模式)"""
schema_path = DATA / "schema.md"
if schema_path.exists():
text = schema_path.read_text(encoding="utf-8")
self.send_json({"format": "markdown", "content": text, "source": "schema.md"})
else:
self.send_err("schema not found", 404)

def serve_index(self, params):

        """渐进披露索引 — Karpathy 模式: L1→L4 四级"""
level = int(params.get("level", [1])[0])
category = params.get("category", [None])[0]
_graph.reload()
nodes = list(_graph.data["nodes"].values())
if category:
nodes = [n for n in nodes if n.get("category") == category]
nodes.sort(key=lambda n: n.get("importance", 1), reverse=True)
items = []
for n in nodes:
item = {"id": n["id"], "title": n.get("title",""), "category": _digester.get_category_name(n.get("category","life")), "importance": n.get("importance",1)}
if level >= 2: item["summary"] = n.get("summary","")[:100]; item["tags"] = n.get("tags",[])[:5]; item["source"] = n.get("source","")
if level >= 3: item["content_preview"] = n.get("content","")[:200]
if level >= 4: item["content"] = n.get("content",""); item["created_at"] = n.get("created_at","")
items.append(item)
tokens = sum(len(str(i))//3 for i in items)
self.send_json({"level": level, "total_nodes": len(items), "estimated_tokens": tokens, "index": items})

    # ---------- Export ----------
def export_framework(self, data):

        """导出知识框架: 选中节点 → Markdown/Markmap 知识框架
集成 knowledge-framework-builder 模式
"""
node_ids = data.get("node_ids", [])
category = data.get("category", None)
fmt = data.get("format", "md")

_graph.reload()

        # 选择节点
if node_ids:
nodes = []
for nid in node_ids:
node = _graph.get_node(nid)
if node:
nodes.append(node)
elif category:
nodes = list(_graph.data["nodes"].values())
nodes = [n for n in nodes if n.get("category") == category]
else:
nodes = list(_graph.data["nodes"].values())

if not nodes:
return self.send_err("no nodes selected")

        # 构建知识框架 Markdown
framework = self._build_framework(nodes, fmt)
self.send_json({"format": fmt, "framework": framework, "node_count": len(nodes)})

def _build_framework(self, nodes: list[dict], fmt: str) -> str:

        """构建知识框架文档"""
        # 按分类分组
from collections import defaultdict
by_cat = defaultdict(list)
for n in nodes:
cat_name = _digester.get_category_name(n.get("category", "life"))
by_cat[cat_name].append(n)

lines = []
lines.append(f"# 第二大脑知识框架")
lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  节点数: {len(nodes)}  |  分类: {len(by_cat)}")
lines.append("")

        # 框架总览
lines.append("## 框架总览")
lines.append("")
for cat_name, cat_nodes in sorted(by_cat.items()):
lines.append(f"### {cat_name} ({len(cat_nodes)}个节点)")
for n in sorted(cat_nodes, key=lambda x: x.get("importance", 1), reverse=True):
star = "⭐" if n.get("importance", 4) >= 4 else ""
lines.append(f"- {star} **{n.get('title', '')}**")
if n.get("summary"):
lines.append(f"  > {n['summary'][:100]}")
lines.append("")

        # 重点知识讲解
important = [n for n in nodes if n.get("importance", 1) >= 4]
if important:
lines.append("## 重点知识讲解")
lines.append("")
for i, n in enumerate(important[:10], 1):
lines.append(f"### {i}. {n.get('title', '')}")
cat_name = _digester.get_category_name(n.get("category", "life"))
lines.append(f"分类: {cat_name}  |  来源: {n.get('source', '')}  |  标签: {', '.join(n.get('tags', [])[:5])}")
lines.append("")
lines.append(n.get("content", ""))
lines.append("")
lines.append(f"**核心要点**: {n.get('summary', '')}")
lines.append("")

        # 知识点关联
_graph.reload()
edges = []
node_ids = {n["id"] for n in nodes}
for eid, e in _graph.data.get("edges", {}).items():
if e["source_id"] in node_ids or e["target_id"] in node_ids:
src = _graph.get_node(e["source_id"])
tgt = _graph.get_node(e["target_id"])
if src and tgt:
edges.append((src, tgt, e))

if edges:
lines.append("## 知识点关联图")
lines.append("")
lines.append("| 关系 | 知识点A | 知识点B | 强度 |")
lines.append("|------|---------|---------|------|")
for src, tgt, e in edges[:30]:
lines.append(f"| {e.get('relation','related_to')} | {src.get('title','')[:30]} | {tgt.get('title','')[:30]} | {e.get('strength',0.5):.2f} |")
lines.append("")

        # 延伸学习
tags = []
for n in nodes:
tags.extend(n.get("tags", [])[:3])
from collections import Counter
top_tags = Counter(tags).most_common(5)
if top_tags:
lines.append("## 延伸学习建议")
lines.append("")
for i, (tag, count) in enumerate(top_tags, 1):
lines.append(f"{i}. **深入探索 [{tag}]**: 此标签在 {count} 个节点中出现，可进一步研究相关主题")
lines.append("")

return "\n".join(lines)



    # ========== Trading Brain ==========
def trading_rules(self):

        """GET /api/trading/rules — 获取交易规则"""
result = _trading_brain.get_rules()
self.send_json(result)

def trading_lessons(self):

        """GET /api/trading/lessons — 获取历史教训"""
stock = parse_qs(urlparse(self.path).query).get("stock", [None])[0]
lessons = _trading_brain.get_lessons(stock)
self.send_json({"lessons": lessons, "count": len(lessons)})

def trading_stats(self):

        """GET /api/trading/stats — 获取交易知识库统计"""
stats = _trading_brain.get_stats()
self.send_json(stats)

def trading_recent_logs(self):

        """GET /api/trading/recent-logs — 获取近期交易日志"""
days = int(parse_qs(urlparse(self.path).query).get("days", ["7"])[0])
logs = _trading_brain.get_recent_logs(days)
self.send_json({"logs": logs, "count": len(logs)})

def trading_regime(self, params):

        """GET /api/trading/regime — 判断市场状态"""
index_change = float(params.get("index_change", ["0"])[0])
up_count = int(params.get("up_count", ["0"])[0])
down_count = int(params.get("down_count", ["0"])[0])
volatility = params.get("volatility", ["medium"])[0]
        
result = _trading_brain.judge_market_regime({
"index_change": index_change,
"up_count": up_count,
"down_count": down_count,
"volatility": volatility,
})
self.send_json(result)

def trading_check(self, data):

        """POST /api/trading/check — 决策前检查"""
decision = data.get("decision", "")
context = data.get("context", {})
result = _trading_brain.pre_decision_check(decision, context)
self.send_json(result)

def trading_add_log(self, data):

        """POST /api/trading/add-log — 添加每日日志"""
result = _trading_brain.add_daily_log(data)
self.send_json(result)

def trading_signal_context(self, data):

        """POST /api/trading/signal-context — 获取信号上下文"""
stock = data.get("stock", "300418")
result = _trading_brain.get_signal_context(stock)
self.send_json(result)

def trading_add_lesson(self, data):

        """POST /api/trading/add-lesson — 添加教训"""
lesson = data.get("lesson", "")
date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
lesson_type = data.get("type", "negative")
        
if not lesson:
return self.send_err("lesson required")
        
        # 追加到lessons.md
try:
with open(_trading_brain.lessons_path, "a", encoding="utf-8") as f:
if lesson_type == "negative":
f.write(f"\n\n## 教训: {lesson} ({date})\n")
else:
f.write(f"\n\n## 正向经验: {lesson} ({date})\n")
self.send_json({"success": True, "date": date})
except Exception as e:
self.send_err(str(e), 500)

def cognitive_think(self, data):

            topic = data.get("topic", "")
context = data.get("context", {})
mode = data.get("mode", "deliberate")
depth = int(data.get("depth", 3))
        
if not topic:
return self.send_err("topic required")
        
signal = _cognitive.think(topic, context, mode, depth)
self.send_json({
"id": signal.id,
"topic": signal.topic,
"confidence": signal.confidence,
"decision": signal.decision,
"warnings": signal.warnings,
"reasoning_chain": signal.reasoning_chain,
"associated_nodes": [{"id": n.get("id"), "title": n.get("title", ""), "activation": n.get("activation", 0)} for n in signal.associated_nodes[:5]],
"blind_spot_detected": signal.blind_spot_detected,
"reasoning_gaps": signal.reasoning_gaps,
"formatted": _cognitive.format_think_output(signal)
})
    
def cognitive_decision(self, data):

            decision_type = data.get("type", "general")
context = data.get("context", {})
options = data.get("options", [])
reasoning = data.get("reasoning", "")
        
result = _cognitive.make_decision(decision_type, context, options, reasoning)
self.send_json(result)
    
def cognitive_outcome(self, data):

            decision_id = data.get("decision_id", "")
outcome = data.get("outcome", "")
was_correct = data.get("was_correct", False)
lessons = data.get("lessons", [])
        
if not decision_id:
return self.send_err("decision_id required")
        
result = _cognitive.record_outcome(decision_id, outcome, was_correct, lessons)
self.send_json(result)
    
def cognitive_stats(self):

            stats = _cognitive.get_cognition_stats()
stats["recent_decisions"] = _cognitive.get_recent_decisions(5)
stats["learned_rules"] = _cognitive.get_learned_rules()
stats["suggestions"] = _cognitive.suggest_improvements()
self.send_json(stats)
    
def reason_cross_domain(self, data):

            topic = data.get("topic", "")
context_nodes = data.get("context_nodes", [])
depth = int(data.get("depth", 3))
        
if not topic:
return self.send_err("topic required")
        
result = _reason.reason(topic, context_nodes, depth)
self.send_json({
"result": result,
"formatted": _reason.format_reasoning(result)
})
    
def reason_knowledge(self, data):

            node_id = data.get("node_id", "")
        
if not node_id:
return self.send_err("node_id required")
        
result = _reason.get_cross_domain_knowledge(node_id)
self.send_json(result)


            # ========== Super Cognitive API ==========

def super_think(self, data):

            situation = data.get("situation", "")
mode = data.get("mode", "deliberate")
depth = int(data.get("depth", 3))
            
            # 构造市场上下文
context = _super_cog.MarketContext(
stock=data.get("stock", ""),
current_price=float(data.get("current_price", 0)),
change_pct=float(data.get("change_pct", 0)),
volume=float(data.get("volume", 0)),
avg_volume=float(data.get("avg_volume", 1)),
market_trend=data.get("market_trend", "neutral"),
market_sentiment=data.get("market_sentiment", "neutral"),
volatility=data.get("volatility", "medium"),
recent_news=data.get("recent_news", [])
)
            
snapshot = _super_cog.think(situation, context, mode, depth)
self.send_json({
"snapshot_id": str(uuid.uuid4())[:8],
"situation": snapshot.situation,
"confidence": snapshot.confidence,
"final_judgment": snapshot.final_judgment,
"recommended_action": snapshot.recommended_action,
"questions": snapshot.questions,
"reasoning_chain": snapshot.reasoning_chain,
"warnings": snapshot.warnings,
"opportunities": snapshot.opportunities,
"alternatives": snapshot.alternatives,
"formatted": _super_cog.format_snapshot(snapshot)
})
        
def super_decision(self, data):

            decision_id = _super_cog.record_decision(
data.get("situation", ""),
data.get("action", ""),
_super_cog.MarketContext(
stock=data.get("stock", ""),
current_price=float(data.get("current_price", 0))
),
data.get("reasoning", "")
)
self.send_json({"decision_id": decision_id})
        
def super_record_outcome(self, data):

            _super_cog.record_outcome(
data.get("decision_id", ""),
data.get("outcome", ""),
data.get("was_correct", False),
data.get("lessons", [])
)
self.send_json({"success": True})
        
def super_stats(self):

            self.send_json(_super_cog.get_stats())

            # ========== Game Theory API ==========

def game_analyze(self, data):

            stock = data.get("stock", "")
price_data = data.get("price_data", {})
volume_data = data.get("volume_data", {})
news = data.get("news", [])
            
state = _game_theory.analyze_market_game(stock, price_data, volume_data, news)
self.send_json({
"game_type": state.detected_pattern,
"confidence": state.confidence,
"action": state.recommended_action,
"risk_signals": state.risk_signals,
"opportunities": state.opportunities,
"reasoning_chain": state.reasoning_chain,
"formatted": _game_theory.format_analysis(state)
})
        
def game_think_enemy(self, data):

            current_position = data.get("current_position", {})
market_state = data.get("market_state", {})
my_intent = data.get("my_intent", "")
            
result = _game_theory.think_like_enemy(current_position, market_state, my_intent)
self.send_json(result)
        
def game_multi_step(self, data):

            current_state = data.get("current_state", {})
num_steps = int(data.get("num_steps", 3))
            
result = _game_theory.multi_step_prediction(current_state, num_steps)
self.send_json(result)
        
def game_advantage(self, data):

            my_position = data.get("my_position", {})
market = data.get("market", {})
            
result = _game_theory.analyze_advantage(my_position, market)
self.send_json(result)
        
def game_stats(self):

            self.send_json(_game_theory.get_stats())

            # ========== Market Detective API ==========

def detective_investigate(self, data):

            stock = data.get("stock", "")
price_history = data.get("price_history", [])
volume_history = data.get("volume_history", [])
minute_data = data.get("minute_data", [])
            
report = _detective.investigate(stock, price_history, volume_history, minute_data)
self.send_json({
"has_mainforce": report.has_mainforce,
"confidence": report.confidence,
"mainforce_type": report.mainforce_type,
"verdict": report.verdict,
"evidence_chain": report.evidence_chain,
"risk_signals": report.risk_signals,
"opportunities": report.opportunities,
"formatted": _detective.format_report(report)
})
        
def detective_washout_risk(self, data):

            current_price = float(data.get("current_price", 0))
support_levels = [float(x) for x in data.get("support_levels", [])]
recent_lows = [float(x) for x in data.get("recent_lows", [])]
            
result = _detective.analyze_washout_risk(current_price, support_levels, recent_lows)
self.send_json(result)
        
def detective_breakout(self, data):

            price = float(data.get("price", 0))
resistance = float(data.get("resistance", 0))
volume_trend = data.get("volume_trend", "stable")
sentiment = data.get("market_sentiment", "neutral")
            
result = _detective.calculate_breakout_probability(price, resistance, volume_trend, sentiment)
self.send_json(result)
        
def detective_stats(self):

            self.send_json(_detective.get_stats())

            # ========== News Verification API ==========

def news_verify(self, data):

            news = data.get("news", {})
stock = data.get("stock", "")
price_data = data.get("price_data", {})
            
result = _news_verifier.verify(news, stock, price_data)
self.send_json({
"is_authentic": result.is_authentic,
"authenticity_score": result.authenticity_score,
"freshness": result.freshness,
"market_digested": result.market_digested,
"digestion_level": result.digestion_level,
"manipulation_suspect": result.manipulation_suspect,
"manipulation_score": result.manipulation_score,
"prior_leakage": result.prior_leakage,
"verdict": result.verdict,
"evidence_chain": result.evidence_chain,
"similar_history": result.similar_news_history,
"formatted": _news_verifier.format_verification(result, news)
})
        
def news_batch(self, data):

            news_list = data.get("news_list", [])
stock = data.get("stock", "")
            
results = _news_verifier.batch_verify(news_list, stock)
self.send_json({
"count": len(results),
"results": [
{
"verdict": r.verdict,
"authenticity": r.authenticity_score,
"manipulation": r.manipulation_score
}
for r in results
]
})
        
def news_stats(self):

            self.send_json(_news_verifier.get_stats())

            # ========== Scenario Planner API ==========

def scenario_plan(self, data):

            stock = data.get("stock", "")
current_price = float(data.get("current_price", 0))
market_state = data.get("market_state", {})
            
plan = _scenario.create_scenario_plan(stock, current_price, market_state)
self.send_json({
"scenarios": [
{"name": s.name, "prob": s.probability, "impact": s.impact}
for s in plan.scenarios
],
"strategy": plan.recommended_strategy,
"risk_limit": plan.risk_limit,
"formatted": _scenario.format_scenario_plan(plan)
})
        
def scenario_decision_tree(self, data):

            decision_points = data.get("decision_points", [])
current_state = data.get("current_state", {})
            
result = _scenario.analyze_decision_tree(decision_points, current_state)
self.send_json({
"expected_value": result.expected_value,
"best_option": result.best_option,
"risk_adjusted_score": result.risk_adjusted_score,
"options": result.options
})
        
def scenario_monte_carlo(self, data):

            initial_capital = float(data.get("initial_capital", 100000))
position_size = float(data.get("position_size", 0.5))
num_simulations = int(data.get("num_simulations", 1000))
time_horizon = int(data.get("time_horizon_days", 20))
            
result = _scenario.monte_carlo_simulation(
initial_capital, position_size, num_simulations, time_horizon
)
self.send_json({
"result": result,
"formatted": _scenario.format_monte_carlo(result)
})
        
def scenario_stats(self):

            self.send_json(_scenario.get_stats())

            # ========== Anti Gaming API ==========

def anti_gaming_detect(self, data):

            stock = data.get("stock", "")
price_history = data.get("price_history", [])
volume_history = data.get("volume_history", [])
minute_data = data.get("minute_data", [])
            
report = _anti_gaming.detect(stock, price_history, volume_history, minute_data)
self.send_json({
"is_gamed": report.is_gamed,
"confidence": report.confidence,
"survival_score": report.survival_score,
"patterns": [
{"type": p.pattern_type, "stage": p.stage, "risk": p.risk_level}
for p in report.patterns
],
"risk_signals": report.risk_signals,
"warnings": report.warnings,
"survival_tips": report.survival_tips,
"recommended_action": report.recommended_action,
"formatted": _anti_gaming.format_report(report, stock)
})
        
def anti_gaming_stats(self):

            self.send_json(_anti_gaming.get_stats())



def load_user_profile() -> dict:

    return json_load(DATA / "user-profile.json")


def main():

    port = 8766
for d in [DATA, DATA / "pending", APP, ROOT / "imports", ROOT / "exports"]:
d.mkdir(parents=True, exist_ok=True)
server = HTTPServer(("0.0.0.0", port), SecondBrainHandler)
print(f"[第二大脑] (The Second Brain) vMVP-0.1.0")
print(f"   地址: http://localhost:{port}")
print(f"   模块: graph.py ({len(open(__file__, encoding='utf-8').readlines())} 行 server) + digest.py")
print(f"   按 Ctrl+C 停止")
print("-" * 50)
try:
server.serve_forever()
except KeyboardInterrupt:
print("\n第二大脑已停止。")
server.shutdown()


if __name__ == "__main__":
main()




















