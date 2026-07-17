"""tdx_connector.py — 通达信MCP连接封装

连接 WorkBuddy 桥接的 TDX MCP 服务，封装以下能力：
  - 实时行情 tdx_quotes
  - 分时K线 tdx_kline
  - 新闻查询 wenda_news_query
  - 公告查询 wenda_notice_query

脱接设计：没有MCP时降级到本地二进制文件读取，
保证回测和模拟运行正常。
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, date
import struct

# ---- MCP客户端（通过WorkBuddy的MCP桥接） -----------------
# 如果 MCP 可用，导入桥接层；否则降级
try:
    from mcp.client import ClientSession
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False


# ============================================================
# 内部数据访问（降级模式）
# ============================================================

def _read_tdx_day(code: str, market: str = "sz") -> List[Dict]:
    """直接读通达信二进制日K"""
    path = rf"F:\tongdaxin\vipdoc\{market}\lday\{market}{code}.day"
    if not os.path.exists(path):
        return []

    with open(path, "rb") as f:
        data = f.read()

    bars = []
    for i in range(len(data) // 32):
        off = i * 32
        u = struct.unpack_from("<IIIIIfII", data, off)
        date_int = u[0]
        if date_int < 20000000:
            continue
        bars.append({
            "date": str(date_int),
            "open":  u[1] / 100.0,
            "high":  u[2] / 100.0,
            "low":   u[3] / 100.0,
            "close": u[4] / 100.0,
            "amount": u[5],
            "volume": u[6],
        })
    return bars


def _read_tdx_min5(code: str, market: str = "sz",
                    start_date: str = None, limit: int = None) -> List[Dict]:
    """直接读通达信二进制5分K"""
    path = rf"F:\tongdaxin\vipdoc\{market}\fzline\{market}{code}.lc5"
    if not os.path.exists(path):
        return []

    def unpack_date(w: int) -> str:
        y = (w // 2048) + 2004
        md = w % 2048
        m, d = md // 100, md % 100
        return f"{y:04d}{m:02d}{d:02d}"

    with open(path, "rb") as f:
        data = f.read()

    bars = []
    for i in range(len(data) // 32):
        off = i * 32
        u = struct.unpack_from("<HHfffffIHH", data, off)
        dw, minute = u[0], u[1]
        o, h, l, c = u[2], u[3], u[4], u[5]
        amt, vol = u[6], u[7]
        up, dn = u[8], u[9]

        ds = unpack_date(dw)
        if ds.startswith("1970") or o == 0:
            continue
        if start_date and ds < start_date:
            continue

        sec = minute * 60
        hh, mm = divmod(minute, 60)
        bars.append({
            "date": ds,
            "time_sec": sec,
            "time_str": f"{hh:02d}:{mm:02d}",
            "open": o, "high": h, "low": l, "close": c,
            "amount": amt, "volume": vol,
            "up_count": up, "down_count": dn,
        })

    if limit and len(bars) > limit:
        bars = bars[-limit:]
    return bars


# ============================================================
# TDX连接器主类
# ============================================================

class TDXConnector:
    """
    通达信数据连接器

    用法（生产/实时模式）：
      conn = TDXConnector(mcp_server="https://txmcp.tdx.com.cn:3001/txmcp")
      quote = conn.get_quote("300418")

    用法（回测/离线模式）：
      conn = TDXConnector(offline=True)
      daily = conn.get_daily("300418", limit=120)
      min5  = conn.get_min5("300418", date="20260601", limit=100)
    """

    def __init__(self, mcp_server: str = None, offline: bool = False):
        self.mcp_server = mcp_server
        self.offline = offline
        self._session = None

    # ----------------------------------------------------------
    # 实时行情
    # ----------------------------------------------------------

    def get_quote(self, code: str) -> Optional[Dict]:
        """
        获取单只股票实时行情
        返回: {code, name, now, open, high, low, pre_close,
              volume, amount, up_count, down_count, ...}
        """
        if self.offline:
            return self._offline_quote(code)

        if not _MCP_AVAILABLE:
            return self._offline_quote(code)

        # TODO: 通过MCP调用
        # async def _fetch():
        #     async with ClientSession(self.mcp_server) as s:
        #         return await s.call_tool("tdx_quotes",
        #             {"codes": [code], "fields": [...]})
        return self._offline_quote(code)

    def get_quotes(self, codes: List[str]) -> List[Dict]:
        """批量获取实时行情"""
        return [q for c in codes if (q := self.get_quote(c))]

    def _offline_quote(self, code: str) -> Dict:
        """从今日分时数据构建伪实时行情"""
        today = datetime.now().strftime("%Y%m%d")
        bars = _read_tdx_min5(code, limit=100)
        today_bars = [b for b in bars if b["date"] == today]

        if not today_bars:
            # 取最近一根日K
            days = _read_tdx_day(code)
            if not days:
                return {}
            d = days[-1]
            return {
                "code": code,
                "name": _CODE_NAMES.get(code, code),
                "now": d["close"],
                "open": d["open"],
                "high": d["high"],
                "low": d["low"],
                "pre_close": days[-2]["close"] if len(days) >= 2 else d["close"],
                "volume": d["volume"],
                "amount": d["amount"],
            }

        first = today_bars[0]
        last = today_bars[-1]
        prev = _read_tdx_day(code)
        pre_close = prev[-2]["close"] if len(prev) >= 2 else first["open"]

        return {
            "code": code,
            "name": _CODE_NAMES.get(code, code),
            "now": last["close"],
            "open": first["open"],
            "high": max(b["high"] for b in today_bars),
            "low":  min(b["low"]  for b in today_bars),
            "pre_close": pre_close,
            "volume": sum(b["volume"] for b in today_bars),
            "amount": sum(b["amount"] for b in today_bars),
        }

    # ----------------------------------------------------------
    # K线数据
    # ----------------------------------------------------------

    def get_daily(self, code: str, days: int = 120) -> List[Dict]:
        """获取日K线（最近N天）"""
        bars = _read_tdx_day(code)
        return bars[-days:] if bars else []

    def get_min5(self, code: str, date: str = None,
                 limit: int = 200) -> List[Dict]:
        """
        获取5分K线
        date=None  → 今天
        date="20260601" → 指定日期
        """
        bars = _read_tdx_min5(code, limit=9999)
        if date:
            bars = [b for b in bars if b["date"] == date]
        return bars[-limit:] if bars else []

    def get_today_min5(self, code: str) -> List[Dict]:
        """获取今日5分K（实时）"""
        today = datetime.now().strftime("%Y%m%d")
        return self.get_min5(code, date=today, limit=300)

    # ----------------------------------------------------------
    # 新闻/公告（仅实时模式）
    # ----------------------------------------------------------

    def get_news(self, keyword: str = "AI",
                 category: str = "题材",
                 hours: int = 24) -> List[Dict]:
        """获取关联新闻"""
        if self.offline or not _MCP_AVAILABLE:
            return []

        # TODO: 通过MCP调用 wenda_news_query
        return []

    def get_notices(self, code: str,
                    days: int = 7) -> List[Dict]:
        """获取公告"""
        if self.offline or not _MCP_AVAILABLE:
            return []
        # TODO: 通过MCP调用 wenda_notice_query
        return []

    # ----------------------------------------------------------
    # 辅助
    # ----------------------------------------------------------

    def get_prev_close(self, code: str) -> float:
        """获取前收盘"""
        days = self.get_daily(code, days=3)
        return days[-2]["close"] if len(days) >= 2 else 0.0

    def get_recent_closes(self, code: str, n: int = 20) -> List[float]:
        """获取最近N日收盘价列表"""
        bars = self.get_daily(code, days=n + 2)
        return [b["close"] for b in bars[-n-1:-1]] if len(bars) > n else []


# ============================================================
# 股票代码映射
# ============================================================

_CODE_NAMES = {
    "300418": "蓝色光标",
    "300058": "昆仑万维",
}


# ============================================================
# 快速测试
# ============================================================

if __name__ == "__main__":
    conn = TDXConnector(offline=True)

    for code in ["300418", "300058"]:
        q = conn.get_quote(code)
        print(f"{q['name']}({code}): 现价={q['now']:.4f} 涨跌="
              f"{(q['now']/q['pre_close']-1)*100:+.2f}%")

    # 测试日K
    d = conn.get_daily("300418", days=5)
    print("日K最近5天:", [(x["date"], x["close"]) for x in d])
