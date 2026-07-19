"""
个股情绪追踪器 — 5层情绪模型
基于学术论文+华尔街实践，针对昆仑万维/蓝色光标定制

理论来源:
  - FinBERT (ProsusAI, ACL 2020): 金融文本情感分类
  - CNN Fear & Greed Index (7因素)
  - 华泰证券 A股情绪指数 (14因素)
  - 浦银国际 量化情绪策略

数据源计划:
  - Tushare Pro: 资金流向(moneyflow)、新闻(news)、龙虎榜(top_list)
  - 腾讯 qt.gtimg.cn: 实时行情、盘口数据
  - 通达信MCP: K线、实时报价、板块数据
"""

import sys, os
import hashlib
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.tdx_parser import read_minute_kline, read_daily_kline, group_by_date
from strategies.volume_profile import volume_profile as get_vol_profile

# ============================================================
# Layer 1: 新闻情绪 (NLP-based) — 权重15%
# ============================================================

class NewsSentiment:
    """金融新闻情感分析 - 先做规则版，后续可升级FinBERT"""

    # 新闻去重缓存: {hash: (发布时间, 情感分)}
    _news_cache = {}

    # 中文金融情感词典
    POSITIVE_WORDS = [
        "涨停","大涨","突破","拉升","放量","利好","超预期","业绩大增",
        "净流入","机构买入","回购","增持","战略合作","新品发布",
        "政策支持","国产替代","市场份额","翻倍","涨停板",
        "主力","抢筹","爆买","起飞","乐观","看好","升级"
    ]

    NEGATIVE_WORDS = [
        "跌停","大跌","暴跌","跳水","利空","减持","亏损","下滑",
        "净流出","机构卖出","套现","退市","风险提示","被调查",
        "处罚","关停","缩水","腰斩","崩盘","恐慌","抛售",
        "暴雷","缩量","阴跌","调整","承压","担忧"
    ]

    @classmethod
    def _hash_headline(cls, headline: str) -> str:
        """标题去重哈希：同标题重复=旧闻炒作"""
        return hashlib.md5(headline.strip().encode()).hexdigest()[:12]

    @classmethod
    def score_headline(cls, headline: str) -> float:
        """简单词汇匹配法评分 (-1 ~ +1)"""
        pos_count = sum(1 for w in cls.POSITIVE_WORDS if w in headline)
        neg_count = sum(1 for w in cls.NEGATIVE_WORDS if w in headline)
        if pos_count + neg_count == 0:
            return 0.0
        return round((pos_count - neg_count) / max(pos_count + neg_count, 1), 2)

    @classmethod
    def analyze_batch(cls, headlines: list) -> dict:
        """批量分析新闻标题，自动去重旧闻"""
        if not headlines:
            return {"avg_sentiment": 0, "pos_ratio": 0, "neg_ratio": 0, "count": 0,
                    "dup_count": 0, "fresh_count": 0}

        fresh = []
        dup_count = 0
        now = datetime.now()

        for h in headlines:
            hh = cls._hash_headline(h)
            if hh in cls._news_cache:
                cached_time, _ = cls._news_cache[hh]
                # 24小时内重复 = 旧闻炒作
                if (now - cached_time).total_seconds() < 86400:
                    dup_count += 1
                    continue
            cls._news_cache[hh] = (now, 0)
            fresh.append(h)

        scores = [cls.score_headline(h) for h in fresh] if fresh else []
        avg = sum(scores) / len(scores) if scores else 0
        pos = sum(1 for s in scores if s > 0) / len(scores) if scores else 0
        neg = sum(1 for s in scores if s < 0) / len(scores) if scores else 0

        return {
            "avg_sentiment": round(avg, 2),
            "pos_ratio": round(pos, 2),
            "neg_ratio": round(neg, 2),
            "count": len(headlines),
            "fresh_count": len(fresh),
            "dup_count": dup_count,
            "dedup_warning": f"⚠️ 检测到{dup_count}条旧闻炒作" if dup_count > 0 else "✅ 无重复新闻",
        }


# ============================================================
# Layer 2: 资金情绪
# ============================================================

