"""
板块题材情绪分析 + 突发消息实时监测
通过通达信 MCP 的新闻/公告接口，实时监测持仓股相关动态

功能：
  1. 定时扫描持仓股相关新闻（wenda_news_query）
  2. 分类新闻对走势的影响（利好/利空/中性）
  3. 板块联动分析：昆仑（AI/大模型）、蓝色（数字营销/短视频）
  4. 突发事件对当前持仓的影响评估
  5. 消息对技术信号的可信度修正
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from live.tdx_mcp_client import get_client

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORK_DIR, "data")
SENTIMENT_FILE = os.path.join(DATA_DIR, "news_sentiment.json")

# ============================================================
# 板块/题材关键词配置
# ============================================================
STOCK_KEYWORDS = {
    "300418": {
        "name": "昆仑万维",
        "sectors": ["AI", "大模型", "人工智能", "AGI", "AIGC"],
        "tags": ["天工AI", "昆仑万维", "大模型", "AI应用", "TMT"],
    },
    "300058": {
        "name": "蓝色光标",
        "sectors": ["数字营销", "广告", "短视频", "Meta"],
        "tags": ["蓝色光标", "数字营销", "AIGC营销", "出海"],
    },
}

# 板块联动（当某板块出现重大消息时，可能影响对应持仓股）
SECTOR_MAP = {
    "AI": ["300418"],
    "人工智能": ["300418"],
    "大模型": ["300418"],
    "AIGC": ["300418", "300058"],
    "数字营销": ["300058"],
    "广告": ["300058"],
    "Meta": ["300058"],
    "出海": ["300058"],
}

# 利好/利空关键词
BULLISH_WORDS = [
    "涨停", "大涨", "利好", "增持", "回购", "获批", "突破",
    "合作", "中标", "订单", "超预期", "扭亏", "放量", "新高",
    "上调", "推荐", "买入", "增资", "扩张"
]
BEARISH_WORDS = [
    "跌停", "大跌", "利空", "减持", "解禁", "被否", "回落",
    "亏损", "下调", "卖出", "减持", "爆雷", "立案", "调查",
    "撤回", "终止", "暂停", "风险"
]


# ============================================================
# 新闻情绪分析器
# ============================================================
class NewsMonitor:
    """
    新闻情绪监测器
    定时从通达信 MCP 拉取新闻，分析情绪，评估影响
    """

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.client = get_client()
        # 已处理的新闻ID（去重）
        self._seen_news: set = set()
        self._sentiment_state: Dict = {
            "last_update": "",
            "stock_news": {},
            "sector_alerts": [],
            "impact_analysis": {},
        }
        self._load()

    def _load(self):
        if os.path.exists(SENTIMENT_FILE):
            try:
                with open(SENTIMENT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._sentiment_state = data
            except Exception:
                pass

    def _save(self):
        self._sentiment_state["last_update"] = datetime.now().isoformat()
        with open(SENTIMENT_FILE, "w", encoding="utf-8") as f:
            json.dump(self._sentiment_state, f, ensure_ascii=False, indent=2)

    def fetch_news(self, codes: List[str] = None, hours_back: int = 24) -> Dict[str, List[Dict]]:
        """
        获取持仓股相关新闻
        Returns: {stock_code: [news_items]}
        """
        codes = codes or list(STOCK_KEYWORDS.keys())
        result = {}
        cutoff = (datetime.now() - timedelta(hours=hours_back)).isoformat()

        for code in codes:
            news_list = []
            # 按股票代码查
            try:
                news = self.client.get_news(code, limit=10, date_range="today")
                news_list.extend(news)
            except Exception:
                pass

            # 按板块关键词查
            info = STOCK_KEYWORDS.get(code, {})
            for tag in info.get("tags", [])[:3]:
                try:
                    tag_news = self.client.get_news(tag, limit=5, date_range="today")
                    news_list.extend(tag_news)
                except Exception:
                    pass

            # 去重
            seen = set()
            unique_news = []
            for n in news_list:
                nid = n.get("id") or n.get("title", "")[:50]
                if nid not in seen:
                    seen.add(nid)
                    unique_news.append(n)
            result[code] = unique_news

        return result

    def analyze_sentiment(self, news_item: Dict) -> Dict:
        """
        分析单条新闻情绪
        Returns: {"sentiment": "bullish"|"bearish"|"neutral", "score": -5~5, "relevance": 0~1}
        """
        title = str(news_item.get("title", ""))
        content = str(news_item.get("content", "") or news_item.get("summary", ""))
        combined = title + " " + content

        bullish_score = sum(1 for w in BULLISH_WORDS if w in combined)
        bearish_score = sum(1 for w in BEARISH_WORDS if w in combined)

        net = bullish_score - bearish_score
        if net > 2:
            sentiment = "bullish"
            score = min(net, 5)
        elif net < -2:
            sentiment = "bearish"
            score = max(net, -5)
        elif net > 0:
            sentiment = "slightly_bullish"
            score = 1
        elif net < 0:
            sentiment = "slightly_bearish"
            score = -1
        else:
            sentiment = "neutral"
            score = 0

        # 关联度（标题出现股票名/代码=高相关）
        relevance = 0.3
        for code in STOCK_KEYWORDS:
            if code in combined:
                relevance = 1.0
                break
            info = STOCK_KEYWORDS.get(code, {})
            name = info.get("name", "")
            if name and name in combined:
                relevance = 1.0
                break
            for tag in info.get("tags", []):
                if tag in title:
                    relevance = max(relevance, 0.8)
                elif tag in combined:
                    relevance = max(relevance, 0.5)

        return {
            "sentiment": sentiment,
            "score": score,
            "relevance": round(relevance, 2),
            "bullish_words": bullish_score,
            "bearish_words": bearish_score,
        }

    def scan_and_analyze(self, codes: List[str] = None) -> Dict:
        """
        完整扫描流程：拉新闻 → 分析情绪 → 板块警报
        """
        codes = codes or list(STOCK_KEYWORDS.keys())
        news_by_code = self.fetch_news(codes)

        result = {}
        sector_signals = {}

        for code, news_list in news_by_code.items():
            analyzed_news = []
            total_bullish = 0
            total_bearish = 0

            for n in news_list:
                sentiment = self.analyze_sentiment(n)
                if sentiment["relevance"] > 0.3:  # 仅保留有关联的
                    analyzed_news.append({
                        "title": n.get("title", ""),
                        "time": n.get("time", n.get("date", "")),
                        "source": n.get("source", ""),
                        **sentiment,
                    })
                    if sentiment["score"] > 0:
                        total_bullish += sentiment["score"]
                    elif sentiment["score"] < 0:
                        total_bearish += abs(sentiment["score"])

            net_sentiment = total_bullish - total_bearish
            impact = "利空" if net_sentiment < -3 else "利好" if net_sentiment > 3 else "中性"

            result[code] = {
                "net_sentiment": net_sentiment,
                "impact": impact,
                "news_count": len(analyzed_news),
                "total_bullish": total_bullish,
                "total_bearish": total_bearish,
                "news": analyzed_news,
            }

        # 板块层面聚合
        sector_sentiment = {}
        for sector, affected_codes in SECTOR_MAP.items():
            scores = [result.get(c, {}).get("net_sentiment", 0) for c in affected_codes]
            avg_score = sum(scores) / len(scores) if scores else 0
            if abs(avg_score) > 2:
                sector_signals[sector] = {
                    "avg_sentiment": avg_score,
                    "direction": "利好" if avg_score > 2 else "利空",
                    "affected_codes": affected_codes,
                    "alert": f"板块【{sector}】情绪偏{('正' if avg_score > 0 else '负')}",
                }

        self._sentiment_state["stock_news"] = result
        self._sentiment_state["sector_signals"] = sector_signals
        self._sentiment_state["last_update"] = datetime.now().isoformat()
        self._save()

        return {"stock_news": result, "sector_signals": sector_signals}

    def assess_impact_on_position(self, stock_code: str, current_price: float,
                                    today_chg_pct: float) -> Dict:
        """
        评估当前消息对持仓的影响
        判断：当前走势是否受消息影响？是否有持续性？
        """
        news = self._sentiment_state.get("stock_news", {}).get(stock_code, {})
        if not news:
            return {"impact": "unknown", "note": "无足够消息"}

        net = news.get("net_sentiment", 0)

        # 判断价格走势与情绪是否一致
        if net > 3 and today_chg_pct < -1:
            consistency = "背离"
            note = "利好氛围但股价下跌，可能是错杀或还未发酵"
        elif net < -3 and today_chg_pct > 1:
            consistency = "背离"
            note = "利空氛围但股价上涨，可能是利空出尽"
        elif net > 3 and today_chg_pct > 1:
            consistency = "一致"
            note = "利好与上涨一致，关注持续性"
        elif net < -3 and today_chg_pct < -1:
            consistency = "一致"
            note = "利空与下跌一致，注意风险"
        else:
            consistency = "中性"
            note = "消息影响有限，以技术信号为主"

        return {
            "stock": stock_code,
            "net_sentiment": net,
            "news_count": news.get("news_count", 0),
            "consistency": consistency,
            "note": note,
            "impact_level": "高" if abs(net) > 5 else "中" if abs(net) > 2 else "低",
        }

    def get_sentiment_adjustment(self, stock_code: str) -> float:
        """
        情绪修正因子（用于修正信号可信度）
        Returns: -10~10 的修正值，正值增加卖信号可信度
        """
        info = self._sentiment_state.get("stock_news", {}).get(stock_code, {})
        net = info.get("net_sentiment", 0)

        # 利空消息 → 倒T卖信号更可信（股价可能跌更多）
        # 利好消息 → 倒T卖信号可信度降低（股价可能撑住）
        if net < -3:
            return +8  # 利空加持，卖信号更可信
        elif net < -1:
            return +3
        elif net > 3:
            return -8  # 利好，卖信号可信度降低
        elif net > 1:
            return -3
        return 0


# ============================================================
# 全局单例
# ============================================================
_monitor: Optional[NewsMonitor] = None

def get_news_monitor() -> NewsMonitor:
    global _monitor
    if _monitor is None:
        _monitor = NewsMonitor()
    return _monitor


# ============================================================
# 快速测试/单次运行
# ============================================================
def quick_scan(codes: List[str] = None):
    """快速扫描情绪并输出"""
    import json as j
    monitor = get_news_monitor()
    print("=== 情绪扫描 ===")
    result = monitor.scan_and_analyze(codes)
    for code, info in result["stock_news"].items():
        print(f"\n【{STOCK_KEYWORDS[code]['name']}({code})】")
        print(f"  消息数量: {info['news_count']}条")
        print(f"  净情绪: {info['net_sentiment']} ({info['impact']})")
        print(f"  板块信号: {j.dumps(result.get('sector_signals', {}), ensure_ascii=False, indent=2)}")
        if info['news']:
            print(f"  最新消息:")
            for n in info['news'][:5]:
                print(f"    · {n['title'][:60]} [{n['sentiment']}]")
    return result


if __name__ == "__main__":
    quick_scan()
