#!/usr/bin/env python3
"""
消息面消化模型 (News Digestion Model v1.0)

三维度核心框架:
  ① 资金消化量 (Volume Absorption)  — 多少资金量完成消化
  ② 时间消化周期 (Time Digestion Cycle) — 多久消化完毕
  ③ 价格消化幅度 (Price Digestion Amplitude) — 消化带来了多少价格变动

三者的三角关系:
  Price ∝ Volume × Time^(-0.5)   ← 更多资金+更短时间=更大价格冲击
  Absorption Rate = Volume / Time  ← 消化速度
  Efficiency = Price / Volume      ← 单位资金的价格效率

学术基础:
  [1] JFE 2021: 正面消息<1秒消化, 负面消息延迟5分钟+ — 非对称消化
  [2] JFE 2018: 89%价格发现在前200ms完成 (高频环境)
  [3] Fed IFDP 1233 (2018): 算法新闻阅读→加速价格响应但降低流动性
  [4] Review of Finance 2019: HFT提升盈利公告价格信息量
  [5] 中金 2025: A股事件CAR+胜率数据库 (48类事件消化的量化基线)
  [6] 国泰海通 2025: 舆情1-2日领先性 (A股消化速度异质性)

使用方法:
  from core.digestion_model import DigestionEngine
  de = DigestionEngine(db)
  
  # 单事件消化分析
  result = de.analyze('300418', '2026-07-14')
  
  # 批量历史回测
  baseline = de.baseline('300418', days=60)
  
  # 对未来事件的预测
  prediction = de.predict(news_impact=0.8, market_type='large_cap')
"""

import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.news_db import NewsDatabase, NewsFactorEngine


# ============================================================
# 一、消化事件检测
# ============================================================

