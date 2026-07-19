"""
agents.py — 多 Agent 协作体系 (Phase 6)

蓝图 §6: 七种独立 Agent + Orchestrator 中央仲裁

核心设计:
1. AgentProtocol: 统一接口 think(context)→AgentSignal
2. AgentSignal: 标准化输出 {signal:+1/0/-1, confidence:0-1, reason:str}
3. SignalFusion: 加权融合公式 Fusion=Σ(W_i×S_i×C_i)/Σ(W_i)
4. DebateSystem: Bull vs Bear → Judge 裁决 (冲突升级)
5. AuditTrail: 所有决策记录到 decision_audit/

七种 Agent:
- MemoryAgent: 记忆检索与知识激活
- EmotionAgent: 情绪感知与关系评估
- PlannerAgent: 目标规划与任务调度
- SimulationAgent: 多路径未来推演
- SafetyAgent: 风险边界检测
- ReflectionAgent: 元认知与自我反思
- Orchestrator: 中央协调与信号融合
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Callable

from brain_core.contracts import new_id, now_iso, to_dict, clamp


# ═══════════════════════════════════════════
# AgentSignal — 标准化输出
# ═══════════════════════════════════════════

@dataclass
class AgentSignal:
    """所有 Agent 的统一输出信号"""
    agent_id: str = ""          # e.g. "memory", "emotion", "planner"
    agent_name: str = ""        # human-readable name
    signal: int = 0             # +1 (同意/做多/正向), 0 (中性/观望), -1 (反对/做空/负向)
    confidence: float = 0.5     # 0.0 ~ 1.0
    reason: str = ""            # 一句话解释
    evidence: list[str] = field(default_factory=list)  # 引用来源
    warnings: list[str] = field(default_factory=list)  # 风险提示
    alternatives: list[str] = field(default_factory=list)  # 替代方案
    latency_ms: float = 0.0     # 分析耗时
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "signal": self.signal,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "evidence": self.evidence,
            "warnings": self.warnings,
            "alternatives": self.alternatives,
            "latency_ms": round(self.latency_ms, 1),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentSignal":
        return cls(
            agent_id=d.get("agent_id", ""),
            agent_name=d.get("agent_name", ""),
            signal=d.get("signal", 0),
            confidence=d.get("confidence", 0.5),
            reason=d.get("reason", ""),
            evidence=d.get("evidence", []),
            warnings=d.get("warnings", []),
            alternatives=d.get("alternatives", []),
            latency_ms=d.get("latency_ms", 0.0),
            metadata=d.get("metadata", {}),
        )

    @classmethod
    def neutral(cls, agent_id: str = "", reason: str = "") -> "AgentSignal":
        return cls(agent_id=agent_id, signal=0, confidence=0.5, reason=reason or "无明确信号")

    @classmethod
    def positive(cls, agent_id: str = "", confidence: float = 0.6, reason: str = "") -> "AgentSignal":
        return cls(agent_id=agent_id, signal=+1, confidence=confidence, reason=reason)

    @classmethod
    def negative(cls, agent_id: str = "", confidence: float = 0.6, reason: str = "") -> "AgentSignal":
        return cls(agent_id=agent_id, signal=-1, confidence=confidence, reason=reason)


# ═══════════════════════════════════════════
# AgentProtocol — 统一接口
# ═══════════════════════════════════════════

class BaseAgent:
    """Agent 基类 — Phase 6 统一协议"""

    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.stats = {"calls": 0, "errors": 0, "total_latency_ms": 0.0}
        self.rolling_window: list[dict] = []  # 最近10次决策结果

    def think(self, context: dict) -> AgentSignal:
        """子类实现: 分析上下文，返回信号"""
        raise NotImplementedError

    def record_outcome(self, was_correct: bool):
        """记录决策结果用于权重演化"""
        self.rolling_window.append({"correct": was_correct, "at": now_iso()})
        if len(self.rolling_window) > 10:
            self.rolling_window.pop(0)

    @property
    def win_rate(self) -> float:
        """滚动窗口胜率"""
        if not self.rolling_window:
            return 0.5  # 默认中性
        correct = sum(1 for r in self.rolling_window if r.get("correct"))
        return correct / len(self.rolling_window)

    @property
    def weight(self) -> float:
        """Agent权重 = 胜率，连续3次错误触发熔断"""
        wr = self.win_rate
        if len(self.rolling_window) >= 3:
            recent = self.rolling_window[-3:]
            if all(not r.get("correct") for r in recent):
                return wr * 0.5  # 熔断：权重减半
        return wr


# ═══════════════════════════════════════════
# MemoryAgent
# ═══════════════════════════════════════════

class MemoryAgent(BaseAgent):
    """记忆 Agent — 知识检索与模式匹配"""

    def __init__(self, memory=None, fast_index=None):
        super().__init__("memory", "记忆Agent")
        self.memory = memory
        self.fast_index = fast_index

    def think(self, context: dict) -> AgentSignal:
        """检索相关记忆，判断是否有已知模式

        Args:
            context: {query, topic, user_id}
        """
        query = context.get("query", context.get("topic", ""))
        if not query:
            return AgentSignal.neutral(self.agent_id, "无查询内容")

        signals = []

        # 1. Fast index search
        if self.fast_index:
            try:
                results = self.fast_index.search(query, top_k=5)
                if results and len(results) > 0:
                    top_score = results[0].get("score", 0) if isinstance(results[0], dict) else 0.5
                    signals.append({
                        "source": "fast_index",
                        "hits": len(results),
                        "top_score": top_score,
                    })
            except Exception:
                pass

        # 2. Memory engine
        if self.memory:
            try:
                mems = self.memory.search(query, top_k=3)
                if mems:
                    signals.append({"source": "memory", "hits": len(mems)})
            except Exception:
                pass

        if not signals:
            return AgentSignal.neutral(self.agent_id, "无相关记忆")

        # Synthesize
        total_hits = sum(s.get("hits", 0) for s in signals)
        max_score = max((s.get("top_score", 0.3) for s in signals if s.get("source") == "fast_index"), default=0.3)

        if total_hits >= 5:
            return AgentSignal.positive(self.agent_id, min(0.9, 0.4 + max_score),
                f"找到 {total_hits} 条相关记忆，最高匹配度 {max_score:.0%}")
        elif total_hits >= 2:
            return AgentSignal(self.agent_id, "记忆Agent", 0, 0.4,
                f"找到 {total_hits} 条弱相关记忆")
        else:
            return AgentSignal.neutral(self.agent_id, "无强相关记忆")


# ═══════════════════════════════════════════
# EmotionAgent
# ═══════════════════════════════════════════

class EmotionAgent(BaseAgent):
    """情绪 Agent — 情绪感知与关系评估"""

    def __init__(self, emotion=None):
        super().__init__("emotion", "情绪Agent")
        self.emotion = emotion

    def think(self, context: dict) -> AgentSignal:
        """分析情绪状态对决策的影响

        Args:
            context: {text, user_id}
        """
        text = context.get("text", context.get("query", ""))
        if not text or not self.emotion:
            return AgentSignal.neutral(self.agent_id, "无输入或无引擎")

        try:
            snapshot = self.emotion.get_user_snapshot()
            em = snapshot.get("emotion", {})
            rel = snapshot.get("relationship", {})

            current = em.get("current", "neutral")
            valence = em.get("valence", 0)
            closeness = rel.get("closeness", 50)

            # Positive emotion → signal +1
            if valence > 0.3:
                if closeness > 60:
                    return AgentSignal.positive(self.agent_id, min(0.9, 0.5 + abs(valence)),
                        f"积极情绪 (valence={valence:.1f}), 关系亲密 (closeness={closeness})")
                else:
                    return AgentSignal.positive(self.agent_id, 0.5 + abs(valence) * 0.5,
                        f"积极情绪 (valence={valence:.1f})")

            # Negative emotion → signal -1
            elif valence < -0.3:
                return AgentSignal.negative(self.agent_id, 0.5 + abs(valence) * 0.5,
                    f"消极情绪 '{current}' (valence={valence:.1f}), 建议谨慎行动")

            # Neutral
            return AgentSignal(self.agent_id, "情绪Agent", 0, 0.6,
                f"情绪平稳 ({current}), valence={valence:.1f}")

        except Exception:
            return AgentSignal.neutral(self.agent_id, "情绪分析异常")


# ═══════════════════════════════════════════
# PlannerAgent
# ═══════════════════════════════════════════

class PlannerAgent(BaseAgent):
    """规划 Agent — 目标可行性 + 任务冲突检测"""

    def __init__(self, goals=None, tasks=None, events=None):
        super().__init__("planner", "规划Agent")
        self.goals = goals
        self.tasks = tasks
        self.events = events

    def think(self, context: dict) -> AgentSignal:
        """评估提议行动的可行性

        Args:
            context: {action, goal_id, time_window, energy_budget}
        """
        action = context.get("action", context.get("query", ""))
        goal_id = context.get("goal_id", "")

        warnings = []
        signals = []

        # 1. Check conflicts with existing events
        if self.events:
            try:
                conflicts = self.events.check_conflicts({})
                open_conflicts = sum(
                    len(c) for c in [conflicts.get("time_overlap", []),
                                     conflicts.get("same_day", []),
                                     conflicts.get("adjacent", [])]
                )
                if open_conflicts > 0:
                    warnings.append(f"存在 {open_conflicts} 个日程冲突")
                    signals.append(-0.2)
            except Exception:
                pass

        # 2. Check goal progress
        if self.goals and goal_id:
            try:
                goal = self.goals.get_goal(goal_id)
                if goal:
                    prog = goal.get("progress", 0)
                    if prog < 0.2:
                        warnings.append(f"目标 '{goal.get('title','')}' 进度仅 {prog:.0%}，可能不切实际")
                        signals.append(-0.3)
                    elif prog > 0.7:
                        signals.append(+0.2)
            except Exception:
                pass

        # 3. Check task load
        if self.tasks:
            try:
                stats = self.tasks.stats()
                active = stats.get("active", 0)
                if active > 10:
                    warnings.append(f"活跃任务 {active} 个，负荷较高")
                    signals.append(-0.1)
                elif active <= 5:
                    signals.append(+0.1)
            except Exception:
                pass

        if not signals:
            return AgentSignal.neutral(self.agent_id, "无足够信息评估")

        avg_signal = sum(signals) / len(signals)
        confidence = min(0.9, 0.4 + abs(avg_signal) * 0.5)

        if avg_signal > 0.15:
            return AgentSignal.positive(self.agent_id, confidence,
                f"行动可行: {', '.join(warnings[:2]) if warnings else '无重大风险'}")
        elif avg_signal < -0.15:
            return AgentSignal.negative(self.agent_id, confidence,
                f"风险较高: {'; '.join(warnings[:2])}")
        else:
            return AgentSignal(self.agent_id, "规划Agent", 0, confidence,
                f"中性: {'; '.join(warnings[:2])}" if warnings else "信息不足")


# ═══════════════════════════════════════════
# SimulationAgent
# ═══════════════════════════════════════════

class SimulationAgent(BaseAgent):
    """模拟 Agent — 多路径推演与概率评估"""

    def __init__(self, goals=None):
        super().__init__("simulation", "模拟Agent")
        self.goals = goals

    def think(self, context: dict) -> AgentSignal:
        """推演行动的多条可能路径

        Args:
            context: {query/description, goal_id, time_months}
        """
        desc = context.get("query", context.get("description", ""))
        goal_id = context.get("goal_id", "")
        months = context.get("time_months", 6)

        if not desc and not goal_id:
            return AgentSignal.neutral(self.agent_id, "无目标描述")

        if not self.goals:
            return AgentSignal.neutral(self.agent_id, "模拟引擎未就绪")

        try:
            sim = self.goals.simulate_future(
                goal_id=goal_id,
                description=desc,
                time_horizon_months=months,
            )
            paths = sim.get("paths", [])
            if not paths:
                return AgentSignal.neutral(self.agent_id, "推演无结果")

            # Analyze paths
            positive = sum(1 for p in paths if p["path_type"] in ("optimistic", "most_likely"))
            negative = sum(1 for p in paths if p["path_type"] in ("pessimistic", "wildcard"))
            max_prob = max(p.get("probability", 0) for p in paths)

            if positive >= 3 and max_prob > 0.4:
                return AgentSignal.positive(self.agent_id, min(0.9, 0.4 + max_prob),
                    f"推演偏向积极 ({positive}/5 路径), 最可能概率 {max_prob:.0%}")
            elif negative >= 3:
                return AgentSignal.negative(self.agent_id, 0.4 + max_prob * 0.5,
                    f"推演偏向消极 ({negative}/5 路径), 建议缓冲预案")
            else:
                return AgentSignal(self.agent_id, "模拟Agent", 0, max_prob * 0.8,
                    f"5条推演路径概率均衡 (pos:{positive} neg:{negative})")

        except Exception:
            return AgentSignal.neutral(self.agent_id, "推演异常")


# ═══════════════════════════════════════════
# SafetyAgent
# ═══════════════════════════════════════════

class SafetyAgent(BaseAgent):
    """安全 Agent — 边界检测与风险拦截

    检查维度:
    - 承诺超载 (7天内同类型≥3个)
    - 时间冲突 (已有时段被新行动占据)
    - 精力透支 (ENERGY_COST × importance)
    - 紧急度异常 (非紧急事项占黄金时段)
    - 依赖断裂 (前置目标未达成)
    - 隐私边界 (敏感信息暴露)
    """

    RED_FLAGS = [
        "立即", "马上", "必须", "绝不允许", "我命令",
        "不顾一切", "不管后果", "删除所有",
    ]

    def __init__(self, events=None, goals=None, tasks=None):
        super().__init__("safety", "安全Agent")
        self.events = events
        self.goals = goals
        self.tasks = tasks

    def think(self, context: dict) -> AgentSignal:
        """检测行动的安全边界

        Args:
            context: {action, query, goal_id, task_id}
        """
        action = context.get("action", context.get("query", ""))
        warnings = []

        # 1. Red flag keyword detection
        red_flags = [rf for rf in self.RED_FLAGS if rf in action]
        if red_flags:
            warnings.append(f"检测到高风险关键词: {red_flags}")

        # 2. Commitment overload
        if self.events:
            try:
                conflicts = self.events.check_conflicts({})
                commitment = conflicts.get("commitment", [])
                if len(commitment) >= 3:
                    warnings.append(f"承诺超载: 7天内 {len(commitment)} 个同类型事件")
            except Exception:
                pass

        # 3. Energy overcommit
        if self.goals and self.tasks:
            try:
                stats = self.goals.stats()
                high_energy = stats.get("by_priority", {}).get("critical", 0)
                if high_energy >= 3:
                    warnings.append(f"高优先级目标 {high_energy} 个，精力可能不足")
            except Exception:
                pass

        if not warnings:
            return AgentSignal.positive(self.agent_id, 0.7, "无安全风险")

        return AgentSignal.negative(self.agent_id,
            min(0.9, 0.3 + len(warnings) * 0.2),
            f"安全风险: {'; '.join(warnings[:3])}",
            warnings=warnings)


# ═══════════════════════════════════════════
# ReflectionAgent
# ═══════════════════════════════════════════

class ReflectionAgent(BaseAgent):
    """反思 Agent — 元认知与决策回顾

    在决策后回顾:
    - 偏差检测 (确认偏误/锚定/过度自信)
    - 学习提取 (可复用的经验)
    - 策略建议 (if 再来一次会怎么做)
    """

    def __init__(self, memory=None):
        super().__init__("reflection", "反思Agent")
        self.memory = memory
        self.decisions: list[dict] = []

    def think(self, context: dict) -> AgentSignal:
        """反思最近的决策模式

        Args:
            context: {decision_id, outcome, review_mode: "post_mortem"|"periodic"}
        """
        review_mode = context.get("review_mode", "periodic")

        # Analyze recent agent signals for bias
        all_signals = context.get("signals", [])  # list of AgentSignal dicts
        if not all_signals:
            return AgentSignal.neutral(self.agent_id, "无信号可供反思")

        positive_count = sum(1 for s in all_signals if s.get("signal", 0) > 0)
        negative_count = sum(1 for s in all_signals if s.get("signal", 0) < 0)
        avg_conf = sum(s.get("confidence", 0.5) for s in all_signals) / max(len(all_signals), 1)

        insights = []

        # Bias: overconfidence
        if avg_conf > 0.8:
            insights.append(f"平均置信度 {avg_conf:.0%} 偏高，可能存在过度自信偏误")

        # Bias: optimism
        if positive_count > negative_count * 2 and len(all_signals) >= 3:
            insights.append(f"正向信号占比 {positive_count}/{len(all_signals)}，确认偏误风险")

        # Bias: pessimism
        if negative_count > positive_count * 2 and len(all_signals) >= 3:
            insights.append(f"负向信号占比 {negative_count}/{len(all_signals)}，可能过度谨慎")

        if not insights:
            return AgentSignal.positive(self.agent_id, 0.6, "信号分布合理，无明显偏误")

        return AgentSignal(self.agent_id, "反思Agent", 0, 0.5,
            f"检测到 {len(insights)} 个偏误信号: {insights[0]}",
            warnings=insights)


# ═══════════════════════════════════════════
# Signal Fusion
# ═══════════════════════════════════════════

class SignalFusion:
    """信号融合引擎 — Phase 6 核心公式"""

    @staticmethod
    def fuse(signals: list[AgentSignal], weights: dict[str, float] = None) -> dict:
        """加权信号融合

        Fusion_Score = Σ(W_i × Signal_i × Confidence_i) / Σ(W_i)

        Returns:
            {score, direction, confidence, signals_detail, requires_debate}
        """
        if not signals:
            return {"score": 0.0, "direction": "neutral", "confidence": 0.0,
                    "signals_detail": [], "requires_debate": False}

        if weights is None:
            weights = {}

        total_w = 0.0
        weighted_sum = 0.0
        details = []

        for s in signals:
            w = weights.get(s.agent_id, 0.5)  # default weight 0.5
            # If agent has its own rolling window win_rate, use it
            w = max(0.1, min(1.0, w))

            contribution = w * s.signal * s.confidence
            weighted_sum += contribution
            total_w += max(w, 0.01)
            details.append({
                "agent_id": s.agent_id,
                "agent_name": s.agent_name,
                "signal": s.signal,
                "confidence": s.confidence,
                "weight": round(w, 2),
                "contribution": round(contribution, 3),
                "reason": s.reason,
            })

        fusion_score = round(weighted_sum / max(total_w, 0.01), 3)

        if fusion_score > 0.3:
            direction = "positive"
            confidence = min(0.95, 0.5 + abs(fusion_score))
            requires_debate = False
        elif fusion_score < -0.3:
            direction = "negative"
            confidence = min(0.95, 0.5 + abs(fusion_score))
            requires_debate = False
        else:
            direction = "neutral"
            confidence = 0.5
            requires_debate = abs(fusion_score) <= 0.3

        return {
            "score": fusion_score,
            "direction": direction,
            "confidence": round(confidence, 2),
            "signals_detail": details,
            "requires_debate": requires_debate,
            "agent_count": len(signals),
        }


# ═══════════════════════════════════════════
# Debate System
# ═══════════════════════════════════════════

class DebateSystem:
    """冲突升级辩论系统

    当核心Agent信号方向相反时:
    1. Bull Advocate 综合所有看多理由
    2. Bear Advocate 综合所有看空风险
    3. Judge 裁决 → 返回最终信号
    """

    @staticmethod
    def debate(signals: list[AgentSignal]) -> dict:
        """执行 Bull vs Bear debate

        Returns:
            {verdict, bull_case, bear_case, judge_reasoning, final_signal}
        """
        bull = [s for s in signals if s.signal > 0]
        bear = [s for s in signals if s.signal < 0]
        neutral = [s for s in signals if s.signal == 0]

        # Bull case: aggregate all positive reasons
        bull_reasons = [f"[{s.agent_name}] {s.reason}" for s in bull]
        bull_confidence = sum(s.confidence for s in bull) / max(len(bull), 1) if bull else 0
        bull_total = len(bull)

        # Bear case: aggregate all negative reasons
        bear_reasons = [f"[{s.agent_name}] {s.reason}" for s in bear]
        bear_confidence = sum(s.confidence for s in bear) / max(len(bear), 1) if bear else 0
        bear_total = len(bear)

        # Judge: weighted by count × confidence
        bull_score = bull_total * bull_confidence
        bear_score = bear_total * bear_confidence

        if bull_score > bear_score * 1.5:
            # Bull wins
            verdict = "bull"
            final_signal = +1
            final_confidence = min(0.9, bull_confidence * 0.9)
            reason = f"看多理由更强: {bull_total}个vs{bear_total}个, 信度 {bull_confidence:.0%}vs{bear_confidence:.0%}"
        elif bear_score > bull_score * 1.5:
            # Bear wins
            verdict = "bear"
            final_signal = -1
            final_confidence = min(0.9, bear_confidence * 0.9)
            reason = f"看空理由更强: {bear_total}个vs{bull_total}个, 信度 {bear_confidence:.0%}vs{bull_confidence:.0%}"
        elif bull_score >= bear_score:
            # Tilt bull
            verdict = "lean_bull"
            final_signal = +1
            final_confidence = 0.5 + (bull_score - bear_score) * 0.5
            reason = f"看多看空接近 (bull={bull_total} bear={bear_total}), 略偏多做多"
        else:
            # Tilt bear
            verdict = "lean_bear"
            final_signal = -1
            final_confidence = 0.5 + (bear_score - bull_score) * 0.5
            reason = f"看多看空接近 (bull={bull_total} bear={bear_total}), 略偏空规避"

        return {
            "verdict": verdict,
            "final_signal": final_signal,
            "final_confidence": round(final_confidence, 2),
            "judge_reasoning": reason,
            "bull_case": {"agents": len(bull), "reasons": bull_reasons, "avg_confidence": round(bull_confidence, 2)},
            "bear_case": {"agents": len(bear), "reasons": bear_reasons, "avg_confidence": round(bear_confidence, 2)},
            "neutral_agents": len(neutral),
        }


# ═══════════════════════════════════════════
# Audit Trail
# ═══════════════════════════════════════════

@dataclass
class DecisionAudit:
    """决策审计记录"""
    id: str = field(default_factory=lambda: new_id("audit"))
    query: str = ""
    context_summary: str = ""
    signals: list[dict] = field(default_factory=list)
    fusion: dict = field(default_factory=dict)
    debate: dict | None = None
    final_decision: str = ""
    final_signal: int = 0
    final_confidence: float = 0.5
    action_taken: str = ""
    outcome: str = ""
    was_correct: bool | None = None
    created_at: str = field(default_factory=now_iso)
    resolved_at: str = ""
    metadata: dict = field(default_factory=dict)


class AuditTrail:
    """决策审计管理器"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.audit_dir = data_dir / "decision_audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def record(self, audit: DecisionAudit):
        path = self.audit_dir / f"{audit.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(to_dict(audit), f, ensure_ascii=False, indent=2)

    def list_recent(self, limit: int = 20) -> list[dict]:
        files = sorted(self.audit_dir.glob("audit_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        results = []
        for f in files[:limit]:
            with open(f, "r", encoding="utf-8") as fp:
                results.append(json.load(fp))
        return results

    def get(self, audit_id: str) -> dict | None:
        path = self.audit_dir / f"{audit_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def update_outcome(self, audit_id: str, outcome: str, was_correct: bool):
        path = self.audit_dir / f"{audit_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                record = json.load(f)
            record["outcome"] = outcome
            record["was_correct"] = was_correct
            record["resolved_at"] = now_iso()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════
# Orchestrator — 中央协调
# ═══════════════════════════════════════════

class Orchestrator:
    """Orchestrator — Phase 6 中央仲裁

    协调所有 Agent 完成一次完整决策:
    1. 分发 context 给各 Agent
    2. 收集 AgentSignal 列表
    3. 信号融合 (SignalFusion.fuse)
    4. 如果需要 → 升级辩论 (DebateSystem.debate)
    5. 记录审计 (AuditTrail.record)
    6. 通知各 Agent 更新权重 (record_outcome)
    """

    def __init__(self, data_dir: Path):
        self.agents: dict[str, BaseAgent] = {}
        self.fusion = SignalFusion()
        self.debate = DebateSystem()
        self.audit = AuditTrail(data_dir)
        self.data_dir = data_dir
        self.weights_path = data_dir / "agent_weights.json"
        self.weights = self._load_weights()

    def _load_weights(self) -> dict:
        try:
            with open(self.weights_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_weights(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.weights_path, "w", encoding="utf-8") as f:
            json.dump(self.weights, f, ensure_ascii=False, indent=2)

    def register(self, agent: BaseAgent):
        """注册 Agent"""
        self.agents[agent.agent_id] = agent
        # Initialize weight from rolling window win_rate
        if agent.agent_id not in self.weights:
            self.weights[agent.agent_id] = agent.weight

    def unregister(self, agent_id: str):
        self.agents.pop(agent_id, None)
        self.weights.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        return self.agents.get(agent_id)

    def orchestrate(self, query: str, context: dict = None,
                    agent_ids: list[str] = None,
                    auto_debate: bool = True) -> dict:
        """执行完整决策流程

        Args:
            query: 决策问题
            context: 额外上下文
            agent_ids: 指定参与的 Agent (默认全部)
            auto_debate: 自动触发辩论

        Returns:
            {decision, fusion, debate, signals, audit_id}
        """
        if context is None:
            context = {}
        context["query"] = query

        # 1. Select agents
        if agent_ids is None:
            candidates = list(self.agents.values())
        else:
            candidates = [a for aid, a in self.agents.items() if aid in agent_ids]

        if not candidates:
            return {"error": "No agents available", "decision": "wait"}

        # 2. Collect signals (simulate parallel)
        signals = []
        for agent in candidates:
            try:
                t0 = datetime.now(timezone.utc)
                signal = agent.think(context)
                signal.agent_id = signal.agent_id or agent.agent_id
                signal.agent_name = signal.agent_name or agent.agent_name
                signal.latency_ms = (datetime.now(timezone.utc) - t0).total_seconds() * 1000
                signals.append(signal)
                agent.stats["calls"] += 1
                agent.stats["total_latency_ms"] += signal.latency_ms
            except Exception as e:
                agent.stats["errors"] += 1
                signals.append(AgentSignal.neutral(agent.agent_id, f"Error: {str(e)[:80]}"))

        # 3. Update weights from rolling windows
        for agent in candidates:
            self.weights[agent.agent_id] = agent.weight
        self._save_weights()

        # 4. Signal fusion
        fusion_result = self.fusion.fuse(signals, self.weights)

        # 5. Debate if needed
        debate_result = None
        final_signal = 0
        final_confidence = fusion_result["confidence"]

        if fusion_result["requires_debate"] and auto_debate and len(signals) >= 3:
            debate_result = self.debate.debate(signals)
            final_signal = debate_result["final_signal"]
            final_confidence = debate_result["final_confidence"]
            final_decision = f"辩论裁决: {debate_result['verdict']}"
        else:
            final_signal = 1 if fusion_result["score"] > 0 else (-1 if fusion_result["score"] < 0 else 0)
            final_decision = fusion_result["direction"]

        # 6. Generate action
        action_map = {
            1: "proceed",     # 推荐执行
            0: "wait",        # 观望/收集更多信息
            -1: "avoid",      # 不建议执行
        }
        action = action_map.get(final_signal, "wait")

        # 7. Audit
        audit_record = DecisionAudit(
            query=query,
            context_summary=str(context.get("summary", query))[:200],
            signals=[s.to_dict() for s in signals],
            fusion=fusion_result,
            debate=debate_result,
            final_decision=final_decision,
            final_signal=final_signal,
            final_confidence=final_confidence,
            action_taken=action,
        )
        self.audit.record(audit_record)

        # 8. Return
        signal_labels = ["avoid ⛔", "wait ⏸", "proceed ✅"]
        return {
            "query": query,
            "decision": final_decision,
            "action": action,
            "signal": final_signal,
            "signal_label": signal_labels[final_signal + 1],
            "confidence": final_confidence,
            "fusion": fusion_result,
            "debate": debate_result,
            "agents_consulted": [s.agent_id for s in signals],
            "signals": [s.to_dict() for s in signals],
            "audit_id": audit_record.id,
            "audit_dir": str(self.audit.audit_dir),
        }

    def record_outcome(self, audit_id: str, outcome: str, was_correct: bool, signals: list[dict] = None):
        """记录决策结果，更新各 Agent 胜率"""
        self.audit.update_outcome(audit_id, outcome, was_correct)

        # Update each agent's rolling window
        if signals:
            for sig in signals:
                agent = self.agents.get(sig.get("agent_id", ""))
                if agent:
                    agent.record_outcome(was_correct)
                    self.weights[agent.agent_id] = agent.weight

        self._save_weights()

    def get_weights(self) -> dict:
        """获取当前权重快照 (含熔断状态)"""
        result = {}
        for aid, agent in self.agents.items():
            result[aid] = {
                "weight": round(self.weights.get(aid, 0.5), 3),
                "win_rate": round(agent.win_rate, 2),
                "window": len(agent.rolling_window),
                "is_circuit_breaker": (
                    len(agent.rolling_window) >= 3 and
                    all(not r.get("correct") for r in agent.rolling_window[-3:])
                ),
            }
        return result

    def stats(self) -> dict:
        return {
            "agents": {
                aid: {
                    "name": a.agent_name,
                    "calls": a.stats["calls"],
                    "errors": a.stats["errors"],
                    "win_rate": round(a.win_rate, 2),
                    "weight": round(self.weights.get(aid, 0.5), 3),
                    "avg_latency_ms": round(a.stats["total_latency_ms"] / max(a.stats["calls"], 1), 1),
                }
                for aid, a in self.agents.items()
            },
            "total_decisions": len(self.audit.list_recent(1000)),
        }
