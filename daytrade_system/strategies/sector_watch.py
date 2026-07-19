"""
板块联动监控模块 v2 — 加入板块级涨停扫描

配置:
  昆仑万维(300418) → AI软件: 科大讯飞(002230) + 三六零(601360)
  蓝色光标(300058) → 广告传媒: 分众传媒(002027) + 省广集团(002400)

竞价分析强制规则:
  1. 先拉预设关联股涨跌
  2. 再扫描同板块涨停/跌停情况（通过通达信行业分类）
  3. 至少看同板块前5只涨幅最大票 — 避免漏掉小票涨停潮
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.tdx_parser import read_minute_kline, group_by_date

# 扩展的板块关联（按通达信行业分类代码）
SECTOR_CODE_MAP = {
    "300418": "84301",  # 昆仑万维 → 互联网
    "300058": "84302",  # 蓝色光标 → 广告传媒
    "002230": "84202",  # 科大讯飞 → 软件服务
    "601360": "84202",  # 三六零 → 软件服务
}

# 广告传媒板块小票池（需要额外监控的涨停候选）
AD_SECTOR_SMALL_CAPS = [
    "300071",  # 福石控股
    "002995",  # 天地在线
    "002354",  # 天娱数科
    "603598",  # 引力传媒
    "002400",  # 省广集团
    "002027",  # 分众传媒
    "300063",  # 天龙集团
    "600986",  # 浙文互联
]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECTOR_MAP = {
    "300418": {
        "name": "昆仑万维",
        "sector": "AI软件",
        "peers": [
            {"code": "002230", "setcode": "0", "name": "科大讯飞"},
            {"code": "601360", "setcode": "1", "name": "三六零"},
        ],
    },
    "300058": {
        "name": "蓝色光标",
        "sector": "广告传媒",
        "peers": [
            {"code": "002027", "setcode": "0", "name": "分众传媒"},
            {"code": "002400", "setcode": "0", "name": "省广集团"},
        ],
    },
}


def analyze_sector_sync(main_stock: dict, peers: list) -> dict:
    """
    分析主股与关联股的联动性
    main_stock: {"chg_pct": -3.9, "vwap_pos": "below", ...}
    peers: [{"chg_pct": -4.7, ...}, ...]
    
    Returns: {"sync": "同步"|"分化"|"独立", "score": 0-100, "signal": str}
    """
    if not peers or not main_stock:
        return {"sync": "无数据", "score": 0, "signal": "无法判断"}

    main_chg = main_stock.get("chg_pct", 0)
    main_low = main_stock.get("low_pct", 0)  # 距日低百分比
    main_vwap = main_stock.get("vwap_pos", "neutral")

    peer_chgs = [p.get("chg_pct", 0) for p in peers if p]
    if not peer_chgs:
        return {"sync": "无数据", "score": 0, "signal": "无关联数据"}

    avg_peer_chg = sum(peer_chgs) / len(peer_chgs)
    chg_spread = abs(main_chg - avg_peer_chg)

    # 同步打分
    score = 100
    details = []

    # 涨跌幅偏离度
    if chg_spread < 0.5:
        score -= 0
        details.append("涨跌幅高度一致")
    elif chg_spread < 1.0:
        score -= 10
        details.append(f"涨跌幅偏离{chg_spread:.1f}%")
    elif chg_spread < 2.0:
        score -= 25
        details.append(f"涨跌幅明显偏离{chg_spread:.1f}%")
    else:
        score -= 50
        details.append(f"涨跌幅严重分化{chg_spread:.1f}%")

    # VWAP位置一致
    all_below = all(p.get("vwap_pos") == "below" for p in peers) and main_vwap == "below"
    all_above = all(p.get("vwap_pos") == "above" for p in peers) and main_vwap == "above"
    if all_below or all_above:
        details.append("VWAP位置一致")
    else:
        score -= 15
        details.append("VWAP位置分化")

    # 距日低位置
    peer_lows = [p.get("low_pct", 0) for p in peers if p.get("low_pct") is not None]
    if peer_lows:
        avg_peer_low = sum(peer_lows) / len(peer_lows)
        low_spread = abs(main_low - avg_peer_low)
        if low_spread < 1.0:
            details.append("日内低点位置同步")
        elif low_spread < 2.0:
            score -= 10
            details.append("日内低点略分化")
        else:
            score -= 20
            details.append("日内低点严重分化")

    # 信号输出
    if score >= 85:
        sync = "高度同步"
        signal = "板块共振 → 信号可靠，可执行"
    elif score >= 65:
        sync = "基本同步"
        signal = "轻微分化 → 信号可参考，适当谨慎"
    elif score >= 40:
        sync = "部分分化"
        signal = "关联股走势分歧 → 降低仓位，注意风险"
    else:
        sync = "严重分化"
        signal = "个股独立行情 → 信号不可靠，观望"

    return {
        "sync": sync,
        "score": max(0, min(100, score)),
        "signal": signal,
        "details": details,
        "main_chg": main_chg,
        "peer_avg_chg": round(avg_peer_chg, 2),
        "chg_spread": round(chg_spread, 2),
    }


def build_stock_summary(quote_data: dict) -> dict:
    """
    从通达信行情数据提取关键指标
    """
    hq = quote_data.get("HQInfo", {})
    now = float(hq.get("Now", 0))
    close = float(hq.get("Close", 0))
    low = float(hq.get("MinP", 0))
    avg = float(hq.get("Average", 0))

    if close == 0:
        return {}

    chg_pct = round((now / close - 1) * 100, 2)
    low_pct = round((now / low - 1) * 100, 2) if low > 0 else 0
    vwap_pos = "above" if now > avg else "below"

    return {
        "code": quote_data.get("BaseInfo", {}).get("Code", ""),
        "name": quote_data.get("BaseInfo", {}).get("Name", ""),
        "now": now,
        "chg_pct": chg_pct,
        "low_pct": low_pct,
        "vwap_pos": vwap_pos,
        "avg_price": round(avg, 2),
        "day_low": low,
    }


def get_peer_config(main_code: str) -> list:
    """获取关联股配置"""
    return SECTOR_MAP.get(main_code, {}).get("peers", [])