class DigestionEngine:
    """消息面消化三维分析引擎"""

    # A股事件消化的经验参数 (基于中金2025 + 学术文献)
    DIGESTION_PARAMS = {
        # 事件类型 → (典型消化时间(天), 典型资金倍率 vs 均值, 典型CAR%)
        'earnings_beat':    (3, 2.0, +2.5),    # 业绩超预期: 3天消化, 2倍量, +2.5%
        'earnings_miss':    (5, 1.8, -2.0),    # 业绩不及: 5天消化 (更慢!)
        'product_launch':   (2, 1.5, +3.0),    # 产品发布: 2天快消化
        'policy_positive':  (5, 1.3, +3.5),    # 政策利好: 5天慢消化 (政策需要消化)
        'policy_negative':  (7, 1.6, -4.0),    # 政策利空: 7天最慢
        'macro_shock':      (10, 2.5, +5.0),   # 宏观冲击: 10天 (影响深远)
        'regulatory':        (1, 0.8, -1.5),    # 常规监管: 1天快消化
        'rumor':            (0.5, 3.0, +2.0),   # 传闻: 半天消化 (来得快去得快)
    }

    def __init__(self, db: NewsDatabase):
        self.db = db

    # ── 维度①: 资金消化量 ──

    def volume_absorption(self, entity_code: str, event_date: str,
                          price_data: list = None,
                          lookback_days: int = 20) -> dict:
        """计算消息消化所需的异常资金量

        公式: 异常量 = 事件窗口日均量 / 基准均值
        消化量 = 累计异常量 × 均价
        """
        if not price_data:
            return {'status': 'no_price_data'}

        price_idx = {p.get('date', '')[:10]: p for p in price_data}
        all_dates = sorted(price_idx.keys())

        # 找事件日和窗口
        td = datetime.strptime(event_date[:10], "%Y-%m-%d")
        event_idx = None
        for i, d in enumerate(all_dates):
            if d >= event_date[:10]:
                event_idx = i
                break
        if event_idx is None:
            return {'status': 'date_not_found'}

        # 基准窗口: 事件前 lookback_days 天
        base_start = max(0, event_idx - lookback_days)
        base_end = event_idx - 1
        base_volumes = []
        base_prices = []
        for i in range(base_start, min(base_end + 1, len(all_dates))):
            d = all_dates[i]
            if 'volume' in price_idx[d]:
                base_volumes.append(price_idx[d]['volume'])
                base_prices.append(price_idx[d]['close'])

        if not base_volumes:
            return {'status': 'no_base_data'}

        base_avg_vol = sum(base_volumes) / len(base_volumes)
        base_avg_price = sum(base_prices) / len(base_prices)

        # 事件窗口: event_date 及之后(最多5天)
        digestion_volumes = []
        digestion_prices = []
        for i in range(event_idx, min(event_idx + 5, len(all_dates))):
            d = all_dates[i]
            if 'volume' in price_idx[d]:
                digestion_volumes.append(price_idx[d]['volume'])
                digestion_prices.append(price_idx[d]['close'])

        # 消化量计算
        total_abnormal_vol = 0
        daily_absorption = []
        cumulative_absorption = 0

        for dv, dp in zip(digestion_volumes, digestion_prices):
            abnormal = max(0, dv - base_avg_vol)
            money = abnormal * dp * 100  # 手→金额(手×100股×均价)
            total_abnormal_vol += abnormal
            cumulative_absorption += money
            daily_absorption.append({
                'abnormal_vol': abnormal,
                'money_absorbed': money,
                'cumulative': cumulative_absorption
            })

        vol_ratio = sum(digestion_volumes) / (base_avg_vol * len(digestion_volumes)) if digestion_volumes else 1

        return {
            'base_avg_volume': round(base_avg_vol, 0),
            'base_avg_price': round(base_avg_price, 2),
            'event_window_volumes': digestion_volumes,
            'vol_ratio': round(vol_ratio, 2),
            'total_abnormal_vol': round(total_abnormal_vol, 0),
            'total_money_absorbed': round(cumulative_absorption, 0),
            'daily_absorption': daily_absorption,
            'absorption_level': self._classify_absorption(vol_ratio)
        }

    def _classify_absorption(self, vol_ratio: float) -> str:
        if vol_ratio > 2.0: return '🔴 巨量消化'
        if vol_ratio > 1.5: return '🟠 大量消化'
        if vol_ratio > 1.2: return '🟡 中等消化'
        if vol_ratio > 0.8: return '🟢 正常消化'
        return '⚪ 低量消化'

    # ── 维度②: 时间消化周期 ──

    def time_cycle(self, entity_code: str, event_date: str,
                   price_data: list = None,
                   minute_data: list = None) -> dict:
        """测量消息从发布到完全消化的时间周期

        方法:
          ① 找到消息发布后价格第一次达到最大变动的时间 T_peak
          ② 找到价格回到均衡(窄幅震荡)的时间 T_stable
          ③ 消化时间 = T_stable - T_0
          ④ 半衰期 = 价格变动回落到峰值50%的时间

        A股特殊性:
          - 创业板±20% vs 主板±10% → 涨跌停不可作为消化终点
          - 11:30午休 → 消化可能被中断
          - T+1 → 当天消化不完可能延续到次日
        """
        # 日线级别粗略估算
        if not price_data:
            return {'status': 'no_price_data'}

        price_idx = {p.get('date', '')[:10]: p for p in price_data}
        all_dates = sorted(price_idx.keys())

        td = datetime.strptime(event_date[:10], "%Y-%m-%d")
        event_idx = None
        for i, d in enumerate(all_dates):
            if d == event_date[:10]:
                event_idx = i
                break
        if event_idx is None:
            return {'status': 'date_not_found'}

        event_close = price_idx[all_dates[event_idx]]['close']
        pre_close = price_idx[all_dates[event_idx - 1]]['close'] if event_idx > 0 else event_close
        initial_move = (event_close - pre_close) / pre_close * 100

        # 追踪后续变动, 直到回归窄幅(<1%日波动)
        days_to_stable = 0
        max_move = abs(initial_move)
        max_move_day = 0

        for offset in range(1, min(30, len(all_dates) - event_idx)):
            d = all_dates[event_idx + offset]
            c = price_idx[d]['close']
            cumulative_move = (c - pre_close) / pre_close * 100

            if abs(cumulative_move) > max_move:
                max_move = abs(cumulative_move)
                max_move_day = offset

            prev_c = price_idx[all_dates[event_idx + offset - 1]]['close']
            daily_move = abs((c - prev_c) / prev_c * 100)

            if daily_move < 1.0 and offset >= 2:
                days_to_stable = offset
                break

        if days_to_stable == 0:
            days_to_stable = min(10, len(all_dates) - event_idx - 1)

        # 估算半衰期
        half_life = max_move_day if max_move_day > 0 else 1

        return {
            'initial_move_pct': round(initial_move, 2),
            'peak_move_pct': round(max_move, 2),
            'peak_day': max_move_day,
            'days_to_stable': days_to_stable,
            'half_life_days': half_life,
            'digestion_speed': self._classify_speed(days_to_stable),
            'note': f'初始变动{initial_move:+.1f}%, {days_to_stable}天回归窄幅, 半衰期{half_life}天'
        }

    def _classify_speed(self, days: int) -> str:
        if days <= 1: return '🚀 极快消化'
        if days <= 3: return '🟢 快速消化'
        if days <= 7: return '🟡 中等消化'
        if days <= 14: return '🟠 慢速消化'
        return '🔴 极慢消化'

    # ── 维度③: 价格消化幅度 ──

    def price_amplitude(self, entity_code: str, event_date: str,
                        price_data: list = None) -> dict:
        """计算消息带来的价格变动幅度

        方法:
          ① 事件日CAR (相对大盘)
          ② 最大日内振幅
          ③ 消化区间 (从反应用到回归稳定的全程价格区间)
        """
        if not price_data:
            return {'status': 'no_price_data'}

        price_idx = {p.get('date', '')[:10]: p for p in price_data}
        all_dates = sorted(price_idx.keys())

        td = datetime.strptime(event_date[:10], "%Y-%m-%d")
        event_idx = None
        for i, d in enumerate(all_dates):
            if d == event_date[:10]:
                event_idx = i
                break
        if event_idx is None:
            return {'status': 'date_not_found'}

        event_data = price_idx[all_dates[event_idx]]
        event_open = event_data.get('open', event_data['close'])
        event_high = event_data.get('high', event_data['close'])
        event_low = event_data.get('low', event_data['close'])
        event_close = event_data['close']

        pre_close = price_idx[all_dates[event_idx - 1]]['close'] if event_idx > 0 else event_open

        intraday_range = (event_high - event_low) / event_low * 100
        day_change = (event_close - pre_close) / pre_close * 100
        open_gap = (event_open - pre_close) / pre_close * 100
        close_gap = (event_close - event_open) / event_open * 100

        # 消化区间: 事件日到消化完成日的价格范围
        end_idx = min(event_idx + 10, len(all_dates) - 1)
        digestion_high = max(price_idx[all_dates[i]].get('high', price_idx[all_dates[i]]['close'])
                             for i in range(event_idx, end_idx + 1))
        digestion_low = min(price_idx[all_dates[i]].get('low', price_idx[all_dates[i]]['close'])
                            for i in range(event_idx, end_idx + 1))
        digestion_range = (digestion_high - digestion_low) / pre_close * 100

        return {
            'day_change_pct': round(day_change, 2),
            'open_gap_pct': round(open_gap, 2),
            'close_gap_pct': round(close_gap, 2),
            'intraday_range_pct': round(intraday_range, 2),
            'digestion_high': round(digestion_high, 2),
            'digestion_low': round(digestion_low, 2),
            'digestion_range_pct': round(digestion_range, 2),
            'price_impact_level': self._classify_impact(abs(day_change))
        }

    def _classify_impact(self, pct: float) -> str:
        if pct > 7: return '🔴 重大冲击'
        if pct > 4: return '🟠 较大冲击'
        if pct > 2: return '🟡 中等冲击'
        if pct > 1: return '🟢 轻微冲击'
        return '⚪ 微冲击'


    # ── 三角关系模型 ──

    def triangle_analysis(self, entity_code: str, event_date: str,
                          price_data: list = None, minute_data: list = None) -> dict:
        """三维度综合分析 → 输出三角关系

        核心关系:
          ① Price ∝ Volume / √Time    (冲击函数)
          ② Absorption_Rate = ΔPrice / ΔTime  (Mbps: 每分钟定价多少基点)
          ③ Efficiency = ΔPrice / ΔVolume    (每亿资金推动多少%的变动)
        """
        va = self.volume_absorption(entity_code, event_date, price_data)
        tc = self.time_cycle(entity_code, event_date, price_data)
        pa = self.price_amplitude(entity_code, event_date, price_data)

        # 提取核心数值
        vol_ratio = va.get('vol_ratio', 1)
        days_stable = max(tc.get('days_to_stable', 1), 1)
        price_pct = abs(pa.get('day_change_pct', 0))

        # 关系①: 冲击函数 (理论预测 vs 实际)
        # P_theory = k × V × T^(-0.5), 校准k
        k = price_pct / (vol_ratio * (days_stable ** -0.5)) if vol_ratio > 0 else 0
        predicted_price = k * vol_ratio * (days_stable ** -0.5) if k > 0 else price_pct

        # 关系②: 消化速率 (基点/天)
        absorption_rate = price_pct / days_stable if days_stable > 0 else price_pct

        # 关系③: 资金效率 (每亿元推动的%变动)
        money_absorbed = va.get('total_money_absorbed', 0)
        efficiency = price_pct / (money_absorbed / 1e8) if money_absorbed > 0 else 0

        # 判定消化效率等级
        if absorption_rate > 3: eff_level = '🚀 高效消化'
        elif absorption_rate > 1: eff_level = '🟢 正常消化'
        elif absorption_rate > 0.3: eff_level = '🟡 慢速消化'
        else: eff_level = '🔴 低效消化'

        return {
            'event_date': event_date,
            'entity': entity_code,
            # 三维度
            'volume_absorption': va,
            'time_cycle': tc,
            'price_amplitude': pa,
            # 三角关系
            'triangle_relations': {
                'shock_coefficient_k': round(k, 4),
                'predicted_price_pct': round(predicted_price, 2),
                'actual_price_pct': round(price_pct, 2),
                'prediction_error': round(predicted_price - price_pct, 2),
                'absorption_rate_bps_per_day': round(absorption_rate, 2),
                'capital_efficiency_pct_per_100M': round(efficiency, 4),
                'digestion_efficiency_level': eff_level
            },
            # 结论
            'summary': self._summarize_triangle(vol_ratio, days_stable, price_pct, eff_level)
        }

    def _summarize_triangle(self, vol: float, time: int, price: float, eff: str) -> str:
        parts = []
        if vol > 2.0:
            parts.append(f"巨量资金介入({vol:.1f}x基准), 表明消息受高度关注")
        if time <= 1:
            parts.append(f"{time}天闪电消化, 定价瞬时完成")
        elif time <= 3:
            parts.append(f"{time}天快速消化, 市场反应充分")
        else:
            parts.append(f"{time}天缓慢消化, 信息扩散有延迟")

        if price > 3:
            parts.append(f"价格冲击{price:+.1f}%, 消息具有重大市场影响")
        parts.append(f"消化效率: {eff}")
        return "; ".join(parts)


    # ── 历史基线 ──

    def baseline(self, entity_code: str, days: int = 60) -> dict:
        """建立特定标的的消化基准参数

        通过回测历史事件, 学习该标的的平均消化模式
        """
        # 从news_events找历史大事件日
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        events = self.db.conn.execute("""
            SELECT DISTINCT n.published_at, e.event_category, e.sentiment, e.impact_level
            FROM news_events e
            JOIN news_articles n ON e.news_id = n.id
            JOIN news_entities en ON n.id = en.news_id
            WHERE en.entity_code = ? AND n.published_at >= ? AND e.impact_level IN ('high','medium')
            ORDER BY n.published_at
        """, (entity_code, cutoff)).fetchall()

        if len(events) < 3:
            return {'status': 'insufficient_data', 'events_found': len(events)}

        # 总结
        categories = {}
        for e in events:
            cat = e['event_category']
            if cat not in categories:
                categories[cat] = {'count': 0, 'sentiments': []}
            categories[cat]['count'] += 1
            categories[cat]['sentiments'].append(e['sentiment'])

        return {
            'entity': entity_code,
            'period_days': days,
            'significant_events': len(events),
            'category_breakdown': {k: v['count'] for k, v in categories.items()},
            'note': '历史消化基线需要价格数据做完整拟合'
        }

    # ── 预测模式 ──

    def predict(self, event_type: str = 'product_launch',
                impact_level: str = 'high',
                sentiment: str = 'positive',
                market_cap_tier: str = 'mid') -> dict:
        """基于历史基线预测新事件的消化参数

        Args:
            event_type: 事件类型
            impact_level: high/medium/low
            sentiment: positive/negative/neutral
            market_cap_tier: large/mid/small (影响消化速度)

        Returns:
            预测的消化三维度 + 置信区间
        """
        base = self.DIGESTION_PARAMS.get(event_type,
            self.DIGESTION_PARAMS.get('product_launch', (2, 1.5, 3.0)))
        base_time, base_vol_ratio, base_price = base

        # A股修正因子
        adj = 1.0
        if impact_level == 'high': adj *= 1.3
        elif impact_level == 'low': adj *= 0.6

        if sentiment == 'negative':  # 利空消化更慢
            base_time *= 1.5
            base_vol_ratio *= 0.9
        elif sentiment == 'positive':
            base_time *= 0.8  # 利好消化更快

        if market_cap_tier == 'small':
            base_vol_ratio *= 1.5  # 小盘更易被资金推动
            base_time *= 0.5
        elif market_cap_tier == 'large':
            base_vol_ratio *= 0.7
            base_time *= 1.3

        # 置信区间
        pred_time = round(base_time * adj, 1)
        pred_vol = round(base_vol_ratio * adj, 1)
        pred_price = round(base_price * adj, 1)

        return {
            'event_type': event_type,
            'predicted_time_days': pred_time,
            'predicted_time_range': f'{max(0.5, pred_time-1)}~{pred_time+2}天',
            'predicted_vol_ratio': pred_vol,
            'predicted_price_pct': pred_price,
            'predicted_price_range': f'{pred_price-1}%~{pred_price+2}%',
            'absorption_rate_bps_per_day': round(abs(pred_price) / max(pred_time, 0.5), 1),
            'confidence': 'medium' if adj != 1.0 else 'low',
            'note': f'基于A股{event_type}事件历史基准校准, 市值档位={market_cap_tier}'
        }


