"""
通达信本地二进制数据解析器
解析 .day(日K), .lc1(1分钟K), .lc5(5分钟K) 文件
免依赖，纯 struct 实现
"""

import struct
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TDXBar:
    """通用K线数据结构"""
    date: str        # YYYYMMDD
    time_sec: int    # 秒数（日内）
    time_str: str    # HH:MM
    open: float
    high: float
    low: float
    close: float
    amount: float    # 成交额
    volume: int      # 成交量（股）
    up_count: int    # 主动买笔数
    down_count: int  # 主动卖笔数


def _unpack_date(w: int) -> str:
    """解包通达信日期格式 -> YYYYMMDD
    格式: (year-2004)*2048 + month*100 + day
    """
    year = (w // 2048) + 2004
    md = w % 2048
    month = md // 100
    day = md % 100
    return f"{year:04d}{month:02d}{day:02d}"


def _minutes_to_sec(minutes: int) -> int:
    """通达信分钟数转秒数"""
    return minutes * 60


def _parse_lc_record(data: bytes, offset: int) -> Optional[TDXBar]:
    """解析单条.lc1/.lc5记录 (32 bytes)"""
    if offset + 32 > len(data):
        return None

    unpacked = struct.unpack_from('<HHfffffIHH', data, offset)
    date_word, minute = unpacked[0], unpacked[1]
    open_p, high_p, low_p, close_p = unpacked[2], unpacked[3], unpacked[4], unpacked[5]
    amount = unpacked[6]
    volume = unpacked[7]
    up_count, down_count = unpacked[8], unpacked[9]

    try:
        date_str = _unpack_date(date_word)
    except (ValueError, ZeroDivisionError):
        return None

    if date_str.startswith('1970') or open_p == 0:
        return None  # 无效记录

    sec = _minutes_to_sec(minute)
    h, m = divmod(minute, 60)

    return TDXBar(
        date=date_str,
        time_sec=sec,
        time_str=f"{h:02d}:{m:02d}",
        open=open_p,
        high=high_p,
        low=low_p,
        close=close_p,
        amount=amount,
        volume=volume,
        up_count=up_count,
        down_count=down_count,
    )


def read_minute_kline(filepath: str, start_date: str = None,
                       end_date: str = None, limit: int = None) -> List[TDXBar]:
    """
    读取通达信分钟K线文件 (.lc1 或 .lc5)
    """
    with open(filepath, 'rb') as f:
        data = f.read()

    record_size = 32
    total_records = len(data) // record_size
    bars = []

    for i in range(total_records):
        bar = _parse_lc_record(data, i * record_size)
        if bar is None:
            continue

        # 日期过滤
        if start_date and bar.date < start_date:
            continue
        if end_date and bar.date > end_date:
            continue

        bars.append(bar)

    if limit and len(bars) > limit:
        bars = bars[-limit:]

    return bars


def read_daily_kline(filepath: str) -> List[TDXBar]:
    """
    读取通达信日K线文件 (.day)
    格式 (32 bytes): date(I) open(I) high(I) low(I) close(I) amount(f) volume(I) reserved(I)
    OHLC 存储为 uint32 * 100 (即价格×100)
    """
    import struct
    with open(filepath, 'rb') as f:
        data = f.read()

    record_size = 32
    total_records = len(data) // record_size
    bars = []

    for i in range(total_records):
        offset = i * record_size
        if offset + 32 > len(data):
            break
        unpacked = struct.unpack_from('<IIIIIfII', data, offset)
        date_int = unpacked[0]
        if date_int < 20000000:
            continue

        date_str = str(date_int)
        open_p = unpacked[1] / 100.0
        high_p = unpacked[2] / 100.0
        low_p = unpacked[3] / 100.0
        close_p = unpacked[4] / 100.0
        amount = unpacked[5]
        volume = unpacked[6]

        bars.append(TDXBar(
            date=date_str, time_sec=0, time_str="",
            open=open_p, high=high_p, low=low_p, close=close_p,
            amount=amount, volume=volume,
            up_count=0, down_count=0,
        ))

    return bars


def group_by_date(bars: List[TDXBar]) -> Dict[str, List[TDXBar]]:
    """按日期分组K线"""
    from collections import defaultdict
    groups = defaultdict(list)
    for bar in bars:
        groups[bar.date].append(bar)
    return dict(groups)


def bars_to_dict_list(bars: List[TDXBar]) -> List[Dict]:
    """转为字典列表，方便JSON/存储"""
    return [{
        "date": b.date,
        "time_sec": b.time_sec,
        "time_str": b.time_str,
        "open": b.open,
        "high": b.high,
        "low": b.low,
        "close": b.close,
        "amount": b.amount,
        "volume": b.volume,
        "up_count": b.up_count,
        "down_count": b.down_count,
    } for b in bars]