class FundSentiment:
    """主力资金情绪打分"""

    @classmethod
    def score(cls, main_inflow: float, total_amount: float = 1, margin_days: int = 0) -> dict:
        """
        main_inflow: 主力净流入(亿)
        total_amount: 成交额(亿)
        margin_days: 连续N日净流入
        """
        ratio = main_inflow / total_amount * 100 if total_amount > 0 else 0

        # 主力净占比评分
        if ratio > 10:
            flow_score = 3.0
        elif ratio > 5:
            flow_score = 2.0
        elif ratio > 2:
            flow_score = 1.0
        elif ratio > -2:
            flow_score = 0
        elif ratio > -5:
            flow_score = -1.0
        elif ratio > -10:
            flow_score = -2.0
        else:
            flow_score = -3.0

        # 连续净流入加分
        continuity_bonus = min(margin_days, 3) * 0.3

        return {
            "score": round(flow_score + continuity_bonus, 1),
            "main_inflow": main_inflow,
            "inflow_ratio_pct": round(ratio, 1),
            "margin_days": margin_days,
        }


# ============================================================
# Layer 3: 微观结构情绪
# ============================================================

class MicroSentiment:
    """量价微观结构"""

    @classmethod
    def score(cls, current_price: float, avg_price: float, volume_ratio: float,
              high: float, low: float, open_price: float) -> dict:
        """综合量价指标评分"""
        score = 0
        details = []

        # 1. 量比 (vs 5日均)
        if volume_ratio > 1.5:
            score += 0.5
            details.append(f"放量{volume_ratio:.1f}x")
        elif volume_ratio < 0.5:
            score -= 0.5
            details.append(f"缩量{volume_ratio:.1f}x")

        # 2. VWAP偏离
        if avg_price > 0:
            vwap_dev = (current_price / avg_price - 1) * 100
            if vwap_dev > 1.5:
                score += 0.5
                details.append(f"均线上{vwap_dev:.1f}%")
            elif vwap_dev < -1.5:
                score -= 0.5
                details.append(f"均线下{vwap_dev:.1f}%")

        # 3. 冲高回落
        if high > 0 and open_price > 0:
            upper_wick = (high - max(current_price, open_price)) / open_price * 100
            if upper_wick > 3:
                score -= 1.0
                details.append(f"长上影{upper_wick:.1f}%")
            elif upper_wick > 1.5:
                score -= 0.5

        # 4. 日内涨幅
        if open_price > 0:
            day_chg = (current_price / open_price - 1) * 100
            if day_chg > 3:
                score += 0.5
            elif day_chg < -3:
                score -= 1.0

        return {"score": round(max(-3, min(3, score)), 1), "details": details}


# ============================================================
# Layer 4: 板块共振
# ============================================================

class PeerSentiment:
    """关联股同步分析 + 题材板块热度"""

    PEERS = {
        "300418": ["002230", "601360"],         # 昆仑 → 讯飞+360
        "300058": ["002027", "002400"],         # 蓝标 → 分众+省广
    }

    # 关联题材板块（板块编号 × 权重）
    SECTOR_THEMES = {
        "300418": [  # 昆仑万维
            ("3126", 0.30, "词元经济"),
            ("2790", 0.25, "虚拟数字人"),
            ("3008", 0.25, "AI语料"),
            ("3012", 0.20, "秘塔AI"),
        ],
        "300058": [  # 蓝色光标
            ("3126", 0.25, "词元经济"),
            ("3121", 0.25, "即梦AI"),
            ("2790", 0.20, "虚拟数字人"),
            ("2923", 0.15, "GPT5"),
            ("2927", 0.15, "文心一言"),
        ],
    }

    @classmethod
    def score_sector_heat(cls, code: str, sector_heat_data: dict = None) -> dict:
        """
        题材板块热度评分
        
        sector_heat_data: {板块编号: {limit_up_count, avg_chg, names}, ...}
        """
        themes = cls.SECTOR_THEMES.get(code, [])
        if not themes or not sector_heat_data:
            return {"score": 0, "detail": "无题材数据"}

        weighted_score = 0
        details = []
        for section_num, weight, name in themes:
            data = sector_heat_data.get(section_num, {})
            limit_ups = data.get("limit_up_count", 0)
            avg_chg = data.get("avg_chg", 0)

            # 涨停越多分越高
            if limit_ups >= 5:
                section_score = 3
            elif limit_ups >= 3:
                section_score = 2
            elif limit_ups >= 1:
                section_score = 1
            else:
                section_score = 0

            # 平均涨幅加分
            if avg_chg > 3:   section_score += 1
            elif avg_chg < -1: section_score -= 1

            contribution = round(section_score * weight, 1)
            weighted_score += contribution

            if limit_ups > 0:
                details.append(f"🚀 {name}({limit_ups}涨停+{avg_chg:.1f}%) +{contribution:.1f}")

        total = round(min(3, max(-1, weighted_score)), 1)
        return {
            "score": total,
            "detail": " | ".join(details) if details else f"题材中性({weighted_score:.1f})",
            "raw": weighted_score,
        }

    @classmethod
    def score_sync(cls, code: str, my_chg: float, peer_changes: list) -> dict:
        """
        my_chg: 目标股涨跌幅
        peer_changes: [{"name":"讯飞","chg":2.5}, ...]
        """
        if not peer_changes:
            return {"score": 0, "sync": "unknown"}

        avg_peer = sum(p["chg"] for p in peer_changes) / len(peer_changes)
        all_same = all((p["chg"] > 0) == (my_chg > 0) for p in peer_changes)

        score = 0
        detail = ""

        if all_same:
            if abs(avg_peer) > 2:
                score = 2.0
                detail = f"板块强共振(均{avg_peer:+.1f}%)"
            elif abs(avg_peer) > 1:
                score = 1.0
                detail = f"板块共振(均{avg_peer:+.1f}%)"
            else:
                score = 0.5
                detail = f"板块弱共振"
        else:
            if avg_peer > 1 and my_chg < 0:
                score = -2.0
                detail = f"板块涨但个股跌(分化)"
            elif avg_peer < -1 and my_chg > 0:
                score = 2.0
                detail = f"板块跌但个股涨(独立强势)"
            else:
                detail = f"板块分化"

        return {"score": score, "avg_peer_chg": round(avg_peer, 1), "sync": detail}


