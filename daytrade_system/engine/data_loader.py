"""
数据加载器 —— 将通达信MCP原始JSON转为内部数据结构
"""

from typing import Dict, List, Any
from engine.indicators import KBar, QuoteSnapshot


def parse_daily_kline(raw: Dict) -> List[KBar]:
    """解析日K线数据"""
    bars = []
    items = raw.get("ListItem", [])
    for item in items:
        data = item["Item"]
        bars.append(KBar(
            date=data[0],
            time_sec=int(data[1]),
            open=float(data[2]),
            high=float(data[3]),
            low=float(data[4]),
            close=float(data[5]),
            amount=float(data[6]),
            volume=float(data[8])
        ))
    return bars


def parse_minute_kline(raw: Dict) -> List[KBar]:
    """解析分钟K线（5min/15min/30min/60min）"""
    bars = []
    items = raw.get("ListItem", [])
    for item in items:
        data = item["Item"]
        bars.append(KBar(
            date=data[0],
            time_sec=int(data[1]),
            open=float(data[2]),
            high=float(data[3]),
            low=float(data[4]),
            close=float(data[5]),
            amount=float(data[6]),
            volume=float(data[8])
        ))
    return bars


def parse_quote(raw: Dict) -> QuoteSnapshot:
    """解析实时行情"""
    hq = raw.get("HQInfo", {})
    ext = raw.get("ExtInfo", {})
    pro = raw.get("ProInfo", {})
    base = raw.get("BaseInfo", {})
    bsp = raw.get("BspInfo", [])

    return QuoteSnapshot(
        code=base.get("Code", ""),
        name=raw.get("AttachInfo", {}).get("Name", base.get("Name", "")),
        date=hq.get("HQDate", ""),
        time=hq.get("HQTime", ""),
        open=float(hq.get("Open", 0)),
        high=float(hq.get("MaxP", 0)),
        low=float(hq.get("MinP", 0)),
        pre_close=float(hq.get("Close", 0)),  # 通达信Close=前收
        now=float(hq.get("Now", 0)),
        volume=float(hq.get("Volume", 0)),
        amount=float(hq.get("Amount", 0)),
        avg_price=float(hq.get("Average", 0)),
        hsl=float(hq.get("HSL", 0)),
        inside=float(hq.get("Inside", 0)),
        outside=float(hq.get("Outside", 0)),
        zt_price=float(ext.get("ZTPrice", 0)),
        dt_price=float(ext.get("DTPrice", 0)),
        ltgb=float(ext.get("LTGB", 0)),
        zsz=float(ext.get("ZSZ", 0)),
        inflow=float(pro.get("InOut", 0)),  # 主力净流入（元）
        wtb=float(pro.get("Wtb", 0)),       # 小单比
        bsp=bsp
    )


def load_stock_data(quote_raw: Dict, daily_raw: Dict, hourly_raw: Dict = None,
                    min5_raw: Dict = None) -> Dict:
    """
    一站式加载单只股票的所有数据
    Returns: {quote, daily_bars, hourly_bars, min5_bars}
    """
    result = {
        "quote": parse_quote(quote_raw),
        "daily_bars": parse_daily_kline(daily_raw),
        "hourly_bars": parse_minute_kline(hourly_raw) if hourly_raw else [],
        "min5_bars": parse_minute_kline(min5_raw) if min5_raw else [],
    }
    return result
