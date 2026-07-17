#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二大脑 · 交易总司令部 (Trading Headquarters)
═══════════════════════════════════════════════════════

设计哲学（用户原话）:
  "脚感觉到痛 → 停下来，准确但片面。
   眼睛看到熊在追 → 不能停，要拼命跑。
   总司令部不是做加法，是做'矛盾统一'——单一信号正确但不够，
   跨信号交叉才能得出任何单一传感器给不了的判断。"

架构:
  Phase 1: INDEPENDENT — 各分析器独立运行，仅用原始数据
  Phase 2: EXCHANGE   — 关联分析器互取对方 Phase 1 结论，注入为上下文
  Phase 3: ENRICHED   — 分析器基于交叉信息重跑
  Phase 4: FUSION     — 总部融合所有信号，检测矛盾，解决冲突
  Phase 5: SYNTHESIS  — 生成跨维度洞察（单一分析器看不到的东西）

运行模式:
  - 独立系统: python core/trading_headquarters.py run
  - 被 skills 调用: from core.trading_headquarters import TradingHeadquarters
  - 作为 WorkBuddy 技能 system-analysis 的计算后端
"""

import json, os, sys, time
from datetime import datetime
from typing import Optional, Any
from collections import defaultdict, OrderedDict
import itertools

# ═══════════════════════════════════════════════════════════
# 0. 路径与依赖
# ═══════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from core.data_pipeline_orchestrator import DataPipelineOrchestrator
    _HAS_ORCHESTRATOR = True
except ImportError:
    _HAS_ORCHESTRATOR = False

# ═══════════════════════════════════════════════════════════
# 1. 统一信号协议 (Signal Protocol)
# ═══════════════════════════════════════════════════════════

class AnalyzerSignal:
    """每个分析器输出的标准信号格式。

    设计约束:
      - signal: +1(看多)/0(中性)/-1(看空) —— 强制三值，禁止模糊概率
      - confidence: 0.0-1.0 —— 分析器对自己判断的确信度
      - reasoning: 必须用中文写出"为什么这么判断"的核心逻辑
      - cross_needs: 声明"我还需要哪些其他分析器的数据才能更准"
      - cross_offers: 声明"我能给其他分析器提供什么"
    """

    def __init__(self, analyzer_id: str, signal: int, confidence: float,
                 reasoning: str = "", **kwargs):
        assert signal in (-1, 0, 1), f"signal must be +1/0/-1, got {signal}"
        assert 0.0 <= confidence <= 1.0, f"confidence must be 0-1, got {confidence}"

        self.analyzer_id = analyzer_id
        self.signal = signal
        self.confidence = confidence
        self.reasoning = reasoning
        self.phase = kwargs.get("phase", 1)  # 1=独立, 3=交叉后
        self.cross_needs = kwargs.get("cross_needs", [])
        self.cross_offers = kwargs.get("cross_offers", [])
        self.raw_data = kwargs.get("raw_data", {})
        self.tags = kwargs.get("tags", [])
        self.timestamp = datetime.now().isoformat()

    def label(self) -> str:
        """人类可读的信号标签。"""
        if self.signal == 1:
            return "🟢 看多"
        elif self.signal == -1:
            return "🔴 看空"
        return "🟡 中性"

    def to_dict(self) -> dict:
        return {
            "analyzer": self.analyzer_id,
            "signal": self.signal,
            "confidence": round(self.confidence, 3),
            "label": self.label(),
            "reasoning": self.reasoning,
            "phase": self.phase,
            "cross_needs": self.cross_needs,
            "cross_offers": self.cross_offers,
            "tags": self.tags,
        }

    def __repr__(self):
        return f"<{self.analyzer_id} {self.label()} conf={self.confidence:.2f}>"


# ═══════════════════════════════════════════════════════════
# 2. 分析器注册表 (Analyzer Registry)
# ═══════════════════════════════════════════════════════════

class AnalyzerRegistry:
    """注册所有可用的分析器，管理它们之间的依赖关系。

    每个分析器声明:
      - id: 唯一标识
      - category: 所属分类(结构/资金/量价/筹码/宏观/板块)
      - dependencies: 需要哪些其他分析器的 Phase 1 输出
      - provides: 能给哪些其他分析器提供数据
    """

    def __init__(self):
        self._analyzers = OrderedDict()
        self._build_default_registry()

    def _build_default_registry(self):
        """内置分析器注册表——覆盖 18 个核心维度。"""
        default = OrderedDict([
            # ── 结构分析 ──
            ("phase_structure", {
                "category": "structure",
                "name": "Phase D 结构分析",
                "description": "威科夫四阶段判断：吸筹/拉升/派发/下跌",
                "dependencies": [],
                "provides": ["trend_context", "phase_label"],
                "priority": 10,
            }),
            ("supply_test", {
                "category": "structure",
                "name": "供应测试",
                "description": "检测是否存在大单压盘测试——区分真卖压和假洗盘",
                "dependencies": ["volume_profile"],
                "provides": ["supply_pressure", "shakeout_signal"],
                "priority": 9,
            }),
            ("cause_effect", {
                "category": "structure",
                "name": "因果法则目标推测",
                "description": "威科夫因果法则：横盘区间→目标价位推算",
                "dependencies": ["phase_structure", "volume_profile"],
                "provides": ["price_target", "risk_reward"],
                "priority": 8,
            }),
            # ── 资金分析 ──
            ("money_flow", {
                "category": "capital",
                "name": "四渠道资金流",
                "description": "小单/中单/大单/超大单 净流向分析",
                "dependencies": [],
                "provides": ["capital_direction", "smart_money_signal"],
                "priority": 10,
            }),
            ("fund_pool", {
                "category": "capital",
                "name": "资金池 FIFO 追踪",
                "description": "逐日资金池进出——识别积累/撤退模式",
                "dependencies": ["money_flow"],
                "provides": ["accumulation_trend", "exit_signal"],
                "priority": 8,
            }),
            ("ddx_direction", {
                "category": "capital",
                "name": "DDX 方向判断",
                "description": "大单动向指标——连续红/绿柱判断主力意图",
                "dependencies": [],
                "provides": ["ddx_trend"],
                "priority": 9,
            }),
            # ── 量价分析 ──
            ("volume_profile", {
                "category": "volume",
                "name": "量价剖面",
                "description": "Volume Profile——识别高成交量节点(HVN)和低成交量节点(LVN)",
                "dependencies": [],
                "provides": ["hvn_lvn", "value_area", "poc"],
                "priority": 10,
            }),
            ("vwap_anchor", {
                "category": "volume",
                "name": "锚定 VWAP 盈亏",
                "description": "AVWAP 锚定——判断当前价格相对于锚定均价的偏离",
                "dependencies": [],
                "provides": ["vwap_deviation", "anchor_pnl"],
                "priority": 8,
            }),
            ("effort_result", {
                "category": "volume",
                "name": "努力vs结果",
                "description": "威科夫第三定律——量价配合/背离判断变盘",
                "dependencies": ["volume_profile"],
                "provides": ["effort_result_divergence"],
                "priority": 9,
            }),
            # ── 筹码分析 ──
            ("lockup_depth", {
                "category": "chip",
                "name": "筹码锁仓深度",
                "description": "四层锁仓模型——法定/机构/定增/ESOP 锁仓比例",
                "dependencies": [],
                "provides": ["float_ratio", "lockup_pressure"],
                "priority": 7,
            }),
            ("t1_tracking", {
                "category": "chip",
                "name": "T+1 锁仓追踪",
                "description": "昨日主力筹码今日解禁方向预判",
                "dependencies": ["money_flow"],
                "provides": ["unlock_direction", "rotation_signal"],
                "priority": 8,
            }),
            ("anchoring", {
                "category": "chip",
                "name": "散户锚定检测",
                "description": "检测散户行为锚定——处置效应/有限注意力",
                "dependencies": ["volume_profile", "vwap_anchor"],
                "provides": ["retail_bias", "anchoring_zone"],
                "priority": 7,
            }),
            # ── 板块/宏观 ──
            ("sector_radar", {
                "category": "sector",
                "name": "板块资金雷达",
                "description": "全市场板块资金流向——热钱在往哪跑",
                "dependencies": [],
                "provides": ["hot_sectors", "cold_sectors", "rotation_direction"],
                "priority": 9,
            }),
            ("siphon_detect", {
                "category": "sector",
                "name": "虹吸效应检测",
                "description": "检测是否有单个板块吸走全市场资金",
                "dependencies": ["sector_radar"],
                "provides": ["siphon_active", "siphon_target"],
                "priority": 8,
            }),
            ("rotation_tide", {
                "category": "sector",
                "name": "旋转门反向潮汐",
                "description": "T+1 解锁→昨日热门今日反向",
                "dependencies": ["sector_radar", "t1_tracking"],
                "provides": ["reversal_risk", "tide_direction"],
                "priority": 8,
            }),
            ("market_panic", {
                "category": "macro",
                "name": "市场恐慌指数",
                "description": "A股专属恐慌指数——涨跌比/跌停数/炸板率",
                "dependencies": [],
                "provides": ["panic_level", "sentiment"],
                "priority": 9,
            }),
            ("market_perception", {
                "category": "macro",
                "name": "全局盘面感知",
                "description": "聚合市场情绪/涨跌分布/板块温度——仓位建议",
                "dependencies": ["market_panic", "sector_radar"],
                "provides": ["position_advice", "market_regime"],
                "priority": 10,
            }),
            ("cross_stock", {
                "category": "macro",
                "name": "蓝标对比",
                "description": "昆仑 vs 蓝标 走势对比——谁强谁弱",
                "dependencies": [],
                "provides": ["relative_strength", "pair_signal"],
                "priority": 7,
            }),
        ])

        for aid, meta in default.items():
            self.register(aid, **meta)

    def register(self, analyzer_id: str, **meta):
        self._analyzers[analyzer_id] = meta

    def get(self, analyzer_id: str) -> Optional[dict]:
        return self._analyzers.get(analyzer_id)

    def list_all(self) -> list:
        return list(self._analyzers.keys())

    def list_by_category(self) -> dict:
        cats = defaultdict(list)
        for aid, meta in self._analyzers.items():
            cats[meta["category"]].append(aid)
        return dict(cats)

    def get_dependency_graph(self) -> dict:
        """返回完整的依赖关系图。"""
        graph = {}
        for aid, meta in self._analyzers.items():
            graph[aid] = {
                "category": meta["category"],
                "deps": meta.get("dependencies", []),
                "provides": meta.get("provides", []),
            }
        return graph

    def phase1_analyzers(self) -> list:
        """Phase 1 可以独立运行的分析器（无依赖或依赖可获取）。"""
        return [aid for aid, meta in self._analyzers.items()
                if not meta.get("dependencies")]

    def phase3_analyzers(self) -> list:
        """Phase 3 需要交叉数据的分析器。"""
        return [aid for aid, meta in self._analyzers.items()
                if meta.get("dependencies")]


# ═══════════════════════════════════════════════════════════
# 3. 战情板 (Battle Board) — 跨分析器共享内存
# ═══════════════════════════════════════════════════════════

class BattleBoard:
    """所有分析器的信号在此汇总和交换。

    脚痛信号 + 眼睛信号 → 战情板 → 总司令部判断：跑！

    两层存储:
      signals[analyzer_id] = AnalyzerSignal  # Phase 1 独立结果
      cross_data[analyzer_id] = {...}        # 注入的交叉数据 (Phase 2)
    """

    def __init__(self):
        self.signals: dict[str, AnalyzerSignal] = {}
        self.cross_data: dict[str, dict] = {}
        self.contradictions: list = []
        self.insights: list = []

    def post(self, signal: AnalyzerSignal):
        self.signals[signal.analyzer_id] = signal

    def get(self, analyzer_id: str) -> Optional[AnalyzerSignal]:
        return self.signals.get(analyzer_id)

    def inject_cross_data(self, target: str, data: dict):
        """给指定分析器注入其他分析器的数据。"""
        if target not in self.cross_data:
            self.cross_data[target] = {}
        self.cross_data[target].update(data)

    def get_cross_data(self, analyzer_id: str) -> dict:
        return self.cross_data.get(analyzer_id, {})

    def summary_by_signal(self) -> dict:
        """按信号方向汇总。"""
        bulls = [s for s in self.signals.values() if s.signal == 1]
        bears = [s for s in self.signals.values() if s.signal == -1]
        neutrals = [s for s in self.signals.values() if s.signal == 0]
        return {
            "bullish": len(bulls),
            "bearish": len(bears),
            "neutral": len(neutrals),
            "bullish_list": [s.analyzer_id for s in bulls],
            "bearish_list": [s.analyzer_id for s in bears],
            "net_score": sum(s.signal * s.confidence for s in self.signals.values()),
        }

    def to_export(self) -> dict:
        return {
            "signals": {aid: s.to_dict() for aid, s in self.signals.items()},
            "summary": self.summary_by_signal(),
            "contradictions": self.contradictions,
            "insights": self.insights,
        }


# ═══════════════════════════════════════════════════════════
# 4. 分析器运行器 — 桥接协议→执行
# ═══════════════════════════════════════════════════════════

class AnalyzerRunner:
    """运行单个分析器——加载数据 → 执行分析 → 输出标准化信号。

    作为"技能(协议) → Python(执行)"的桥梁。
    每个分析器在这里被调用，输入是原始数据 + 交叉数据，输出是 AnalyzerSignal。
    """

    def __init__(self, orchestrator=None):
        self.orch = orchestrator

    def run_phase1(self, analyzer_id: str, board: BattleBoard) -> AnalyzerSignal:
        """Phase 1: 独立分析——只用自己的原始数据。"""
        registry = AnalyzerRegistry()
        meta = registry.get(analyzer_id)
        if not meta:
            return AnalyzerSignal(analyzer_id, 0, 0, reasoning="分析器未注册")

        # 尝试加载数据
        data = {}
        if self.orch and _HAS_ORCHESTRATOR:
            try:
                ds_map = {
                    "phase_structure": ["300418_daily", "300058_daily"],
                    "supply_test": ["300418_daily", "300058_daily"],
                    "cause_effect": ["300418_daily", "300058_daily"],
                    "money_flow": ["300418_moneyflow", "300058_moneyflow"],
                    "fund_pool": ["300418_moneyflow", "300058_moneyflow"],
                    "ddx_direction": ["300418_daily", "300058_daily"],
                    "volume_profile": ["300418_daily", "300058_daily"],
                    "vwap_anchor": ["300418_daily", "300058_daily"],
                    "effort_result": ["300418_daily", "300058_daily"],
                    "lockup_depth": ["300418_share_float", "300058_share_float"],
                    "t1_tracking": ["300418_moneyflow", "300058_moneyflow"],
                    "anchoring": ["300418_daily", "300058_daily"],
                    "sector_radar": ["concept_flow"],
                    "siphon_detect": ["concept_flow"],
                    "rotation_tide": ["concept_flow"],
                    "market_panic": ["index_000001_daily"],
                    "market_perception": ["index_000001_daily", "index_000300_daily"],
                    "cross_stock": ["300418_daily", "300058_daily"],
                }
                dataset_ids = ds_map.get(analyzer_id, [])
                data = self.orch.load_multi(dataset_ids)
            except Exception as e:
                data = {"_error": str(e)}

        # 调用分析器逻辑
        signal = self._call_analyzer(analyzer_id, meta, data, board.get_cross_data(analyzer_id), phase=1)
        board.post(signal)
        return signal

    def run_phase3(self, analyzer_id: str, board: BattleBoard) -> AnalyzerSignal:
        """Phase 3: 交叉分析——使用 Phase 1 其他分析器的结论作为附加输入。"""
        registry = AnalyzerRegistry()
        meta = registry.get(analyzer_id)
        if not meta:
            return AnalyzerSignal(analyzer_id, 0, 0, reasoning="分析器未注册", phase=3)

        # 收集依赖的其他分析器信号
        cross_context = {}
        for dep_id in meta.get("dependencies", []):
            dep_signal = board.get(dep_id)
            if dep_signal:
                cross_context[dep_id] = dep_signal.to_dict()

        board.inject_cross_data(analyzer_id, cross_context)

        # 重新加载数据（可能包含更新后的交叉数据）
        data = {}
        if self.orch and _HAS_ORCHESTRATOR:
            try:
                ds_map = {
                    "supply_test": ["300418_daily", "300058_daily"],
                    "cause_effect": ["300418_daily", "300058_daily"],
                    "fund_pool": ["300418_moneyflow", "300058_moneyflow"],
                    "effort_result": ["300418_daily", "300058_daily"],
                    "anchoring": ["300418_daily", "300058_daily"],
                    "t1_tracking": ["300418_moneyflow", "300058_moneyflow"],
                    "siphon_detect": ["concept_flow"],
                    "rotation_tide": ["concept_flow"],
                    "market_perception": ["index_000001_daily", "index_000300_daily"],
                }
                data = self.orch.load_multi(ds_map.get(analyzer_id, []))
            except Exception:
                pass

        signal = self._call_analyzer(analyzer_id, meta, data, board.get_cross_data(analyzer_id), phase=3)
        board.post(signal)
        return signal

    def _call_analyzer(self, analyzer_id: str, meta: dict, data: dict,
                       cross: dict, phase: int) -> AnalyzerSignal:
        """实际调用分析逻辑——目前是启发式规则引擎，可扩展为调用外部脚本。"""

        # Phase 3: 如果已有 Phase 1 信号且交叉数据无变化，直接复用
        if phase == 3 and not cross:
            # 没有依赖的其他分析器，Phase 3 与 Phase 1 相同
            return AnalyzerSignal(
                analyzer_id, 0, 0.5,
                reasoning=f"[Phase{phase}] {meta['name']}: 无交叉依赖，信号不变",
                phase=phase, tags=[meta["category"]]
            )

        # ── 实际分析逻辑 ──
        # 此处是启发式规则引擎。
        # 未来的进化方向：每个分析器可以注册自己的 Python 函数/类。
        result = self._heuristic_analyze(analyzer_id, meta, data, cross, phase)
        return AnalyzerSignal(
            analyzer_id, result["signal"], result["confidence"],
            reasoning=result["reasoning"],
            phase=phase,
            tags=[meta["category"]] + result.get("tags", []),
            cross_needs=meta.get("dependencies", []),
            cross_offers=meta.get("provides", []),
            raw_data=result.get("raw", {}),
        )

    def _heuristic_analyze(self, analyzer_id: str, meta: dict, data: dict,
                           cross: dict, phase: int) -> dict:
        """启发式分析——基于数据特征推断信号。

        这不是"真正的分析"——真正的分析由 WorkBuddy 技能在 AI 层面完成。
        这个方法是引擎的"速算层"：当技能调用引擎时，引擎先跑一遍基础分析，
        把结构化结论交给技能的 AI 解读层做深度研判。
        """
        cat = meta["category"]
        has_data = any(v for v in data.values() if v and isinstance(v, list) and len(v) > 0)

        if not has_data:
            return {"signal": 0, "confidence": 0.3,
                    "reasoning": f"[Phase{phase}] {meta['name']}: 数据不可用，输出中性",
                    "tags": ["no_data"]}

        # 简单规则引擎——检测数据特征
        reasoning_parts = [f"[Phase{phase}] {meta['name']}"]

        # 如果有交叉数据注入
        if phase == 3 and cross:
            deps_info = []
            for dep_id, dep_signal in cross.items():
                deps_info.append(f"{dep_id}={dep_signal.get('signal', '?')}")
            reasoning_parts.append(f"交叉输入: {', '.join(deps_info)}")

        # 数据量统计
        for dsid, dsdata in data.items():
            if dsdata and isinstance(dsdata, list):
                reasoning_parts.append(f"{dsid}: {len(dsdata)}条")

        return {
            "signal": 0,  # 启发式默认中性——真实信号由 AI 技能层给出
            "confidence": 0.5,
            "reasoning": " | ".join(reasoning_parts),
            "tags": [cat, "heuristic"],
            "raw": {"data_keys": list(data.keys()), "cross_keys": list(cross.keys())},
        }


# ═══════════════════════════════════════════════════════════
# 5. 融合引擎 v2 — 学术级融合 (2026.07.13 升级)
# ═══════════════════════════════════════════════════════════
#
# 升级来源:
#   [1] MASS (Multi-Agent Simulation Scaling, 2025)
#       → Consensus-Divergence 评分: Signal = α·共识 - (1-α)·分歧
#   [2] Hierarchical Multi-Agent Fundamental Investing (2025, A-share)
#       → 分层架构: Macro→Sector→Firm→Portfolio, CSI300验证
#   [3] Bridgewater / Dalio "Principles"
#       → 可信度加权: 权重 = 历史准确率 × 领域专业度 × 时效衰减
#       → 四象限思维: 将矛盾放入不同时间/逻辑维度
#       → 痛苦+反思=进步: 错误→分析→规则→算法迭代
#   [4] MSIF-OEM (2025, ScienceDirect)
#       → 在线集成更新: 市场制度变化时自适应调整权重
#   [5] A股因子共振 (雪球/申万宏源)
#       → 估值×技术×情绪 三维交叉验证→过滤虚假信号
#   [6] Stacking 集成 (A-share 三层模型)
#       → 基学习器→元学习器 分层次融合
# ═══════════════════════════════════════════════════════════

class FusionEngine:
    """Phase 4: 学术级融合——多维度信号融合 + 矛盾检测 + 制度自适应。

    六大核心机制:
      1. 可信度加权 (Dalio) — 不民主投票，按历史准确率加权
      2. 共识-分歧评分 (MASS) — 高共识+低分歧=强信号
      3. 因子共振 (A股量化) — 跨独立维度交叉验证
      4. 分层融合 (A-share论文) — 宏观→板块→个股 逐层收紧
      5. 制度自适应 (MSIF-OEM) — 波动率/趋势环境下动态调权
      6. 痛苦→规则 (Dalio+系统反补) — 矛盾→分析→规则→权重更新
    """

    def __init__(self, registry: AnalyzerRegistry):
        self.registry = registry
        # 可信度追踪——每个分析器的历史表现
        self.track_record: dict[str, dict] = {}  # {analyzer_id: {hits, misses, last_hit}}
        # 制度自适应——当前市场状态
        self.market_regime: str = "neutral"  # trending / volatile / neutral
        # 共识-分歧参数
        self.alpha: float = 0.65  # MASS公式: α=0.65 → 共识权重65%, 分歧惩罚35%

    def fuse(self, board: BattleBoard) -> dict:
        """主融合入口——分层递进融合。"""
        signals = board.signals
        if not signals:
            return {"verdict": "no_data", "confidence": 0, "reasoning": "无分析信号"}

        # 第1层: 类别内融合 (Category Fusion)
        category_scores = self._category_fusion(board)

        # 第2层: 跨类别融合 (Cross-Category Fusion)
        cross_score = self._cross_category_fusion(category_scores)

        # 第3层: 共识-分歧评分 (MASS Consensus-Divergence)
        cd_score = self._consensus_divergence_score(board)

        # 第4层: 因子共振检测 (Factor Resonance)
        resonance = self._factor_resonance(board)

        # 第5层: 矛盾检测
        contradictions = self._detect_contradictions(board)
        board.contradictions = contradictions

        # 第6层: 可信度加权融合
        weighted = self._credibility_weighted_fusion(board, category_scores)

        # 综合评分——融合所有层次
        final_score = (
            weighted["fused_score"] * 0.40 +
            cd_score["consensus_score"] * 0.25 +
            resonance["resonance_score"] * 0.20 +
            cross_score * 0.15
        )

        # 矛盾惩罚
        conflict_penalty = min(len(contradictions) * 0.08, 0.25)
        if resonance["resonance_strength"] == "strong":
            conflict_penalty *= 0.5  # 共振强→矛盾影响减半

        adjusted_score = final_score - (conflict_penalty * abs(final_score))
        adjusted_confidence = min(max(abs(adjusted_score) - conflict_penalty, 0.1), 1.0)

        # 信号判定
        if adjusted_score > 0.15:
            fused_signal = 1
        elif adjusted_score < -0.15:
            fused_signal = -1
        else:
            fused_signal = 0

        # 跨维度洞察
        insights = self._generate_insights(board)
        board.insights = insights

        # 仓位建议——考虑制度
        if fused_signal == 1:
            position = "积极做多" if self.market_regime == "trending" else "谨慎加仓"
        elif fused_signal == -1:
            position = "积极减仓" if self.market_regime == "volatile" else "减仓观望"
        elif len(contradictions) >= 3:
            position = "信号矛盾多，坚决观望"
        else:
            position = "中性持仓，等待突破信号"

        stats = board.summary_by_signal()

        return {
            "verdict": fused_signal,
            "label": "🟢 综合看多" if fused_signal == 1 else ("🔴 综合看空" if fused_signal == -1 else "🟡 综合中性"),
            "confidence": round(adjusted_confidence, 3),
            "position_advice": position,
            "fused_score": round(final_score, 4),
            "adjusted_score": round(adjusted_score, 4),
            "signal_breakdown": stats,
            "contradictions_count": len(contradictions),
            "insights_count": len(insights),
            "market_regime": self.market_regime,
            "resonance": resonance,
            "consensus_divergence": cd_score,
            "category_fusion": category_scores,
            "weighted_details": weighted.get("details", []),
        }

    # ── 1. 类别内融合 (Category Fusion) ──
    def _category_fusion(self, board: BattleBoard) -> dict:
        """每个类别内部独立融合——6类→6个类别分数。

        学术依据: A-share论文的分层架构——同类别信号有内在关联，
        先在同类别内融合可以放大信噪比。
        """
        categories = self.registry.list_by_category()
        cat_scores = {}

        for cat, analyzer_ids in categories.items():
            cat_signals = [board.get(aid) for aid in analyzer_ids if board.get(aid)]
            if not cat_signals:
                cat_scores[cat] = {"score": 0, "consensus": 0, "confidence": 0, "count": 0}
                continue

            # 类别内共识度——同一类别内信号越一致越好
            directions = [s.signal for s in cat_signals]
            positive_ratio = sum(1 for d in directions if d == 1) / len(directions)
            negative_ratio = sum(1 for d in directions if d == -1) / len(directions)

            if positive_ratio > 0.6:
                consensus = positive_ratio
                direction = 1
            elif negative_ratio > 0.6:
                consensus = negative_ratio
                direction = -1
            else:
                consensus = 0.5  # 分歧
                direction = 0

            # 类别内加权平均
            weighted = sum(s.signal * s.confidence for s in cat_signals) / max(len(cat_signals), 1)
            avg_conf = sum(s.confidence for s in cat_signals) / len(cat_signals)

            cat_scores[cat] = {
                "score": round(weighted * consensus, 4),
                "consensus": round(consensus, 3),
                "confidence": round(avg_conf, 3),
                "direction": direction,
                "count": len(cat_signals),
                "analyzers": [s.analyzer_id for s in cat_signals],
            }

        return cat_scores

    # ── 2. 跨类别融合 ──
    def _cross_category_fusion(self, cat_scores: dict) -> float:
        """6个类别分数→综合跨类别分数。

        核心逻辑: 类别之间越一致，综合分数绝对值越大。
        如果结构/资金/量价三个核心类别一致→强信���。
        """
        core_cats = ["structure", "capital", "volume"]
        core_scores = [cat_scores[c]["score"] for c in core_cats if c in cat_scores]

        if not core_scores:
            return 0.0

        mean_score = sum(core_scores) / len(core_scores)
        # 如果三个核心类别方向一致，放大分数
        directions = [1 if s > 0.1 else (-1 if s < -0.1 else 0) for s in core_scores]
        if len(set(directions)) == 1 and directions[0] != 0:
            mean_score *= 1.5  # 共振放大

        return mean_score

    # ── 3. 共识-分歧评分 (MASS: Consensus-Divergence) ──
    def _consensus_divergence_score(self, board: BattleBoard) -> dict:
        """MASS论文核心公式: Signal = α × consensus - (1-α) × divergence

        consensus = 所有信号加权平均（向同一方向的程度）
        divergence = 信号的标准差（分歧越大越不稳定）
        高共识 + 低分歧 = 强信号
        """
        signals = list(board.signals.values())
        if not signals:
            return {"consensus_score": 0, "consensus": 0, "divergence": 0}

        # 加权平均 = 共识
        values = [s.signal * s.confidence for s in signals]
        consensus = sum(values) / len(values)

        # 标准差 = 分歧（归一化到 [0,1]）
        import math
        mean_val = sum(v / (s.confidence + 0.01) for v, s in zip(values, signals)) / len(signals)
        variance = sum(((s.signal - mean_val) ** 2) * s.confidence for s in signals) / len(signals)
        divergence = min(math.sqrt(variance) / 1.0, 1.0)  # 归一化

        # MASS公式
        cd_score = self.alpha * consensus - (1 - self.alpha) * divergence

        return {
            "consensus_score": round(cd_score, 4),
            "consensus": round(consensus, 4),
            "divergence": round(divergence, 4),
            "interpretation": self._interpret_cd(consensus, divergence),
        }

    def _interpret_cd(self, consensus: float, divergence: float) -> str:
        if abs(consensus) > 0.3 and divergence < 0.3:
            return "高共识+低分歧 → 强信号，可行动"
        elif abs(consensus) > 0.3 and divergence > 0.5:
            return "高共识+高分歧 → 存在隐藏风险，需谨慎"
        elif abs(consensus) < 0.15 and divergence < 0.2:
            return "低共识+低分歧 → 市场方向不明，等待"
        else:
            return "信号混合，以保守策略为主"

    # ── 4. 因子共振 (Factor Resonance) ──
    def _factor_resonance(self, board: BattleBoard) -> dict:
        """A股量化实践: 估值×技术×情绪 三维交叉验证。

        不应只让所有因子投票——应该看"独立维度"之间是否相互验证。
        3个独立维度都指同一方向→高置信度。
        只有1个维度指某方向→可能是虚假信号。
        """
        signals = board.signals
        # 三维度分组 (独立信息来源)
        dimensions = {
            "技术面": ["phase_structure", "volume_profile", "effort_result", "vwap_anchor", "supply_test"],
            "资金面": ["money_flow", "fund_pool", "ddx_direction", "t1_tracking"],
            "情绪/宏观": ["market_panic", "market_perception", "sector_radar", "siphon_detect", "rotation_tide", "cross_stock"],
        }

        dim_scores = {}
        for dim_name, analyzer_ids in dimensions.items():
            scores = [signals[aid].signal * signals[aid].confidence
                      for aid in analyzer_ids if aid in signals]
            if scores:
                dim_scores[dim_name] = sum(scores) / len(scores)
            else:
                dim_scores[dim_name] = 0

        # 共振强度: 3个维度指向同一方向
        directions = {d: (1 if s > 0.1 else (-1 if s < -0.1 else 0))
                      for d, s in dim_scores.items()}
        pos_count = sum(1 for d in directions.values() if d == 1)
        neg_count = sum(1 for d in directions.values() if d == -1)

        if pos_count == 3:
            resonance_strength = "strong"
            resonance_score = 0.6
            msg = "🔵 三维共振看多: 技术面+资金面+情绪面一致→高置信度看多信号"
        elif neg_count == 3:
            resonance_strength = "strong"
            resonance_score = -0.6
            msg = "🔴 三维共振看空: 技术面+资金面+情绪面一致→高置信度看空信号"
        elif pos_count == 2:
            resonance_strength = "moderate"
            resonance_score = 0.3
            msg = f"🟡 二维看多，{3-pos_count-neg_count}维中性→中等置信度"
        elif neg_count == 2:
            resonance_strength = "moderate"
            resonance_score = -0.3
            msg = f"🟡 二维看空，{3-pos_count-neg_count}维中性→中等置信度"
        else:
            resonance_strength = "weak"
            resonance_score = 0
            msg = "⚪ 无共振→信号不可靠，需更多确认"

        return {
            "resonance_strength": resonance_strength,
            "resonance_score": resonance_score,
            "dimension_scores": dim_scores,
            "message": msg,
        }

    # ── 5. 可信度加权融合 (Dalio Credibility-Weighted) ──
    def _credibility_weighted_fusion(self, board: BattleBoard, cat_scores: dict) -> dict:
        """Dalio 可信度加权: 不是民主投票，是按可信度加权。

        可信度 = 历史准确率 × 领域专业度 × 时效衰减 × 制度适配

        学术依据: Bridgewater的决策系统——每个观点不是按人头投票，
        而是按说话人的"可信度"加权。可信度来自历史表现+领域专长。
        """
        # 初始化/更新 track_record
        for aid in board.signals:
            if aid not in self.track_record:
                self.track_record[aid] = {"hits": 0, "misses": 0, "last_hit": None}

        details = []
        total_credibility = 0
        weighted_sum = 0

        for aid, sig in board.signals.items():
            meta = self.registry.get(aid) or {}
            tr = self.track_record.get(aid, {"hits": 0, "misses": 0})

            # 1. 历史准确率 (Bayesian smoothing: 防止0次时的冷启动)
            total_trials = tr["hits"] + tr["misses"]
            if total_trials > 0:
                accuracy = (tr["hits"] + 1) / (total_trials + 2)  # Laplace平滑
            else:
                accuracy = 0.5  # 冷启动→50%

            # 2. 领域专业度 (从分析器优先级转化)
            priority = meta.get("priority", 5)
            expertise = priority / 10.0  # 归一化到 [0,1]

            # 3. 时效衰减 (最近一次命中距今越久，可信度越低)
            recency = 1.0
            if tr.get("last_hit"):
                try:
                    last = datetime.fromisoformat(tr["last_hit"])
                    days_ago = (datetime.now() - last).days
                    recency = max(0.5, 1.0 - days_ago * 0.02)  # 每天衰减2%, 最低50%
                except Exception:
                    pass

            # 4. 制度适配 (trending市场→趋势策略权重↑; volatile→反转策略↑)
            regime_factor = 1.0
            cat = meta.get("category", "")
            if self.market_regime == "trending" and cat in ("structure", "volume"):
                regime_factor = 1.3  # 趋势市场中结构/量价更可靠
            elif self.market_regime == "volatile" and cat in ("capital", "macro"):
                regime_factor = 1.3  # 波动市场中资金/宏观更值得看

            # 综合可信度
            credibility = (accuracy * 0.40 + expertise * 0.30 + recency * 0.15 + regime_factor * 0.15)
            credibility = min(max(credibility, 0.1), 1.0)

            weighted_sum += sig.signal * credibility
            total_credibility += credibility

            details.append({
                "analyzer": aid,
                "category": cat,
                "signal": sig.signal,
                "confidence": sig.confidence,
                "credibility": round(credibility, 3),
                "accuracy": round(accuracy, 3),
                "expertise": round(expertise, 3),
                "regime_factor": round(regime_factor, 3),
            })

        if total_credibility == 0:
            return {"fused_score": 0, "fused_signal": 0, "details": details}

        fused_score = weighted_sum / total_credibility
        fused_signal = 1 if fused_score > 0.15 else (-1 if fused_score < -0.15 else 0)

        return {
            "fused_score": round(fused_score, 4),
            "fused_signal": fused_signal,
            "fused_label": "🟢 可信度加权看多" if fused_signal == 1 else ("🔴 可信度加权看空" if fused_signal == -1 else "🟡 可信度加权中性"),
            "total_credibility": round(total_credibility, 3),
            "details": details,
        }

    # ── 6. 矛盾检测 (保留并增强) ──
    def _detect_contradictions(self, board: BattleBoard) -> list:
        contradictions = []
        signals = board.signals

        conflict_rules = [
            ("supply_test", "money_flow",
             "供应测试看空 + 资金流看多 → 大单压盘洗盘，非真出货",
             "supply_test为真信号(供应测试通常准确)→倾向不卖"),
            ("phase_structure", "ddx_direction",
             "结构看多 + DDX流出 → 诱多陷阱，需警惕",
             "资金流向比结构判断更实时→倾向谨慎"),
            ("volume_profile", "effort_result",
             "量价中性 + 努力vs结果背离 → 变盘前兆",
             "变盘方向不确定，观察突破方向"),
            ("market_panic", "money_flow",
             "恐慌高 + 资金流入 → 恐慌性买入，可能见底",
             "这是经典见底信号→倾向看多"),
            ("sector_radar", "rotation_tide",
             "板块流入 + 旋转门预警 → 今日热门=明日陷阱",
             "短期追高有T+1风险→倾向不追"),
            ("money_flow", "anchoring",
             "资金流出 + 散户锚定 → 可能是洗盘而非出货",
             "散户出+主力进→倾向看多"),
            ("ddx_direction", "lockup_depth",
             "DDX流出 + 高锁仓 → 假流出，真实抛压有限",
             "锁仓高→真抛压小→倾向不恐慌"),
        ]

        for a_id, b_id, meaning, resolution in conflict_rules:
            sa = signals.get(a_id)
            sb = signals.get(b_id)
            if sa and sb and sa.signal != 0 and sb.signal != 0 and sa.signal != sb.signal:
                contradictions.append({
                    "type": "signal_conflict",
                    "analyzers": [a_id, b_id],
                    "signal_a": sa.to_dict(),
                    "signal_b": sb.to_dict(),
                    "meaning": meaning,
                    "resolution": resolution,
                    "severity": "high" if abs(sa.confidence - sb.confidence) < 0.2 else "medium",
                })

        return contradictions

    # ── 7. 跨维度洞察 (保留并增强) ──
    def _generate_insights(self, board: BattleBoard) -> list:
        insights = []
        signals = board.signals

        # 共振洞察 (新增)
        resonance = self._factor_resonance(board)
        if resonance["resonance_strength"] in ("strong", "moderate"):
            insights.append({
                "type": "resonance",
                "message": resonance["message"],
                "analyzers": list(signals.keys()),
            })

        # 强共识警示 (Dalio: 一致性强可能是陷阱)
        bulls = [s for s in signals.values() if s.signal == 1 and s.confidence > 0.6]
        bears = [s for s in signals.values() if s.signal == -1 and s.confidence > 0.6]
        total = len(signals)

        if len(bulls) / max(total, 1) > 0.7:
            insights.append({
                "type": "too_consensus",
                "message": f"⚠️ Dalio警示: {len(bulls)}/{total} 看多→一致性过高，警惕反转",
                "analyzers": [s.analyzer_id for s in bulls],
            })
        elif len(bears) / max(total, 1) > 0.7:
            insights.append({
                "type": "too_consensus",
                "message": f"⚠️ Dalio警示: {len(bears)}/{total} 看空→恐慌一致性过高，可能见底",
                "analyzers": [s.analyzer_id for s in bears],
            })

        # 结构 vs 资金 背离
        struct_sig = signals.get("phase_structure")
        money_sig = signals.get("money_flow")
        if struct_sig and money_sig and struct_sig.signal != 0 and money_sig.signal != 0:
            if struct_sig.signal != money_sig.signal:
                insights.append({
                    "type": "dalio_quadrant",
                    "message": f"Dalio四象限: 结构({struct_sig.label()}) vs 资金({money_sig.label()}) 方向相反 → "
                              f"放不同时间维���看: 短期{'诱多' if struct_sig.signal == 1 else '洗盘'}, "
                              f"中期{'偏多' if money_sig.signal == 1 else '偏空'}",
                })

        # 恐慌抄底
        panic = signals.get("market_panic")
        if panic and money_sig and panic.signal == -1 and money_sig.signal == 1:
            insights.append({
                "type": "dalio_pain_reflection",
                "message": "🟢 Dalio'痛苦+反思': 恐慌中资金逆向流入→经典'别人恐惧我贪婪'信号",
            })

        return insights

    # ── 8. 制度检测 (Regime Detection) ──
    def detect_regime(self, board: BattleBoard) -> str:
        """检测当前市场制度——用于自适应权重调整。

        学术依据: MSIF-OEM在线集成更新——不同市场制度下，
        不同因子的预测能力不同。trending市场技术面有效，
        volatile市场资金面/情绪面更可靠。
        """
        signals = board.signals
        panic = signals.get("market_panic")
        perception = signals.get("market_perception")

        # 恐慌程度
        high_panic = panic and panic.signal == -1 and panic.confidence > 0.6

        # 板块分散度——如果板块信号极端化→趋势市
        sector = signals.get("sector_radar")
        siphon = signals.get("siphon_detect")
        high_concentration = siphon and siphon.signal != 0

        if high_panic and high_concentration:
            self.market_regime = "volatile"
        elif high_concentration and not high_panic:
            self.market_regime = "trending"
        else:
            self.market_regime = "neutral"

        return self.market_regime

    # ── 9. 反馈学习接口 (Dalio 痛苦→规则) ──
    def record_outcome(self, analyzer_id: str, was_correct: bool):
        """记录分析器的实际结果——用于更新可信度加权。

        每次事后验证调用此方法，分析器可信度会自动更新。
        痛苦(错误)+反思(记录)→进步(权重优化)。
        """
        if analyzer_id not in self.track_record:
            self.track_record[analyzer_id] = {"hits": 0, "misses": 0, "last_hit": None}

        if was_correct:
            self.track_record[analyzer_id]["hits"] += 1
        else:
            self.track_record[analyzer_id]["misses"] += 1

        self.track_record[analyzer_id]["last_hit"] = datetime.now().isoformat()

        adjusted_confidence = min(max(
            abs(weighted["fused_score"]) - conflict_penalty + insight_bonus, 0.1
        ), 1.0)

        # 仓位建议
        if fused_signal == 1 and adjusted_confidence > 0.5:
            position = "可适度加仓/做正T"
        elif fused_signal == -1 and adjusted_confidence > 0.5:
            position = "建议减仓/做倒T"
        elif len(contradictions) >= 3:
            position = "信号矛盾多，建议观望不动"
        else:
            position = "中性持仓，等待明确信号"

        return {
            "verdict": fused_signal,
            "label": weighted["fused_label"],
            "confidence": round(adjusted_confidence, 3),
            "position_advice": position,
            "fused_score": weighted["fused_score"],
            "signal_breakdown": stats,
            "contradictions_count": len(contradictions),
            "insights_count": len(insights),
            "weighted_details": weighted.get("details", []),
        }


# ═══════════════════════════════════════════════════════════
# 6. 总司令部 (Trading Headquarters) — 主调度器
# ═══════════════════════════════════════════════════════════

class TradingHeadquarters:
    """交易总司令部——"不是做加法，是做矛盾统一"。

    用法:
        hq = TradingHeadquarters()
        result = hq.run_full_analysis()
        # result.board.to_export() → 完整 JSON
        # result.verdict → 最终裁决
    """

    def __init__(self):
        self.registry = AnalyzerRegistry()
        self.orch = None
        if _HAS_ORCHESTRATOR:
            try:
                self.orch = DataPipelineOrchestrator()
            except Exception:
                pass
        self.runner = AnalyzerRunner(self.orch)
        self.fusion = FusionEngine(self.registry)
        self.board = BattleBoard()

    def run_full_analysis(self, verbose: bool = False) -> 'HeadquartersResult':
        """执行完整的五阶段分析。

        Phase 1: 独立分析——18 个分析器并行
        Phase 2: 数据交换——依赖关系匹配
        Phase 3: 交叉分析——依赖注入后重跑
        Phase 4: 融合研判——矛盾检测 + 加权融合
        Phase 5: 综合输出——生成决策报告
        """
        t0 = time.time()

        # ── Phase 1: INDEPENDENT ──
        if verbose:
            print("[HQ] Phase 1: 独立分析...")
        phase1_ids = self.registry.phase1_analyzers()
        for aid in phase1_ids:
            self.runner.run_phase1(aid, self.board)
        if verbose:
            print(f"[HQ] Phase 1 完成: {len(phase1_ids)} 个分析器")

        # ── Phase 2: EXCHANGE ──
        if verbose:
            print("[HQ] Phase 2: 数据交换...")
        self._exchange_phase2()
        if verbose:
            print("[HQ] Phase 2 完成")

        # ── Phase 3: ENRICHED ──
        if verbose:
            print("[HQ] Phase 3: 交叉分析...")
        phase3_ids = self.registry.phase3_analyzers()
        for aid in phase3_ids:
            self.runner.run_phase3(aid, self.board)
        if verbose:
            print(f"[HQ] Phase 3 完成: {len(phase3_ids)} 个分析器")
            print(f"[HQ] 总计: Phase1 {len(phase1_ids)} + Phase3 {len(phase3_ids)} = {len(self.board.signals)} 个信号")

        # ── Phase 4: FUSION ──
        if verbose:
            print("[HQ] Phase 4: 融合研判...")
        # 制度检测 (MSIF-OEM: 融合前先判断市场制度)
        regime = self.fusion.detect_regime(self.board)
        if verbose:
            print(f"[HQ] 市场制度: {regime}")
        verdict = self.fusion.fuse(self.board)
        if verbose:
            print(f"[HQ] Phase 4 完成: {verdict['label']} (置信度 {verdict['confidence']})")

        # ── Phase 5: SYNTHESIS ──
        elapsed = time.time() - t0

        return HeadquartersResult(
            board=self.board,
            verdict=verdict,
            registry=self.registry,
            elapsed=elapsed,
        )

    def _exchange_phase2(self):
        """Phase 2: 分析器之间交换 Phase 1 结论。

        脚痛分析器 "我需要眼睛的数据" → 战情板 → 眼睛分析器 "我提供视觉信息"
        """
        for aid in self.registry.list_all():
            meta = self.registry.get(aid)
            deps = meta.get("dependencies", [])
            cross_context = {}
            for dep_id in deps:
                dep_signal = self.board.get(dep_id)
                if dep_signal:
                    cross_context[dep_id] = dep_signal.to_dict()
            if cross_context:
                self.board.inject_cross_data(aid, cross_context)

    def quick_analysis(self, stock_code: str = "300418") -> dict:
        """快速分析——只跑与该股票最相关的分析器。"""
        # 只取 direct 相关 + 宏观层面
        relevant = ["phase_structure", "money_flow", "ddx_direction",
                    "volume_profile", "vwap_anchor", "effort_result",
                    "market_panic", "market_perception"]
        for aid in relevant:
            self.runner.run_phase1(aid, self.board)
        verdict = self.fusion.fuse(self.board)
        return {
            "stock": stock_code,
            "verdict": verdict,
            "signals": {aid: s.to_dict() for aid, s in self.board.signals.items()},
        }

    def dependency_graph(self) -> dict:
        return self.registry.get_dependency_graph()

    def categories(self) -> dict:
        return self.registry.list_by_category()


class HeadquartersResult:
    """分析结果封装——包含所有阶段的完整数据。"""

    def __init__(self, board: BattleBoard, verdict: dict,
                 registry: AnalyzerRegistry, elapsed: float):
        self.board = board
        self.verdict = verdict
        self.registry = registry
        self.elapsed = elapsed

    def full_report(self) -> str:
        """生成完整的中文分析报告。"""
        lines = []
        lines.append("=" * 60)
        lines.append("  第二大脑 · 交易总司令部 系统分析报告")
        lines.append(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  耗时: {self.elapsed:.2f}s")
        lines.append("=" * 60)

        # 摘要
        v = self.verdict
        lines.append(f"\n📊 综合裁决: {v['label']}")
        lines.append(f"   置信度: {v['confidence']:.2f}")
        lines.append(f"   仓位建议: {v['position_advice']}")
        lines.append(f"   融合分数: {v['fused_score']:.3f}")

        # 信号统计
        s = v["signal_breakdown"]
        lines.append(f"\n📈 信号统计: 🟢{s['bullish']} 🔴{s['bearish']} 🟡{s['neutral']}")
        lines.append(f"   净得分: {s['net_score']:.3f}")

        # 各分析器信号
        lines.append(f"\n🔍 各维度信号:")
        for aid, sig in self.board.signals.items():
            meta = self.registry.get(aid) or {}
            lines.append(f"   {sig.label()} [{meta.get('category', '?')}] {meta.get('name', aid)}")
            if sig.reasoning:
                lines.append(f"      {sig.reasoning[:100]}")

        # 矛盾
        if self.board.contradictions:
            lines.append(f"\n⚠️ 信号矛盾 ({len(self.board.contradictions)} 处):")
            for c in self.board.contradictions:
                lines.append(f"   {c['analyzers'][0]} vs {c['analyzers'][1]}: {c['meaning'][:80]}")
                lines.append(f"   → {c['resolution']}")

        # 洞察
        if self.board.insights:
            lines.append(f"\n💡 跨维度洞察 ({len(self.board.insights)} 条):")
            for ins in self.board.insights:
                lines.append(f"   [{ins['type']}] {ins['message'][:100]}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def to_json(self) -> str:
        """导出为 JSON。"""
        return json.dumps(self.board.to_export(), ensure_ascii=False, indent=2)

    def to_dict(self) -> dict:
        """导出为 Python dict——供技能 AI 解读层使用。"""
        return {
            "verdict": self.verdict,
            "signals": {aid: s.to_dict() for aid, s in self.board.signals.items()},
            "contradictions": self.board.contradictions,
            "insights": self.board.insights,
            "categories": self.registry.list_by_category(),
            "elapsed": self.elapsed,
        }


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"

    if cmd == "run":
        hq = TradingHeadquarters()
        result = hq.run_full_analysis(verbose=True)
        print(result.full_report())

    elif cmd == "quick":
        code = sys.argv[2] if len(sys.argv) > 2 else "300418"
        hq = TradingHeadquarters()
        result = hq.quick_analysis(code)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "graph":
        hq = TradingHeadquarters()
        print(json.dumps(hq.dependency_graph(), ensure_ascii=False, indent=2))

    elif cmd == "categories":
        hq = TradingHeadquarters()
        print(json.dumps(hq.categories(), ensure_ascii=False, indent=2))

    elif cmd == "json":
        hq = TradingHeadquarters()
        result = hq.run_full_analysis()
        print(result.to_json())

    else:
        print("""
╔══════════════════════════════════════════════╗
║  第二大脑 · 交易总司令部                     ║
╠══════════════════════════════════════════════╣
║  run         完整五阶段分析 + 报告            ║
║  quick [code] 快速分析 (默认300418)           ║
║  graph       依赖关系图                       ║
║  categories  分析器分类概览                   ║
║  json        JSON 格式输出                    ║
╚══════════════════════════════════════════════╝
        """)
