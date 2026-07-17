"""
market_detective.py — 市场侦探引擎
=========================================
识别主力行为、追踪资金流向、判断个股是否有庄、分析庄家意图。
这是大奖章级别量化的核心技术之一。

核心理论：
1. 资金流分析：大单代表主力，小单代表散户
2. 筹码分布：获利盘/套牢盘分析
3. 量价关系：缩量、放量、堆量的含义
4. 分时图分析：日内主力痕迹
5. 龙虎榜数据：机构席位追踪

设计理念：
- 像侦探一样分析市场
- 不相信表面的涨跌，要找背后的真相
- 通过多重证据链确认判断
"""

import json
import math
import uuid
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter


@dataclass
class MoneyFlow:
    """资金流向数据"""
    large_buy: float = 0.0      # 大单买入
    large_sell: float = 0.0     # 大单卖出
    small_buy: float = 0.0      # 小单买入
    small_sell: float = 0.0     # 小单卖出
    net_flow: float = 0.0       # 净流入
    flow_direction: str = "neutral"  # 流入/流出/中性
    mainforce_score: float = 0.0 # 主力参与度 0-1


@dataclass
class ChipDistribution:
    """筹码分布"""
    cost_center: float = 0.0    # 成本集中区
    profit_ratio: float = 0.0   # 获利盘比例
    loss_ratio: float = 0.0     # 套牢盘比例
    concentration: float = 0.0   # 集中度
    density_curve: List[dict] = field(default_factory=list)


@dataclass
class DetectiveReport:
    """侦探报告"""
    has_mainforce: bool = False           # 是否有主力
    confidence: float = 0.0              # 判断置信度
    mainforce_type: str = ""             # 主力类型
    mainforce_intent: str = ""           # 主力意图
    evidence_chain: List[dict] = field(default_factory=list)  # 证据链
    money_flow: Optional[MoneyFlow] = None
    chip_distribution: Optional[ChipDistribution] = None
    risk_signals: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    verdict: str = ""                    # 侦探结论


