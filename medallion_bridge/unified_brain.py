"""
unified_brain.py — 统一决策引擎 v2.0
整合: Medallion 6因子 + 智慧大脑(8767) + 量价剖面 + TDX实时数据

用法:
  python unified_brain.py 300418 --decision
"""

import sys, os, json, urllib.request, struct, time, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daytrade_system"))

from daytrade_system.medallion.config import STOCK_CONFIGS, get_confidence, current_window
from daytrade_system.medallion.signal_pipeline import SignalPipeline
from daytrade_system.medallion.tdx_connector import TDXConnector
from daytrade_system.strategies.crossover_tracker import adjusted_profile as vp_adjusted_profile
from daytrade_system.engine.indicators import KBar

BRAIN_URL = "http://localhost:8767"
from daytrade_system.medallion.tdx_connector import TDXConnector

tdx = TDXConnector(offline=True)

def get_realtime_quote(code: str) -> dict:
    """通过TDXConnector获取实时数据"""
    try:
        quote = tdx.get_quote(code)
        daily = tdx.get_daily(code, 20)
        min5_today = tdx.get_today_min5(code)
    except Exception as e:
        return {"error": str(e)}
    
    if not quote or not daily:
        return {"error": "无数据"}
    
    # 转为KBar
    daily_bars = [KBar(date=str(d["date"]), time_sec=0, open=d["open"], high=d["high"],
                        low=d["low"], close=d["close"], volume=d["volume"], amount=d["amount"])
                  for d in daily]
    
    min5_bars = [KBar(date=m["date"], time_sec=m["time"], open=m["open"], high=m["high"],
                       low=m["low"], close=m["close"], volume=m["volume"], amount=m["amount"])
                 for m in min5_today] if min5_today else []
    
    return {
        "current": quote.get("now", quote.get("close", 0)),
        "open": quote.get("open", 0),
        "high": quote.get("high", 0),
        "low": quote.get("low", 0),
        "prev_close": quote.get("pre_close", quote.get("prev_close", 0)),
        "volume": quote.get("volume", 0),
        "avg_price": quote.get("amount", 0) / max(quote.get("volume", 1), 1),
        "change_pct": (quote.get("now", 0) / max(quote.get("pre_close", 1), 1) - 1) * 100,
        "daily_bars": daily_bars,
        "min5_bars": min5_bars or daily_bars[-5:]
    }

# ============================================================
# 2. 智慧大脑 API
# ============================================================

def brain_post(endpoint, data):
    url = f"{BRAIN_URL}{endpoint}"
    req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except: return {"error": "brain offline"}

def brain_memory_search(query: str):
    return brain_post("/api/deep/memory/read", {"key": query})

# ============================================================
# 3. 统一分析引擎
# ============================================================

