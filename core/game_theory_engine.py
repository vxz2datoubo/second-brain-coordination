"""
game_theory_engine.py — 博弈论推理引擎
=========================================
让第二大脑具备顶级人类博弈思维：识别庄家意图、预判对手行为、
理解市场博弈结构、做出反身性分析。

核心理论支撑：
1. 博弈论基础：零和博弈、囚徒困境、斗鸡博弈、智猪博弈
2. 行为金融：庄家行为模式、散户心理偏差、主力操盘套路
3. 反身性理论：索罗斯的反射理论，股价影响基本面
4. 逆向思维：站在对手角度思考，预判对手的预判

设计参考：
- 大奖章基金的量化博弈思维
- 华尔街顶级交易员的思维模式
- 行为金融学的核心洞见
"""

import json
import uuid
import math
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class GameState:
    """博弈状态快照"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    players: List[str] = field(default_factory=list)  # 参与者
    positions: Dict[str, dict] = field(default_factory=dict)  # 各方持仓
    market_sentiment: str = "neutral"  # 市场情绪
    price_trend: str = "sideways"  # 价格趋势
    volume_profile: str = "normal"  # 量能特征
    detected_pattern: str = ""  # 检测到的博弈模式
    confidence: float = 0.0  # 置信度
    risk_signals: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    recommended_action: str = ""  # 推荐行动
    reasoning_chain: List[dict] = field(default_factory=list)


@dataclass
class ActorProfile:
    """市场参与者画像"""
    actor_type: str  # 主力/机构/大户/散户
    behavioral_signature: str  # 行为特征
    typical_patterns: List[str]  # 典型套路
    strength_score: float = 0.5  # 实力评分
    risk_tolerance: float = 0.5  # 风险承受
    historical_win_rate: float = 0.5  # 历史胜率


class GameTheoryEngine:
    """博弈论推理引擎
    
    核心能力：
    1. 博弈结构识别 — 判断当前市场属于哪种博弈类型
    2. 对手建模 — 识别主力/庄家/散户的行为模式
    3. 策略推理 — 基于博弈论计算最优策略
    4. 反身性分析 — 识别自我强化的价格循环
    5. 多步推演 — 预判对手下一步和下下一步的行动
    """
    
    # 博弈类型定义
    GAME_TYPES = {
        "zero_sum": {
            "name": "零和博弈",
            "description": "一方所得必为另一方所失",
            "typical_scenario": "短线T仓、题材炒作",
            "strategy": "逆向思维，领先一步",
        },
        "coordination": {
            "name": "协调博弈",
            "description": "参与者利益一致，需要协调行动",
            "typical_scenario": "趋势行情、板块启动",
            "strategy": "顺势而为，跟随主导力量",
        },
        "chicken": {
            "name": "斗鸡博弈",
            "description": "两方对峙，一方退让为赢",
            "typical_scenario": "突破关键阻力位、多空对峙",
            "strategy": "识别虚张声势，等待确认",
        },
        "stag_hunt": {
            "name": "智猪博弈",
            "description": "小猪等待大猪行动后搭便车",
            "typical_scenario": "题材轮动、跟庄操作",
            "strategy": "等待信号，确认后再行动",
        },
        "prisoner": {
            "name": "囚徒困境",
            "description": "个人理性导致集体非理性",
            "typical_scenario": "散户集体恐慌、主力的洗盘",
            "strategy": "逆向操作，脱离群体",
        },
    }
    
    # 主力操盘套路模式库
    MAINFORCE_PATTERNS = {
        "accumulation": {
            "name": "吸筹阶段",
            "signals": ["低量低波动", "尾盘拉升", "大单托底"],
            "interpretation": "主力在收集筹码",
            "counter_strategy": "耐心持有，不被洗出",
        },
        "manipulation": {
            "name": "拉升阶段",
            "interpretation": "主力在推高股价",
            "counter_strategy": "持有至滞涨信号出现",
        },
        "distribution": {
            "name": "派发阶段",
            "signals": ["高位放量", "日内震仓", "利好频出"],
            "interpretation": "主力在出货",
            "counter_strategy": "警惕，追高必套",
        },
        "washout": {
            "name": "洗盘阶段",
            "signals": ["恐慌性杀跌", "跌破均线", "利空配合"],
            "interpretation": "主力在清洗浮筹",
            "counter_strategy": "逆势买入或加仓",
        },
        "fake_break": {
            "name": "假突破",
            "signals": ["突破后快速回落", "量能不足", "无跟风盘"],
            "interpretation": "主力诱多/诱空",
            "counter_strategy": "等待回踩确认",
        },
        "short_squeeze": {
            "name": "逼空行情",
            "signals": ["连续上涨", "空头被套", "踏空资金焦虑"],
            "interpretation": "主力在逼空",
            "counter_strategy": "小仓追入，严格止损",
        },
    }
    
    # 反身性模式
    REFLEXIVITY_PATTERNS = {
        "bull_cycle": {
            "name": "牛市正反馈循环",
            "stages": ["低估→吸引资金→上涨→基本面改善→更多资金→继续上涨"],
            "exit_signals": ["估值泡沫化", "IPO狂潮", "杠杆率飙升"],
        },
        "bear_cycle": {
            "name": "熊市负反馈循环",
            "stages": ["高估→资金流出→下跌→基本面恶化→更多资金流出→继续下跌"],
            "exit_signals": ["估值合理化", "无人谈论", "产业资本增持"],
        },
        "meme_cycle": {
            "name": "题材炒作循环",
            "stages": ["消息刺激→资金涌入→价格上涨→吸引更多资金→泡沫化→崩溃"],
            "exit_signals": ["官方降温", "媒体狂吹", "大妈入场"],
        },
    }
    
    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.state_path = data_dir / "game_theory_state.json"
        self.state = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "game_history": [],
                "detected_patterns": [],
                "actor_profiles": {},
                "meta": {
                    "total_analyzes": 0,
                    "pattern_matches": 0,
                    "last_update": ""
                }
            }
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    # ========== 核心分析方法 ==========
    
    def analyze_market_game(
        self,
        stock: str,
        price_data: dict,
        volume_data: dict,
        news: Optional[List[dict]] = None,
        order_flow: Optional[dict] = None,
    ) -> GameState:
        """综合博弈分析
        
        Args:
            stock: 股票代码
            price_data: 价格数据 {open, high, low, close, change%}
            volume_data: 量能数据 {volume, avg_volume, vwap}
            news: 新闻列表
            order_flow: 订单流数据 {large_buy, large_sell, net_flow}
        
        Returns:
            GameState: 博弈状态分析结果
        """
        state = GameState()
        state.players = ["主力", "机构", "大户", "散户"]
        
        # 1. 识别博弈类型
        game_type = self._identify_game_type(price_data, volume_data)
        state.detected_pattern = game_type["type"]
        
        # 2. 检测主力行为模式
        mainforce = self._detect_mainforce_pattern(price_data, volume_data, order_flow)
        state.positions["mainforce"] = mainforce
        
        # 3. 识别反身性信号
        reflexivity = self._detect_reflexivity(price_data, news)
        state.positions["market"] = reflexivity
        
        # 4. 分析对手意图
        intentions = self._analyze_actor_intentions(price_data, volume_data, mainforce)
        
        # 5. 计算最优策略
        strategy = self._calculate_optimal_strategy(
            game_type, mainforce, reflexivity, intentions
        )
        
        state.reasoning_chain = strategy["reasoning_chain"]
        state.risk_signals = strategy["risk_signals"]
        state.opportunities = strategy["opportunities"]
        state.recommended_action = strategy["action"]
        state.confidence = strategy["confidence"]
        state.market_sentiment = strategy["sentiment"]
        state.price_trend = strategy["trend"]
        
        # 记录历史
        self.state["game_history"].append({
            "stock": stock,
            "timestamp": state.timestamp,
            "game_type": state.detected_pattern,
            "mainforce_pattern": mainforce.get("detected_pattern", ""),
            "action": state.recommended_action,
            "confidence": state.confidence,
        })
        self.state["meta"]["total_analyzes"] += 1
        self._save()
        
        return state
    
    def _identify_game_type(
        self,
        price_data: dict,
        volume_data: dict
    ) -> dict:
        """识别博弈类型"""
        change = abs(price_data.get("change_pct", 0))
        volume_ratio = volume_data.get("volume", 0) / max(volume_data.get("avg_volume", 1), 1)
        
        reasoning = []
        
        # 基于波动性和量能判断博弈类型
        if change > 3 and volume_ratio > 1.5:
            # 高波动+高量能 = 零和博弈（短线机会大）
            reasoning.append({
                "step": 1,
                "type": "pattern_recognition",
                "content": f"检测到高波动({change:.1f}%)+高量能({volume_ratio:.1f}x)，符合零和博弈特征"
            })
            game_type = "zero_sum"
            interpretation = "短线博弈激烈，适合T仓操作"
        
        elif volume_ratio > 2 and price_data.get("close", 0) > price_data.get("open", 0):
            # 放量上涨 = 协调博弈
            reasoning.append({
                "step": 1,
                "type": "pattern_recognition", 
                "content": f"放量上涨({volume_ratio:.1f}x)，市场参与者协调做多"
            })
            game_type = "coordination"
            interpretation = "趋势行情，顺势而为"
        
        elif abs(change) < 0.5 and volume_ratio < 0.8:
            # 低波动+低量能 = 智猪博弈（等待信号）
            reasoning.append({
                "step": 1,
                "type": "pattern_recognition",
                "content": "低波动低量能，市场在等待主导力量行动"
            })
            game_type = "stag_hunt"
            interpretation = "观望为主，等待突破信号"
        
        else:
            # 默认分析
            reasoning.append({
                "step": 1,
                "type": "analysis",
                "content": "市场处于混合格斗状态，需要更多信号确认"
            })
            game_type = "chicken"
            interpretation = "方向不明，谨慎操作"
        
        reasoning.append({
            "step": 2,
            "type": "interpretation",
            "content": f"识别为{self.GAME_TYPES[game_type]['name']}: {interpretation}"
        })
        
        return {
            "type": game_type,
            "interpretation": interpretation,
            "reasoning": reasoning,
            "game_info": self.GAME_TYPES[game_type]
        }
    
    def _detect_mainforce_pattern(
        self,
        price_data: dict,
        volume_data: dict,
        order_flow: Optional[dict] = None
    ) -> dict:
        """检测主力行为模式"""
        patterns_detected = []
        confidence_scores = {}
        
        # 计算各项指标
        change = price_data.get("change_pct", 0)
        volume_ratio = volume_data.get("volume", 0) / max(volume_data.get("avg_volume", 1), 1)
        
        # 模式1: 吸筹模式
        if change < 0 and volume_ratio < 0.8:
            patterns_detected.append("accumulation")
            confidence_scores["accumulation"] = 0.7
        
        # 模式2: 拉升模式  
        if change > 2 and volume_ratio > 1.2:
            patterns_detected.append("manipulation")
            confidence_scores["manipulation"] = 0.8
        
        # 模式3: 派发模式
        if change > 5 and volume_ratio > 2.0:
            patterns_detected.append("distribution")
            confidence_scores["distribution"] = 0.9
        
        # 模式4: 洗盘模式
        if change < -2 and volume_ratio > 1.5:
            patterns_detected.append("washout")
            confidence_scores["washout"] = 0.75
        
        # 模式5: 假突破
        if order_flow:
            # 假突破特征：突破时大单卖出
            if order_flow.get("fake_break_signal"):
                patterns_detected.append("fake_break")
                confidence_scores["fake_break"] = 0.85
        
        # 模式6: 逼空
        if change > 7 and volume_ratio > 2.5:
            patterns_detected.append("short_squeeze")
            confidence_scores["short_squeeze"] = 0.9
        
        # 确定最可能的模式
        if patterns_detected:
            dominant = max(confidence_scores, key=confidence_scores.get)
            pattern_info = self.MAINFORCE_PATTERNS[dominant]
            confidence = confidence_scores[dominant]
        else:
            dominant = "unknown"
            pattern_info = {"name": "未识别", "interpretation": "需要更多数据"}
            confidence = 0.3
        
        return {
            "detected_pattern": dominant,
            "pattern_name": pattern_info["name"],
            "interpretation": pattern_info["interpretation"],
            "counter_strategy": pattern_info["counter_strategy"],
            "confidence": confidence,
            "all_detected": patterns_detected,
            "confidence_scores": confidence_scores
        }
    
    def _detect_reflexivity(
        self,
        price_data: dict,
        news: Optional[List[dict]] = None
    ) -> dict:
        """检测反身性信号"""
        change = price_data.get("change_pct", 0)
        reflexivity_indicators = []
        
        # 检测正反馈循环信号
        if change > 5:
            reflexivity_indicators.append({
                "indicator": "价格快速上涨",
                "implication": "可能触发更多买入，形成正反馈",
                "stage": "加速阶段"
            })
        
        # 检测新闻与价格的互动
        if news:
            recent_news_count = sum(1 for n in news if self._is_recent_news(n))
            if recent_news_count > 3:
                reflexivity_indicators.append({
                    "indicator": f"近期{recent_news_count}条相关新闻",
                    "implication": "消息与价格可能形成正反馈循环",
                    "stage": "题材炒作期"
                })
        
        # 检测情绪过热
        if change > 8 and reflexivity_indicators:
            reflexivity_indicators.append({
                "indicator": "情绪过热信号",
                "implication": "距离反转可能不远",
                "stage": "泡沫化前期"
            })
        
        return {
            "reflexivity_detected": len(reflexivity_indicators) > 0,
            "indicators": reflexivity_indicators,
            "current_cycle": self._identify_cycle_stage(reflexivity_indicators)
        }
    
    def _analyze_actor_intentions(
        self,
        price_data: dict,
        volume_data: dict,
        mainforce: dict
    ) -> dict:
        """分析各方意图"""
        intentions = {}
        pattern = mainforce.get("detected_pattern", "unknown")
        
        # 主力意图推断
        if pattern == "accumulation":
            intentions["mainforce"] = {
                "intent": "吸筹",
                "likely_action": "继续压盘或震荡",
                "counter_move": "持有或逢低加仓"
            }
        elif pattern == "manipulation":
            intentions["mainforce"] = {
                "intent": "拉升",
                "likely_action": "继续推高或洗盘后拉升",
                "counter_move": "持有至滞涨"
            }
        elif pattern == "distribution":
            intentions["mainforce"] = {
                "intent": "派发",
                "likely_action": "高位震荡出货",
                "counter_move": "谨慎，不追高"
            }
        elif pattern == "washout":
            intentions["mainforce"] = {
                "intent": "洗盘",
                "likely_action": "快速杀跌后拉回",
                "counter_move": "不恐慌，逆势加仓"
            }
        else:
            intentions["mainforce"] = {
                "intent": "观望",
                "likely_action": "等待明确信号",
                "counter_move": "观望为主"
            }
        
        # 散户行为推断
        intentions["retail"] = {
            "typical_behavior": "追涨杀跌",
            "likely_action": "在高位追入或低位割肉",
            "win_rate": 0.3,  # 散户胜率统计
        }
        
        return intentions
    
    def _calculate_optimal_strategy(
        self,
        game_type: dict,
        mainforce: dict,
        reflexivity: dict,
        intentions: dict
    ) -> dict:
        """计算最优策略"""
        reasoning_chain = []
        risk_signals = []
        opportunities = []
        
        # 构建推理链
        reasoning_chain.append({
            "step": 1,
            "type": "game_type",
            "content": f"识别博弈类型: {game_type['game_info']['name']}",
            "detail": game_type["interpretation"]
        })
        
        reasoning_chain.append({
            "step": 2,
            "type": "mainforce_analysis",
            "content": f"主力行为: {mainforce.get('pattern_name', '未知')}",
            "detail": mainforce.get("interpretation", "")
        })
        
        if reflexivity.get("reflexivity_detected"):
            reasoning_chain.append({
                "step": 3,
                "type": "reflexivity",
                "content": "检测到反身性信号",
                "detail": f"当前阶段: {reflexivity.get('current_cycle', '未知')}"
            })
        
        # 基于分析生成策略
        pattern = mainforce.get("detected_pattern", "")
        confidence = mainforce.get("confidence", 0.5)
        
        if pattern == "accumulation":
            action = "持有，不被洗出"
            opportunities.append("低位吸筹机会")
            reasoning_chain.append({
                "step": 4,
                "type": "strategy",
                "content": f"策略: {action}",
                "detail": mainforce.get("counter_strategy", "")
            })
        
        elif pattern == "manipulation":
            action = "持有，等待滞涨信号"
            opportunities.append("趋势延续机会")
            reasoning_chain.append({
                "step": 4,
                "type": "strategy",
                "content": f"策略: {action}",
                "detail": "主力正在拉升，持有为上"
            })
        
        elif pattern == "distribution":
            action = "谨慎，减仓或止盈"
            risk_signals.append("主力可能在派发，追高必套")
            reasoning_chain.append({
                "step": 4,
                "type": "strategy",
                "content": f"策略: {action}",
                "detail": "高位风险大，建议减仓"
            })
        
        elif pattern == "washout":
            action = "逆势买入机会"
            opportunities.append("恐慌性杀跌可能是买点")
            reasoning_chain.append({
                "step": 4,
                "type": "strategy",
                "content": f"策略: {action}",
                "detail": "主力洗盘往往是买入机会"
            })
        
        elif pattern == "fake_break":
            action = "等待回踩确认"
            risk_signals.append("假突破后可能快速回落")
            reasoning_chain.append({
                "step": 4,
                "type": "strategy",
                "content": f"策略: {action}",
                "detail": "不追突破，等回踩再介入"
            })
        
        else:
            action = "观望，等待明确信号"
            reasoning_chain.append({
                "step": 4,
                "type": "strategy",
                "content": f"策略: {action}",
                "detail": "信号不明确，谨慎操作"
            })
        
        # 添加风险信号
        if reflexivity.get("reflexivity_detected"):
            for indicator in reflexivity.get("indicators", []):
                if "泡沫" in indicator.get("implication", ""):
                    risk_signals.append("反身性警告: " + indicator.get("implication", ""))
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning_chain": reasoning_chain,
            "risk_signals": risk_signals,
            "opportunities": opportunities,
            "sentiment": self._judge_sentiment(action),
            "trend": mainforce.get("detected_pattern", "unknown")
        }
    
    def _is_recent_news(self, news: dict) -> bool:
        """判断是否为近期新闻"""
        try:
            news_time = news.get("time", "")
            if news_time:
                dt = datetime.fromisoformat(news_time)
                return (datetime.now() - dt).days <= 3
        except:
            pass
        return False
    
    def _identify_cycle_stage(self, indicators: list) -> str:
        """识别循环阶段"""
        if not indicators:
            return "初始阶段"
        
        stages = [i.get("stage", "") for i in indicators]
        if "泡沫化前期" in stages:
            return "泡沫化前期"
        elif "加速阶段" in stages:
            return "加速上涨期"
        elif "题材炒作期" in stages:
            return "题材炒作期"
        return "发展中"
    
    def _judge_sentiment(self, action: str) -> str:
        """判断情绪"""
        if "持有" in action or "加仓" in action:
            return "看多"
        elif "减仓" in action or "止盈" in action:
            return "看空"
        elif "观望" in action:
            return "中性"
        return "中性"
    
    # ========== 逆向博弈分析 ==========
    
    def think_like_enemy(
        self,
        current_position: dict,
        market_state: dict,
        my_intent: str
    ) -> dict:
        """站在对手角度思考
        
        核心问题：
        1. 如果我这么做，对手会怎么反应？
        2. 对手的反应会如何影响市场？
        3. 我的最优应对是什么？
        """
        reasoning = []
        
        # 推断主力可能的反应
        if my_intent == "买入":
            reasoning.append({
                "step": 1,
                "question": "主力会如何应对我的买入？",
                "possibilities": [
                    "如果买入量小，主力可能无视",
                    "如果买入量大，主力可能借机洗盘",
                    "如果突破关键位，主力可能被迫止损"
                ]
            })
            
            # 计算最优买入策略
            reasoning.append({
                "step": 2,
                "conclusion": "建议分批买入，避免被主力发现意图",
                "tactics": [
                    "第一笔: 试探性买入(10%)",
                    "第二笔: 确认后加仓(30%)",
                    "第三笔: 回调确认后重仓(60%)"
                ]
            })
        
        elif my_intent == "卖出":
            reasoning.append({
                "step": 1,
                "question": "主力会如何应对我的卖出？",
                "possibilities": [
                    "如果盈利，主力可能借机洗盘",
                    "如果亏损，主力可能继续压盘",
                    "如果大单卖出，可能引发恐慌"
                ]
            })
            
            reasoning.append({
                "step": 2,
                "conclusion": "建议分批卖出，避免冲击成本",
                "tactics": [
                    "第一笔: 减半仓",
                    "第二笔: 反弹时再减",
                    "第三笔: 最后清仓"
                ]
            })
        
        return {
            "my_intent": my_intent,
            "enemy_possible_reactions": reasoning[0] if reasoning else {},
            "recommended_tactics": reasoning[1] if len(reasoning) > 1 else {},
            "reasoning": reasoning
        }
    
    # ========== 多步推演 ==========
    
    def multi_step_prediction(
        self,
        current_state: dict,
        num_steps: int = 3
    ) -> dict:
        """多步市场推演
        
        模拟未来几种可能的发展路径
        """
        predictions = []
        
        # 路径1: 延续当前趋势
        path1 = self._simulate_path(current_state, "continuation", num_steps)
        predictions.append(path1)
        
        # 路径2: 反转
        path2 = self._simulate_path(current_state, "reversal", num_steps)
        predictions.append(path2)
        
        # 路径3: 震荡
        path3 = self._simulate_path(current_state, "sideways", num_steps)
        predictions.append(path3)
        
        # 计算各路径概率
        probabilities = self._calculate_path_probabilities(current_state, predictions)
        
        return {
            "current_state": current_state,
            "predictions": predictions,
            "probabilities": probabilities,
            "recommended_path": self._choose_path(probabilities)
        }
    
    def _simulate_path(
        self,
        current_state: dict,
        direction: str,
        steps: int
    ) -> dict:
        """模拟单条路径"""
        path = {
            "direction": direction,
            "steps": [],
            "total_change": 0,
            "risk_level": "medium"
        }
        
        for i in range(steps):
            if direction == "continuation":
                change = 1.5  # 每日预期变化
                risk = "medium"
            elif direction == "reversal":
                change = -1.0 if i == 0 else 0.5  # 先跌后涨
                risk = "high"
            else:  # sideways
                change = 0.2 * (1 if i % 2 == 0 else -1)
                risk = "low"
            
            path["steps"].append({
                "step": i + 1,
                "expected_change": change,
                "cumulative": path["total_change"] + change
            })
            path["total_change"] += change
        
        path["risk_level"] = risk
        return path
    
    def _calculate_path_probabilities(
        self,
        current_state: dict,
        predictions: list
    ) -> dict:
        """计算路径概率"""
        # 基于当前市场状态调整概率
        base_probs = {
            "continuation": 0.4,
            "reversal": 0.3,
            "sideways": 0.3
        }
        
        # 如果是高位，调整反转概率
        if current_state.get("price_level") == "high":
            base_probs["reversal"] += 0.2
            base_probs["continuation"] -= 0.15
            base_probs["sideways"] -= 0.05
        
        # 如果有大利好，调整延续概率
        if current_state.get("has_major_news"):
            base_probs["continuation"] += 0.15
            base_probs["reversal"] -= 0.1
        
        # 归一化
        total = sum(base_probs.values())
        return {k: round(v / total, 2) for k, v in base_probs.items()}
    
    def _choose_path(self, probabilities: dict) -> dict:
        """选择推荐路径"""
        best = max(probabilities, key=probabilities.get)
        return {
            "path": best,
            "probability": probabilities[best],
            "confidence": "high" if probabilities[best] > 0.5 else "medium"
        }
    
    # ========== 博弈优势分析 ==========
    
    def analyze_advantage(self, my_position: dict, market: dict) -> dict:
        """分析博弈优势
        
        关键问题：
        1. 我的位置是否有利？
        2. 主力在哪里？
        3. 谁更容易被洗出？
        """
        advantages = []
        disadvantages = []
        
        # 成本优势
        if my_position.get("cost", 0) < market.get("current_price", 0):
            advantages.append({
                "type": "cost_advantage",
                "description": f"成本低于现价{((market['current_price'] - my_position['cost']) / my_position['cost'] * 100):.1f}%",
                "implication": "有安全垫，可以承受一定波动"
            })
        else:
            disadvantages.append({
                "type": "cost_disadvantage",
                "description": "成本高于现价，处于浮亏",
                "implication": "需要谨慎，避免追加仓位"
            })
        
        # 时间优势
        holding_days = my_position.get("holding_days", 0)
        if holding_days > 30:
            advantages.append({
                "type": "time_advantage",
                "description": f"持有{holding_days}天，经历多次洗盘",
                "implication": "短期投机者可能已被洗出"
            })
        else:
            disadvantages.append({
                "type": "time_disadvantage",
                "description": f"持有仅{holding_days}天",
                "implication": "可能被短期波动洗出"
            })
        
        # 信息优势
        if my_position.get("has_private_info"):
            advantages.append({
                "type": "information_advantage",
                "description": "拥有内幕信息",
                "implication": "但需注意法律风险"
            })
        
        return {
            "advantages": advantages,
            "disadvantages": disadvantages,
            "overall_advantage": len(advantages) > len(disadvantages),
            "recommendation": self._generate_position_recommendation(advantages, disadvantages)
        }
    
    def _generate_position_recommendation(
        self,
        advantages: list,
        disadvantages: list
    ) -> str:
        """生成持仓建议"""
        if len(advantages) > len(disadvantages):
            return "优势明显，继续持有"
        elif len(advantages) == len(disadvantages):
            return "势均力敌，谨慎持有"
        else:
            return "劣势明显，考虑减仓"
    
    # ========== 格式化输出 ==========
    
    def format_analysis(self, state: GameState) -> str:
        """格式化分析输出"""
        lines = []
        lines.append(f"🎯 博弈分析报告")
        lines.append(f"{'='*50}")
        lines.append(f"时间: {state.timestamp}")
        lines.append(f"博弈类型: {self.GAME_TYPES.get(state.detected_pattern, {}).get('name', '未知')}")
        lines.append(f"置信度: {state.confidence:.0%}")
        lines.append("")
        
        if state.positions.get("mainforce"):
            mainforce = state.positions["mainforce"]
            lines.append(f"🐋 主力行为分析:")
            lines.append(f"  检测模式: {mainforce.get('pattern_name', '未知')}")
            lines.append(f"  解读: {mainforce.get('interpretation', '未知')}")
            lines.append(f"  应对策略: {mainforce.get('counter_strategy', '未知')}")
            lines.append("")
        
        if state.reasoning_chain:
            lines.append("📋 推理链:")
            for step in state.reasoning_chain:
                lines.append(f"  {step.get('step')}. [{step.get('type')}] {step.get('content')}")
                if step.get('detail'):
                    lines.append(f"     └ {step['detail']}")
            lines.append("")
        
        if state.risk_signals:
            lines.append("⚠️ 风险信号:")
            for signal in state.risk_signals:
                lines.append(f"  • {signal}")
            lines.append("")
        
        if state.opportunities:
            lines.append("💡 机会提示:")
            for opp in state.opportunities:
                lines.append(f"  • {opp}")
            lines.append("")
        
        lines.append("🎯 推荐行动:")
        lines.append(f"  {state.recommended_action}")
        
        return "\n".join(lines)
    
    # ========== 统计和历史 ==========
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_analyzes": self.state["meta"]["total_analyzes"],
            "pattern_matches": self.state["meta"]["pattern_matches"],
            "recent_games": self.state["game_history"][-10:],
            "dominant_pattern": self._get_dominant_pattern()
        }
    
    def _get_dominant_pattern(self) -> str:
        """获取最常见的模式"""
        if not self.state["game_history"]:
            return "unknown"
        
        from collections import Counter
        patterns = [g.get("mainforce_pattern", "unknown") for g in self.state["game_history"]]
        return Counter(patterns).most_common(1)[0][0]


# ========== 辅助函数 ==========

def calculate_ev(
    outcomes: List[Tuple[float, float]],
    probabilities: List[float]
) -> float:
    """计算期望值
    
    Args:
        outcomes: 结果列表，每项为(盈亏金额, 概率)
        probabilities: 各结果概率
    
    Returns:
        float: 期望值
    """
    return sum(outcome * prob for outcome, prob in zip(outcomes, probabilities))


def calculate_sharpe_ratio(returns: List[float], risk_free: float = 0.03) -> float:
    """计算夏普比率"""
    if not returns:
        return 0.0
    
    avg_return = sum(returns) / len(returns)
    std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
    
    if std_return == 0:
        return 0.0
    
    return (avg_return - risk_free) / std_return

