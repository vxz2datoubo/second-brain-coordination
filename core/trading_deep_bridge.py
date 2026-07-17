"""
trading_deep_bridge.py — 交易系统与深度学习集成桥接
==================================================
将深度学习模块与交易系统深度集成，实现智能交易决策。

功能:
1. 深度学习信号生成
2. 情境感知决策
3. 持续学习交易策略
4. 多模型集成

集成架构:
┌─────────────────────────────────────────────────────────────┐
│                  TradingDeepBridge                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐ │
│  │ DeepBrain    │     │ TradingBrain │     │ 规则系统   │ │
│  │ (深度推理)   │────>│  (交易引擎)  │<────│ (风控/规则)│ │
│  └──────────────┘     └──────────────┘     └────────────┘ │
│         │                    │                     │          │
│         └────────────────────┼─────────────────────┘        │
│                              │                              │
│                    ┌─────────▼─────────┐                   │
│                    │  UnifiedSignal    │                   │
│                    │   (统一信号)       │                   │
│                    └───────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from core.deep_memory_integration import UnifiedBrain, get_unified_brain
from core.episodic_memory import EpisodicMemory, get_episodic_memory
from core.continual_learning import ContinualLearningEngine, get_continual_learner


# ========== 交易信号定义 ==========

@dataclass
class TradingSignal:
    """交易信号"""
    action: str              # "buy", "sell", "hold"
    confidence: float        # 置信度 0-1
    reasoning: str          # 推理说明
    
    # 信号来源
    signal_sources: Dict[str, float] = field(default_factory=dict)
    
    # 风险评估
    risk_level: str = "medium"  # "low", "medium", "high", "extreme"
    stop_loss: float = 0.0
    take_profit: float = 0.0
    
    # 上下文
    stock_code: str = ""
    stock_name: str = ""
    current_price: float = 0.0
    timestamp: str = ""
    
    # 历史对比
    similar_episodes: int = 0
    historical_win_rate: float = 0.0


@dataclass
class MarketContext:
    """市场上下文"""
    stock_code: str
    stock_name: str
    current_price: float
    change_pct: float
    volume_ratio: float
    avg_volume: float
    
    market_trend: str = "neutral"  # "up", "down", "neutral"
    volatility: str = "medium"     # "high", "medium", "low"
    market_sentiment: str = "neutral"
    
    # 时间窗口
    time_window: str = "T2"  # T1-T8
    
    # 新闻
    recent_news: List[Dict] = field(default_factory=list)
    
    # 持仓
    position: Optional[Dict] = None


# ========== 交易深度学习桥接 ==========

class TradingDeepBridge:
    """
    交易深度学习桥接
    
    整合深度大脑与交易系统，提供智能交易决策
    """
    
    def __init__(self, graph, data_dir: Path):
        self.data_dir = data_dir
        
        # 初始化深度学习模块
        self.unified_brain = get_unified_brain(graph, data_dir)
        self.episodic_memory = get_episodic_memory(data_dir)
        self.continual_learner = get_continual_learner(data_dir)
        
        # 信号融合权重
        self.signal_weights = {
            "deep_brain": 0.35,      # 深度大脑
            "episodic": 0.30,        # 情景记忆
            "meta_learner": 0.20,   # 元学习
            "rules": 0.15            # 规则系统
        }
    
    def generate_signal(self, context: MarketContext) -> TradingSignal:
        """
        生成交易信号
        
        整合多个模块的信号，生成统一的交易建议
        """
        signal = TradingSignal(
            action="hold",
            confidence=0.0,
            reasoning="分析中...",
            stock_code=context.stock_code,
            stock_name=context.stock_name,
            current_price=context.current_price,
            timestamp=datetime.now().isoformat()
        )
        
        # 1. 获取深度大脑决策
        deep_result = self._get_deep_brain_signal(context)
        signal.signal_sources["deep_brain"] = deep_result["confidence"]
        
        # 2. 获取情景记忆建议
        episodic_result = self._get_episodic_advice(context)
        signal.signal_sources["episodic"] = episodic_result["confidence"]
        signal.similar_episodes = episodic_result.get("similar_experiences", 0)
        signal.historical_win_rate = episodic_result.get("success_rate", 0.0)
        
        # 3. 获取元学习决策
        meta_result = self._get_meta_decision(context)
        signal.signal_sources["meta_learner"] = meta_result["confidence"]
        
        # 4. 获取规则系统判断
        rules_result = self._get_rules_check(context)
        signal.signal_sources["rules"] = rules_result["confidence"]
        
        # 5. 融合信号
        final_action, final_confidence = self._fuse_signals(signal.signal_sources)
        
        signal.action = final_action
        signal.confidence = final_confidence
        
        # 6. 风险评估
        signal.risk_level = self._assess_risk(context, signal)
        
        # 7. 计算止盈止损
        if signal.action != "hold":
            signal.stop_loss, signal.take_profit = self._calculate_targets(
                context, signal
            )
        
        # 8. 生成推理说明
        signal.reasoning = self._generate_reasoning(context, signal, {
            "deep_brain": deep_result,
            "episodic": episodic_result,
            "meta": meta_result,
            "rules": rules_result
        })
        
        return signal
    
    def _get_deep_brain_signal(self, context: MarketContext) -> Dict:
        """获取深度大脑信号"""
        situation = f"{context.stock_name} {context.market_trend} 市场交易"
        
        deep_context = {
            "market_trend": context.market_trend,
            "change_pct": context.change_pct,
            "volatility": context.volatility,
            "volume_ratio": context.volume_ratio,
            "buy_signal": context.change_pct > 2,
            "volume_surge": context.volume_ratio > 1.5
        }
        
        result = self.unified_brain.think(situation, deep_context)
        
        return {
            "action": result.get("decision", "hold"),
            "confidence": result.get("confidence", 0.5),
            "reasoning": result
        }
    
    def _get_episodic_advice(self, context: MarketContext) -> Dict:
        """获取情景记忆建议"""
        situation = {
            "market_trend": context.market_trend,
            "volatility": context.volatility,
            "price_change": context.change_pct,
            "volume_ratio": context.volume_ratio,
            "action": "hold"
        }
        
        advice = self.episodic_memory.get_action_advice(situation)
        
        return advice
    
    def _get_meta_decision(self, context: MarketContext) -> Dict:
        """获取元学习决策"""
        from core.meta_learning import get_meta_learner
        
        meta_learner = get_meta_learner(self.data_dir)
        
        # 判断市场状态
        if context.change_pct > 3:
            market_condition = "trending"
        elif context.change_pct < -3:
            market_condition = "volatile"
        else:
            market_condition = "range"
        
        decision = meta_learner.decide(
            market_condition=market_condition,
            stock_type="tech",
            context={
                "change_pct": context.change_pct,
                "volume_ratio": context.volume_ratio,
                "trend_strength": abs(context.change_pct) / 5
            }
        )
        
        return decision
    
    def _get_rules_check(self, context: MarketContext) -> Dict:
        """获取规则系统检查"""
        warnings = []
        can_buy = True
        can_sell = True
        
        # 买入规则检查
        if context.market_trend == "down":
            can_buy = False
            warnings.append("下跌趋势禁止追高买入")
        
        if context.time_window == "T1" and not context.position:
            can_buy = False
            warnings.append("开盘30分钟内禁止买入（无持仓）")
        
        if context.change_pct < -5 and context.position:
            warnings.append("持仓跌幅超5%谨慎补仓")
        
        # 卖出规则检查
        if context.market_trend == "up" and context.change_pct > 3:
            can_sell = False
            warnings.append("上涨趋势建议持有")
        
        # 计算置信度
        if not warnings:
            confidence = 0.8
        elif len(warnings) == 1:
            confidence = 0.6
        else:
            confidence = 0.4
        
        return {
            "can_buy": can_buy,
            "can_sell": can_sell,
            "warnings": warnings,
            "confidence": confidence
        }
    
    def _fuse_signals(self, signals: Dict[str, float]) -> Tuple[str, float]:
        """融合多个信号"""
        action_scores = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        
        for source, confidence in signals.items():
            weight = self.signal_weights.get(source, 0.25)
            
            # 模拟不同源的行动建议
            if source == "deep_brain" and confidence > 0.6:
                action_scores["buy"] += weight * 0.8
                action_scores["sell"] += weight * 0.1
            elif source == "episodic" and confidence > 0.5:
                # 基于历史胜率调整
                if confidence > 0.6:
                    action_scores["buy"] += weight * 0.6
                    action_scores["sell"] += weight * 0.2
                else:
                    action_scores["hold"] += weight * 0.5
            elif source == "meta_learner":
                # 元学习直接输出
                pass
            elif source == "rules":
                # 规则约束
                if confidence < 0.5:
                    action_scores["buy"] *= 0.5
                    action_scores["sell"] *= 0.5
        
        # 选择最高分
        best_action = max(action_scores.items(), key=lambda x: x[1])
        return best_action[0], best_action[1]
    
    def _assess_risk(self, context: MarketContext, signal: TradingSignal) -> str:
        """评估风险等级"""
        risk_factors = []
        
        # 波动性风险
        if context.volatility == "high":
            risk_factors.append("高波动")
        
        # 位置风险
        if context.change_pct > 5:
            risk_factors.append("价格异动")
        
        # 仓位风险
        if context.position and context.position.get("size", 0) > 0.8:
            risk_factors.append("重仓")
        
        # 规则风险
        if context.time_window not in ["T2", "T6"]:
            risk_factors.append("非常规时间")
        
        # 新闻风险
        if len(context.recent_news) > 3:
            risk_factors.append("多新闻干扰")
        
        # 综合评估
        if len(risk_factors) >= 3 or "价格异动" in risk_factors:
            return "high"
        elif len(risk_factors) >= 2 or "高波动" in risk_factors:
            return "medium"
        elif len(risk_factors) == 1:
            return "low"
        else:
            return "low"
    
    def _calculate_targets(self, context: MarketContext, 
                          signal: TradingSignal) -> Tuple[float, float]:
        """计算止盈止损"""
        price = context.current_price
        
        # 根据风险等级调整
        if signal.risk_level == "high":
            stop_loss = price * 0.97  # 3%止损
            take_profit = price * 1.03  # 3%止盈
        elif signal.risk_level == "medium":
            stop_loss = price * 0.98  # 2%止损
            take_profit = price * 1.04  # 4%止盈
        else:
            stop_loss = price * 0.985  # 1.5%止损
            take_profit = price * 1.05  # 5%止盈
        
        return stop_loss, take_profit
    
    def _generate_reasoning(self, context: MarketContext, signal: TradingSignal,
                            detailed: Dict) -> str:
        """生成推理说明"""
        reasons = []
        
        # 深度大脑分析
        if detailed["deep_brain"].get("reasoning"):
            reasons.append("深度大脑分析完成")
        
        # 情景记忆参考
        if signal.similar_episodes > 0:
            reasons.append(
                f"找到{signal.similar_episodes}个相似情景，"
                f"历史胜率{signal.historical_win_rate:.0%}"
            )
        
        # 规则检查
        if detailed["rules"].get("warnings"):
            reasons.extend(detailed["rules"]["warnings"][:2])
        
        # 风险提示
        if signal.risk_level != "low":
            reasons.append(f"风险等级: {signal.risk_level}")
        
        return "；".join(reasons) if reasons else "综合分析无明显信号，建议观望"
    
    # ========== 经验记录与学习 ==========
    
    def record_decision(self, context: MarketContext, signal: TradingSignal, 
                        outcome: Optional[float] = None,
                        reflection: str = ""):
        """
        记录决策结果
        
        用于持续学习和经验积累
        """
        # 1. 记录情景记忆
        from core.episodic_memory import Episode
        
        episode = Episode(
            id="",
            timestamp=signal.timestamp,
            situation_type=context.market_trend,
            market_trend=context.market_trend,
            volatility=context.volatility,
            price_change=context.change_pct,
            volume_ratio=context.volume_ratio,
            sector_performance=0.0,
            action=signal.action,
            position_size=context.position.get("size", 0) if context.position else 0,
            confidence=signal.confidence,
            outcome=outcome,
            reflection=reflection,
            stock_code=context.stock_code,
            stock_name=context.stock_name,
            tags=["trading", signal.action]
        )
        
        episode_id = self.episodic_memory.record(episode)
        
        # 2. 记录持续学习任务
        if outcome is not None:
            from core.continual_learning import LearningTask
            
            task = LearningTask(
                id="",
                name=f"{context.stock_code}_{signal.action}_{datetime.now().strftime('%Y%m%d')}",
                timestamp=datetime.now().isoformat(),
                category="trading",
                samples=[{
                    "price_change": context.change_pct,
                    "volume_ratio": context.volume_ratio,
                    "market_trend": context.market_trend,
                    "action": signal.action
                }],
                labels=[outcome],
                before_performance=0.5,
                after_performance=0.5 + outcome
            )
            
            self.continual_learner.learn_task(task)
        
        return episode_id
    
    # ========== 统计与分析 ==========
    
    def get_trading_insights(self) -> Dict:
        """获取交易洞察"""
        return {
            "episodic_memory": self.episodic_memory.get_stats(),
            "continual_learning": self.continual_learner.get_stats(),
            "deep_brain": self.unified_brain.get_full_stats(),
            "signal_weights": self.signal_weights
        }


# ========== 便捷函数 ==========

_trading_bridge: Optional[TradingDeepBridge] = None


def get_trading_bridge(graph, data_dir: Path) -> TradingDeepBridge:
    """获取交易深度学习桥接"""
    global _trading_bridge
    if _trading_bridge is None:
        _trading_bridge = TradingDeepBridge(graph, data_dir)
    return _trading_bridge