def unified_analysis(code: str):
    config = STOCK_CONFIGS.get(code)
    if not config: return {"error": f"未配置 {code}"}
    
    # 3.1 实时数据
    q = get_realtime_quote(code)
    if not q: return {"error": "无数据"}
    
    # 3.2 Medallion 6因子评分
    pipeline = SignalPipeline(code, config)
    signal = pipeline.evaluate(q["current"], q["min5_bars"], q["daily_bars"], 
                                q["prev_close"], "HIGH_VOL_RANGE")
    
    # 3.3 量价剖面
    adj = vp_adjusted_profile(code, q["current"], days=10, min_pct=0.2)
    p_layers = [p for p in adj if p.get("side") == "resistance"]
    s_layers = [s for s in adj if s.get("side") == "support"]
    
    # 3.4 时间窗口
    from datetime import datetime
    window = current_window(datetime.now().strftime("%H:%M"))
    
    # 3.5 查询智慧大脑记忆
    brain = brain_memory_search("trading")
    brain_has = len(brain.get("results", [])) > 0 if isinstance(brain, dict) else False
    
    # 3.6 威科夫供应测试
    from supply_tester import analyze_supply_test, quick_check
    supply = analyze_supply_test(code, q["current"], q["high"], q["low"])
    
    # 3.7 资金流背离分析
    from flow_divergence import flow_price_analysis
    flow = flow_price_analysis(code)
    
    return {
        "code": code, "name": config.name,
        "price": q,
        "signal": {
            "total": round(signal.total_score, 1),
            "sell": round(signal.sell_score, 1),
            "buy": round(signal.buy_score, 1),
            "confidence": signal.confidence,
            "suggestion": signal.suggestion,
            "factors": {k: round(v.score,1) for k,v in (signal.factors or {}).items()},
            "details": signal.details[:5]
        },
        "volume_profile": {
            "pressure": [{"r": p["label"], "pct": p["adjusted_pct"], "cross": p["cross_label"]} 
                         for p in p_layers[-2:]],
            "support": [{"r": s["label"], "pct": s["adjusted_pct"], "cross": s["cross_label"]} 
                        for s in s_layers[:2]],
        },
        "window": {"id": window.id, "note": window.notes, "allow_new": window.allow_new_entry},
        "brain_knowledge": f"{brain_has and '已连接' or '无数据'}",
        "supply_test": {
            "signal": supply["signal"],
            "confidence": supply["confidence"],
            "check": quick_check(code, q["current"], q["high"], q["low"]),
            "velocity": supply["velocity"]
        },
        "money_flow": {
            "cmf": flow.get("current_cmf", 0),
            "pressure": flow.get("pressure", "?"),
            "trend": flow.get("trend_5bar", "?"),
            "divergence": flow.get("divergence", {}).get("type")
        }
    }

# ============================================================
# 4. 主入口
# ============================================================

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code"); p.add_argument("--decision", action="store_true")
    args = p.parse_args()
    
    r = unified_analysis(args.code)
    if "error" in r:
        print(f"❌ {r['error']}"); sys.exit(1)
    
    q, s, v, w, st = r["price"], r["signal"], r["volume_profile"], r["window"], r.get("supply_test", {})
    
    print(f"\n{'='*60}")
    print(f"  🧠 统一决策引擎 — {r['name']}({r['code']})  [{r['brain_knowledge']}]")
    print(f"  📍 {q['current']:.2f} ({q['change_pct']:+.2f}%)  高{q['high']:.2f} 低{q['low']:.2f}")
    print(f"  ⏰ {w['id']} | {w['note']}")
    print(f"{'='*60}")

    # 供应测试
    if st:
        vt = st.get("velocity", {})
        icon = "✅" if st.get("signal") == "TEST_PASSED" else "🟡" if st.get("signal") == "NO_SUPPLY" else "❌"
        print(f"  🔬 供应测试: {icon} {st.get('check','')}")
        if vt:
            print(f"     走势: {vt.get('type','?')}+{vt.get('volume_level','?')}量 | 置信度{st.get('confidence',0)}")
    
    print(f"\n  ┌─ 6因子评分 ────────────────────────────┐")
    print(f"  │ 卖{s['sell']:.0f}  买{s['buy']:.0f}  总{s['total']:.0f}  [{s['confidence']}]")
    if s['factors']:
        f_str = "  ".join(f"{k}={v:.0f}" for k,v in s['factors'].items())
        print(f"  │ {f_str}")
    print(f"  │ {s['suggestion']}")
    if s['details']:
        for d in s['details'][:2]: print(f"  │ > {d}")
    print(f"  └────────────────────────────────────────┘")
    
    if v['pressure']:
        for pr in v['pressure']:
            print(f"  🔴 压力: {pr['r']} ({pr['pct']:.1f}% {pr['cross']})")
    if v['support']:
        for su in v['support']:
            print(f"  🟢 支撑: {su['r']} ({su['pct']:.1f}% {su['cross']})")
    
    if args.decision:
        print(f"\n  {'─'*58}")
        conf = s['confidence']
        if conf in ('A++','A'):
            print(f"  🎯 强信号 — 可执行卖T，目标看最近压力层")
        elif conf == 'B':
            print(f"  🎯 中等信号 — 降低仓位，挂限价单")
        else:
            print(f"  🎯 信号不足 — 等待或手动判断")
    
    print(f"\n{'='*60}\n")
