# -*- coding: utf-8 -*-
"""sector_monitor.py - 板块题材情绪监测

监测昆仑/蓝标关联板块涨跌，评估突发消息影响和持续性。
"""

import json
from datetime import datetime
from typing import List, Dict

SECTOR_MAP = {
    "300418": ["AI","游戏","传媒","人工智能","昆仑"],
    "300058": ["传媒","营销","蓝色","广告"],
}


class SectorMonitor:
    def __init__(self, news_data: List[Dict]):
        self.news = news_data

    def assess_sentiment(self, stock_code: str) -> Dict:
        keywords = SECTOR_MAP.get(stock_code, [])
        score = 0
        count = 0
        for item in self.news:
            text = item.get("title","") + " " + item.get("content","")
            for kw in keywords:
                if kw in text:
                    count += 1
                    if any(w in text for w in ["涨","利好","突破","爆发"]):
                        score += 5
                    elif any(w in text for w in ["跌","利空","风险","减持"]):
                        score -= 5
                    break
        label = "积极" if score > 10 else ("消极" if score < -10 else "中性")
        return {"stock": stock_code, "sentiment": score, "label": label, "news_count": count}

    def news_impact(self, text: str, stock_code: str) -> Dict:
        keywords = SECTOR_MAP.get(stock_code, [])
        relevant = any(kw in text for kw in keywords)
        impact = 0
        if "利好" in text or "突破" in text: impact = 5
        elif "利空" in text or "减持" in text: impact = -5
        return {"relevant": relevant, "impact": impact,
                "action": "VERIFY" if abs(impact) >= 5 else "IGNORE"}


def monitor(stock_codes: List[str], news_list: List[Dict]) -> Dict:
    mon = SectorMonitor(news_list)
    return {code: mon.assess_sentiment(code) for code in stock_codes}


if __name__ == "__main__":
    test = [{"title":"AI概念爆发","content":"昆仑万维大涨"}]
    print(json.dumps(monitor(["300418"], test), ensure_ascii=False))
