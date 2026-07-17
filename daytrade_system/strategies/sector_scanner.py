"""
板块涨停扫描器 — 竞价分析强制流程

设计原则:
  每次竞价分析必须扫描同板块小票涨停情况，
  不依赖人工观察，自动发现板块级别的异常信号。

当前方案（无全板块API的过渡期）:
  使用预定义的小票池，逐票拉取涨停状态。
  未来升级：接入通达信板块API批量获取。
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 各板块小票监控池 (至少5只)
SECTOR_POOLS = {
    "300058": [  # 蓝色光标 → 广告传媒板块
        "300071",   # 福石控股
        "002995",   # 天地在线
        "002354",   # 天娱数科
        "603598",   # 引力传媒
        "002400",   # 省广集团
        "300063",   # 天龙集团
        "002027",   # 分众传媒
    ],
    "300418": [  # 昆仑万维 → AI/互联网板块
        "002230",   # 科大讯飞
        "601360",   # 三六零
        "300624",   # 万兴科技
        "688111",   # 金山办公
        "002261",   # 拓维信息
    ],
}


def scan_sector_heat(code: str, tdx_quotes_fn) -> dict:
    """
    扫描同板块小票涨停情况

    Args:
        code: 主票代码
        tdx_quotes_fn: 通达信MCP报价函数 (code, setcode) -> dict

    Returns:
        {limit_ups: [{code, name, chg_pct}], summary: str}
    """
    pool = SECTOR_POOLS.get(code, [])
    if not pool:
        return {"limit_ups": [], "summary": "无板块数据"}

    limit_ups = []
    for peer_code in pool:
        try:
            setcode = "1" if peer_code.startswith(("6", "5")) else "0"
            quote = tdx_quotes_fn(peer_code, setcode)
            if not quote:
                continue

            hq = quote.get("HQInfo", {})
            now = float(hq.get("Now", 0))
            close = float(hq.get("Close", 0))
            name = quote.get("BaseInfo", {}).get("Name", peer_code)

            if close > 0:
                chg = (now / close - 1) * 100
                is_limit = abs(chg) >= 9.5
                if is_limit:
                    limit_ups.append({
                        "code": peer_code,
                        "name": name,
                        "chg_pct": round(chg, 1),
                    })
        except Exception:
            continue

    if limit_ups:
        names = ", ".join(f"{x['name']}({x['chg_pct']:+.1f}%)" for x in limit_ups)
        heat = "涨停潮" if len(limit_ups) >= 3 else "涨停"
        summary = f"🚀 板块{heat}: {names}"
        signal = "🔥 板块强共振"
    else:
        summary = "同板块无涨停"
        signal = "—"

    return {
        "limit_ups": limit_ups,
        "count": len(limit_ups),
        "summary": summary,
        "signal": signal,
    }