# ============================================================
# Layer 5: 宏观情绪锚
# ============================================================

class MacroAnchor:
    """大盘情绪 + 涨停比 + 上涨家数 + 恐慌指数"""

    @classmethod
    def score(cls, up_count: int, down_count: int, limit_up: int, limit_down: int,
              deep_drop_count: int = 0) -> dict:
        total = up_count + down_count
        up_ratio = up_count / total * 100 if total > 0 else 50
        down_ratio = 100 - up_ratio

        # ===== 上涨家数 (30%) =====
        if up_ratio > 80:
            up_pct_score = 2.0; up_label = f"极端普涨({up_ratio:.0f}%)"
        elif up_ratio > 60:
            up_pct_score = 1.0; up_label = f"赚钱效应({up_ratio:.0f}%)"
        elif up_ratio > 40:
            up_pct_score = 0; up_label = f"中性({up_ratio:.0f}%)"
        elif up_ratio > 20:
            up_pct_score = -1.0; up_label = f"亏钱效应({up_ratio:.0f}%)"
        else:
            up_pct_score = -2.0; up_label = f"极端普跌({up_ratio:.0f}%)"

        # ===== 涨停比 (20%) =====
        limit_ratio = limit_up / total * 100 if total > 0 else 0
        if limit_ratio > 3:
            limit_score = 2.0; limit_label = f"涨停热({limit_up}家)"
        elif limit_ratio > 1.5:
            limit_score = 1.0; limit_label = f"涨停活({limit_up}家)"
        else:
            limit_score = 0; limit_label = f"涨停少({limit_up}家)"

        # ===== 恐慌指数 (50%) — 极恐=买点 =====
        ld_ratio = limit_down / total * 100 if total > 0 else 0
        dd_ratio = deep_drop_count / total * 100 if total > 0 and deep_drop_count > 0 else 0
        fear_raw = down_ratio * 0.4 + ld_ratio * 20 + dd_ratio * 10

        if fear_raw > 60:
            fear_score = 3.0; fear_label = f"极恐(f={fear_raw:.0f})→最佳买点"
        elif fear_raw > 45:
            fear_score = 2.0; fear_label = f"恐慌(f={fear_raw:.0f})"
        elif fear_raw > 30:
            fear_score = 1.0; fear_label = f"偏恐(f={fear_raw:.0f})"
        elif fear_raw > 20:
            fear_score = 0; fear_label = f"中性(f={fear_raw:.0f})"
        else:
            fear_score = -1.0; fear_label = f"偏贪(f={fear_raw:.0f})"

        total_score = round(up_pct_score * 0.30 + limit_score * 0.20 + fear_score * 0.50, 1)
        details = [up_label, limit_label, f"恐慌: {fear_label}"]

        return {"score": total_score, "up_ratio": round(up_ratio, 1), "details": details}


# ============================================================
# 综合引擎
# ============================================================

