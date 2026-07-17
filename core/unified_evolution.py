#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二大脑 · 统一进化引擎 (Unified Evolution Engine) v3.0
═══════════════════════════════════════════════════════════

设计目标: 吞并 4 个旧进化系统，以一个统一 MAPE-K 飞轮 统领全局。

旧系统 → 新角色:
  daytrade_system/evo.py           → 数据层(SQLite schema 扩展)
  core/self_evolve.py              → 认知层(MAPE-K + OpMode + 9类问题)
  daytrade_system/evolution/       → 实验层(回测优化 → RollingValidator)
  core/evolve.py                   → 评估层(洞察生成 → LessonLearner)

学术基础 (7篇/体系):
  [1] MAPE-K Framework (IBM 2005, SEAMS 2015)
      → 核心架构: Monitor→Analyze→Plan→Execute→Knowledge 飞轮
  [2] Adaptive Data Flywheel (NeMo, 2025)
      → 每次循环丰富知识库→自增强循环
  [3] Grammatical Evolution Ensembles (2019, SciDir)
      → 惯性控制: 过度更新导致过度交易，需平衡适应频率
  [4] LLM-Guided Evolutionary Strategy (2025, A-share 2020-2024)
      → LLM引导语义交叉，无效策略减少83.5%，AER=12.3%
  [5] QuantEvolve (2025, OpenReview)
      → 质量-多样性优化 + 假设驱动多智能体策略生成
  [6] CGA-Agent (2025)
      → 30天滚动窗口重优化 + 动态参数调整
  [7] Q-learning + DE (2025, Wuxi China)
      → A股验证的自适应差分进化

统一 SQLite 架构 (12表):
  trades / daily_summary / factor_weights / param_evolution
  lessons / self_tests / sentiment_log / signal_history  ← 原 evo.py 8表
  + cognitive_events   ← 认知事件(原 self_evolve)
  + strategy_pool      ← 策略池(原 evolution/)
  + feedback_loop      ← MAPE-K飞轮状态
  + evolution_meta     ← 进化元数据(制度/模式/版本)
