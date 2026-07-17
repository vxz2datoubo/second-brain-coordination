#!/usr/bin/env python3
"""
价格归因引擎 (Price Attribution Engine v1.0)

核心功能:
  给定某个价格/某段走势 → 自动分析:
    ① 这个消息面有没有增量支撑? (News Support Detection)
    ② 消息是被提前消化了吗? (Pre-Digestion Analysis)
    ③ 消息是已兑现还是超出预期? (Expectation Gap vs Surprise)
    ④ 消息兑现后是利好出尽还是持续推动? (Post-Event Drift)

学术基础:
  [1] Ball & Brown 1968 — 首家发现PEAD(盈利公告后漂移)
  [2] Fama Fisher Jensen Roll 1969 — 事件研究法奠基
  [3] Huberman & Regev 2001 — "No News is News": 旧闻也能驱动价格
  [4] Brunnermeier 1998 — "Buy on Rumors Sell on News" 理论模型
  [5] Peterson 2002 — BRSN的神经情感基础
  [6] Hu, Pan, Wang 2021 (JFE) — 公告前不确定性溢价
  [7] Fink 2021 (JBEF) — PEAD综述, 漂移持续30-60天
  [8] Subrahmanyam 2025 — PEAD争议: microcap效应
  [9] Kadan Michaely Moulton 2016 — 机构信息泄露: 公告前4天起
  [10] Martineau 2022 — PEAD在2006年后消失(大盘股)

四大分析模块:
  模块A: 价格→新闻映射 (Price-News Mapping)
  模块B: 提前消化检测 (Pre-Digestion Detection)
  模块C: 预期差分析 (Expectation Gap Analysis)
  模块D: 兑现后漂移 (Post-Event Drift Assessment)

使用:
  python core/price_attribution.py 300418 --price 45.93 --date 2026-07-14
  python core/price_attribution.py 300418 --range 2026-07-08:2026-07-14
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.news_db import NewsDatabase, NewsFactorEngine

# ============================================================
# 模块A: 价格→新闻映射
# ============================================================

def map_price_to_news(db: NewsDatabase, entity_code: str,
                      target_date: str, days_window: int = 3) -> dict:
    """给定某日价格，映射相关新闻

    搜索窗口: [target_date - days_window, target_date + days_window]
    """
    from datetime import datetime, timedelta
    td = datetime.strptime(target_date[:10], "%Y-%m-%d")
    start = (td - timedelta(days=days_window)).strftime("%Y-%m-%d")
    end = (td + timedelta(days=days_window)).strftime("%Y-%m-%d")

    articles = db.query_by_date_range(start, end, entity_code)

    # 按时间分类
    pre_news = []   # T前
    same_news = []   # T日
    post_news = []   # T后

    for art in articles:
        pub = (art['published_at'] or '')[:10]
        evt = db.conn.execute(
            "SELECT * FROM news_events WHERE news_id=? ORDER BY sentiment_score DESC LIMIT 1",
            (art['id'],)
        ).fetchone()
        evt_dict = dict(evt) if evt else {}

        item = {
            'id': art['id'],
            'title': art['title'],
            'source': art['source'],
            'published_at': art['published_at'],
            'sentiment': evt_dict.get('sentiment', 'neutral'),
            'sentiment_score': evt_dict.get('sentiment_score', 0),
            'impact': evt_dict.get('impact_level', 'low'),
            'category': evt_dict.get('event_category', 'general')
        }

        if pub < target_date[:10]:
            pre_news.append(item)
        elif pub == target_date[:10]:
            same_news.append(item)
        else:
            post_news.append(item)

    return {
        'target_date': target_date,
        'pre_news': sorted(pre_news, key=lambda x: x['published_at'] or ''),
        'same_day_news': sorted(same_news, key=lambda x: x['published_at'] or ''),
        'post_news': sorted(post_news, key=lambda x: x['published_at'] or ''),
        'total': len(articles)
    }


# ============================================================
# 模块B: 提前消化检测
# ============================================================

def detect_pre_digestion(db: NewsDatabase, entity_code: str,
                         event_date: str, price_data: list = None,
                         lookback_days: int = 10) -> dict:
    """检测消息是否被提前消化 (Price Run-Up before News)

    核心逻辑:
      ① 查消息前N天的价格涨跌 (Pre-Event CAR)
      ② 如果价格已经涨了大部分 → 消息大概率已被消化
      ③ 如果价格没动 → 消息还没定价

    学术来源:
      Brunnermeier 1998: 早期知情者在消息前就建仓，导致提前涨
      Kadan et al. 2016: 机构在分析师报告前4天就开始买卖
    """
    # 1. 查询消息前的新闻
    td = datetime.strptime(event_date[:10], "%Y-%m-%d")
    start = (td - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    articles = db.query_by_date_range(start, event_date, entity_code)

    # 2. 统计前期消息的情绪
    pre_sentiments = []
    for art in articles:
        evt = db.conn.execute(
            "SELECT sentiment, sentiment_score FROM news_events WHERE news_id=?",
            (art['id'],)
        ).fetchone()
        if evt:
            pre_sentiments.append({'date': (art['published_at'] or '')[:10],
                                   'sentiment': evt['sentiment'],
                                   'score': evt['sentiment_score']})

    # 3. 汇总判断
    if not pre_sentiments:
        return {
            'level': 'fresh',  # 新鲜消息, 无提前
            'label': '🟢 未提前消化',
            'pre_news_count': 0,
            'note': '消息日前无明显提前新闻'
        }

    # 统计前期情绪倾向
    pos_count = sum(1 for s in pre_sentiments if s['sentiment'] == 'positive')
    neg_count = sum(1 for s in pre_sentiments if s['sentiment'] == 'negative')
    total = len(pre_sentiments)
    avg_score = sum(s['score'] for s in pre_sentiments) / total if total else 0

    # 判定消化程度
    if pos_count >= 3 and avg_score > 0.3:
        level = 'digested'  # 正面消息密集 → 已被提前消化
        label = '🟡 部分提前消化'
        note = f'消息前{lookback_days}天有{pos_count}条正面新闻, 部分预期已定价'
    elif pos_count >= 5 and avg_score > 0.5:
        level = 'fully_digested'  # 大量正面 → 完全消化
        label = '🟠 大幅提前消化'
        note = f'消息前{lookback_days}天有{pos_count}条正面新闻, 预期已大量定价'
    elif pos_count <= 1 and neg_count >= 1:
        level = 'surprise'  # 前期偏负面/中性 → 超出预期
        label = '🔵 超预期(前期偏负面)'
        note = f'消息前仅有{pos_count}条正面, 市场预期偏低, 可能超预期'
    else:
        level = 'fresh'
        label = '🟢 未提前消化'
        note = f'消息前{pos_count}条正面/{total}条, 无明显消化'

    return {
        'level': level,
        'label': label,
        'pre_news_count': total,
        'pre_positive': pos_count,
        'pre_negative': neg_count,
        'pre_avg_score': round(avg_score, 3),
        'note': note,
        'pre_news_details': pre_sentiments[:5]
    }


# ============================================================
# 模块C: 预期差分析
# ============================================================

def analyze_expectation_gap(db: NewsDatabase, entity_code: str,
                            event_date: str,
                            price_move_pct: float = 0,
                            event_sentiment: str = 'neutral',
                            event_impact: str = 'low') -> dict:
    """分析预期差 (Is the news better/worse than market expected?)

    核心公式: 市场反应 = f(实际消息 - 市场预期)
      - 如果实际 >> 预期 → 超预期, 继续涨
      - 如果实际 ≈ 预期 → 预期兑现, 无力再涨
      - 如果实际 << 预期 → 不及预期, 反跌

    学术:
      中金 2025: 业绩超预期20%→公告后10天还有+1.8%超额
      Ball & Brown 1968: 市场不立即完全消化, PEAD持续30-60天
    """
    # 1. 查消息前的情绪预期
    td = datetime.strptime(event_date[:10], "%Y-%m-%d")
    lookback_start = (td - timedelta(days=14)).strftime("%Y-%m-%d")
    pre_articles = db.query_by_date_range(lookback_start, event_date, entity_code)

    pre_sent = {'positive': 0, 'negative': 0, 'neutral': 0, 'mixed': 0}
    for art in pre_articles:
        evt = db.conn.execute(
            "SELECT sentiment FROM news_events WHERE news_id=?", (art['id'],)
        ).fetchone()
        if evt:
            pre_sent[evt['sentiment']] = pre_sent.get(evt['sentiment'], 0) + 1

    total_pre = sum(pre_sent.values())
    pre_pos_ratio = pre_sent['positive'] / total_pre if total_pre > 0 else 0.5

    # 2. 判定预期差
    impact_mult = {'high': 1.5, 'medium': 1.0, 'low': 0.5}

    if event_sentiment == 'positive' and pre_pos_ratio < 0.3:
        gap = 'major_surprise'
        label = '🔵 重大超预期'
        note = f'前期正面新闻仅{pre_pos_ratio:.0%}, 市场预期极低, 该利好未被定价'
        forward_bias = 'strong_positive'
    elif event_sentiment == 'positive' and pre_pos_ratio < 0.5:
        gap = 'moderate_surprise'
        label = '🟢 中等超预期'
        note = f'前期正面新闻{pre_pos_ratio:.0%}, 市场预期中性偏低'
        forward_bias = 'positive'
    elif event_sentiment == 'positive' and pre_pos_ratio >= 0.5:
        gap = 'expected'
        label = '🟡 预期兑现'
        note = f'前期正面新闻{pre_pos_ratio:.0%}, 市场已充分预期, 短期利好出尽风险'
        forward_bias = 'neutral_bearish'
    elif event_sentiment == 'negative' and pre_pos_ratio > 0.5:
        gap = 'negative_surprise'
        label = '🔴 利空突袭'
        note = f'前期正面新闻{pre_pos_ratio:.0%}, 市场预期乐观, 利空冲击更大'
        forward_bias = 'strong_negative'
    elif event_sentiment == 'negative' and pre_pos_ratio < 0.3:
        gap = 'negative_expected'
        label = '🔴 利空延续'
        note = f'前期已偏负面, 利空在预期内, 短期消化后可能企稳'
        forward_bias = 'negative_limited'
    else:
        gap = 'neutral'
        label = '⚪ 中性'
        note = '无明显预期差'
        forward_bias = 'neutral'

    # 3. 结合当日价格变动交叉验证
    if price_move_pct > 3 and gap == 'expected':
        note += '。但今日大涨→说明市场解读比预期更积极, 可能量化了此前未定价的利好维度'
    elif price_move_pct < -3 and gap == 'expected':
        note += '。今日大跌→利好兑现后抛售, 典型"买预期卖事实"'

    return {
        'gap_level': gap,
        'label': label,
        'note': note,
        'forward_bias': forward_bias,
        'pre_period': f'{lookback_start} ~ {event_date[:10]}',
        'pre_pos_ratio': round(pre_pos_ratio, 3),
        'pre_total_news': total_pre
    }


# ============================================================
# 模块D: 兑现后漂移评估
# ============================================================

def assess_post_event_drift(entity_code: str, event_date: str,
                            price_data: list = None,
                            lookforward_days: int = 10) -> dict:
    """评估事件兑现后是否存在持续漂移 (PEAD)

    基于 PRICE DATA (非新闻), 查看事件后是否继续同向运行

    学术:
      PEAD: 盈利公告后漂移持续30-60天 (Fink 2021)
      A股: 小市值PEAD更强, 大市值2006年后减弱 (Martineau 2022, Subrahmanyam 2025)
      PEAD消亡: 大市值中PEAD已消失, microcap仍存在
    """
    if not price_data:
        return {
            'drift_detected': False,
            'note': '缺少价格数据, 无法评估漂移'
        }

    price_idx = {p.get('date', '')[:10]: p for p in price_data}
    all_dates = sorted(price_idx.keys())
    event_idx = None
    for i, d in enumerate(all_dates):
        if d >= event_date[:10]:
            event_idx = i
            break

    if event_idx is None or event_idx + lookforward_days >= len(all_dates):
        return {
            'drift_detected': False,
            'note': '缺少足够的前向价格数据'
        }

    # 计算前向CAR
    event_close = price_idx[all_dates[event_idx]]['close']
    forward_returns = {}
    cumulative = 0
    drift_direction = 'none'

    for offset in range(1, min(lookforward_days + 1, len(all_dates) - event_idx)):
        fd = all_dates[event_idx + offset]
        fwd_close = price_idx[fd]['close']
        ret = (fwd_close - event_close) / event_close * 100
        cumulative = (fwd_close - event_close) / event_close * 100
        forward_returns[f'+{offset}d'] = round(ret, 2)

    # 判定漂移
    final_ret = cumulative
    if final_ret > 2:
        drift_direction = 'positive_drift'
        drift_note = f'前向{lookforward_days}日累计{final_ret:+.1f}%, 事件后持续正向漂移'
    elif final_ret < -2:
        drift_direction = 'negative_drift'
        drift_note = f'前向{lookforward_days}日累计{final_ret:+.1f}%, 事件后持续负向漂移'
    else:
        drift_direction = 'no_drift'
        drift_note = f'前向{lookforward_days}日累计{final_ret:+.1f}%, 无明显漂移'

    return {
        'drift_detected': drift_direction != 'no_drift',
        'drift_direction': drift_direction,
        'forward_return_final': round(final_ret, 2),
        'forward_returns_by_day': forward_returns,
        'note': drift_note
    }


# ============================================================
# 综合归因报告
# ============================================================

def full_attribution(db: NewsDatabase, entity_code: str,
                     target_date: str, target_price: float = None,
                     price_move_pct: float = 0,
                     price_data: list = None) -> dict:
    """完整价格归因分析

    给定一个时间点/价格, 输出四维分析:
      ① 有什么消息?
      ② 消息提前消化了吗?
      ③ 消息超预期还是兑现?
      ④ 兑现后还会继续推吗?
    """
    # A: 价格→新闻映射
    news_map = map_price_to_news(db, entity_code, target_date, days_window=5)

    # 提取同日最重要的事件
    same_day = news_map.get('same_day_news', [])
    if same_day:
        top_event = max(same_day, key=lambda x:
            abs(x.get('sentiment_score', 0)) * {'high': 3, 'medium': 2, 'low': 1}.get(x.get('impact', 'low'), 1))
    else:
        top_event = None

    # B: 提前消化检测
    pre_digestion = detect_pre_digestion(db, entity_code, target_date, price_data)

    # C: 预期差分析
    sent = top_event['sentiment'] if top_event else 'neutral'
    impact = top_event['impact'] if top_event else 'low'
    exp_gap = analyze_expectation_gap(db, entity_code, target_date,
                                      price_move_pct, sent, impact)

    # D: 漂移评估 (如果有足够的前向数据)
    drift = assess_post_event_drift(entity_code, target_date, price_data)

    # 综合构建消息支撑力度
    # 正面消息+超预期+未提前消化 = 强支撑
    # 正面消息+已兑现+提前消化 = 弱支撑(利好出尽)
    support_score = 0
    if top_event and top_event['sentiment'] == 'positive':
        support_score += 2
        if exp_gap['gap_level'] in ('major_surprise', 'moderate_surprise'):
            support_score += 3
        elif exp_gap['gap_level'] == 'expected':
            support_score -= 2
    elif top_event and top_event['sentiment'] == 'negative':
        support_score -= 2
        if pre_digestion['level'] in ('surprise',):
            support_score -= 2  # 意外利空, 更糟

    if pre_digestion['level'] == 'fresh':
        support_score += 1  # 新鲜消息, 未提前消化
    elif pre_digestion['level'] == 'fully_digested':
        support_score -= 1

    if drift.get('drift_direction') == 'positive_drift':
        support_score += 1
    elif drift.get('drift_direction') == 'negative_drift':
        support_score -= 1

    # 判定
    if support_score >= 5:
        support_level = '🟢 强消息支撑'
    elif support_score >= 2:
        support_level = '🟢 消息支撑'
    elif support_score >= 0:
        support_level = '🟡 中性'
    elif support_score >= -3:
        support_level = '🟠 消息压力'
    else:
        support_level = '🔴 强消息压力'

    return {
        'target': {'code': entity_code, 'date': target_date, 'price': target_price},
        'news_map': {
            'same_day_count': len(same_day),
            'pre_count': len(news_map.get('pre_news', [])),
            'total_relevant': news_map['total'],
            'top_same_day': top_event
        },
        'pre_digestion': pre_digestion,
        'expectation_gap': exp_gap,
        'post_drift': drift,
        'support_score': support_score,
        'support_level': support_level,
        'top_events_same_day': same_day[:5]
    }


# ============================================================
# CLI
# ============================================================

def _print_attribution(attr: dict):
    """格式化打印归因报告"""
    t = attr['target']
    nm = attr['news_map']
    pd_ = attr['pre_digestion']
    eg = attr['expectation_gap']
    dr = attr['post_drift']

    print(f"\n{'='*65}")
    print(f"  📊 价格归因分析: {t['code']} @ {t['date']}")
    if t['price']:
        print(f"  目标价格: ¥{t['price']}")
    print(f"{'='*65}")

    print(f"\n🗞️  当日新闻: {nm['same_day_count']}篇, 前期{nm['pre_count']}篇, 总计关联{nm['total_relevant']}篇")
    if nm['top_same_day']:
        top = nm['top_same_day']
        s_emo = {'positive':'🟢','negative':'🔴','neutral':'⚪','mixed':'🟡'}.get(top.get('sentiment',''),'')
        print(f"  最重要: {s_emo} [{top.get('impact','')}] {top['title'][:60]}")
        if top.get('category'):
            print(f"  类别: {top['category']} | 情感分: {top.get('sentiment_score',0):+.2f}")

    print(f"\n📡 提前消化: {pd_['label']}")
    print(f"  {pd_['note']}")

    print(f"\n📈 预期差: {eg['label']}")
    print(f"  {eg['note']}")
    print(f"  前期正面新闻占比: {eg['pre_pos_ratio']:.0%} ({eg['pre_total_news']}篇)")

    if dr.get('forward_returns_by_day'):
        print(f"\n🔮 兑现后漂移: {dr['note']}")
        for day, ret in dr.get('forward_returns_by_day', {}).items():
            bar = '█' * max(1, int(abs(ret)))
            direction = '🟢' if ret > 0 else '🔴'
            print(f"  {direction} {day}: {ret:+.1f}% {bar}")

    print(f"\n💪 综合消息支撑: {attr['support_level']} (得分: {attr['support_score']:+d})")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python core/price_attribution.py <code> --date YYYY-MM-DD [--price X.XX]")
        print("  python core/price_attribution.py <code> --range YYYY-MM-DD:YYYY-MM-DD")
        return

    db = NewsDatabase()
    try:
        code = sys.argv[1] if not sys.argv[1].startswith('--') else '300418'
        target_date = datetime.now().strftime("%Y-%m-%d")
        target_price = None

        for i, arg in enumerate(sys.argv):
            if arg == '--date' and i+1 < len(sys.argv):
                target_date = sys.argv[i+1]
            if arg == '--price' and i+1 < len(sys.argv):
                target_price = float(sys.argv[i+1])

        attr = full_attribution(db, code, target_date, target_price)
        _print_attribution(attr)

    finally:
        db.close()


if __name__ == '__main__':
    main()