class SentimentEngine:
    """5层情绪加权综合"""

    WEIGHTS = {
        "news": 0.15,   # 新闻权重降至15%——波仔定调，旧闻炒作+情感不准
        "fund": 0.35,   # 资金权重升至35%——最可靠的信号
        "micro": 0.20,  # 微观结构
        "peer": 0.20,   # 板块共振升至20%——关联验证很重要
        "macro": 0.10,  # 宏观锚定
    }

    @classmethod
    def analyze(cls, data: dict) -> dict:
        """
        data = {
            "code": "300418",
            "headlines": [...],
            "main_inflow": 3.14, "total_amount": 26.68, "margin_days": 0,
            "current_price": 40.50, "avg_price": 40.10, "volume_ratio": 1.1,
            "high": 41.00, "low": 38.78, "open": 39.90,
            "peer_changes": [{"name":"讯飞","chg":2.5}, ...],
            "up_count": 2500, "down_count": 1500,
            "limit_up": 110, "limit_down": 5,
        }
        """
        results = {}

        # L1
        news = NewsSentiment.analyze_batch(data.get("headlines", []))
        news_s = news["avg_sentiment"] * 3  # 映射到-3~+3
        results["news"] = {"score": round(news_s, 1), **news}

        # L2
        fund = FundSentiment.score(
            data.get("main_inflow", 0),
            data.get("total_amount", 1),
            data.get("margin_days", 0)
        )
        results["fund"] = fund

        # L3
        micro = MicroSentiment.score(
            data.get("current_price", 0),
            data.get("avg_price", 0),
            data.get("volume_ratio", 1.0),
            data.get("high", 0),
            data.get("low", 0),
            data.get("open", 0),
        )
        results["micro"] = micro

        # L4: 板块关联 + 题材热度合并
        peer = PeerSentiment.score_sync(
            data.get("code", ""),
            data.get("my_chg", 0),
            data.get("peer_changes", [])
        )
        # 题材板块热度（权重50%融入板块层）
        sector = PeerSentiment.score_sector_heat(
            data.get("code", ""),
            data.get("sector_heat_data", {})
        )
        # 合并：关联股(50%) + 题材热度(50%)
        combined_peer_score = round(peer["score"] * 0.5 + sector["score"] * 0.5, 1)
        results["peer"] = {
            "score": combined_peer_score,
            "peer_sync": peer["sync"],
            "sector_heat": sector["detail"],
            "peer_raw": peer["score"],
            "sector_raw": sector["score"],
        }

        # L5
        macro = MacroAnchor.score(
            data.get("up_count", 2500),
            data.get("down_count", 1500),
            data.get("limit_up", 100),
            data.get("limit_down", 10),
        )
        results["macro"] = macro

        # 加权综合
        total = sum(r.get("score", 0) * cls.WEIGHTS[k] for k, r in results.items())
        results["total_score"] = round(total, 1)

        if total >= 2.0:
            results["level"] = "🔥 极度贪婪 — 卖出信号"
        elif total >= 1.0:
            results["level"] = "⚠️ 偏贪婪"
        elif total > -1.0:
            results["level"] = "➖ 中性"
        elif total > -2.0:
            results["level"] = "🔵 偏恐惧"
        else:
            results["level"] = "❄️ 极度恐惧 — 买入信号（最可靠）"

        return results

    @classmethod
    def format_report(cls, results: dict, stock_name: str = "") -> str:
        """美观输出"""
        lines = [f"\n{'='*50}"]
        lines.append(f"  {stock_name} 情绪报告")
        lines.append(f"{'='*50}")
        for layer in ["news", "fund", "micro", "peer", "macro"]:
            r = results[layer]
            name = {"news":"📰 新闻","fund":"💰 资金","micro":"📊 微观","peer":"🤝 板块","macro":"🌍 宏观"}[layer]
            lines.append(f"  {name}: {r.get('score',0):+.1f}")
            if "details" in r:
                for d in r["details"]:
                    lines.append(f"    └ {d}")
            if layer == "news":
                if results['news']['count'] > 0:
                    lines.append(f"    └ 新闻{results['news']['count']}条 去重后{results['news']['fresh_count']}条 正面{results['news']['pos_ratio']:.0%}")
                lines.append(f"    └ {results['news']['dedup_warning']}")
            if layer == "fund":
                lines.append(f"    └ 主力{results['fund']['main_inflow']:.1f}亿 占{results['fund']['inflow_ratio_pct']:.1f}%")
            if layer == "peer":
                if "sync" in results["peer"]:
                    lines.append(f"    └ {results['peer']['sync']}")
                if "peer_sync" in results["peer"]:
                    lines.append(f"    └ 关联: {results['peer']['peer_sync']}")
                if "sector_heat" in results["peer"]:
                    lines.append(f"    └ 题材: {results['peer']['sector_heat']}")
        lines.append(f"  {'─'*48}")
        lines.append(f"  🎯 综合情绪: {results['total_score']:+.1f}")
        lines.append(f"  {results['level']}")
        lines.append(f"{'='*50}\n")
        return "\n".join(lines)
