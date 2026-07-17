"""
入市信号评分卡 — Layer 1核心模块
4维共振：量价(30%) + 资金(30%) + 情绪(20%) + 板块(20%)
绿灯(≥5): 买入 | 黄灯(3-4): 半仓试探 | 红灯(<3): 禁止

设计依据：
  - 海龟法则：突破信号必须配合趋势过滤
  - 华泰A股情绪：恐惧端是最可靠买点
  - KDD2024多模态：多信号共振优于单一信号
  - 波仔实战：主力资金方向是第一顺位
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategies.volume_profile import find_support_resistance
from strategies.sentiment_tracker.engine import SentimentEngine


class EntryScorer:
    """
    入市信号评分卡

    使用方式：
        scorer = EntryScorer("300418")
        scorer.add_volume_profile(current_price=40.50)
        scorer.add_fund_flow(main_inflow=3.14, total_amount=26.68)
        scorer.add_sentiment(sentiment_score=-1.5)
        scorer.add_peer_sync(my_chg=-1.2, peer_changes=[...])
        result = scorer.verdict()
    """

    def __init__(self, code: str, name: str = ""):
        self.code = code
        self.name = name
        self.scores = {}
        self.details = {}

    def add_volume_profile(self, current_price: float):
        """
        量价维度：价格是否在支撑带内
        支撑带内 = 买点（+3），偏离 = 观望，突破压力 = 卖点（-3）
        """
        support, resistance = find_support_resistance(self.code, current_price, days=5)

        # 找最近的支撑和压力
        nearest_support = support[0] if support else None
        nearest_resist = resistance[0] if resistance else None

        if nearest_support:
            support_mid = (nearest_support["price_min"] + nearest_support["price_max"]) / 2
            dist_to_support = (current_price - support_mid) / support_mid * 100

            if dist_to_support <= 0.5:   # 在支撑带内
                score = 3
                detail = f"🟢 在支撑带{support_mid:.2f}内 (距{dist_to_support:+.1f}%)"
            elif dist_to_support <= 1.5: # 靠近支撑
                score = 1
                detail = f"🟡 接近支撑带{support_mid:.2f} (距{dist_to_support:+.1f}%)"
            else:  # 远离支撑
                score = -2
                detail = f"🔴 远离支撑带{support_mid:.2f} (距{dist_to_support:+.1f}%)"
        else:
            score = -1
            detail = "⚠️ 下方无显著支撑带"

        self.scores["volume"] = score
        self.details["volume"] = detail
        return self

    def add_fund_flow(self, main_inflow: float, total_amount: float, margin_days: int = 0):
        """
        资金维度：主力净流入方向
        主力买入 = 最强信号（+3），主力卖出 = 最弱信号（-3）
        """
        if total_amount <= 0:
            self.scores["fund"] = 0
            self.details["fund"] = "无数据"
            return self

        ratio = main_inflow / total_amount * 100

        if ratio > 5:
            score = 3
            detail = f"🟢 主力大幅流入{ratio:.1f}% ({main_inflow:.1f}亿)"
        elif ratio > 2:
            score = 2
            detail = f"🟢 主力流入{ratio:.1f}% ({main_inflow:.1f}亿)"
        elif ratio > 0:
            score = 1
            detail = f"🟡 主力微流入{ratio:.1f}%"
        elif ratio > -2:
            score = -1
            detail = f"🟠 主力微流出{ratio:.1f}%"
        elif ratio > -5:
            score = -2
            detail = f"🔴 主力流出{ratio:.1f}% ({main_inflow:.1f}亿)"
        else:
            score = -3
            detail = f"🔴 主力大幅流出{ratio:.1f}% ({main_inflow:.1f}亿)"

        # 连续流入加分
        if margin_days >= 2 and score > 0:
            score = min(3, score + 1)
            detail += f" 连续{margin_days}日流入"

        self.scores["fund"] = score
        self.details["fund"] = detail
        return self

    def add_sentiment(self, sentiment_score: float):
        """
        情绪维度：恐惧时买入（+2），贪婪时不买（-2）
        基于华泰A股情绪分位策略：恐慌区间是买点
        """
        if sentiment_score <= -2.0:
            score = 2
            detail = f"🟢 极度恐惧(-{abs(sentiment_score):.1f}) ← 历史上最可靠买点"
        elif sentiment_score <= -1.0:
            score = 1
            detail = f"🟡 偏恐惧({sentiment_score:.1f})"
        elif sentiment_score <= 1.0:
            score = 0
            detail = f"➖ 中性({sentiment_score:.1f})"
        elif sentiment_score <= 2.0:
            score = -1
            detail = f"🟠 偏贪婪({sentiment_score:+.1f})"
        else:
            score = -2
            detail = f"🔴 极度贪婪({sentiment_score:+.1f}) ← 不买"

        self.scores["sentiment"] = score
        self.details["sentiment"] = detail
        return self

    def add_peer_sync(self, my_chg: float, peer_changes: list):
        """
        板块维度：关联股同涨同跌 = 共振（+2），分化 = 谨慎
        peer_changes: [{"name":"讯飞","chg":2.5}, ...]
        """
        if not peer_changes:
            self.scores["peer"] = 0
            self.details["peer"] = "无关联数据"
            return self

        avg_peer = sum(p["chg"] for p in peer_changes) / len(peer_changes)
        all_same_dir = all((p["chg"] > 0) == (my_chg > 0) for p in peer_changes)

        if all_same_dir and abs(avg_peer) > 1.5:
            score = 2
            detail = f"🟢 板块强共振(均{avg_peer:+.1f}%)"
        elif all_same_dir:
            score = 1
            detail = f"🟡 板块共振(均{avg_peer:+.1f}%)"
        elif avg_peer > 1 and my_chg < 0:
            score = -2
            detail = f"🔴 板块涨个股跌→危险(均{avg_peer:+.1f}%)"
        elif avg_peer < -1 and my_chg > 0:
            score = 2
            detail = f"🟢 板块跌个股涨→独立强势"
        else:
            detail = f"➖ 板块分化"
            score = 0

        self.scores["peer"] = score
        self.details["peer"] = detail
        return self

    def verdict(self) -> dict:
        """综合评分，输出买入/观望/禁止"""
        weights = {"volume": 0.30, "fund": 0.30, "sentiment": 0.20, "peer": 0.20}
        total = sum(self.scores.get(k, 0) * w for k, w in weights.items())

        # 归一化到0-10
        total = round(total + 3, 1)  # 偏移使负分也有意义

        if total >= 5.0:
            signal = "🟢 买入信号"
            action = "正常仓买入"
        elif total >= 3.0:
            signal = "🟡 观望信号"
            action = "可半仓试探，等待确认"
        else:
            signal = "🔴 禁止买入"
            action = "不操作，继续等待"

        return {
            "code": self.code,
            "name": self.name,
            "total": total,
            "signal": signal,
            "action": action,
            "scores": self.scores,
            "details": self.details,
            "breakdown": [
                f"量价({weights['volume']*100:.0f}%): {self.scores.get('volume',0):+d}",
                f"资金({weights['fund']*100:.0f}%): {self.scores.get('fund',0):+d}",
                f"情绪({weights['sentiment']*100:.0f}%): {self.scores.get('sentiment',0):+d}",
                f"板块({weights['peer']*100:.0f}%): {self.scores.get('peer',0):+d}",
            ]
        }

    def format_report(self) -> str:
        v = self.verdict()
        lines = [f"\n{'='*40}"]
        lines.append(f"  {v['name']}({v['code']}) 入市评分")
        lines.append(f"{'='*40}")
        for dim in ["volume", "fund", "sentiment", "peer"]:
            lines.append(f"  {v['details'].get(dim, '无数据')}")
        lines.append(f"  {'─'*38}")
        lines.append(f"  🎯 {v['total']:.1f}/10 {v['signal']}")
        lines.append(f"  📋 {v['action']}")
        lines.append(f"{'='*40}")
        return "\n".join(lines)
