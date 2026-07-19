"""
集合竞价分析模块 — 判断开盘前该竞价出还是开盘后走
基于多维数据综合评分

核心指标:
  1. 竞价匹配量 vs 历史均值 = 承接力度
  2. 竞价价格趋势 = 方向意愿
  3. 关联股同步表现 = 板块确认
  4. 昨日资金方向 = 趋势延续性
  5. 量价剖面位置 = 支撑/压力相对位置
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PEER_MAP = {
    "300418": {"peers": [("300418", 0, "昆仑万维"), ("002230", 0, "科大讯飞"), ("601360", 1, "三六零")]},
    "300058": {"peers": [("300058", 0, "蓝色光标"), ("002027", 0, "分众传媒"), ("002400", 0, "省广集团")]},
}


class AuctionJudge:
    """
    竞价裁判系统
    输入多项数据后给出综合评分：竞价出 vs 开盘等
    score > 0: 偏向等到开盘
    score < 0: 偏向竞价直接出
    """

    def __init__(self):
        self.signals = []

    def add_signal(self, name: str, score: float, detail: str, weight: float = 1.0):
        """添加一个信号，score范围-3到+3，正值=偏多（等开盘），负值=偏空（竞价出）"""
        self.signals.append({
            "name": name, "score": score, "weight": weight, "detail": detail,
            "weighted": score * weight,
        })

    def verdict(self) -> dict:
        total = sum(s["weighted"] for s in self.signals)
        total_w = sum(abs(s["weight"]) for s in self.signals)
        if total_w == 0:
            return {"action": "无数据，默认等开盘", "score": 0}

        score = total / total_w * 3  # 归一化到-3到+3

        if score > 1.0:
            action = "🟢 等到开盘再出（竞价偏强）"
        elif score > 0:
            action = "🟡 可以等开盘（竞价中性偏强）"
        elif score > -1.0:
            action = "🟠 倾向竞价直接出（竞价偏弱）"
        else:
            action = "🔴 竞价直接出（竞价明显弱势）"

        return {
            "action": action,
            "score": round(score, 1),
            "signals": self.signals,
        }

    def analyze_auction_volume(self, match_vol: int, avg_vol_5d: int):
        """
        竞价匹配量分析
        match_vol: 当前竞价匹配量(手)
        avg_vol_5d: 近5天同时点均值(手)
        """
        if match_vol == 0 or avg_vol_5d == 0:
            ratio = 1.0
        else:
            ratio = match_vol / avg_vol_5d

        if ratio >= 1.5:
            self.add_signal("竞价量能", 2.0, f"匹配量{ratio:.1f}x = 承接很强", weight=1.5)
        elif ratio >= 1.2:
            self.add_signal("竞价量能", 1.0, f"匹配量{ratio:.1f}x = 承接偏强", weight=1.5)
        elif ratio >= 0.8:
            self.add_signal("竞价量能", 0.0, f"匹配量{ratio:.1f}x = 正常", weight=1.5)
        elif ratio >= 0.5:
            self.add_signal("竞价量能", -1.0, f"匹配量{ratio:.1f}x = 承接偏弱", weight=1.5)
        else:
            self.add_signal("竞价量能", -2.0, f"匹配量{ratio:.1f}x = 几乎无量", weight=1.5)

    def analyze_price_trend(self, auction_data_list: list):
        """
        竞价价格趋势 — 分两阶段分析
        auction_data_list: [{"time": "091530", "price": 13.25, "vol": 5000}, ...]
        
        9:15-9:20: 可撤单阶段（试探，可能造假）
        9:20-9:25: 不可撤单阶段（真金白银）
        
        关键信号：
        1. 9:20前后价格大幅跳变 → 撤单暴露真面目
        2. 不可撤阶段价格走势 = 真实方向
        3. 最后一笔 vs 第一笔的价差 = 真实意愿
        """
        if not auction_data_list or len(auction_data_list) < 2:
            self.add_signal("价格趋势", 0, "数据不足", weight=1.0)
            return

        # 按时间分两组
        cancelable = [d for d in auction_data_list if self._time_in_range(d.get("time", ""), 15, 20)]
        locked = [d for d in auction_data_list if self._time_in_range(d.get("time", ""), 20, 25)]

        score = 0
        details = []

        # ==== 核心信号1: 20分前后价格跳变 ====
        if cancelable and locked:
            can_last = cancelable[-1]["price"]  # 可撤阶段最后价
            lock_first = locked[0]["price"]     # 不可撤阶段第一价
            jump_pct = (lock_first / can_last - 1) * 100

            if jump_pct < -1.0:
                score -= 3.0
                details.append(f"⚡9:20跳空{jump_pct:.1f}% = 大量虚假买单撤走")
            elif jump_pct < -0.3:
                score -= 1.5
                details.append(f"⚠️9:20小幅跳低{jump_pct:.1f}% = 部分撤单")
            elif abs(jump_pct) <= 0.3:
                details.append(f"9:20价格平稳 = 挂单真实")
            elif jump_pct > 0.3:
                score += 1.0
                details.append(f"9:20跳高{jump_pct:.1f}% = 真买盘涌入")

        # ==== 核心信号2: 不可撤阶段价格走势 ====
        if len(locked) >= 2:
            lock_first = locked[0]["price"]
            lock_last = locked[-1]["price"]
            lock_trend = (lock_last / lock_first - 1) * 100

            if lock_trend > 0.5:
                score += 2.0
                details.append(f"不可撤阶段走高+{lock_trend:.1f}% = 真买盘推升")
            elif lock_trend > 0:
                score += 0.5
                details.append(f"不可撤阶段微升+{lock_trend:.1f}%")
            elif lock_trend > -0.5:
                details.append(f"不可撤阶段平稳")
            elif lock_trend > -1.0:
                score -= 1.0
                details.append(f"不可撤阶段走低{lock_trend:.1f}%")
            else:
                score -= 2.5
                details.append(f"不可撤阶段明显走低{lock_trend:.1f}% = 真卖压")

        # ==== 核心信号3: 可撤阶段是否有试探性拉高 ====
        if cancelable and len(cancelable) >= 2:
            can_high = max(d["price"] for d in cancelable)
            can_low = min(d["price"] for d in cancelable)
            if can_high / can_low > 1.02:  # 试探区间超2%
                # 看9:20后是否全吐回去了
                if locked and locked[-1]["price"] < can_high * 0.99:
                    score -= 1.0
                    details.append("可撤阶段虚拉后全吐 = 诱多")

        if details:
            self.add_signal("价格趋势(两段)", score, "; ".join(details), weight=2.0)
        else:
            self.add_signal("价格趋势(两段)", 0, "无有效数据", weight=2.0)

    def _time_in_range(self, time_str: str, min_min: int, max_min: int) -> bool:
        """判断时间戳是否在指定分钟范围内, time_str格式: '091530'"""
        try:
            if len(time_str) >= 4:
                m = int(time_str[2:4])
                return min_min <= m < max_min
        except (ValueError, TypeError):
            pass
        return False

    def analyze_peers(self, peer_signals: list, target_chg: float = 0):
        """
        关联股竞价表现
        peer_signals: [{"name":"分众传媒","chg":0.5,"vol_ratio":1.2}, ...]
        target_chg: 目标股票本身的竞价涨幅
        """
        if not peer_signals:
            self.add_signal("关联股", 0, "无数据", weight=1.0)
            return

        avg_chg = sum(p["chg"] for p in peer_signals) / len(peer_signals)
        avg_vol = sum(p.get("vol_ratio", 1) for p in peer_signals) / len(peer_signals)
        all_same = all((p["chg"] >= 0) == (target_chg >= 0) for p in peer_signals)

        score = 0
        details = []
        if avg_chg > 0.5:
            score += 1.5
            details.append(f"关联全红均+{avg_chg:.1f}%")
        elif avg_chg > 0:
            score += 0.5
            details.append(f"关联偏红均+{avg_chg:.1f}%")
        elif avg_chg > -0.5:
            details.append(f"关联平盘均{avg_chg:.1f}%")
        else:
            score -= 1.5
            details.append(f"关联全绿均{avg_chg:.1f}%")

        if avg_vol > 1.3:
            score += 1.0
            details.append("关联放量")
        if not all_same and avg_chg < 0:
            score -= 0.5
            details.append("板块分化")

        self.add_signal("关联股", score, "; ".join(details), weight=1.2)

    def analyze_fund_flow(self, yesterday_inflow: float, inflow_days: int):
        """
        昨日资金方向
        yesterday_inflow: 昨日主力净流入(亿), 正=流入, 负=流出
        inflow_days: 最近几天连续净流入的天数
        """
        score = 0
        details = []

        if yesterday_inflow > 1.0:
            score = 2.5
            details.append(f"昨主力大幅流入{yesterday_inflow:.1f}亿")
        elif yesterday_inflow > 0.2:
            score = 1.0
            details.append(f"昨主力小幅流入{yesterday_inflow:.1f}亿")
        elif yesterday_inflow > -0.5:
            score = 0
            details.append(f"昨主力基本持平")
        elif yesterday_inflow > -2.0:
            score = -1.5
            details.append(f"昨主力流出{yesterday_inflow:.1f}亿")
        else:
            score = -2.5
            details.append(f"昨主力大幅流出{abs(yesterday_inflow):.1f}亿")

        if inflow_days >= 2:
            score += 1.0
            details.append(f"连续{inflow_days}天净流入")

        self.add_signal("资金方向", score, "; ".join(details), weight=1.5)

    def analyze_support_distance(self, current_price: float, nearest_support: float):
        """
        当前位置距支撑带的距离
        如果紧挨着支撑（距离<2%）→ 下方空间小，等开盘更划算
        如果远在支撑上方（距离>5%）→ 下方有下跌空间，竞价出
        注意：对于做空（割肉）方向是反的——我们需要判断继续跌的风险
        """
        distance = (current_price / nearest_support - 1) * 100

        if distance < 1.0:
            self.add_signal("支撑距离", 2.0, f"距支撑仅{distance:.1f}% = 下方空间小", weight=1.2)
        elif distance < 2.0:
            self.add_signal("支撑距离", 0.5, f"距支撑{distance:.1f}% = 有限空间", weight=1.2)
        elif distance < 5.0:
            self.add_signal("支撑距离", -1.0, f"距支撑{distance:.1f}% = 有下跌空间", weight=1.2)
        else:
            self.add_signal("支撑距离", -2.0, f"距支撑{distance:.1f}% = 下方无支撑", weight=1.2)


# 便捷函数
def quick_verdict(code: str, name: str, auction_data: dict = None) -> dict:
    """快速裁判，用于盘中"""
    judge = AuctionJudge()

    # 需要从MCP取的数据在调用前准备好
    if auction_data:
        if "vol_ratio" in auction_data:
            judge.analyze_auction_volume(auction_data.get("match_vol", 0), auction_data.get("avg_vol", 1))
        if "prices" in auction_data:
            judge.analyze_price_trend(auction_data["prices"])
        if "peers" in auction_data:
            judge.analyze_peers(auction_data["peers"])
        if "yesterday_inflow" in auction_data:
            judge.analyze_fund_flow(
                auction_data["yesterday_inflow"],
                auction_data.get("inflow_days", 0)
            )
        if "support_price" in auction_data and "now" in auction_data:
            judge.analyze_support_distance(auction_data["now"], auction_data["support_price"])

    v = judge.verdict()
    v["stock"] = f"{name}({code})"
    return v
