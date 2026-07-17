"""tdx_bridge.py — 通达信数据 MCP 服务器 (stdio)

将通达信本地行情数据暴露为 MCP 工具，供 MaiBot Planner 调用。

数据源：通达信本地 .day / .lc1 / .lc5 二进制文件（零成本，不需要付费API）
参考：MEMORY.md — 通达信本地数据零成本方案，lc1分钟线可直接解析完整OHLCV+成交量

协议: JSON-RPC 2.0 over stdin/stdout
暴露 4 个工具:
  tdx_realtime     — 股票实时行情（日K最新一根）
  tdx_kline_day    — 日K线历史数据
  tdx_kline_min    — 分钟K线（1min/5min，来自lc1/lc5）
  tdx_search       — 搜索股票代码/名称

启动方式 (bot_config.toml):
  [[mcp.servers]]
  name = "tdx-bridge"
  transport = "stdio"
  command = "python"
  args = ["-u", "F:/aidanao/mcp/tdx_bridge.py"]

通达信数据目录自动探测，或通过环境变量 TDX_HOME 指定。
"""

import json
import os
import struct
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


# ============ 通达信路径探测 ============

def _find_tdx_home() -> Path | None:
    """自动探测通达信安装目录"""
    env = os.environ.get("TDX_HOME", "")
    if env and Path(env).exists():
        return Path(env)

    candidates = [
        Path("F:/tongdaxin"),
        Path("D:/new_tdx"),
        Path("C:/new_tdx"),
        Path("E:/new_tdx"),
        Path("D:/tdx"), Path("C:/tdx"), Path("F:/tongdaxin"),
    ]
    for c in candidates:
        vipdoc = c / "vipdoc"
        if vipdoc.exists():
            return c
    return None


TDX_HOME = _find_tdx_home()
TDX_AVAILABLE = TDX_HOME is not None

if TDX_AVAILABLE:
    VIPDOC = TDX_HOME / "vipdoc"
else:
    VIPDOC = None


# ============ 二进制解析 ============

def _parse_day_record(data: bytes) -> dict:
    """解析通达信 .day 单条记录 (32 bytes)
    
    格式: <I I I I I f I I
      [0]   uint32:  YYYYMMDD
      [1-4] uint32:  O/H/L/C（单位: 0.01元，需除以100）
      [5]   float32: 成交额（元）
      [6]   uint32:  成交量（手）
      [7]   uint32:  保留
    """
    if len(data) < 32:
        return {}
    date_int, open_raw, high_raw, low_raw, close_raw, amount, vol, reserved = struct.unpack("<IIIIIfII", data[:32])
    # 日期格式: YYYYMMDD
    y = date_int // 10000
    m = (date_int % 10000) // 100
    d = date_int % 100
    return {
        "date": f"{y}-{m:02d}-{d:02d}",
        "open": round(open_raw / 100.0, 2),
        "high": round(high_raw / 100.0, 2),
        "low": round(low_raw / 100.0, 2),
        "close": round(close_raw / 100.0, 2),
        "amount": round(amount, 2),
        "volume": vol,
    }


def _parse_lc1_record(data: bytes) -> dict:
    """解析通达信 .lc1 单条记录 (32 bytes, 1分钟K线)
    
    格式: <I f f f f f I I
      [0]  packed uint32: hi16=日内分钟, lo16=距1901-10-17的天数
      [1-4] float32: O/H/L/C (实际价格)
      [5]   float32: 成交额（元）
      [6]   uint32:  成交量（手）
      [7]   uint32:  保留
    """
    if len(data) < 32:
        return {}
    packed, open_p, high_p, low_p, close_p, amount, vol, reserved = struct.unpack("<IfffffII", data[:32])
    
    # 拆分时间编码
    hi = (packed >> 16) & 0xFFFF   # 日内分钟数
    lo = packed & 0xFFFF           # 距 1901-10-17 的天数
    
    # 计算实际日期
    LC1_EPOCH = date(1901, 10, 17)
    dt = LC1_EPOCH + timedelta(days=lo)
    hh = hi // 60
    mm = hi % 60
    
    return {
        "datetime": f"{dt.strftime('%Y-%m-%d')} {hh:02d}:{mm:02d}",
        "open": round(open_p, 2),
        "high": round(high_p, 2),
        "low": round(low_p, 2),
        "close": round(close_p, 2),
        "amount": round(amount, 2),
        "volume": vol,
    }


def _parse_lc5_record(data: bytes) -> dict:
    """解析通达信 .lc5 单条记录 (32 bytes, 5分钟K线，结构与lc1相同)"""
    return _parse_lc1_record(data)  # 格式完全一致


def _get_day_file(code: str, market: str = "sz") -> Path | None:
    """获取日K线文件路径"""
    if not VIPDOC:
        return None
    if code.startswith(("60", "68")):
        market = "sh"
    elif code.startswith(("00", "30")):
        market = "sz"
    f = VIPDOC / market / "lday" / f"{market}{code}.day"
    return f if f.exists() else None