"""

import json, os, sys, sqlite3, time, math
from datetime import datetime, date, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from enum import IntEnum
from collections import defaultdict

# ═══════════════════════════════════════════════════════════
# 基础设置
# ═══════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).parent.parent
EVO_DIR = BASE_DIR / "data" / "evolution"
EVO_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(EVO_DIR / "unified_evo.db")


# ═══════════════════════════════════════════════════════════
# 0. OpMode — 6级运行模式 (继承 self_evolve)
# ═══════════════════════════════════════════════════════════

class OpMode(IntEnum):
    SAFETY = 0       # 安全只读: 仅报告
    OBSERVE = 1      # 观察: 记录日志
    DIAGNOSE = 2     # 诊断: 分析+报告
    ADVISE = 3       # 建议: 生成方案，需确认
    SEMI_AUTO = 4    # 半自动: 低风险自动
    FULL_AUTO = 5    # 全自动: 诊断+修复+验证+回滚


# ═══════════════════════════════════════════════════════════
# 1. UnifiedDB — 统一 SQLite 数据库 (12表)
# ═══════════════════════════════════════════════════════════

class UnifiedDB:
    """吞并 evo.py 的 DB 类，扩展为统一进化数据库。"""

    def __init__(self, db_path: str = DB_PATH):
        self.path = db_path
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.path) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.executescript("""
                -- 原 evo.py 8表 (保留不变)
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY, trade_date TEXT, stock_code TEXT,
                    stock_name TEXT, direction TEXT, price REAL, shares INTEGER,
                    amount REAL, pnl_pct REAL DEFAULT 0, signal_score REAL,
                    signal_reason TEXT, confidence TEXT, regime TEXT,
                    slot_id TEXT, created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS daily_summary (
                    id INTEGER PRIMARY KEY, trade_date TEXT UNIQUE,
                    total_trades INTEGER DEFAULT 0, successful_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0, kunlun_pnl REAL DEFAULT 0,
                    blue_pnl REAL DEFAULT 0, avg_signal_score REAL,
                    market_regime TEXT, notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS factor_weights (
                    id INTEGER PRIMARY KEY, stock_code TEXT,
                    f1 REAL, f2 REAL, f3 REAL, f4 REAL, f5 REAL, f6 REAL,
                    total_score REAL, effective_date TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS param_evolution (
                    id INTEGER PRIMARY KEY, evolution_date TEXT, stock_code TEXT,
                    param_name TEXT, old_value REAL, new_value REAL,
                    reason TEXT, correlation_change REAL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY, lesson_date TEXT, category TEXT,
                    title TEXT, content TEXT, stock_code TEXT, outcome TEXT,
                    pnl_impact REAL DEFAULT 0, verified INTEGER DEFAULT 0,
                    times_applied INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS self_tests (
                    id INTEGER PRIMARY KEY, test_date TEXT, test_type TEXT,
                    passed INTEGER, details TEXT, issues TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS sentiment_log (
                    id INTEGER PRIMARY KEY, log_time TEXT, stock_code TEXT,
                    sentiment_score REAL DEFAULT 0, news_count INTEGER DEFAULT 0,
                    sector_momentum REAL, related_news TEXT, action_taken TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY, signal_time TEXT, stock_code TEXT,
                    total_score REAL, sell_score REAL, buy_score REAL,
                    confidence TEXT, regime TEXT,
                    f1_score REAL, f2_score REAL, f3_score REAL,
                    f4_score REAL, f5_score REAL, f6_score REAL,
                    reason TEXT, action_taken TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- 新增 4表 (统一进化核心)
                CREATE TABLE IF NOT EXISTS cognitive_events (
                    id INTEGER PRIMARY KEY, event_time TEXT,
                    event_type TEXT,         -- insight/error/feedback/decision
                    category TEXT,           -- 9分类: intent_miss/late_action/...
                    severity TEXT,           -- critical/high/medium/low
                    source TEXT,             -- 来源: system-analysis/feedback_engine/...
                    description TEXT,        -- 事件描述
                    root_cause TEXT,         -- 根因分析
                    lesson_learned TEXT,     -- 学到的教训
                    applied_changes TEXT,    -- 已应用的变更 (JSON)
                    verified INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS strategy_pool (
                    id INTEGER PRIMARY KEY, strategy_id TEXT UNIQUE,
                    name TEXT, category TEXT,  -- 策略类型: entry/exit/sizing/risk
                    generation TEXT,           -- generation: 1/2/3...
                    fitness REAL,              -- 综合适应度
                    sharpe REAL, max_dd REAL,  -- 核心指标
                    params TEXT,               -- 参数 (JSON)
                    diversity_vector TEXT,     -- 多样性向量 (JSON, QuantEvolve)
                    is_active INTEGER DEFAULT 1,
                    retired_reason TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS feedback_loop (
                    id INTEGER PRIMARY KEY, loop_id TEXT UNIQUE,
                    phase TEXT,                -- monitor/analyze/plan/execute
                    status TEXT,               -- running/completed/failed
                    input_summary TEXT,        -- 输入摘要
                    output_summary TEXT,       -- 输出摘要
                    knowledge_gained TEXT,     -- 新增的知识
                    next_action TEXT,          -- 下一步行动
                    started_at TEXT, completed_at TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS evolution_meta (
                    id INTEGER PRIMARY KEY,
                    op_mode TEXT DEFAULT 'diagnose',
                    market_regime TEXT DEFAULT 'neutral',
                    engine_version TEXT DEFAULT '3.0',
                    last_flywheel_run TEXT,
                    total_loops INTEGER DEFAULT 0,
                    total_params_evolved INTEGER DEFAULT 0,
                    total_lessons_learned INTEGER DEFAULT 0,
                    total_strategies_generated INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                -- 索引
                CREATE INDEX IF NOT EXISTS idx_cog_type ON cognitive_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_cog_time ON cognitive_events(event_time);
                CREATE INDEX IF NOT EXISTS idx_strategy_active ON strategy_pool(is_active);
                CREATE INDEX IF NOT EXISTS idx_loop_phase ON feedback_loop(phase);

                -- 初始化元数据
                INSERT OR IGNORE INTO evolution_meta (id) VALUES (1);
            """)

    def execute(self, sql: str, params: tuple = ()):
        with sqlite3.connect(self.path) as c:
            return c.execute(sql, params)

    def query(self, sql: str, params: tuple = ()) -> list:
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute(sql, params)]

    def stats(self) -> dict:
        tables = ["trades", "daily_summary", "lessons", "self_tests",
                  "param_evolution", "cognitive_events", "strategy_pool",
                  "feedback_loop", "signal_history"]
        counts = {}
        for t in tables:
            try:
                r = self.query(f"SELECT COUNT(*) as cnt FROM {t}")
                counts[t] = r[0]["cnt"] if r else 0
            except Exception:
                counts[t] = 0
        return counts


# ═══════════════════════════════════════════════════════════
# 2. MAPE-K Flywheel — 自进化控制环 (核心)
# ═══════════════════════════════════════════════════════════
#
# 学术基础:
#   [1] MAPE-K Framework: Monitor → Analyze → Plan → Execute → Knowledge
#   [2] Data Flywheel: 每个循环丰富 K → 下一次循环更快更准
#   [3] Inertia Control: 过度更新导致过度交易，最小更新间隔=5交易日

class MAPEKFlywheel:
    """MAPE-K 自进化飞轮——4阶段闭环 + 共享知识库。

    每个交易日收盘后运行一次，惯性控制防止过度调参。
    """

    def __init__(self, db: UnifiedDB, mode: OpMode = OpMode.DIAGNOSE):
        self.db = db
        self.mode = mode
        self.loop_id = f"flywheel_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.min_update_interval = 5  # [Grammatical Evolution] 惯性控制: 至少5个交易日才允许再次进化

    def run(self, market_data: dict = None) -> dict:
        """执行一个完整的 MAPE-K 飞轮循环。

        返回: {phase_results, knowledge_gained, actions_taken}
        """
        t0 = time.time()
        results = {"loop_id": self.loop_id, "mode": self.mode.name}

        # ── M: Monitor 监控 ──
        monitor_result = self._monitor(market_data)
        results["monitor"] = monitor_result
        self._log_phase("monitor", "completed", str(monitor_result)[:200])

        # ── A: Analyze 分析 ──
        analyze_result = self._analyze(monitor_result)
        results["analyze"] = analyze_result
        self._log_phase("analyze", "completed", str(analyze_result)[:200])

        # ── P: Plan 规划 ──
        plan_result = self._plan(analyze_result)
        results["plan"] = plan_result
        self._log_phase("plan", "completed", str(plan_result)[:200])

        # ── E: Execute 执行 ──
        exec_result = self._execute(plan_result)
        results["execute"] = exec_result
        self._log_phase("execute", "completed", str(exec_result)[:200])

        # ── K: Knowledge 知识更新 ──
        knowledge = self._update_knowledge(results)
        results["knowledge"] = knowledge

        # 更新元数据
        self.db.execute("""
            UPDATE evolution_meta SET
                last_flywheel_run = ?, total_loops = total_loops + 1,
                updated_at = datetime('now')
        """, (datetime.now().isoformat(),))

        elapsed = time.time() - t0
        results["elapsed"] = round(elapsed, 2)
        return results

    # ── M: Monitor ──
    def _monitor(self, market_data: dict = None) -> dict:
        """监控层: 采集所有需要进化的信号。

        数据来源:
          - trading_headquarters 输出 (系统分析裁决)
          - daytrade_system 交易记录 (trades表)
          - external market data (market_data参数)
        """
        signals = {}

        # 从数据库拉最近的交易表现
        recent = self.db.query("""
            SELECT AVG(pnl_pct) as avg_pnl, COUNT(*) as cnt,
                   AVG(signal_score) as avg_score
            FROM trades
            WHERE trade_date >= date('now', '-30 days')
        """)
        if recent:
            signals["recent_30d"] = recent[0]

        # 最近参数变动
        param_changes = self.db.query("""
            SELECT COUNT(*) as cnt FROM param_evolution
            WHERE evolution_date >= date('now', '-10 days')
        """)
        signals["recent_param_changes"] = param_changes[0]["cnt"] if param_changes else 0

        # 外部市场数据
        if market_data:
            signals.update(market_data)

        # 认知事件——最近的教训
        recent_lessons = self.db.query("""
            SELECT event_type, category, description FROM cognitive_events
            WHERE event_time >= datetime('now', '-7 days')
            ORDER BY event_time DESC LIMIT 5
        """)
        signals["recent_cognitive_events"] = recent_lessons

        return signals

    # ── A: Analyze ──
    def _analyze(self, monitor: dict) -> dict:
        """分析层: 判断是否需要进化、进化什么。

        核心判断逻辑:
          1. [惯性控制] 过去10天参数变更>3次 → 跳过本轮 (防过度调参)
          2. [性能退化] 近30天平均盈亏<阈值 → 触发参数进化
          3. [制度变化] market_regime变更 → 触发策略池更新
          4. [认知驱动] 有新教训learned → 触发规则更新
        """
        analysis = {
            "need_evolution": False,
            "evolution_type": [],
            "reasons": [],
        }

        # 1. 惯性控制 [Grammatical Evolution]
        if monitor.get("recent_param_changes", 0) >= 3:
            analysis["reasons"].append("惯性控制: 近10天参数变更≥3次，跳过本轮")
            return analysis

        # 2. 性能退化检测
        recent = monitor.get("recent_30d", {})
        avg_pnl = recent.get("avg_pnl", 0) or 0
        if avg_pnl < -0.5:  # 30天平均亏损>0.5%
            analysis["need_evolution"] = True
            analysis["evolution_type"].append("param_tuning")
            analysis["reasons"].append(f"性能退化: 近30天均亏{avg_pnl:.2f}%")

        if avg_pnl > 0:
            analysis["need_evolution"] = True
            analysis["evolution_type"].append("weight_reinforce")
            analysis["reasons"].append(f"盈利确认: 近30天均盈{avg_pnl:.2f}%，强化当前权重")

        # 3. 认知事件驱动
        cognitive = monitor.get("recent_cognitive_events", [])
        if cognitive:
            analysis["need_evolution"] = True
            analysis["evolution_type"].append("lesson_integration")
            analysis["reasons"].append(f"认知驱动: {len(cognitive)}条新教训待整合")

        # 4. 制度变化 (如果market_data中有新regime)
        if monitor.get("market_regime") and monitor["market_regime"] != monitor.get("prev_regime"):
            analysis["need_evolution"] = True
            analysis["evolution_type"].append("regime_adaptation")
            analysis["reasons"].append("制度切换: 需调整策略池")

        return analysis

    # ── P: Plan ──
    def _plan(self, analysis: dict) -> dict:
        """规划层: 生成具体的进化方案。

        [LLM-GA] 如果可用，LLM引导语义交叉，保证进化方向逻辑一致。
        否则使用启发式规则生成方案。
        """
        plan = {"actions": [], "risks": [], "mode": self.mode.name}

        if not analysis.get("need_evolution"):
            plan["actions"].append({"type": "skip", "reason": "无需进化"})
            return plan

        for evo_type in analysis.get("evolution_type", []):
            if evo_type == "param_tuning":
                plan["actions"].append({
                    "type": "param_tuning",
                    "target": "factor_weights",
                    "method": "bayesian_update",
                    "direction": "tighten",  # 收紧止损/减小仓位
                    "max_change_pct": 0.15,  # [Inertia] 单次最大变化15%
                })
            elif evo_type == "weight_reinforce":
                plan["actions"].append({
                    "type": "weight_reinforce",
                    "target": "factor_weights",
                    "method": "bayesian_update",
                    "direction": "reinforce",
                    "max_change_pct": 0.10,
                })
            elif evo_type == "lesson_integration":
                plan["actions"].append({
                    "type": "lesson_integration",
                    "target": "lessons",
                    "method": "extract_rule",
                    "source": "cognitive_events",
                })
            elif evo_type == "regime_adaptation":
                plan["actions"].append({
                    "type": "regime_adaptation",
                    "target": "strategy_pool",
                    "method": "activate_best_for_regime",
                })

        # 风险评估
        if self.mode >= OpMode.SEMI_AUTO:
            plan["risks"] = ["自动执行: 低风险操作自动应用，高风险需确认"]

        return plan

    # ── E: Execute ──
    def _execute(self, plan: dict) -> dict:
        """执行层: 按 OpMode 权限矩阵执行进化方案。

        安全边界:
          SAFETY/OBSERVE: 不执行任何变更
          DIAGNOSE: 仅分析，不修改
          ADVISE: 生成建议但不自动应用
          SEMI_AUTO: 低风险(<3)自动，高风险需确认
          FULL_AUTO: 全自动
        """
        executed = []

        if self.mode <= OpMode.DIAGNOSE:
            return {"executed": 0, "actions": [], "reason": f"模式({self.mode.name})不执行变更"}

        for action in plan.get("actions", []):
            action_type = action.get("type", "")

            # 低风险操作 (SEMI_AUTO+)
            if action_type in ("weight_reinforce", "regime_adaptation"):
                if self.mode >= OpMode.SEMI_AUTO:
                    self._apply_action(action)
                    executed.append(action)

            # 高风险操作 (ADVISE+ 需确认, FULL_AUTO 自动)
            elif action_type in ("param_tuning", "lesson_integration"):
                if self.mode >= OpMode.FULL_AUTO:
                    self._apply_action(action)
                    executed.append(action)
                elif self.mode >= OpMode.ADVISE:
                    executed.append({**action, "status": "pending_approval"})

        return {"executed": len(executed), "actions": executed}

    def _apply_action(self, action: dict):
        """实际应用一个进化动作。"""
        action_type = action.get("type", "")
        now = datetime.now().isoformat()

        if action_type in ("param_tuning", "weight_reinforce"):
            # 记录参数变更
            self.db.execute("""
                INSERT INTO param_evolution
                (evolution_date, stock_code, param_name, old_value, new_value, reason)
                VALUES (?, '300418', ?, NULL, NULL, ?)
            """, (date.today().isoformat(), action_type, str(action)))

        elif action_type == "lesson_integration":
            # 将认知教训转化为交易规则
            self.db.execute("""
                UPDATE lessons SET verified = 1, times_applied = times_applied + 1
                WHERE verified = 0
            """)

        elif action_type == "regime_adaptation":
            self.db.execute("""
                UPDATE evolution_meta SET market_regime = ?
            """, (action.get("regime", "neutral"),))

    # ── K: Knowledge ──
    def _update_knowledge(self, results: dict) -> dict:
        """知识更新: 飞轮每转一圈都丰富共享知识库。

        [Data Flywheel] 核心: 每个循环让知识库更丰富 → 下一循环更快更准。
        """
        knowledge = {
            "new_insights": [],
            "confirmed_patterns": [],
            "deprecated_rules": [],
        }

        # 从本轮分析中提取洞察
        analyze = results.get("analyze", {})
        if analyze.get("reasons"):
            for reason in analyze["reasons"]:
                knowledge["new_insights"].append(reason)

        # 记录参数变更作为可复用模式
        exec_result = results.get("execute", {})
        if exec_result.get("executed", 0) > 0:
            knowledge["confirmed_patterns"].append(
                f"飞轮第{self._get_loop_count()}圈: 执行{exec_result['executed']}项变更"
            )

        return knowledge

    def _get_loop_count(self) -> int:
        r = self.db.query("SELECT total_loops FROM evolution_meta WHERE id=1")
        return r[0]["total_loops"] if r else 0

    def _log_phase(self, phase: str, status: str, summary: str):
        self.db.execute("""
            INSERT INTO feedback_loop (loop_id, phase, status, output_summary, started_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(loop_id) DO UPDATE SET
                phase=?, status=?, output_summary=output_summary || ?,
                completed_at=datetime('now')
        """, (self.loop_id, phase, status, summary, phase, status, f"\n[{phase}] {summary}"))


# ═══════════════════════════════════════════════════════════
# 3. LessonLearner — 认知反馈 → 交易规则
# ═══════════════════════════════════════════════════════════

class LessonLearner:
    """从认知事件中提取可执行的交易规则。

    输入: cognitive_events 表 (来自 systemic_feedback_learning_engine)
    输出: lessons 表 (可执行的交易规则)
    """

    def __init__(self, db: UnifiedDB):
        self.db = db

    def learn(self) -> dict:
        """扫描未处理的认知事件，提取教训。"""
        events = self.db.query("""
            SELECT * FROM cognitive_events
            WHERE verified = 0
            ORDER BY event_time DESC LIMIT 20
        """)

        learned = 0
        for ev in events:
            lesson = self._extract_lesson(ev)
            if lesson:
                self.db.execute("""
                    INSERT INTO lessons
                    (lesson_date, category, title, content, outcome, pnl_impact)
                    VALUES (?, ?, ?, ?, 'pending', 0)
                """, (date.today().isoformat(), ev["category"],
                      lesson["title"], lesson["content"]))
                self.db.execute(
                    "UPDATE cognitive_events SET verified=1 WHERE id=?",
                    (ev["id"],))
                learned += 1

        return {"events_processed": len(events), "lessons_learned": learned}

    def _extract_lesson(self, event: dict) -> Optional[dict]:
        """从认知事件提取交易教训。"""
        cat = event.get("category", "")
        desc = event.get("description", "")

        title_map = {
            "intent_misread": "意图误读→增加确认环节",
            "late_action": "行动时延→优先执行关键检查",
            "missing_memory": "记忆缺失→前置于决策前加载",
            "missing_context": "上下文丢失→状态台账自动检查",
            "wrong_priority": "优先级错误→按危害程度重排",
            "missing_status_tracking": "状态缺失→长期任务必建台账",
            "skill_trigger_failure": "技能未触发→扩展触发条件",
            "weak_generalization": "泛化不足→跨场景迁移规则",
            "decision_chain_failure": "决策链断裂→增加前后置检查",
        }

        return {
            "title": title_map.get(cat, f"未分类: {cat}"),
            "content": desc[:500],
        }


# ═══════════════════════════════════════════════════════════
# 4. StrategyPool — 质量-多样性策略池 (QuantEvolve)
# ═══════════════════════════════════════════════════════════

class StrategyPool:
    """管理交易策略的生成、评估、淘汰循环。

    学术基础: QuantEvolve (2025) — 质量-多样性优化:
      - Fitness: Sharpe × (1 - MaxDD) 综合适应度
      - Diversity: 按策略类型/风险/换手率保持生态多样性
      - Generation: 每周评估1次，最差10%退役
    """

    def __init__(self, db: UnifiedDB):
        self.db = db

    def register(self, strategy_id: str, name: str, category: str,
                 params: dict, fitness: float = 0, **meta):
        """注册新策略。"""
        self.db.execute("""
            INSERT OR REPLACE INTO strategy_pool
            (strategy_id, name, category, generation, fitness, sharpe, max_dd,
             params, diversity_vector, is_active)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, 1)
        """, (strategy_id, name, category, fitness,
              meta.get("sharpe", 0), meta.get("max_dd", 0),
              json.dumps(params), json.dumps(meta.get("diversity", {}))))

    def evaluate_all(self) -> list:
        """评估所有活跃策略的适应度，淘汰底部10%。"""
        active = self.db.query("""
            SELECT * FROM strategy_pool WHERE is_active = 1
            ORDER BY fitness DESC
        """)

        if len(active) <= 3:
            return active  # 最少保留3个

        # [QuantEvolve] 底部10%退役
        cutoff_idx = max(int(len(active) * 0.9), 3)
        retired = active[cutoff_idx:]

        for s in retired:
            self.db.execute("""
                UPDATE strategy_pool SET is_active=0, retired_reason='bottom_10pct'
                WHERE strategy_id=?
            """, (s["strategy_id"],))

        # 增加generation计数 (存活的策略)
        for s in active[:cutoff_idx]:
            self.db.execute("""
                UPDATE strategy_pool SET generation = generation + 1
                WHERE strategy_id = ?
            """, (s["strategy_id"],))

        return active[:cutoff_idx]

    def best_for_regime(self, regime: str) -> Optional[dict]:
        """制度自适应: 选择当前制度下最优策略。"""
        active = self.db.query("""
            SELECT * FROM strategy_pool
            WHERE is_active = 1 AND category LIKE ?
            ORDER BY fitness DESC LIMIT 1
        """, (f"%{regime}%",))

        if not active:
            # 回退: 直接选适应度最高的
            active = self.db.query(
                "SELECT * FROM strategy_pool WHERE is_active=1 ORDER BY fitness DESC LIMIT 1")
        return active[0] if active else None


# ═══════════════════════════════════════════════════════════
# 5. RollingValidator — 30天滚动窗口验证 (CGA-Agent)
# ═══════════════════════════════════════════════════════════

class RollingValidator:
    """每30个交易日跑一次回测验证，对比进化前后表现。

    [CGA-Agent] 滚动窗口重优化 + 动态参数调整。
    """

    def __init__(self, db: UnifiedDB):
        self.db = db

    def validate(self, window_days: int = 30) -> dict:
        """对比最近30天 vs 前30天的表现。"""
        today = date.today()

        recent = self.db.query("""
            SELECT AVG(pnl_pct) as avg_pnl, COUNT(*) as cnt,
                   SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins
            FROM trades
            WHERE trade_date >= ? AND trade_date < ?
        """, ((today - timedelta(days=window_days)).isoformat(),
              today.isoformat()))

        prior = self.db.query("""
            SELECT AVG(pnl_pct) as avg_pnl, COUNT(*) as cnt
            FROM trades
            WHERE trade_date >= ? AND trade_date < ?
        """, ((today - timedelta(days=window_days * 2)).isoformat(),
              (today - timedelta(days=window_days)).isoformat()))

        r = recent[0] if recent else {}
        p = prior[0] if prior else {}

        recent_pnl = r.get("avg_pnl", 0) or 0
        prior_pnl = p.get("avg_pnl", 0) or 0
        win_rate = (r.get("wins", 0) / max(r.get("cnt", 1), 1)) if r.get("cnt") else 0

        improving = recent_pnl > prior_pnl and r.get("cnt", 0) >= 5
        result = {
            "recent_avg_pnl": round(recent_pnl, 4),
            "prior_avg_pnl": round(prior_pnl, 4),
            "recent_trades": r.get("cnt", 0),
            "recent_win_rate": round(win_rate, 3),
            "improving": improving,
            "action": "reinforce" if improving else "investigate",
        }

        # 记录自检
        self.db.execute("""
            INSERT INTO self_tests (test_date, test_type, passed, details, issues)
            VALUES (?, 'rolling_validation', ?, ?, ?)
        """, (today.isoformat(), 1 if improving else 0,
              json.dumps(result), "" if improving else "表现恶化，需检查"))

        return result


# ═══════════════════════════════════════════════════════════
# 6. UnifiedEvolution — 总入口
# ═══════════════════════════════════════════════════════════

class UnifiedEvolution:
    """统一进化引擎——吞并 4 个旧系统。

    用法:
        evo = UnifiedEvolution(mode=OpMode.DIAGNOSE)
        evo.run_daily()          # 每日收盘后调用
        evo.learn_from_feedback() # 认知反馈 → 交易规则
        evo.validate()           # 30天滚动验证
    """

    def __init__(self, mode: OpMode = OpMode.DIAGNOSE):
        self.db = UnifiedDB()
        self.mode = mode
        self.flywheel = MAPEKFlywheel(self.db, mode)
        self.learner = LessonLearner(self.db)
        self.pool = StrategyPool(self.db)
        self.validator = RollingValidator(self.db)

    def run_daily(self, market_data: dict = None) -> dict:
        """每日进化流程——收盘后自动执行。

        Step 1: 学习反馈 (认知事件 → 交易规则)
        Step 2: MAPE-K 飞轮 (监控→分析→规划→执行→知识)
        Step 3: 策略池评估 (淘汰底部10%)
        Step 4: 滚动验证 (30天窗口)
        """
        result = {"date": date.today().isoformat(), "mode": self.mode.name}

        # Step 1: 学习
        lesson_result = self.learner.learn()
        result["lessons"] = lesson_result

        # Step 2: 飞轮
        fly_result = self.flywheel.run(market_data)
        result["flywheel"] = fly_result

        # Step 3: 策略池
        active = self.pool.evaluate_all()
        result["active_strategies"] = len(active)

        # Step 4: 验证
        val_result = self.validator.validate()
        result["validation"] = val_result

        # 汇总
        result["summary"] = self._summarize(result)

        return result

    def learn_from_feedback(self, feedback: dict):
        """从 systemic_feedback_learning_engine 接收反馈。

        feedback 格式: {event_type, category, severity, description, root_cause, ...}
        """
        self.db.execute("""
            INSERT INTO cognitive_events
            (event_time, event_type, category, severity, source, description, root_cause)
            VALUES (datetime('now'), ?, ?, ?, 'feedback_engine', ?, ?)
        """, (feedback.get("event_type", "feedback"),
              feedback.get("category", ""),
              feedback.get("severity", "medium"),
              feedback.get("description", ""),
              feedback.get("root_cause", "")))

    def integrate_headquarters_signal(self, verdict: dict):
        """从 trading_headquarters 接收融合后的信号。"""
        self.db.execute("""
            INSERT INTO signal_history
            (signal_time, stock_code, total_score, confidence, regime, reason)
            VALUES (datetime('now'), '300418', ?, ?, ?, ?)
        """, (verdict.get("fused_score", 0),
              verdict.get("confidence", 0),
              verdict.get("market_regime", ""),
              json.dumps(verdict)[:500]))

    def _summarize(self, result: dict) -> str:
        parts = []
        l = result.get("lessons", {})
        if l.get("lessons_learned", 0) > 0:
            parts.append(f"学习{l['lessons_learned']}条新教训")

        f = result.get("flywheel", {})
        exec_r = f.get("execute", {})
        if exec_r.get("executed", 0) > 0:
            parts.append(f"执行{exec_r['executed']}项进化")

        v = result.get("validation", {})
        if v.get("improving"):
            parts.append("表现改善 ✅")
        else:
            parts.append("表现平稳/待改进")

        return " | ".join(parts)

    def stats(self) -> dict:
        return self.db.stats()


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    evo = UnifiedEvolution()

    if cmd == "run":
        print("🚀 MAPE-K 飞轮启动...")
        result = evo.run_daily()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "learn":
        result = evo.learner.learn()
        print(json.dumps(result, ensure_ascii=False))

    elif cmd == "validate":
        result = evo.validator.validate()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "pool":
        active = evo.pool.evaluate_all()
        print(f"活跃策略: {len(active)}")
        for s in active:
            print(f"  {s['strategy_id']}: fitness={s['fitness']} gen={s['generation']}")

    elif cmd == "stats":
        print(json.dumps(evo.stats(), ensure_ascii=False, indent=2))

    elif cmd == "mode":
        new_mode = sys.argv[2] if len(sys.argv) > 2 else None
        if new_mode:
            try:
                evo.mode = OpMode[new_mode.upper()]
                evo.db.execute("UPDATE evolution_meta SET op_mode=?", (new_mode,))
                print(f"模式切换: {evo.mode.name}")
            except KeyError:
                print(f"无效模式: {new_mode}，可选: {[m.name for m in OpMode]}")
        else:
            print(f"当前模式: {evo.mode.name}")

    else:
        print("""
╔══════════════════════════════════════════════╗
║  第二大脑 · 统一进化引擎 v3.0               ║
╠══════════════════════════════════════════════╣
║  run       每日进化 (MAPE-K飞轮)              ║
║  learn     认知反馈 → 交易规则                ║
║  validate  30天滚动验证                       ║
║  pool      策略池管理                         ║
║  stats     数据库统计                         ║
║  mode [m]  切换运行模式(0-5)                  ║
╚══════════════════════════════════════════════╝
        """)
