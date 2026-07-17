"""
news_verification.py — 消息时效性验证引擎
==========================================
判断新闻的真假、时效性、是否已被市场消化、是否有人为炒作。
这是顶级交易员必备的"消息鉴别"能力。

核心理论：
1. 信息套利：消息如何被机构/主力提前获取
2. 反身性：消息与股价的相互作用
3. 市场效率：消息如何被price in
4. 行为金融：投资者对消息的非理性反应

设计理念：
- 像新闻调查记者一样核实消息
- 不相信表面的消息，要找背后的真相
- 判断消息是否已被市场消化
"""

import json
import uuid
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter


@dataclass
class NewsVerification:
    """消息验证结果"""
    is_authentic: bool = True           # 是否可信
    authenticity_score: float = 0.8    # 可信度评分
    freshness: str = "unknown"         # 时效性
    market_digested: bool = False      # 是否已被市场消化
    digestion_level: float = 0.0       # 消化程度 0-1
    manipulation_suspect: bool = False # 是否疑似炒作
    manipulation_score: float = 0.0    # 炒作嫌疑评分
    prior_leakage: bool = False        # 是否疑似提前泄露
    evidence_chain: List[dict] = field(default_factory=list)
    similar_news_history: List[dict] = field(default_factory=list)
    verdict: str = ""


@dataclass
class PriceReaction:
    """价格反应分析"""
    reaction_type: str = "none"        # 积极/消极/中性
    reaction_strength: float = 0.0     # 反应强度 0-1
    timing: str = ""                    # 时机
    is_justified: bool = True          # 反应是否合理
    sustainability: str = "unknown"     # 持续性