def _get_lc1_file(code: str, market: str = "sz") -> Path | None:
    """获取1分钟线文件路径（新版通达信放 minline 目录，旧版放 lc1）"""
    if not VIPDOC:
        return None
    if code.startswith(("60", "68")):
        market = "sh"
    elif code.startswith(("00", "30")):
        market = "sz"
    # 优先 minline（新版），fallback lc1（旧版）
    for subdir in ["minline", "lc1"]:
        f = VIPDOC / market / subdir / f"{market}{code}.lc1"
        if f.exists():
            return f
    return None


def _get_lc5_file(code: str, market: str = "sz") -> Path | None:
    """获取5分钟线文件路径"""
    if not VIPDOC:
        return None
    if code.startswith(("60", "68")):
        market = "sh"
    elif code.startswith(("00", "30")):
        market = "sz"
    for subdir in ["minline", "lc5"]:
        f = VIPDOC / market / subdir / f"{market}{code}.lc5"
        if f.exists():
            return f
    return None


def _read_records(fpath: Path, parser, limit: int = 0) -> list:
    """读取二进制文件全部记录"""
    records = []
    try:
        data = fpath.read_bytes()
        record_size = 32
        total = len(data) // record_size
        start = max(0, total - limit) if limit else 0
        for i in range(start, total):
            offset = i * record_size
            record = parser(data[offset:offset + record_size])
            if record:
                records.append(record)
    except Exception as e:
        return [{"error": str(e)}]
    return records


# ============ 工具实现 ============

def tdx_realtime(code: str) -> str:
    """获取实时行情（日K线最新一根）"""
    if not TDX_AVAILABLE:
        return _no_tdx_msg()

    f = _get_day_file(code)
    if not f:
        return f"❌ 未找到股票 {code} 的日线数据文件"

    records = _read_records(f, _parse_day_record)
    if not records:
        return f"❌ {code} 日线数据为空"

    latest = records[-1]
    prev = records[-2] if len(records) > 1 else None

    change_pct = ""
    if prev and prev["close"] != 0:
        chg = (latest["close"] - prev["close"]) / prev["close"] * 100
        change_pct = f"{chg:+.2f}%"

    # 格式化金额
    amt = latest["amount"]
    if amt >= 1e8:
        amt_str = f"{amt/1e8:.2f}亿"
    else:
        amt_str = f"{amt/1e4:.0f}万"

    return json.dumps({
        "code": code,
        "date": latest["date"],
        "open": latest["open"],
        "high": latest["high"],
        "low": latest["low"],
        "close": latest["close"],
        "change_pct": change_pct,
        "volume_手": latest["volume"],
        "amount_元": amt_str,
        "data_records": len(records),
        "source": f"通达信本地 {f.name}",
    }, ensure_ascii=False, indent=2)


def tdx_kline_day(code: str, count: int = 60) -> str:
    """获取日K线历史数据"""
    if not TDX_AVAILABLE:
        return _no_tdx_msg()

    f = _get_day_file(code)
    if not f:
        return f"❌ 未找到股票 {code} 的日线数据文件"

    records = _read_records(f, _parse_day_record, limit=count)
    if not records:
        return f"❌ {code} 日线数据为空"

    # 计算简单统计
    closes = [r["close"] for r in records if r.get("close")]
    summary = {}
    if closes:
        summary["close_min"] = min(closes)
        summary["close_max"] = max(closes)
        summary["close_avg"] = round(sum(closes) / len(closes), 2)
        summary["trend"] = "↑" if closes[-1] > closes[0] else "↓"

    return json.dumps({
        "code": code,
        "period": "日K",
        "count": len(records),
        "range": f"{records[0]['date']} ~ {records[-1]['date']}",
        "summary": summary,
        "records": records,
        "source": f"通达信本地 {f.name}",
    }, ensure_ascii=False, indent=2)


def tdx_kline_min(code: str, period: str = "1min", count: int = 240) -> str:
    """获取分钟K线数据（1min -> lc1, 5min -> lc5）"""
    if not TDX_AVAILABLE:
        return _no_tdx_msg()

    if period == "1min":
        f = _get_lc1_file(code)
        parser = _parse_lc1_record
    elif period == "5min":
        f = _get_lc5_file(code)
        parser = _parse_lc5_record
    else:
        return f"❌ 不支持的周期: {period}（支持 1min / 5min）"

    if not f:
        return f"❌ 未找到股票 {code} 的 {period} 分钟数据文件（需要通达信下载历史分钟数据）"

    records = _read_records(f, parser, limit=count)
    if not records:
        return f"❌ {code} {period} 分钟数据为空"

    # 简单统计
    closes = [r["close"] for r in records if r.get("close")]
    volumes = [r["volume"] for r in records if r.get("volume")]
    summary = {}
    if closes:
        summary["close_high"] = max(closes)
        summary["close_low"] = min(closes)
        summary["close_avg"] = round(sum(closes) / len(closes), 2)
        summary["avg_volume"] = round(sum(volumes) / len(volumes), 0) if volumes else 0

    return json.dumps({
        "code": code,
        "period": period,
        "count": len(records),
        "range": f"{records[0]['datetime']} ~ {records[-1]['datetime']}",
        "summary": summary,
        "records": records,
        "source": f"通达信本地 {f.name}",
    }, ensure_ascii=False, indent=2)


