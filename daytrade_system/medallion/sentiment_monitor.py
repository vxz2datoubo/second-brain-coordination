"""
sentiment_monitor.py — 板块情绪监测模块

功能：
1. 监测昆仑/蓝色相关板块的新闻和公告
2. 分析市场整体情绪（AI板块/科技板块）
3. 提供情绪评分，影响T仓信号的权重
4. 识别突发消息，实时提醒

使用方式：
  monitor = SentimentMonitor()
  sentiment = monitor.get_sentiment()  # "bullish" / "normal" / "bearish"
  alerts = monitor.get_alerts()        # 突发消息列表
"""

import os, sys, json, time, struct
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Optional

# ========== 新闻数据源 ==========
class NewsSource:
    """新闻数据源（可扩展）"""
    
    def __init__(self):
        self.recent_news = []  # 缓存最近新闻
    
    def get_ai_news(self) -> List[Dict]:
        """
        获取AI/科技相关新闻
        目前使用本地数据，日后可接入东方财富/同花顺MCP
        """
        # 占位：日后对接通达信MCP
        return []
    
    def get_stock_news(self, code: str) -> List[Dict]:
        """获取个股新闻"""
        return []


# ========== 板块分类 ==========
SECTOR_STOCKS = {
    "AI": ["300058", "300418", "300496", "002230", "002415"],  # 昆仑、蓝色、科大讯飞、科大讯飞、海康威视
    "GAME": ["300058", "300418", "002558", "603444"],  # 昆仑、蓝色、完美世界、吉比特
    "INTERNET": ["300058", "300418", "300033"],  # 昆仑、蓝色、同花顺
}

SECTOR_NEWS_KEYWORDS = {
    "AI": ["人工智能", "大模型", "LLM", "ChatGPT", "OpenAI", "AI芯片", "算力", "AIGC", "文生图", "文生视频", "游戏引擎"],
    "GAME": ["游戏", "版号", "Steam", "手游", "端游", "元宇宙", "VR", "AR"],
    "INTERNET": ["互联网", "电商", "直播", "短视频", "SaaS", "云服务"],
}

BEARISH_KEYWORDS = ["利空", "减持", "黑嘴", "造假", "监管", "问询函", "调查", "亏损", "预警", "业绩下降"]
BULLISH_KEYWORDS = ["利好", "回购", "增持", "业绩预增", "订单", "突破", "获批", "合作", "AI", "大模型"]