class MarketDetective:
    """市场侦探引擎
    
    核心能力：
    1. 资金流向追踪 — 分辨大单小单，判断主力动向
    2. 庄家识别 — 通过多重特征识别是否有庄
    3. 筹码分析 — 成本分布、获利盘、套牢盘
    4. 量价分析 — 识别放量、缩量、堆量的含义
    5. 异动检测 — 异常交易的预警
    """
    
    # 大单标准（可根据股票市值调整）
    LARGE_ORDER_THRESHOLD = 500  # 万元
    
    # 主力类型特征
    MAINFORCE_TYPES = {
        "long_term": {
            "name": "长庄",
            "signals": ["长期横盘", "量能稳定", "股东减少"],
            "behavior": "慢慢吸筹，长期控盘"
        },
        "short_term": {
            "name": "短庄",
            "signals": ["短期拉升", "高位放量", "快进快出"],
            "behavior": "短期炒作，快进快出"
        },
        "hot_money": {
            "name": "游资",
            "signals": ["涨停板", "连续拉升", "龙虎榜"],
            "behavior": "题材炒作，追求连板"
        },
        "institution": {
            "name": "机构",
            "signals": ["稳健上涨", "下跌缩量", "业绩驱动"],
            "behavior": "价值投资，稳健操作"
        },
        "none": {
            "name": "无主力",
            "signals": ["跟随大盘", "量能萎缩", "无明显控盘"],
            "behavior": "随波逐流，无明显主力"
        }
    }
    
    # 量价异动模式
    VOLUME_PRICE_PATTERNS = {
        "absorption": {
            "name": "吸筹模式",
            "signals": ["下跌缩量", "尾盘拉升", "低位横盘"],
            "interpretation": "主力在收集筹码"
        },
        "distribution": {
            "name": "派发模式",
            "signals": ["上涨放量", "日内震仓", "利好频出"],
            "interpretation": "主力在出货"
        },
        "shakeout": {
            "name": "震仓模式",
            "signals": ["快速杀跌", "快速拉回", "量能放大"],
            "interpretation": "主力在清洗浮筹"
        },
        "breakout": {
            "name": "突破模式",
            "signals": ["放量突破", "缩量回调", "再次放量"],
            "interpretation": "有效突破，后续看涨"
        },
        "fake_break": {
            "name": "假突破模式",
            "signals": ["突破后回落", "量能不足", "快速跌回"],
            "interpretation": "主力诱多，警惕风险"
        }
    }
    
    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.state_path = data_dir / "market_detective_state.json"
        self.state = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "stock_profiles": {},  # 股票画像
                "evidence_log": [],    # 证据记录
                "alerts": [],          # 预警记录
                "meta": {"total_investigations": 0}
            }
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    # ========== 主分析方法 ==========
    
    def investigate(
        self,
        stock: str,
        price_history: List[dict],
        volume_data: List[dict],
        minute_data: Optional[List[dict]] = None,
        news: Optional[List[dict]] = None,
    ) -> DetectiveReport:
        """综合调查
        
        Args:
            stock: 股票代码
            price_history: 历史价格数据
            volume_data: 成交量数据
            minute_data: 分时数据
            news: 相关新闻
        
        Returns:
            DetectiveReport: 侦探报告
        """
        report = DetectiveReport()
        evidence_chain = []
        
        # 1. 分析资金流向
        money_flow = self._analyze_money_flow(volume_data, minute_data)
        report.money_flow = money_flow
        evidence_chain.append({
            "type": "money_flow",
            "finding": f"主力参与度: {money_flow.mainforce_score:.0%}",
            "direction": money_flow.flow_direction,
            "confidence": 0.8 if money_flow.mainforce_score > 0.3 else 0.5
        })
        
        # 2. 分析筹码分布
        chips = self._analyze_chip_distribution(price_history, volume_data)
        report.chip_distribution = chips
        evidence_chain.append({
            "type": "chip_distribution",
            "finding": f"获利盘{chips.profit_ratio:.0%}, 成本集中{chips.cost_center:.2f}",
            "concentration": chips.concentration,
            "confidence": 0.7
        })
        
        # 3. 识别量价模式
        pattern = self._identify_volume_pattern(price_history, volume_data)
        evidence_chain.append({
            "type": "volume_pattern",
            "finding": pattern["name"],
            "interpretation": pattern["interpretation"],
            "confidence": pattern["confidence"]
        })
        
        # 4. 检测异动
        anomalies = self._detect_anomalies(price_history, volume_data, minute_data)
        if anomalies:
            evidence_chain.append({
                "type": "anomaly",
                "finding": f"发现{len(anomalies)}项异常",
                "details": anomalies,
                "confidence": 0.85
            })
        
        # 5. 整合证据链，判断是否有主力
        verdict = self._build_verdict(evidence_chain, money_flow, chips, pattern)
        
        report.has_mainforce = verdict["has_mainforce"]
        report.confidence = verdict["confidence"]
        report.mainforce_type = verdict["mainforce_type"]
        report.mainforce_intent = verdict["intent"]
        report.evidence_chain = evidence_chain
        report.risk_signals = verdict["risk_signals"]
        report.opportunities = verdict["opportunities"]
        report.verdict = verdict["conclusion"]
        
        # 记录调查历史
        self._record_investigation(stock, report)
        
        return report
    
    def _analyze_money_flow(
        self,
        volume_data: List[dict],
        minute_data: Optional[List[dict]] = None
    ) -> MoneyFlow:
        """分析资金流向"""
        flow = MoneyFlow()
        
        if not volume_data:
            return flow
        
        # 从分时数据中分析大单小单
        if minute_data:
            for minute in minute_data:
                volume = minute.get("volume", 0)
                if volume > self.LARGE_ORDER_THRESHOLD:
                    # 大单
                    if minute.get("price", 0) >= minute.get("last_close", 0):
                        flow.large_buy += volume
                    else:
                        flow.large_sell += volume
                else:
                    # 小单
                    if minute.get("price", 0) >= minute.get("last_close", 0):
                        flow.small_buy += volume
                    else:
                        flow.small_sell += volume
        else:
            # 从日线数据粗略估算
            for day in volume_data[-5:]:
                vol = day.get("volume", 0)
                change = day.get("change_pct", 0)
                if change > 0:
                    flow.large_buy += vol * 0.3
                    flow.small_buy += vol * 0.7
                else:
                    flow.large_sell += vol * 0.3
                    flow.small_sell += vol * 0.7
        
        flow.net_flow = (flow.large_buy + flow.small_buy) - (flow.large_sell + flow.small_sell)
        
        # 判断流向
        if flow.net_flow > 0:
            flow.flow_direction = "inflow"
        elif flow.net_flow < 0:
            flow.flow_direction = "outflow"
        else:
            flow.flow_direction = "neutral"
        
        # 计算主力参与度
        total_volume = flow.large_buy + flow.large_sell
        if total_volume > 0:
            main_volume = flow.large_buy - flow.large_sell
            flow.mainforce_score = min(1.0, abs(main_volume) / total_volume * 2)
        
        return flow
    
    def _analyze_chip_distribution(
        self,
        price_history: List[dict],
        volume_data: List[dict]
    ) -> ChipDistribution:
        """分析筹码分布"""
        chips = ChipDistribution()
        
        if len(price_history) < 20:
            return chips
        
        # 简化计算：基于价格区间估算
        prices = [d.get("close", 0) for d in price_history]
        avg_price = sum(prices) / len(prices)
        current_price = prices[-1]
        
        chips.cost_center = avg_price
        
        # 获利盘比例
        low_price = min(prices)
        high_price = max(prices)
        if high_price > low_price:
            chips.profit_ratio = max(0, min(1, (current_price - low_price) / (high_price - low_price)))
        chips.loss_ratio = 1 - chips.profit_ratio
        
        # 集中度（基于价格波动）
        price_std = math.sqrt(sum((p - avg_price) ** 2 for p in prices) / len(prices))
        chips.concentration = 1 - min(1, price_std / avg_price)
        
        return chips
    
    def _identify_volume_pattern(
        self,
        price_history: List[dict],
        volume_data: List[dict]
    ) -> dict:
        """识别量价模式"""
        if len(volume_data) < 5:
            return {"name": "未知", "interpretation": "数据不足", "confidence": 0.3}
        
        # 计算各项指标
        recent_volumes = [v.get("volume", 0) for v in volume_data[-5:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        
        recent_changes = [p.get("change_pct", 0) for p in price_history[-5:]]
        recent_closes = [p.get("close", 0) for p in price_history[-5:]]
        
        # 判断模式
        volume_ratio = recent_volumes[-1] / max(avg_volume, 1)
        price_change = recent_changes[-1]
        
        # 模式识别
        if price_change < -1 and volume_ratio < 0.7:
            # 下跌缩量
            if len(recent_closes) > 5 and all(recent_closes[-i] < recent_closes[-i-1] for i in range(1, 4)):
                pattern = "absorption"  # 吸筹
            else:
                pattern = "shakeout"  # 震仓
            return self.VOLUME_PRICE_PATTERNS[pattern]
        
        elif price_change > 1 and volume_ratio > 1.5:
            # 上涨放量
            if volume_ratio > 2.5:
                return self.VOLUME_PRICE_PATTERNS["distribution"]  # 派发
            else:
                return self.VOLUME_PRICE_PATTERNS["breakout"]  # 突破
        
        elif abs(price_change) < 0.5 and volume_ratio > 1.3:
            # 震荡放量
            if recent_volumes[-1] > avg_volume * 1.8:
                return self.VOLUME_PRICE_PATTERNS["shakeout"]  # 震仓
        
        return {
            "name": "无明显模式",
            "interpretation": "量价关系正常",
            "confidence": 0.5
        }
    
    def _detect_anomalies(
        self,
        price_history: List[dict],
        volume_data: List[dict],
        minute_data: Optional[List[dict]] = None
    ) -> List[dict]:
        """检测异常"""
        anomalies = []
        
        if len(volume_data) < 5:
            return anomalies
        
        # 异常1：异常放量
        volumes = [v.get("volume", 0) for v in volume_data[-10:]]
        avg_vol = sum(volumes) / len(volumes)
        if volumes[-1] > avg_vol * 3:
            anomalies.append({
                "type": "volume_surge",
                "description": f"今日成交量为均量的{volumes[-1]/avg_vol:.1f}倍",
                "severity": "high"
            })
        
        # 异常2：价格异动
        changes = [p.get("change_pct", 0) for p in price_history[-5:]]
        if abs(changes[-1]) > 5:
            anomalies.append({
                "type": "price_surge",
                "description": f"价格变动{changes[-1]:.1f}%",
                "severity": "high" if abs(changes[-1]) > 8 else "medium"
            })
        
        # 异常3：尾盘拉升/砸盘
        if minute_data:
            open_price = minute_data[0].get("price", 0) if minute_data else 0
            close_price = minute_data[-1].get("price", 0) if minute_data else 0
            last_30min = minute_data[-30:] if len(minute_data) >= 30 else minute_data
            
            if last_30min:
                last_30_close = last_30min[-1].get("price", 0)
                last_30_open = last_30min[0].get("price", 0)
                last_30_change = (last_30_close - last_30_open) / max(last_30_open, 1) * 100
                
                if last_30_change > 2:
                    anomalies.append({
                        "type": "tail Surge",
                        "description": f"尾盘30分钟拉升{last_30_change:.1f}%",
                        "severity": "medium"
                    })
                elif last_30_change < -2:
                    anomalies.append({
                        "type": "tail_dump",
                        "description": f"尾盘30分钟砸盘{last_30_change:.1f}%",
                        "severity": "high"
                    })
        
        # 异常4：连续涨跌
        if len(changes) >= 3:
            if all(c > 3 for c in changes[-3:]):
                anomalies.append({
                    "type": "consecutive_rise",
                    "description": "连续3日涨幅超过3%",
                    "severity": "high"
                })
            elif all(c < -3 for c in changes[-3:]):
                anomalies.append({
                    "type": "consecutive_fall",
                    "description": "连续3日跌幅超过3%",
                    "severity": "high"
                })
        
        return anomalies
    
    def _build_verdict(
        self,
        evidence_chain: List[dict],
        money_flow: MoneyFlow,
        chips: ChipDistribution,
        pattern: dict
    ) -> dict:
        """构建最终判断"""
        verdict = {
            "has_mainforce": False,
            "confidence": 0.5,
            "mainforce_type": "none",
            "intent": "未知",
            "risk_signals": [],
            "opportunities": [],
            "conclusion": ""
        }
        
        # 统计证据
        mainforce_evidence = 0
        total_evidence = len(evidence_chain)
        
        # 证据1：主力参与度
        if money_flow.mainforce_score > 0.5:
            mainforce_evidence += 1
        elif money_flow.mainforce_score > 0.3:
            mainforce_evidence += 0.5
        
        # 证据2：量价模式
        pattern_name = pattern.get("name", "")
        if pattern_name in ["吸筹模式", "派发模式", "震仓模式", "突破模式"]:
            mainforce_evidence += 1
        
        # 证据3：筹码集中度
        if chips.concentration > 0.7:
            mainforce_evidence += 0.5
        
        # 证据4：资金流向
        if money_flow.flow_direction == "inflow" and money_flow.mainforce_score > 0.4:
            mainforce_evidence += 1
        
        # 判断是否有主力
        if mainforce_evidence >= 2:
            verdict["has_mainforce"] = True
            verdict["confidence"] = min(0.95, 0.5 + mainforce_evidence * 0.15)
        
        # 判断主力类型和意图
        if verdict["has_mainforce"]:
            if money_flow.mainforce_score > 0.7:
                verdict["mainforce_type"] = "long_term"
                verdict["intent"] = "长期控盘"
            elif money_flow.flow_direction == "inflow":
                verdict["mainforce_type"] = "short_term"
                verdict["intent"] = "短期拉升"
            else:
                verdict["mainforce_type"] = "institution"
                verdict["intent"] = "稳健运作"
            
            # 根据模式判断意图
            if pattern_name == "吸筹模式":
                verdict["intent"] = "吸筹中"
                verdict["opportunities"].append("低位机会，可适当建仓")
            elif pattern_name == "派发模式":
                verdict["intent"] = "派发中"
                verdict["risk_signals"].append("主力在出货，警惕高位风险")
            elif pattern_name == "震仓模式":
                verdict["intent"] = "震仓洗盘"
                verdict["opportunities"].append("震仓后可考虑加仓")
            elif pattern_name == "突破模式":
                verdict["intent"] = "拉升中"
                verdict["opportunities"].append("突破有效，可顺势跟进")
        
        # 构建结论
        if verdict["has_mainforce"]:
            verdict["conclusion"] = f"检测到主力({verdict['mainforce_type']}), 意图: {verdict['intent']}"
        else:
            verdict["conclusion"] = "未检测到明显主力行为，谨慎操作"
        
        return verdict
    
    def _record_investigation(self, stock: str, report: DetectiveReport):
        """记录调查"""
        self.state["stock_profiles"][stock] = {
            "last_investigation": datetime.now().isoformat(),
            "has_mainforce": report.has_mainforce,
            "mainforce_type": report.mainforce_type,
            "confidence": report.confidence,
            "verdict": report.verdict
        }
        
        self.state["evidence_log"].append({
            "stock": stock,
            "timestamp": datetime.now().isoformat(),
            "verdict": report.verdict,
            "confidence": report.confidence
        })
        
        if len(self.state["evidence_log"]) > 1000:
            self.state["evidence_log"] = self.state["evidence_log"][-1000:]
        
        self.state["meta"]["total_investigations"] += 1
        self._save()
    
    # ========== 特定分析 ==========
    
    def analyze_washout_risk(
        self,
        current_price: float,
        support_levels: List[float],
        recent_lows: List[float]
    ) -> dict:
        """分析被洗盘的风险"""
        risk_level = "low"
        evidence = []
        
        # 风险因素1：是否在支撑位附近
        nearest_support = min(support_levels, key=lambda x: abs(x - current_price))
        distance_to_support = abs(current_price - nearest_support) / current_price
        
        if distance_to_support < 0.02:
            risk_level = "high"
            evidence.append(f"距离支撑{nearest_support}仅{distance_to_support*100:.1f}%, 易被破位洗盘")
        elif distance_to_support < 0.05:
            risk_level = "medium"
            evidence.append(f"支撑位在{distance_to_support*100:.1f}%之外")
        
        # 风险因素2：近期是否创新低
        if recent_lows and min(recent_lows) == recent_lows[-1]:
            risk_level = "high"
            evidence.append("今日/近期创出新低，有破位风险")
        
        return {
            "risk_level": risk_level,
            "evidence": evidence,
            "nearest_support": nearest_support,
            "distance_pct": round(distance_to_support * 100, 2)
        }
    
    def calculate_breakout_probability(
        self,
        price: float,
        resistance: float,
        volume_trend: str,  # increasing/decreasing/stable
        market_sentiment: str  # bullish/bearish/neutral
    ) -> dict:
        """计算突破概率"""
        distance_pct = (resistance - price) / price * 100
        
        # 基础概率
        base_prob = 50
        
        # 距离越近，概率越高
        if distance_pct < 1:
            base_prob += 20
        elif distance_pct < 3:
            base_prob += 10
        elif distance_pct > 5:
            base_prob -= 15
        
        # 量能支持
        if volume_trend == "increasing":
            base_prob += 15
        elif volume_trend == "decreasing":
            base_prob -= 10
        
        # 市场情绪
        if market_sentiment == "bullish":
            base_prob += 10
        elif market_sentiment == "bearish":
            base_prob -= 15
        
        probability = max(10, min(95, base_prob))
        
        return {
            "probability": probability,
            "distance_pct": round(distance_pct, 2),
            "confidence": "high" if abs(probability - 50) > 20 else "medium",
            "recommendation": "突破" if probability > 60 else "观望"
        }
    
    # ========== 格式化输出 ==========
    
    def format_report(self, report: DetectiveReport) -> str:
        """格式化报告"""
        lines = []
        lines.append(f"🔍 市场侦探报告")
        lines.append(f"{'='*50}")
        lines.append(f"置信度: {report.confidence:.0%}")
        lines.append(f"结论: {report.verdict}")
        lines.append("")
        
        if report.money_flow:
            mf = report.money_flow
            lines.append("💰 资金流向:")
            lines.append(f"  主力参与度: {mf.mainforce_score:.0%}")
            lines.append(f"  流向: {mf.flow_direction}")
            lines.append(f"  净流入: {mf.net_flow:.0f}万")
            lines.append("")
        
        if report.chip_distribution:
            chips = report.chip_distribution
            lines.append("📊 筹码分布:")
            lines.append(f"  获利盘: {chips.profit_ratio:.0%}")
            lines.append(f"  套牢盘: {chips.loss_ratio:.0%}")
            lines.append(f"  成本集中度: {chips.concentration:.0%}")
            lines.append("")
        
        if report.evidence_chain:
            lines.append("🔗 证据链:")
            for i, evidence in enumerate(report.evidence_chain, 1):
                lines.append(f"  {i}. [{evidence['type']}] {evidence.get('finding', '')}")
            lines.append("")
        
        if report.risk_signals:
            lines.append("⚠️ 风险信号:")
            for signal in report.risk_signals:
                lines.append(f"  • {signal}")
            lines.append("")
        
        if report.opportunities:
            lines.append("💡 机会:")
            for opp in report.opportunities:
                lines.append(f"  • {opp}")
        
        return "\n".join(lines)
    
    # ========== 统计 ==========
    
    def get_stats(self) -> dict:
        """获取统计"""
        total = self.state["meta"]["total_investigations"]
        with_mainforce = sum(1 for p in self.state["stock_profiles"].values() if p.get("has_mainforce"))
        
        return {
            "total_investigations": total,
            "stocks_with_mainforce": with_mainforce,
            "mainforce_rate": round(with_mainforce / max(total, 1), 2),
            "recent_alerts": self.state["alerts"][-10:]
        }