class NewsVerificationEngine:
    """消息时效性验证引擎
    
    核心能力：
    1. 消息真伪鉴别 — 官方来源 vs 传言 vs 谣言
    2. 时效性判断 — 消息是否最新、是否已过时
    3. 消化程度评估 — 市场是否已经price in
    4. 炒作识别 — 判断是否是人为制造的"消息"
    5. 提前泄露检测 — 判断是否有人提前知道
    6. 价格反应分析 — 消息与股价的互动关系
    """
    
    # 消息来源可信度
    SOURCE_CREDIBILITY = {
        "官方": 0.95,      # 证监会、交易所、公司公告
        "权威媒体": 0.85,  # 新华社、人民日报
        "财经媒体": 0.75,  # 证券时报、上海证券报
        "自媒体": 0.5,     # 微信公众号、雪球
        "论坛": 0.3,       # 东方财富股吧
        "匿名": 0.1,       # 匿名消息
    }
    
    # 消息类型时效性
    NEWS_TYPES = {
        "突发事件": {"shelf_life": 0.5, "impact_duration": "short"},
        "政策": {"shelf_life": 24, "impact_duration": "long"},
        "业绩": {"shelf_life": 48, "impact_duration": "medium"},
        "合作": {"shelf_life": 72, "impact_duration": "medium"},
        "公告": {"shelf_life": 0.25, "impact_duration": "short"},
        "传闻": {"shelf_life": 0.5, "impact_duration": "short"},
        "研报": {"shelf_life": 168, "impact_duration": "medium"},
    }
    
    # 炒作特征关键词
    MANIPULATION_KEYWORDS = {
        "high": ["内幕", "提前", "主力", "庄家", "即将", "暴涨", "必涨", "翻倍"],
        "medium": ["利好", "重磅", "突发", "曝光", "埋伏"],
        "low": ["消息", "传闻", "称", "据", "市场传言"],
    }
    
    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.state_path = data_dir / "news_verification_state.json"
        self.state = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "verified_news": [],     # 已验证消息
                "news_history": [],      # 历史消息记录
                "digestion_records": [], # 消化记录
                "manipulation_alerts": [], # 炒作预警
                "meta": {
                    "total_verified": 0,
                    "manipulation_detected": 0,
                    "prior_leakage_suspected": 0
                }
            }
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    # ========== 核心验证方法 ==========
    
    def verify(
        self,
        news: dict,
        stock: str,
        price_data: Optional[dict] = None,
        related_news: Optional[List[dict]] = None,
    ) -> NewsVerification:
        """综合验证消息
        
        Args:
            news: 消息数据 {title, content, source, time, type}
            stock: 股票代码
            price_data: 价格数据（可选）
            related_news: 相关历史消息
        
        Returns:
            NewsVerification: 验证结果
        """
        result = NewsVerification()
        
        # 1. 验证真伪
        authenticity = self._verify_authenticity(news, stock)
        result.is_authentic = authenticity["is_authentic"]
        result.authenticity_score = authenticity["score"]
        result.evidence_chain.append({
            "step": 1,
            "type": "authenticity",
            "finding": f"可信度: {authenticity['score']:.0%}",
            "evidence": authenticity["evidence"]
        })
        
        # 2. 判断时效性
        freshness = self._judge_freshness(news)
        result.freshness = freshness["status"]
        result.evidence_chain.append({
            "step": 2,
            "type": "freshness",
            "finding": freshness["status"],
            "detail": freshness.get("detail", "")
        })
        
        # 3. 评估市场消化程度
        digestion = self._assess_digestion(news, stock, price_data)
        result.market_digested = digestion["digested"]
        result.digestion_level = digestion["level"]
        result.evidence_chain.append({
            "step": 3,
            "type": "digestion",
            "finding": f"消化程度: {digestion['level']:.0%}",
            "detail": digestion.get("reason", "")
        })
        
        # 4. 检测炒作嫌疑
        manipulation = self._detect_manipulation(news, stock, price_data)
        result.manipulation_suspect = manipulation["suspected"]
        result.manipulation_score = manipulation["score"]
        result.evidence_chain.append({
            "step": 4,
            "type": "manipulation",
            "finding": f"炒作嫌疑: {manipulation['score']:.0%}",
            "evidence": manipulation["evidence"]
        })
        
        # 5. 检测提前泄露
        leakage = self._detect_prior_leakage(news, stock, price_data)
        result.prior_leakage = leakage["suspected"]
        result.evidence_chain.append({
            "step": 5,
            "type": "leakage",
            "finding": "可能提前泄露" if leakage["suspected"] else "未发现提前泄露",
            "evidence": leakage["evidence"]
        })
        
        # 6. 历史相似消息
        similar = self._find_similar_history(news, stock)
        result.similar_news_history = similar
        
        # 7. 生成最终判断
        result.verdict = self._generate_verdict(result, news, price_data)
        
        # 记录
        self._record_verification(news, stock, result)
        
        return result
    
    def _verify_authenticity(self, news: dict, stock: str) -> dict:
        """验证消息真伪"""
        score = 0.7  # 基础分
        evidence = []
        
        source = news.get("source", "").lower()
        title = news.get("title", "").lower()
        content = news.get("content", "").lower()
        
        # 来源可信度
        source_type = self._classify_source(source)
        source_score = self.SOURCE_CREDIBILITY.get(source_type, 0.5)
        score = (score * 0.5 + source_score * 0.5)
        evidence.append(f"来源类型: {source_type} ({source_score:.0%})")
        
        # 标题特征
        if any(kw in title for kw in ["公告", "通知", "决定", "批准", "监管"]):
            score = min(1.0, score + 0.1)
            evidence.append("标题具有官方公告特征")
        
        # 内容长度
        if len(content) < 50:
            score *= 0.8
            evidence.append("内容过短，可信度降低")
        
        # 是否有具体数据
        has_numbers = bool(re.search(r'\d+', content))
        if has_numbers:
            score = min(1.0, score + 0.05)
            evidence.append("内容包含具体数据")
        
        # 是否带有强烈情感词
        emotional_words = ["惊人", "震惊", "重磅", "内幕", "必看"]
        if any(w in title for w in emotional_words):
            score *= 0.85
            evidence.append("标题带有强烈情感词，可信度降低")
        
        # 是否带有"据"字（传闻特征）
        if title.startswith("据") or "据报道" in title:
            score *= 0.9
            evidence.append("疑似传闻")
        
        return {
            "is_authentic": score > 0.5,
            "score": round(score, 2),
            "evidence": evidence
        }
    
    def _classify_source(self, source: str) -> str:
        """分类消息来源"""
        source_lower = source.lower()
        
        if any(k in source_lower for k in ["证监会", "交易所", "公司公告", "官方"]):
            return "官方"
        elif any(k in source_lower for k in ["新华社", "人民日报", "央视"]):
            return "权威媒体"
        elif any(k in source_lower for k in ["证券时报", "上海证券报", "第一财经"]):
            return "财经媒体"
        elif any(k in source_lower for k in ["雪球", "公众号", "微博"]):
            return "自媒体"
        elif any(k in source_lower for k in ["股吧", "东财", "同花顺"]):
            return "论坛"
        
        return "未知"
    
    def _judge_freshness(self, news: dict) -> dict:
        """判断时效性"""
        try:
            news_time = datetime.fromisoformat(news.get("time", datetime.now().isoformat()))
        except:
            news_time = datetime.now()
        
        age_hours = (datetime.now() - news_time).total_seconds() / 3600
        
        news_type = news.get("type", "消息")
        shelf_life = self.NEWS_TYPES.get(news_type, {}).get("shelf_life", 24)
        
        if age_hours < 1:
            status = "最新"
            detail = f"发布于{age_hours*60:.0f}分钟前"
        elif age_hours < 6:
            status = "较新"
            detail = f"发布于{age_hours:.1f}小时前"
        elif age_hours < 24:
            status = "一般"
            detail = f"发布于{age_hours:.1f}小时前"
        elif age_hours < shelf_life:
            status = "偏旧"
            detail = f"已发布超过{age_hours:.0f}小时"
        else:
            status = "过时"
            detail = f"已发布{age_hours/24:.1f}天，可能已失效"
        
        return {"status": status, "detail": detail, "age_hours": age_hours}
    
    def _assess_digestion(
        self,
        news: dict,
        stock: str,
        price_data: Optional[dict] = None
    ) -> dict:
        """评估市场消化程度"""
        if not price_data:
            return {"digested": False, "level": 0.0, "reason": "无价格数据"}
        
        # 计算新闻发布后价格变动
        try:
            news_time = datetime.fromisoformat(news.get("time", datetime.now().isoformat()))
        except:
            news_time = datetime.now()
        
        reaction = price_data.get("change_pct", 0)
        
        # 判断消化程度
        if abs(reaction) > 5:
            # 大幅波动 = 基本消化
            if reaction > 0:
                level = 0.8 + min(0.2, reaction / 20)
            else:
                level = 0.6 + min(0.3, abs(reaction) / 15)
        elif abs(reaction) > 2:
            level = 0.5
        elif abs(reaction) > 0.5:
            level = 0.3
        else:
            level = 0.1
        
        # 检查成交量是否放大
        if price_data.get("volume_ratio", 1) > 2:
            level = min(1.0, level + 0.2)
        
        # 时间因素：越久越可能消化
        age_hours = (datetime.now() - news_time).total_seconds() / 3600
        if age_hours > 24:
            level = min(1.0, level + 0.1 * (age_hours / 24))
        
        return {
            "digested": level > 0.7,
            "level": round(min(1.0, level), 2),
            "reason": f"价格反应{reaction:.1f}%"
        }
    
    def _detect_manipulation(
        self,
        news: dict,
        stock: str,
        price_data: Optional[dict] = None
    ) -> dict:
        """检测炒作嫌疑"""
        score = 0.0
        evidence = []
        
        title = news.get("title", "")
        content = news.get("content", "")
        
        # 关键词检测
        high_keywords = self.MANIPULATION_KEYWORDS["high"]
        medium_keywords = self.MANIPULATION_KEYWORDS["medium"]
        
        high_hits = [kw for kw in high_keywords if kw in title]
        medium_hits = [kw for kw in medium_keywords if kw in title]
        
        score += len(high_hits) * 0.2
        score += len(medium_hits) * 0.1
        evidence.append(f"标题关键词匹配: {high_hits + medium_hits}")
        
        # 来源分析
        source = news.get("source", "").lower()
        if any(k in source for k in ["股吧", "论坛", "不明"]):
            score += 0.15
            evidence.append("来源为论坛/匿名")
        
        # 内容分析：是否过于乐观
        optimistic_words = ["暴涨", "翻倍", "必涨", "捡钱", "送钱"]
        if any(w in content for w in optimistic_words):
            score += 0.2
            evidence.append("内容包含过度乐观词汇")
        
        # 是否是"即将"类消息
        if "即将" in title or "马上" in title:
            score += 0.15
            evidence.append("标题含'即将'/'马上'，制造紧迫感")
        
        # 价格配合分析
        if price_data:
            reaction = price_data.get("change_pct", 0)
            if reaction > 3 and score > 0.3:
                score += 0.15
                evidence.append(f"消息+股价大幅上涨({reaction}%)，可能配合炒作")
        
        return {
            "suspected": score > 0.4,
            "score": round(min(1.0, score), 2),
            "evidence": evidence,
            "keywords_found": high_hits + medium_hits
        }
    
    def _detect_prior_leakage(
        self,
        news: dict,
        stock: str,
        price_data: Optional[dict] = None
    ) -> dict:
        """检测提前泄露"""
        suspected = False
        evidence = []
        
        if not price_data:
            return {"suspected": False, "evidence": []}
        
        # 特征1：消息前价格已经上涨
        price_before = price_data.get("change_pct_before", 0)
        if price_before > 2:
            suspected = True
            evidence.append(f"消息公布前股价已上涨{price_before}%")
        
        # 特征2：成交量异常
        volume_ratio = price_data.get("volume_ratio", 1)
        if volume_ratio > 2 and price_before > 0:
            suspected = True
            evidence.append(f"消息前成交量放大{volume_ratio}倍")
        
        # 特征3：尾盘异动
        if price_data.get("tail_surge", False):
            suspected = True
            evidence.append("消息前出现尾盘拉升")
        
        return {
            "suspected": suspected,
            "evidence": evidence,
            "risk_level": "high" if suspected else "low"
        }
    
    def _find_similar_history(
        self,
        news: dict,
        stock: str
    ) -> List[dict]:
        """查找历史相似消息"""
        similar = []
        title = news.get("title", "")
        keywords = self._extract_keywords(title)
        
        for record in self.state["news_history"][-100:]:
            if record.get("stock") != stock:
                continue
            
            record_title = record.get("title", "")
            record_keywords = self._extract_keywords(record_title)
            
            # 计算关键词重叠度
            overlap = len(keywords & record_keywords)
            if overlap >= 2:
                similar.append({
                    "title": record_title,
                    "time": record.get("time", ""),
                    "similarity": overlap / max(len(keywords), 1),
                    "outcome": record.get("outcome", "未知")
                })
        
        return sorted(similar, key=lambda x: x["similarity"], reverse=True)[:5]
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """提取关键词"""
        # 简单实现：提取连续的数字和特定词汇
        keywords = set()
        
        # 提取2-4字的词组
        for i in range(len(text) - 1):
            word = text[i:i+2]
            if '\u4e00' <= word[0] <= '\u9fff':
                keywords.add(word)
        
        # 提取股票代码
        codes = re.findall(r'\d{6}', text)
        keywords.update(codes)
        
        return keywords
    
    def _generate_verdict(
        self,
        result: NewsVerification,
        news: dict,
        price_data: Optional[dict] = None
    ) -> str:
        """生成最终判断"""
        parts = []
        
        # 基础判断
        if result.authenticity_score < 0.5:
            return "[可疑] 消息来源可信度低，建议不参考"
        
        # 时效性判断
        if result.freshness == "过时":
            return "[过时] 消息已过期，可能已被消化"
        
        # 消化程度
        if result.market_digested:
            return "[已消化] 市场已基本消化，消息影响有限"
        
        # 炒作嫌疑
        if result.manipulation_suspect:
            if result.manipulation_score > 0.6:
                return "[高危] 高度疑似炒作，建议远离"
            else:
                return "[警惕] 疑似炒作，操作需谨慎"
        
        # 提前泄露
        if result.prior_leakage:
            return "[泄露嫌疑] 可能存在信息泄露，需验证消息真实性"
        
        # 综合判断
        if result.authenticity_score > 0.8 and result.freshness in ["最新", "较新"]:
            if result.market_digested:
                return "[参考] 消息真实但已消化，操作价值有限"
            else:
                return "[关注] 消息可信且新鲜，可关注但需等待确认"
        
        return "[观察] 消息性质一般，建议观望"
    
    def _record_verification(
        self,
        news: dict,
        stock: str,
        result: NewsVerification
    ):
        """记录验证结果"""
        record = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "stock": stock,
            "title": news.get("title", ""),
            "source": news.get("source", ""),
            "verdict": result.verdict,
            "authenticity": result.authenticity_score,
            "freshness": result.freshness,
            "digested": result.market_digested,
            "manipulation": result.manipulation_suspect,
            "leakage": result.prior_leakage,
            "outcome": None  # 待后续更新
        }
        
        self.state["news_history"].append(record)
        self.state["verified_news"].append(record)
        
        if result.manipulation_suspect:
            self.state["manipulation_alerts"].append(record)
        
        # 保持历史记录上限
        if len(self.state["news_history"]) > 500:
            self.state["news_history"] = self.state["news_history"][-500:]
        
        self.state["meta"]["total_verified"] += 1
        if result.manipulation_suspect:
            self.state["meta"]["manipulation_detected"] += 1
        if result.prior_leakage:
            self.state["meta"]["prior_leakage_suspected"] += 1
        
        self._save()
    
    # ========== 批量验证 ==========
    
    def batch_verify(
        self,
        news_list: List[dict],
        stock: str
    ) -> List[NewsVerification]:
        """批量验证消息"""
        results = []
        for news in news_list:
            result = self.verify(news, stock)
            results.append(result)
        return results
    
    # ========== 格式化输出 ==========
    
    def format_verification(self, result: NewsVerification, news: dict) -> str:
        """格式化验证结果"""
        lines = []
        lines.append(f"📰 消息验证报告")
        lines.append(f"{'='*50}")
        lines.append(f"标题: {news.get('title', '')}")
        lines.append(f"来源: {news.get('source', '未知')}")
        lines.append(f"时间: {news.get('time', '未知')}")
        lines.append("")
        
        lines.append("📋 验证结果:")
        lines.append(f"  真实性: {result.authenticity_score:.0%}")
        lines.append(f"  时效性: {result.freshness}")
        lines.append(f"  消化程度: {result.digestion_level:.0%}")
        lines.append(f"  炒作嫌疑: {result.manipulation_score:.0%}")
        lines.append(f"  提前泄露: {'是' if result.prior_leakage else '否'}")
        lines.append("")
        
        if result.evidence_chain:
            lines.append("🔗 证据链:")
            for evidence in result.evidence_chain:
                lines.append(f"  {evidence.get('finding', '')}")
                if evidence.get('evidence'):
                    for e in evidence.get('evidence', []):
                        lines.append(f"    • {e}")
            lines.append("")
        
        if result.similar_news_history:
            lines.append("📜 历史相似:")
            for similar in result.similar_news_history[:3]:
                lines.append(f"  • {similar['title'][:30]}... ({similar['outcome']})")
            lines.append("")
        
        lines.append("🎯 最终判断:")
        lines.append(f"  {result.verdict}")
        
        return "\n".join(lines)
    
    # ========== 统计 ==========
    
    def get_stats(self) -> dict:
        """获取统计"""
        total = self.state["meta"]["total_verified"]
        manipulated = self.state["meta"]["manipulation_detected"]
        leaked = self.state["meta"]["prior_leakage_suspected"]
        
        return {
            "total_verified": total,
            "manipulation_detected": manipulated,
            "manipulation_rate": round(manipulated / max(total, 1), 2),
            "prior_leakage_suspected": leaked,
            "recent_alerts": self.state["manipulation_alerts"][-10:]
        }