class SentimentMonitor:
    """
    情绪监测器
    
    每日开盘前调用 get_sentiment() 获取当日情绪
    全天可调用 get_alerts() 获取突发消息
    """
    
    def __init__(self):
        self.news_source = NewsSource()
        self.daily_sentiment = "normal"  # 当日情绪
        self.alerts = []  # 突发消息
        self.last_check = None
        self.cache_duration = 300  # 5分钟缓存
    
    def analyze(self):
        """
        分析当日情绪
        """
        # 检查缓存
        now = time.time()
        if self.last_check and now - self.last_check < self.cache_duration:
            return self.daily_sentiment
        
        self.last_check = now
        sentiment_score = 0
        
        # 1. AI板块整体情绪
        ai_news = self.news_source.get_ai_news()
        for news in ai_news:
            title = news.get("title", "")
            content = news.get("content", "")
            text = title + content
            
            for kw in BULLISH_KEYWORDS:
                if kw in text:
                    sentiment_score += 1
            for kw in BEARISH_KEYWORDS:
                if kw in text:
                    sentiment_score -= 2
        
        # 2. 昆仑相关消息
        kunlun_news = self.news_source.get_stock_news("300058")
        for news in kunlun_news:
            title = news.get("title", "")
            content = news.get("content", "")
            text = title + content

            # 昆仑利好关键词（AI、大模型、游戏）
            for kw in ["昆仑万维", "天工", "AI游戏", "大模型", "Opera"]:
                if kw in text:
                    sentiment_score += 2
            
            for kw in ["业绩", "营收", "增长", "突破"]:
                if kw in text:
                    sentiment_score += 1

        # 3. 蓝色相关消息
        blue_news = self.news_source.get_stock_news("300418")
        for news in blue_news:
            title = news.get("title", "")
            content = news.get("content", "")
            text = title + content

            for kw in ["蓝色光标", "AI营销", "元宇宙", "数字人"]:
                if kw in text:
                    sentiment_score += 1

        # 4. 判断情绪级别
        if sentiment_score >= 2:
            self.daily_sentiment = "bullish"
        elif sentiment_score <= -2:
            self.daily_sentiment = "bearish"
        else:
            self.daily_sentiment = "normal"
        
        return self.daily_sentiment
    
    def add_alert(self, alert_type: str, code: str, title: str, content: str = ""):
        """添加突发消息提醒"""
        self.alerts.append({
            "type": alert_type,  # "news" / "announcement" / "sector"
            "code": code,
            "title": title,
            "content": content,
            "time": datetime.now().strftime("%H:%M"),
        })
    
    def get_sentiment(self) -> str:
        """获取当日情绪"""
        return self.analyze()
    
    def get_alerts(self) -> List[Dict]:
        """获取突发消息"""
        return self.alerts[-10:]  # 最近10条
    
    def get_sentiment_info(self) -> Dict:
        """获取完整情绪信息"""
        sentiment = self.get_sentiment()
        
        sentiment_labels = {
            "bullish": "强势(利好)",
            "normal": "正常",
            "bearish": "弱势"
        }
        
        sentiment_descriptions = {
            "bullish": "AI板块整体强势，可能有重大利好。减少卖出，提高接回敏感度。",
            "normal": "市场情绪平稳，按常规信号操作。",
            "bearish": "市场情绪偏弱，注意控制风险。可适当增加卖出信号门槛。"
        }
        
        return {
            "sentiment": sentiment,
            "label": sentiment_labels.get(sentiment, "正常"),
            "description": sentiment_descriptions.get(sentiment, ""),
            "alerts": self.get_alerts(),
        }
    
    def get_trading_advice(self) -> Dict:
        """
        基于情绪给出交易建议
        """
        info = self.get_sentiment_info()
        sentiment = info["sentiment"]
        
        advice = {
            "bullish": {
                "sell_threshold_mult": 1.3,  # 提高卖出门槛
                "buy_threshold_mult": 0.8,    # 降低接回门槛
                "max_slots": 2,              # 减少持仓
                "description": "强势市场，减少T仓操作，底仓持有为主"
            },
            "normal": {
                "sell_threshold_mult": 1.0,
                "buy_threshold_mult": 1.0,
                "max_slots": 3,
                "description": "正常市场，按系统信号操作"
            },
            "bearish": {
                "sell_threshold_mult": 0.8,  # 降低卖出门槛，更容易卖
                "buy_threshold_mult": 1.2,    # 提高接回门槛
                "max_slots": 2,
                "description": "弱势市场，快进快出，不恋战"
            }
        }
        
        return advice.get(sentiment, advice["normal"])


# ========== 盘前自动分析 ==========
def pre_market_analysis():
    """
    盘前自动分析
    在9:15之前调用，获取当日情绪
    """
    print("=" * 50)
    print("  盘前情绪分析")
    print("=" * 50)
    
    monitor = SentimentMonitor()
    info = monitor.get_sentiment_info()
    advice = monitor.get_trading_advice()
    
    print(f"\n当日情绪: {info['label']}")
    print(f"描述: {info['description']}")
    print(f"\n交易建议: {advice['description']}")
    print(f"  卖出门槛: x{advice['sell_threshold_mult']}")
    print(f"  接回门槛: x{advice['buy_threshold_mult']}")
    print(f"  最大持仓: {advice['max_slots']}笔")
    
    if info['alerts']:
        print(f"\n突发消息 ({len(info['alerts'])}条):")
        for alert in info['alerts'][:5]:
            print(f"  [{alert['time']}] {alert['title']}")
    
    return info, advice


# ========== 集成到主系统 ==========
def get_adjusted_threshold(base_threshold: float, sentiment: str, direction: str = "sell") -> float:
    """
    根据情绪调整信号门槛
    
    Args:
        base_threshold: 基础门槛（如50分）
        sentiment: 情绪（bullish/normal/bearish）
        direction: sell或buy
    
    Returns:
        调整后的门槛
    """
    advice = SentimentMonitor().get_trading_advice()
    
    if direction == "sell":
        return base_threshold * advice["sell_threshold_mult"]
    else:  # buy
        return base_threshold * advice["buy_threshold_mult"]


if __name__ == "__main__":
    pre_market_analysis()
