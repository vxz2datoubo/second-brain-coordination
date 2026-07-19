"""
主力筹码峰分析器 — 波仔交易系统 v3

功能:
  基于18个月日K数据，分4个阶段追踪主力筹码行为
  Phase1: 底部试探 | Phase2: 密集建仓 | Phase3: 拉升派发 | Phase4: 冲顶回撤

输出:
  - 主力成本区间
  - 当前筹码阶段
  - 均换手趋势
  - 做T建议

集成: runner.py 盘前分析
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_daily_kline
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

LTGB_MAP = {"300418": 117532, "300058": 347793}

PHASES = {
    "Phase1 底部试探": ("20250101", "20250331"),
    "Phase2 密集建仓": ("20250401", "20250831"),
    "Phase3 拉升派发": ("20250901", "20251231"),
    "Phase4 冲顶回撤": ("20260101", "20260630"),
}


@dataclass
class ChipSnapshot:
    """一个阶段的筹码快照"""
    phase_name: str
    days: int
    price_low: float
    price_high: float
    avg_hsl: float
    max_hsl: float
    key_layers: List[Dict] = field(default_factory=list)    # [{price, pct, days}]
    distribution: str = ""  # "低价集中" "均匀分布" "高价集中"


@dataclass 
class ChipReport:
    """完整筹码分析报告"""
    code: str
    name: str
    current_price: float
    price_18m_high: float
    price_18m_low: float
    phases: List[ChipSnapshot] = field(default_factory=list)
    cost_zone: str = ""           # 主力成本区间
    current_stage: str = ""       # 当前所处阶段
    hsl_trend: str = ""           # 换手率趋势
    positioning: str = ""         # 主力仓位状态
    trade_advice: str = ""        # 做T建议


def analyze_chip(code: str, name: str = "", current_price: float = 0) -> ChipReport:
    """主入口：筹码峰全分析"""
    
    if code.startswith(("6", "5")):
        path = f"F:/tongdaxin/vipdoc/sh/lday/sh{code}.day"
    else:
        path = f"F:/tongdaxin/vipdoc/sz/lday/sz{code}.day"
    
    bars = read_daily_kline(path)
    if not bars or len(bars) < 30:
        return None
    
    ltgb = LTGB_MAP.get(code, 100000)
    recent = [b for b in bars if "20250101" <= str(b.date) <= "20260630"]
    
    all_high = max(b.high for b in recent) if recent else 0
    all_low = min(b.low for b in recent) if recent else 0
    
    report = ChipReport(
        code=code, name=name or code, current_price=current_price,
        price_18m_high=all_high, price_18m_low=all_low,
    )
    
    # 每个阶段分析
    hsl_trend = []
    for phase_name, (start, end) in PHASES.items():
        phase_bars = [b for b in recent if start <= str(b.date) <= end]
        if not phase_bars:
            continue
        
        # 步长根据股价定
        avg_p = sum((b.high + b.low)/2 for b in phase_bars) / len(phase_bars)
        step = 1.0 if avg_p > 30 else 0.5 if avg_p > 15 else 0.2
        
        buckets = defaultdict(lambda: {'vol': 0, 'days': 0})
        hsl_vals = []
        for b in phase_bars:
            mid = (b.high + b.low) / 2
            bucket = round(int(mid / step) * step, 1)
            hsl = (b.volume / (ltgb * 10000)) * 100
            buckets[bucket]['vol'] += b.volume
            buckets[bucket]['days'] += 1
            hsl_vals.append(hsl)
        
        total_vol = sum(v['vol'] for v in buckets.values())
        avg_hsl = sum(hsl_vals) / len(hsl_vals)
        max_hsl = max(hsl_vals)
        hsl_trend.append(avg_hsl)
        phase_high = max(b.high for b in phase_bars)
        phase_low = min(b.low for b in phase_bars)
        
        # 找关键筹码层(>4%)
        sig = [(p, v['vol']/total_vol*100, v['days']) 
               for p, v in buckets.items() if v['vol']/total_vol*100 >= 4]
        sig.sort()
        
        snap = ChipSnapshot(
            phase_name=phase_name,
            days=len(phase_bars),
            price_low=phase_low,
            price_high=phase_high,
            avg_hsl=round(avg_hsl, 1),
            max_hsl=round(max_hsl, 1),
            key_layers=[{"price": p, "pct": round(pct, 1), "days": d} for p, pct, d in sig],
        )
        report.phases.append(snap)
    
    # 判断主力成本区
    p2 = report.phases[1] if len(report.phases) > 1 else None  # Phase2密集建仓
    p4 = report.phases[3] if len(report.phases) > 3 else None  # Phase4当前
    
    if p2 and p2.key_layers:
        lo = min(l["price"] for l in p2.key_layers)
        hi = max(l["price"] for l in p2.key_layers)
        report.cost_zone = f"{lo:.1f}-{hi:.1f}元(Phase2密集建仓)"
    elif p4 and p4.key_layers:
        lo = min(l["price"] for l in p4.key_layers)
        hi = max(l["price"] for l in p4.key_layers)
        report.cost_zone = f"{lo:.1f}-{hi:.1f}元(Phase4)"
    
    # 判断当前阶段 (用主力成本上限做基准)
    if p4 and report.cost_zone:
        cost_lo = p2.key_layers[0]["price"] if p2 and p2.key_layers else 0
        cost_hi = p2.key_layers[-1]["price"] if p2 and p2.key_layers else 0
        ratio = current_price / cost_hi if cost_hi > 0 else 0
        if current_price <= 0:
            report.current_stage = "数据不足"
        elif ratio < 1.2:
            report.current_stage = "二次建仓区(价格接近主力成本)"
        elif ratio < 2.0:
            report.current_stage = f"拉升区(价格{ratio:.1f}x主力成本)"
        elif ratio < 3.0:
            report.current_stage = f"高位博弈区(价格{ratio:.1f}x主力成本)"
        else:
            report.current_stage = f"主力派发区(价格{ratio:.1f}x主力成本)"
    
    # 换手率趋势
    if len(hsl_trend) >= 3:
        p1_h, p2_h, p4_h = hsl_trend[0], hsl_trend[1], hsl_trend[-1]
        if p4_h > p2_h * 2:
            report.hsl_trend = f"加速换手({p2_h:.1f}%→{p4_h:.1f}%，出货特征)"
        elif p4_h > p2_h * 1.3:
            report.hsl_trend = f"温和放量({p2_h:.1f}%→{p4_h:.1f}%，活跃)"
        elif p4_h < p2_h * 0.8:
            report.hsl_trend = f"缩量({p2_h:.1f}%→{p4_h:.1f}%，蓄力)"
        else:
            report.hsl_trend = f"稳定({p2_h:.1f}%→{p4_h:.1f}%)"
    
    # 仓位状态
    if "建仓" in report.current_stage:
        report.positioning = "主力重新吸筹，仓位轻，等待拉升"
    elif "拉升区" in report.current_stage:
        stg = "拉升中" if report.hsl_trend and "出货" in report.hsl_trend else "拉升中但警惕"
        report.positioning = stg
    elif "博弈" in report.current_stage or "派发" in report.current_stage:
        report.positioning = "主力高位减仓/博弈，有出货嫌疑"
    
    # 做T建议
    if report.positioning and "吸筹" in report.positioning:
        report.trade_advice = "🟢 可大胆做T — 主力和你同一战线"
    elif report.positioning and "拉升" in report.positioning:
        report.trade_advice = "🟡 谨慎做T — 主力在拉不要逆势"
    elif report.positioning and "减仓" in report.positioning:
        report.trade_advice = "🔴 做T风险高 — 主力在出货"
    else:
        report.trade_advice = "➖ 观望"
    
    return report


def format_chip_report(report: ChipReport) -> str:
    """格式化筹码报告"""
    if not report:
        return "筹码数据不足"
    
    lines = [f"\n{'='*55}"]
    lines.append(f"  🏔️ 主力筹码分析 — {report.name}({report.code})")
    lines.append(f"{'='*55}")
    lines.append(f"  18月区间: {report.price_18m_low:.1f}-{report.price_18m_high:.1f} | 现价: {report.current_price:.2f}")
    lines.append(f"  主力成本: {report.cost_zone}")
    lines.append(f"  当前阶段: {report.current_stage}")
    lines.append(f"  换手趋势: {report.hsl_trend}")
    lines.append(f"  仓位判断: {report.positioning}")
    lines.append(f"  {'─'*53}")
    lines.append(f"  📋 {report.trade_advice}")
    lines.append(f"{'='*55}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    for code, name in [("300418", "昆仑万维"), ("300058", "蓝色光标")]:
        r = analyze_chip(code, name)
        print(format_chip_report(r))