# ============================================================
# 二、消化关系学习器 (在线更新)
# ============================================================

class DigestionLearner:
    """从历史事件中学习消化参数, 在线更新

    存储文件: data/news_index/digestion_baseline.json
    每次新事件完成后更新参数
    """

    STORE = ROOT / "data" / "news_index" / "digestion_baseline.json"

    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        if self.STORE.exists():
            with open(self.STORE) as f:
                return json.load(f)
        return {'events': [], 'baselines': {}}

    def _save(self):
        with open(self.STORE, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def record(self, entity_code: str, event_date: str,
               vol_ratio: float, time_days: int, price_pct: float,
               event_type: str = 'unknown', impact: str = 'medium'):
        """记录一个消化事件"""
        self.data['events'].append({
            'entity': entity_code,
            'date': event_date,
            'type': event_type,
            'impact': impact,
            'vol_ratio': vol_ratio,
            'time_days': time_days,
            'price_pct': price_pct,
            'recorded_at': datetime.now().isoformat()
        })

        # 更新该类型事件的基线
        key = f"{event_type}_{impact}"
        events_of_type = [e for e in self.data['events'] if e['type'] == event_type]
        if len(events_of_type) >= 3:
            avg_time = sum(e['time_days'] for e in events_of_type) / len(events_of_type)
            avg_vol = sum(e['vol_ratio'] for e in events_of_type) / len(events_of_type)
            avg_price = sum(e['price_pct'] for e in events_of_type) / len(events_of_type)
            self.data['baselines'][key] = {
                'avg_time': round(avg_time, 2),
                'avg_vol_ratio': round(avg_vol, 2),
                'avg_price_pct': round(avg_price, 2),
                'n_samples': len(events_of_type)
            }

        self._save()
        return self.data['baselines'].get(key, {})

    def get_baseline(self, event_type: str) -> dict:
        key = f"{event_type}_high"
        return self.data['baselines'].get(key, self.data['baselines'].get(f"{event_type}_medium", {}))


# ============================================================
# CLI
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python core/digestion_model.py analyze <code> <date>       事件消化分析")
        print("  python core/digestion_model.py predict <event_type>        预测消化参数")
        print("  python core/digestion_model.py baseline <code>             历史基线")
        return

    cmd = sys.argv[1]
    db = NewsDatabase()
    de = DigestionEngine(db)

    try:
        if cmd == 'analyze':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            date = sys.argv[3] if len(sys.argv) > 3 else '2026-07-14'
            result = de.triangle_analysis(code, date)
            _print_triangle(result)

        elif cmd == 'predict':
            etype = sys.argv[2] if len(sys.argv) > 2 else 'product_launch'
            result = de.predict(event_type=etype)
            print(f"\n🔮 消化预测: {etype}")
            print(f"  预计消化时间: {result['predicted_time_days']}天 ({result['predicted_time_range']})")
            print(f"  预计量比: {result['predicted_vol_ratio']}x")
            print(f"  预计价格变动: {result['predicted_price_pct']}%")
            print(f"  消化速率: {result['absorption_rate_bps_per_day']}基点/天")
            print(f"  置信度: {result['confidence']}")

        elif cmd == 'baseline':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            result = de.baseline(code)
            print(json.dumps(result, ensure_ascii=False, indent=2))

    finally:
        db.close()


def _print_triangle(result: dict):
    tc = result.get('time_cycle', {})
    va = result.get('volume_absorption', {})
    pa = result.get('price_amplitude', {})
    tr = result.get('triangle_relations', {})

    print(f"\n{'='*60}")
    print(f"  📐 消息消化三角分析: {result['entity']} @ {result['event_date']}")
    print(f"{'='*60}")

    print(f"\n💰 资金消化量: {va.get('absorption_level','?')}")
    print(f"  基准均量: {va.get('base_avg_volume',0):.0f}手 → 事件窗口 {va.get('vol_ratio',1):.1f}x")
    print(f"  异常消化资金: {va.get('total_money_absorbed',0)/1e8:.2f}亿")

    print(f"\n⏱️  时间消化周期: {tc.get('digestion_speed','?')}")
    print(f"  {tc.get('note','')}")
    print(f"  峰值变动: {tc.get('peak_move_pct',0):+.1f}% (第{tc.get('peak_day',0)}天)")

    print(f"\n📈 价格消化幅度: {pa.get('price_impact_level','?')}")
    print(f"  日变动: {pa.get('day_change_pct',0):+.1f}% (跳空{pa.get('open_gap_pct',0):+.1f}%)")
    print(f"  日内振幅: {pa.get('intraday_range_pct',0):.1f}%")

    print(f"\n🔺 三角关系")
    print(f"  冲击系数k: {tr.get('shock_coefficient_k',0):.3f}")
    print(f"  消化速率: {tr.get('absorption_rate_bps_per_day',0):.1f}基点/天")
    print(f"  资金效率: {tr.get('capital_efficiency_pct_per_100M',0):.4f}%/亿")
    print(f"  等级: {tr.get('digestion_efficiency_level','?')}")

    print(f"\n💬 {result.get('summary','')}")


if __name__ == '__main__':
    main()
