"""
anti_gaming.py — 反坐庄/反操纵检测引擎
==========================================
识别庄家/主力的操盘套路，提前预警，保护散户不被"割韭菜"。
这是顶级交易员的生存技能。

核心理论：
1. 庄家操盘四部曲：吸筹→拉升→洗盘→出货
2. 散户行为偏差：追涨杀跌、恐慌性抛售、贪婪性买入
3. 量价背离：主力与散户行为在量价上的表现差异
4. 分时图异动：日内操盘痕迹

设计理念：
- 像猎手一样识别猎手的陷阱
- 识别庄家行为模式，提前预警
- 保护自己不被"割韭菜"
"""

import json
import uuid
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter


@dataclass
class GamingPattern:
    """坐庄模式"""
    pattern_type: str = ""           # 模式类型
    stage: str = ""                  # 所处阶段
    confidence: float = 0.0          # 置信度
    evidence: List[str] = field(default_factory=list)
    risk_level: str = "unknown"      # 风险等级
    survival_tips: List[str] = field(default_factory=list)


@dataclass
class AntiGamingReport:
    """反坐庄报告"""
    is_gamed: bool = False           # 是否被坐庄
    confidence: float = 0.0          # 判断置信度
    patterns: List[GamingPattern] = field(default_factory=list)
    survival_score: float = 0.0      # 生存分数 0-100
    risk_signals: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    survival_tips: List[str] = field(default_factory=list)
    recommended_action: str = ""