def tdx_search(keyword: str) -> str:
    """搜索股票代码或名称（从通达信数据目录推断）"""
    if not TDX_AVAILABLE:
        return _no_tdx_msg()

    code_only = keyword.strip()
    # 如果是6位数字，直接查有没有数据
    if code_only.isdigit() and len(code_only) == 6:
        for market, name_hint in [("sh", "沪市"), ("sz", "深市")]:
            f = VIPDOC / market / "lday" / f"{market}{code_only}.day"
            if f.exists():
                records = _read_records(f, _parse_day_record)
                latest = records[-1] if records else None
                return json.dumps({
                    "code": code_only,
                    "market": market,
                    "name": f"{name_hint}{code_only}",
                    "has_day": True,
                    "has_lc1": _get_lc1_file(code_only) is not None,
                    "has_lc5": _get_lc5_file(code_only) is not None,
                    "latest_date": latest["date"] if latest else "未知",
                    "latest_close": latest["close"] if latest else None,
                }, ensure_ascii=False, indent=2)
        return f"❌ 未找到股票 {code_only} 的数据"

    # 非数字 → 搜索所有 .day 文件（较慢，只搜名字）
    results = []
    for market in ["sh", "sz"]:
        lday_dir = VIPDOC / market / "lday"
        if not lday_dir.exists():
            continue
        for f in sorted(lday_dir.glob("*.day"))[:500]:
            code = f.stem[2:]  # sh600000.day → 600000
            results.append({"code": code, "market": market, "file": str(f.name)})

    if not results:
        return json.dumps({"error": "未找到任何股票数据，请先下载通达信本地数据"})

    return json.dumps({
        "keyword": keyword,
        "total_stocks": len(results),
        "note": "仅支持代码搜索（6位数字），名称搜索请使用腾讯API（qt.gtimg.cn）",
        "results": results[:50],
    }, ensure_ascii=False)


def _no_tdx_msg() -> str:
    return json.dumps({
        "error": "通达信数据目录未找到",
        "help": "请设置环境变量 TDX_HOME 指向通达信安装目录（如 D:/new_tdx），"
                "或确保通达信已安装在 D:/new_tdx、C:/new_tdx 等标准路径。",
        "paths_checked": [
            "D:/new_tdx", "C:/new_tdx", "E:/new_tdx",
            "D:/tdx", "C:/tdx", "D:/new_tdx_vip",
        ],
    }, ensure_ascii=False)


# ============ MCP 协议 ============

TOOLS = [
    {
        "name": "tdx_realtime",
        "description": "获取股票实时行情（日K线最新一根，含OHLCV，来自通达信本地数据）。零API成本。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "股票代码，6位数字（如 300418、600519）"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "tdx_kline_day",
        "description": "获取日K线历史数据（来自通达信本地 .day 文件）。适合趋势分析、缠论计算。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "股票代码"},
                "count": {"type": "integer", "default": 60, "description": "返回最近多少根K线"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "tdx_kline_min",
        "description": "获取分钟K线数据（1min/5min，来自通达信 .lc1/.lc5 文件）。适合VWAP、T+0策略。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "股票代码"},
                "period": {"type": "string", "enum": ["1min", "5min"], "default": "1min"},
                "count": {"type": "integer", "default": 240, "description": "返回最近多少根K线（1min: 240=4小时）"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "tdx_search",
        "description": "搜索股票代码，确认通达信本地是否有该股票的历史数据。支持6位数字代码搜索。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "6位股票代码（如 300418）"},
            },
            "required": ["keyword"],
        },
    },
]

HANDLERS = {
    "tdx_realtime": tdx_realtime,
    "tdx_kline_day": tdx_kline_day,
    "tdx_kline_min": tdx_kline_min,
    "tdx_search": tdx_search,
}


def handle_request():
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method", "")
        rid = req.get("id")

        if method == "initialize":
            respond(rid, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "tdx-bridge",
                    "version": "1.0.0",
                    "tdx_home": str(TDX_HOME) if TDX_HOME else "未找到",
                },
            })
        elif rid is None:
            continue
        elif method == "tools/list":
            respond(rid, {"tools": TOOLS})
        elif method == "tools/call":
            name = req["params"]["name"]
            args = req["params"].get("arguments", {})
            handler = HANDLERS.get(name)
            if handler:
                try:
                    result = handler(**args)
                except Exception as e:
                    result = f"❌ {name} 异常: {e}"
            else:
                result = f"未知工具: {name}"
            respond(rid, {"content": [{"type": "text", "text": result}]})
        else:
            respond(rid, {"error": f"unsupported method: {method}"})


def respond(rid, result):
    print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    handle_request()