class AntiGamingEngine:
    """反坐庄/反操纵检测引擎
    
    核心能力：
    1. 识别吸筹信号 — 主力在悄悄买入
    2. 识别拉升信号 — 主力开始推高
    3. 识别洗盘信号 — 主力在清洗浮筹
    4. 识别出货信号 — 主力在高位派发
    5. 识别假突破 — 主力诱多/诱空的陷阱
    6. 评估生存概率 — 散户在这种环境下的生存能力
    7. 提供生存建议 — 如何在庄家眼皮底下生存
    """
    
    # 吸筹阶段特征
    ACCUMULATION_SIGNALS = {
        "low_volume_dip": {
            "name": "缩量下跌",
            "description": "下跌时量能萎缩，主力在吸筹",
            "confidence_boost": 0.15
        },
        "support_defense": {
            "name": "支撑位防守",
            "description": "每次跌到关键支撑就被拉起",
            "confidence_boost": 0.2
        },
        "tail_recovery": {
            "name": "尾盘拉升",
            "description": "收盘前价格被拉高",
            "confidence_boost": 0.15
        },
        "hidden_volume": {
            "name": "隐蔽放量",
            "description": "大单悄悄买入",
            "confidence_boost": 0.2
        }
    }
    
    # 拉升阶段特征
    MANIPULATION_SIGNALS = {
        "breakout_surge": {
            "name": "突破拉升",
            "description": "放量突破关键位置",
            "confidence_boost": 0.2
        },
        "momentum_acceleration": {
            "name": "动量加速",
            "description": "涨速越来越快",
            "confidence_boost": 0.15
        },
        "gap_up": {
            "name": "跳空高开",
            "description": "开盘跳空高开",
            "confidence_boost": 0.15
        },
        "chasing_volume": {
            "name": "追涨量能",
            "description": "放量上涨吸引跟风",
            "confidence_boost": 0.2
        }
    }
    
    # 洗盘阶段特征
    SHAKEOUT_SIGNALS = {
        "washout_drop": {
            "name": "震仓下跌",
            "description": "快速下跌后快速拉回",
            "confidence_boost": 0.2
        },
        "fake_breakdown": {
            "name": "假破位",
            "description": "跌破支撑后迅速收回",
            "confidence_boost": 0.25
        },
        "high_volatility": {
            "name": "高波动",
            "description": "日内振幅明显加大",
            "confidence_boost": 0.15
        },
        "mixed_volume": {
            "name": "混量",
            "description": "多空博弈激烈",
            "confidence_boost": 0.15
        }
    }
    
    # 出货阶段特征
    DISTRIBUTION_SIGNALS = {
        "high_volume_drop": {
            "name": "放量滞涨",
            "description": "高位放量但涨不动",
            "confidence_boost": 0.2
        },
        "distribution_volume": {
            "name": "派发量能",
            "description": "高位持续放量",
            "confidence_boost": 0.2
        },
        "top_formation": {
            "name": "顶部形态",
            "description": "形成M顶等顶部形态",
            "confidence_boost": 0.25
        },
        "news_cover": {
            "name": "利好掩护",
            "description": "高位频繁出利好",
            "confidence_boost": 0.2
        }
    }
    
    # 假突破陷阱
    FAKE_BREAKOUT_PATTERNS = {
        "insufficient_volume": {
            "name": "量能不足",
            "description": "突破时量能不够",
            "confidence_boost": 0.2
        },
        "quick_reversal": {
            "name": "快速回落",
            "description": "突破后很快回落",
            "confidence_boost": 0.25
        },
        "weak_close": {
            "name": "收盘弱势",
            "description": "收盘在突破位附近",
            "confidence_boost": 0.15
        },
        "no_follow": {
            "name": "无跟风",
            "description": "突破后无跟风盘",
            "confidence_boost": 0.2
        }
    }
    
    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.state_path = data_dir / "anti_gaming_state.json"
        self.state = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "detected_patterns": {},  # stock -> patterns
                "survival_records": [],   # 生存记录
                "alerts": [],            # 预警记录
                "meta": {"total_scans": 0, "patterns_detected": 0}
            }
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    # ========== 核心检测方法 ==========
    
    def detect(
        self,
        stock: str,
        price_history: List[dict],
        volume_history: List[dict],
        minute_data: Optional[List[dict]] = None
    ) -> AntiGamingReport:
        """检测是否有庄家操纵
        
        Args:
            stock: 股票代码
            price_history: 日线价格历史
            volume_history: 成交量历史
            minute_data: 分时数据（可选）
        
        Returns:
            AntiGamingReport: 检测报告
        """
        report = AntiGamingReport()
        
        if len(price_history) < 10 or len(volume_history) < 10:
            report.warnings.append("数据不足，无法准确判断")
            return report
        
        # 1. 检测吸筹信号
        accumulation_score = self._detect_accumulation(price_history, volume_history)
        
        # 2. 检测拉升信号
        manipulation_score = self._detect_manipulation(price_history, volume_history)
        
        # 3. 检测洗盘信号
        shakeout_score = self._detect_shakeout(price_history, volume_history)
        
        # 4. 检测出货信号
        distribution_score = self._detect_distribution(price_history, volume_history)
        
        # 5. 检测假突破
        fake_breakout_score = self._detect_fake_breakout(
            price_history, volume_history, minute_data
        )
        
        # 6. 综合判断
        scores = {
            "吸筹": accumulation_score,
            "拉升": manipulation_score,
            "洗盘": shakeout_score,
            "出货": distribution_score,
            "假突破": fake_breakout_score
        }
        
        # 找出最可能的阶段
        max_stage = max(scores, key=scores.get)
        max_score = scores[max_stage]
        
        if max_score > 0.4:
            report.is_gamed = True
            report.confidence = max_score
            
            pattern = GamingPattern(
                pattern_type="坐庄",
                stage=max_stage,
                confidence=max_score,
                evidence=self._get_stage_evidence(max_stage, price_history, volume_history),
                risk_level=self._assess_risk_level(max_stage)
            )
            report.patterns.append(pattern)
        
        # 检测假突破（单独的模式）
        if fake_breakout_score > 0.3:
            fake_pattern = GamingPattern(
                pattern_type="假突破陷阱",
                stage="陷阱",
                confidence=fake_breakout_score,
                evidence=self._get_fake_breakout_evidence(price_history, volume_history, minute_data),
                risk_level="high"
            )
            report.patterns.append(fake_pattern)
        
        # 评估生存分数
        report.survival_score = self._calculate_survival_score(
            scores, report.patterns
        )
        
        # 生成风险信号
        report.risk_signals = self._generate_risk_signals(scores)
        
        # 生成预警
        report.warnings = self._generate_warnings(report.patterns, scores)
        
        # 生成生存建议
        report.survival_tips = self._generate_survival_tips(
            report.patterns, report.survival_score
        )
        
        # 推荐行动
        report.recommended_action = self._generate_recommendation(
            report.patterns, report.survival_score
        )
        
        # 记录
        self._record_detection(stock, report)
        
        return report
    
    def _detect_accumulation(
        self,
        price_history: List[dict],
        volume_history: List[dict]
    ) -> float:
        """检测吸筹信号"""
        score = 0.0
        signals_found = []
        
        # 计算各项指标
        recent_10_prices = [p.get("close", 0) for p in price_history[-10:]]
        recent_10_volumes = [v.get("volume", 0) for v in volume_history[-10:]]
        
        avg_volume = sum(recent_10_volumes) / len(recent_10_volumes)
        recent_low = min(recent_10_prices)
        current_price = recent_10_prices[-1]
        
        # 信号1：缩量下跌
        if len(recent_10_prices) >= 5:
            down_days = sum(1 for i in range(1, 5) 
                          if recent_10_prices[-i] < recent_10_prices[-i-1])
            if down_days >= 3:
                low_vol_days = sum(1 for i in range(1, 5)
                                  if recent_10_volumes[-i] < avg_volume * 0.7)
                if low_vol_days >= 2:
                    score += 0.15
                    signals_found.append("缩量下跌")
        
        # 信号2：支撑位防守
        support = recent_low * 1.02
        touches_support = sum(1 for p in recent_10_prices[-5:]
                            if abs(p - support) / support < 0.02)
        if touches_support >= 3:
            score += 0.2
            signals_found.append("支撑位防守")
        
        # 信号3：尾盘拉升（如果有数据）
        # 需要分时数据，这里简化
        if len(price_history) >= 3:
            changes = [p.get("change_pct", 0) for p in price_history[-3:]]
            if all(c > 0 for c in changes) and all(
                p.get("close", 0) > p.get("open", 0) for p in price_history[-3:]
            ):
                score += 0.1
                signals_found.append("连续收阳")
        
        # 信号4：价格区间震荡
        price_range = (max(recent_10_prices) - min(recent_10_prices)) / recent_low
        if price_range < 0.1:  # 振幅小于10%
            score += 0.1
            signals_found.append("低位震荡")
        
        return min(1.0, score)
    
    def _detect_manipulation(
        self,
        price_history: List[dict],
        volume_history: List[dict]
    ) -> float:
        """检测拉升信号"""
        score = 0.0
        signals_found = []
        
        recent_changes = [p.get("change_pct", 0) for p in price_history[-5:]]
        recent_volumes = [v.get("volume", 0) for v in volume_history[-5:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        
        # 信号1：连续上涨
        up_days = sum(1 for c in recent_changes if c > 2)
        if up_days >= 3:
            score += 0.15
            signals_found.append("连续大涨")
        
        # 信号2：放量上涨
        recent_vol_ratio = recent_volumes[-1] / max(avg_volume, 1)
        if recent_vol_ratio > 1.5 and recent_changes[-1] > 2:
            score += 0.2
            signals_found.append("放量拉升")
        
        # 信号3：动量加速
        if len(recent_changes) >= 3:
            if all(recent_changes[i] > recent_changes[i-1] for i in range(1, 3)):
                score += 0.15
                signals_found.append("动量加速")
        
        # 信号4：创新高
        recent_high = max(p.get("high", 0) for p in price_history[-20:][:-5])
        current_high = max(p.get("high", 0) for p in price_history[-5:])
        if current_high > recent_high:
            score += 0.15
            signals_found.append("创新高")
        
        return min(1.0, score)
    
    def _detect_shakeout(
        self,
        price_history: List[dict],
        volume_history: List[dict]
    ) -> float:
        """检测洗盘信号"""
        score = 0.0
        signals_found = []
        
        recent = price_history[-5:]
        recent_vol = volume_history[-5:]
        
        # 信号1：日内震幅大
        volatilities = [(p.get("high", 0) - p.get("low", 0)) / p.get("close", 1) 
                       for p in recent]
        high_vol_days = sum(1 for v in volatilities if v > 0.03)
        if high_vol_days >= 2:
            score += 0.15
            signals_found.append("高波动")
        
        # 信号2：快速下跌快速反弹
        for i in range(len(recent) - 1):
            day1_change = recent[i].get("change_pct", 0)
            day2_change = recent[i+1].get("change_pct", 0)
            if day1_change < -2 and day2_change > 1.5:
                score += 0.2
                signals_found.append("快速洗盘")
                break
        
        # 信号3：量能时大时小
        avg_vol = sum(v.get("volume", 0) for v in recent_vol) / len(recent_vol)
        vol_ratio = [v.get("volume", 0) / max(avg_vol, 1) for v in recent_vol]
        if max(vol_ratio) / min([r for r in vol_ratio if r > 0]) > 3:
            score += 0.15
            signals_found.append("量能不稳")
        
        return min(1.0, score)
    
    def _detect_distribution(
        self,
        price_history: List[dict],
        volume_history: List[dict]
    ) -> float:
        """检测出货信号"""
        score = 0.0
        signals_found = []
        
        recent = price_history[-10:]
        recent_vol = volume_history[-10:]
        
        # 计算近期高点
        recent_high = max(p.get("close", 0) for p in recent)
        current_price = recent[-1].get("close", 0)
        
        # 信号1：高位放量滞涨
        if recent_high - current_price < recent_high * 0.05:  # 在高位
            high_vol_days = sum(1 for v in recent_vol[-5:]
                               if v.get("volume", 0) > sum(
                                   vol.get("volume", 0) for vol in recent_vol[-10:-5]
                               ) / 5)
            if high_vol_days >= 3:
                score += 0.2
                signals_found.append("高位放量")
        
        # 信号2：收盘在低位
        close_positions = [p.get("close", 0) / p.get("high", 1) for p in recent]
        weak_closes = sum(1 for cp in close_positions if cp < 0.97)
        if weak_closes >= 3:
            score += 0.15
            signals_found.append("收盘弱势")
        
        # 信号3：连续高开低走
        high_opens = sum(1 for p in recent
                        if p.get("open", 0) > p.get("close", 0) * 1.01)
        if high_opens >= 3:
            score += 0.2
            signals_found.append("高开低走")
        
        # 信号4：利好频出但股价不涨
        # 需要结合新闻数据，这里简化
        if len(recent) >= 5:
            avg_change = sum(p.get("change_pct", 0) for p in recent) / len(recent)
            if avg_change < 0.5:  # 涨幅很小
                score += 0.1
                signals_found.append("滞涨")
        
        return min(1.0, score)
    
    def _detect_fake_breakout(
        self,
        price_history: List[dict],
        volume_history: List[dict],
        minute_data: Optional[List[dict]]
    ) -> float:
        """检测假突破"""
        score = 0.0
        signals_found = []
        
        if len(price_history) < 5:
            return 0.0
        
        # 信号1：突破后回落
        recent = price_history[-5:]
        breakout_day = recent[-1]
        
        # 判断是否突破
        prev_high = max(p.get("high", 0) for p in price_history[-10:-1])
        if breakout_day.get("high", 0) > prev_high:
            # 突破了！
            breakout_volume = volume_history[-1].get("volume", 0)
            avg_volume = sum(v.get("volume", 0) for v in volume_history[-10:-1]) / 9
            
            # 但是...
            if breakout_volume < avg_volume * 1.3:
                score += 0.2
                signals_found.append("突破量能不足")
            
            if breakout_day.get("close", 0) < prev_high * 1.01:
                score += 0.25
                signals_found.append("突破后回落")
        
        # 信号2：分时图分析（如果有）
        if minute_data:
            # 检查是否有尾盘砸盘
            last_hour = minute_data[-60:] if len(minute_data) >= 60 else minute_data
            if last_hour:
                first_price = last_hour[0].get("price", 0)
                last_price = last_hour[-1].get("price", 0)
                if last_price < first_price * 0.98:
                    score += 0.2
                    signals_found.append("尾盘砸盘")
        
        return min(1.0, score)
    
    def _get_stage_evidence(
        self,
        stage: str,
        price_history: List[dict],
        volume_history: List[dict]
    ) -> List[str]:
        """获取阶段证据"""
        evidence = []
        
        stage_mapping = {
            "吸筹": self.ACCUMULATION_SIGNALS,
            "拉升": self.MANIPULATION_SIGNALS,
            "洗盘": self.SHAKEOUT_SIGNALS,
            "出货": self.DISTRIBUTION_SIGNALS
        }
        
        signals = stage_mapping.get(stage, {})
        evidence = [f"{v['name']}: {v['description']}" for v in signals.values()]
        
        return evidence[:3]
    
    def _get_fake_breakout_evidence(
        self,
        price_history: List[dict],
        volume_history: List[dict],
        minute_data: Optional[List[dict]]
    ) -> List[str]:
        """获取假突破证据"""
        evidence = []
        
        # 量能不足
        recent_vol = volume_history[-1].get("volume", 0)
        avg_vol = sum(v.get("volume", 0) for v in volume_history[-10:-1]) / 9
        if recent_vol < avg_vol * 1.3:
            evidence.append("突破时量能不足")
        
        # 收盘弱势
        last = price_history[-1]
        if last.get("close", 0) < last.get("high", 0) * 0.98:
            evidence.append("收盘未能维持高位")
        
        return evidence
    
    def _assess_risk_level(self, stage: str) -> str:
        """评估风险等级"""
        risk_mapping = {
            "吸筹": "medium",      # 低位，相对安全
            "拉升": "medium",      # 顺势赚钱
            "洗盘": "high",        # 容易被洗出
            "出货": "critical",    # 极度危险
            "假突破": "high"       # 陷阱
        }
        return risk_mapping.get(stage, "unknown")
    
    def _calculate_survival_score(
        self,
        scores: Dict[str, float],
        patterns: List[GamingPattern]
    ) -> float:
        """计算生存分数"""
        # 基础分数
        base_score = 70.0
        
        # 根据阶段调整
        if patterns:
            stage = patterns[0].stage
            if stage == "出货":
                base_score -= 30
            elif stage == "洗盘":
                base_score -= 20
            elif stage == "假突破":
                base_score -= 25
            elif stage == "拉升":
                base_score += 10
            elif stage == "吸筹":
                base_score += 5
        
        # 根据最高信号强度调整
        max_score = max(scores.values())
        if max_score > 0.6:
            base_score -= 15
        elif max_score > 0.4:
            base_score -= 5
        
        return max(0, min(100, base_score))
    
    def _generate_risk_signals(self, scores: Dict[str, float]) -> List[str]:
        """生成风险信号"""
        signals = []
        
        if scores["出货"] > 0.4:
            signals.append("⚠️ 高位派发信号：主力可能在出货")
        
        if scores["假突破"] > 0.3:
            signals.append("⚠️ 假突破风险：可能是陷阱")
        
        if scores["洗盘"] > 0.5:
            signals.append("⚠️ 洗盘信号：容易被洗出")
        
        if scores["拉升"] > 0.6:
            signals.append("💡 拉升信号：顺势赚钱机会")
        
        if scores["吸筹"] > 0.5:
            signals.append("📍 吸筹信号：主力在布局")
        
        return signals
    
    def _generate_warnings(
        self,
        patterns: List[GamingPattern],
        scores: Dict[str, float]
    ) -> List[str]:
        """生成预警"""
        warnings = []
        
        if not patterns:
            warnings.append("未检测到明显的坐庄模式")
            return warnings
        
        pattern = patterns[0]
        
        if pattern.risk_level == "critical":
            warnings.append("🚨 极度危险：主力正在或已经完成出货")
            warnings.append("建议立即减仓或清仓")
        
        elif pattern.risk_level == "high":
            warnings.append("⚠️ 高风险：当前市场可能有陷阱")
            warnings.append("建议谨慎操作，不要追涨")
        
        return warnings
    
    def _generate_survival_tips(
        self,
        patterns: List[GamingPattern],
        survival_score: float
    ) -> List[str]:
        """生成生存建议"""
        tips = []
        
        if survival_score >= 80:
            tips.append("当前市场相对安全")
            tips.append("可以顺势操作，但注意止损")
        elif survival_score >= 60:
            tips.append("市场有一定风险")
            tips.append("控制仓位，不要重仓")
        else:
            tips.append("市场风险较高")
            tips.append("建议观望或减仓")
        
        if patterns:
            pattern = patterns[0]
            if pattern.stage == "洗盘":
                tips.append("被洗出时不要恐慌追加")
                tips.append("如果仓位不重，可以考虑不卖")
            elif pattern.stage == "出货":
                tips.append("不要再追高买入")
                tips.append("有盈利的可以考虑止盈")
            elif pattern.stage == "假突破":
                tips.append("不要追突破，等回踩确认再买")
                tips.append("突破失败要果断止损")
        
        return tips
    
    def _generate_recommendation(
        self,
        patterns: List[GamingPattern],
        survival_score: float
    ) -> str:
        """生成推荐行动"""
        if not patterns:
            return "无明显坐庄信号，建议正常操作"
        
        pattern = patterns[0]
        
        if pattern.stage == "吸筹":
            return "持有或逢低加仓，耐心等待拉升"
        elif pattern.stage == "拉升":
            return "顺势持有，不追涨，设定止盈位"
        elif pattern.stage == "洗盘":
            return "持有不动，不要被洗出"
        elif pattern.stage == "出货":
            return "立即减仓或清仓，不要再买入"
        elif pattern.pattern_type == "假突破陷阱":
            return "不追突破，等待回踩确认"
        
        return "谨慎操作，控制仓位"
    
    def _record_detection(
        self,
        stock: str,
        report: AntiGamingReport
    ):
        """记录检测"""
        self.state["detected_patterns"][stock] = {
            "timestamp": datetime.now().isoformat(),
            "is_gamed": report.is_gamed,
            "confidence": report.confidence,
            "patterns": [
                {"type": p.pattern_type, "stage": p.stage, "risk": p.risk_level}
                for p in report.patterns
            ],
            "survival_score": report.survival_score,
            "action": report.recommended_action
        }
        
        if report.is_gamed and report.confidence > 0.5:
            self.state["alerts"].append({
                "stock": stock,
                "timestamp": datetime.now().isoformat(),
                "confidence": report.confidence,
                "patterns": [p.stage for p in report.patterns]
            })
        
        self.state["meta"]["total_scans"] += 1
        if report.is_gamed:
            self.state["meta"]["patterns_detected"] += 1
        
        self._save()
    
    # ========== 格式化输出 ==========
    
    def format_report(self, report: AntiGamingReport, stock: str) -> str:
        """格式化报告"""
        lines = []
        lines.append(f"🛡️ 反坐庄检测报告 - {stock}")
        lines.append(f"{'='*50}")
        lines.append("")
        
        if report.is_gamed:
            lines.append(f"🐋 检测结果: 疑似被坐庄")
            lines.append(f"置信度: {report.confidence:.0%}")
            lines.append("")
            
            for pattern in report.patterns:
                lines.append(f"📊 模式: {pattern.pattern_type}")
                lines.append(f"  阶段: {pattern.stage}")
                lines.append(f"  风险: {pattern.risk_level}")
                lines.append(f"  证据:")
                for e in pattern.evidence:
                    lines.append(f"    • {e}")
                lines.append("")
        else:
            lines.append("✅ 未检测到明显坐庄信号")
            lines.append("")
        
        lines.append(f"🎯 生存分数: {report.survival_score:.0f}/100")
        lines.append("")
        
        if report.risk_signals:
            lines.append("📡 风险信号:")
            for signal in report.risk_signals:
                lines.append(f"  {signal}")
            lines.append("")
        
        if report.warnings:
            lines.append("🚨 预警:")
            for warning in report.warnings:
                lines.append(f"  {warning}")
            lines.append("")
        
        if report.survival_tips:
            lines.append("💡 生存建议:")
            for tip in report.survival_tips:
                lines.append(f"  • {tip}")
            lines.append("")
        
        lines.append("📋 推荐行动:")
        lines.append(f"  {report.recommended_action}")
        
        return "\n".join(lines)
    
    # ========== 统计 ==========
    
    def get_stats(self) -> dict:
        """获取统计"""
        total = self.state["meta"]["total_scans"]
        detected = self.state["meta"]["patterns_detected"]
        
        recent_alerts = self.state["alerts"][-20:]
        
        return {
            "total_scans": total,
            "patterns_detected": detected,
            "detection_rate": round(detected / max(total, 1), 2),
            "recent_alerts": recent_alerts
        }
