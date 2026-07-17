"""
交易记录器 — 记录每笔交易，存入 JSON
供自进化层回测和参数调优使用
"""

import json
import os
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORK_DIR, "data")
TRADE_LOG_FILE = os.path.join(DATA_DIR, "trade_log.json")
PARAM_HISTORY_FILE = os.path.join(DATA_DIR, "param_history.json")


@dataclass
class TradeRecord:
    """单笔交易记录"""
    date: str
    stock: str
    stock_name: str
    direction: str          # "倒T" / "正T"
    # 卖出
    short_time: str
    short_price: float
    short_shares: int
    short_amount: float
    # 接回
    cover_time: Optional[str] = None
    cover_price: Optional[float] = None
    cover_shares: Optional[int] = None
    # 盈亏
    profit_pct: float = 0.0
    profit_abs: float = 0.0
    # 信号
    signal_score: int = 0
    confidence: str = "C"
    regime: str = "unknown"
    time_window: str = "T0"
    reasons: str = ""
    # 元数据
    is_cross_day: bool = False
    execution_type: str = "signal"  # "signal" / "manual" / "forced"
    # 信号因子详情
    signal_factors: str = ""         # JSON 字符串
    slot_id: int = -1
    created_at: str = ""


class TradeLogger:
    """
    交易记录器，持久化到 JSON
    支持按日期、按股票查询
    """

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.records: List[TradeRecord] = []
        self._load()

    def _load(self):
        if os.path.exists(TRADE_LOG_FILE):
            try:
                with open(TRADE_LOG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.records = [TradeRecord(**r) for r in data]
            except Exception:
                self.records = []

    def _save(self):
        data = [asdict(r) for r in self.records]
        with open(TRADE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def log_open(self, record: TradeRecord):
        """记录开仓"""
        record.created_at = datetime.now().isoformat()
        self.records.append(record)
        self._save()

    def log_cover(self, trade_id: int, cover_price: float, cover_shares: int = None,
                   cover_time: str = None):
        """更新记录，补充接回信息"""
        if 0 <= trade_id < len(self.records):
            r = self.records[trade_id]
            r.cover_price = cover_price
            r.cover_shares = cover_shares or r.short_shares
            r.cover_time = cover_time or datetime.now().strftime("%H:%M:%S")
            r.profit_pct = round((r.short_price - cover_price) / r.short_price * 100, 4)
            r.profit_abs = round((r.short_price - cover_price) * r.short_shares, 2)
            self._save()

    def get_records(self,
                    stock: str = None,
                    start_date: str = None,
                    end_date: str = None,
                    direction: str = None) -> List[TradeRecord]:
        """按条件查询记录"""
        result = self.records
        if stock:
            result = [r for r in result if r.stock == stock]
        if start_date:
            result = [r for r in result if r.date >= start_date]
        if end_date:
            result = [r for r in result if r.date <= end_date]
        if direction:
            result = [r for r in result if r.direction == direction]
        return result

    def get_recent_records(self, n: int = 20, stock: str = None) -> List[TradeRecord]:
        """获取最近 N 条记录"""
        records = self.get_records(stock=stock)
        return records[-n:]

    def get_profit_stats(self, stock: str = None, days: int = 30) -> Dict:
        """统计最近 N 天的盈利情况"""
        from datetime import timedelta
        start_date = (date.today() - timedelta(days=days)).isoformat()
        records = self.get_records(stock=stock, start_date=start_date)

        completed = [r for r in records if r.cover_price is not None]
        total_profit = sum(r.profit_abs for r in completed)
        win_count = sum(1 for r in completed if r.profit_abs > 0)
        loss_count = len(completed) - win_count
        win_rate = win_count / len(completed) if completed else 0

        # 按置信度分组统计
        conf_stats = {}
        for conf in ["A++", "A", "B", "C", "D"]:
            conf_records = [r for r in completed if r.confidence == conf]
            if conf_records:
                conf_profit = sum(r.profit_abs for r in conf_records)
                conf_stats[conf] = {
                    "count": len(conf_records),
                    "win_count": sum(1 for r in conf_records if r.profit_abs > 0),
                    "avg_profit": conf_profit / len(conf_records),
                    "total_profit": round(conf_profit, 2),
                }

        # 按时间窗口分组
        window_stats = {}
        for w in ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]:
            w_records = [r for r in completed if r.time_window == w]
            if w_records:
                w_profit = sum(r.profit_abs for r in w_records)
                window_stats[w] = {
                    "count": len(w_records),
                    "avg_profit": w_profit / len(w_records),
                    "total_profit": round(w_profit, 2),
                }

        # 按市场状态分组
        regime_stats = {}
        for reg in ["TREND_UP", "TREND_DOWN", "HIGH_VOL_RANGE", "LOW_VOL_RANGE", "EXTREME"]:
            r_records = [r for r in completed if r.regime == reg]
            if r_records:
                r_profit = sum(r.profit_abs for r in r_records)
                regime_stats[reg] = {
                    "count": len(r_records),
                    "avg_profit": r_profit / len(r_records),
                    "total_profit": round(r_profit, 2),
                }

        return {
            "period": f"最近{days}天",
            "total_trades": len(completed),
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": round(win_rate * 100, 2),
            "total_profit": round(total_profit, 2),
            "avg_profit": round(total_profit / len(completed), 4) if completed else 0,
            "by_confidence": conf_stats,
            "by_time_window": window_stats,
            "by_regime": regime_stats,
        }

    def get_signal_correlation(self, days: int = 30) -> Dict:
        """分析信号分与盈利的相关性"""
        from datetime import timedelta
        start_date = (date.today() - timedelta(days=days)).isoformat()
        records = self.get_records(start_date=start_date)
        completed = [r for r in records if r.cover_price is not None]

        if len(completed) < 5:
            return {"note": "样本不足，需要至少5笔交易"}

        # 离散化信号分
        buckets = {"低(0-59)": [], "中(60-74)": [], "高(75-89)": [], "极高(90+)": []}
        for r in completed:
            if r.signal_score < 60:
                buckets["低(0-59)"].append(r.profit_abs)
            elif r.signal_score < 75:
                buckets["中(60-74)"].append(r.profit_abs)
            elif r.signal_score < 90:
                buckets["高(75-89)"].append(r.profit_abs)
            else:
                buckets["极高(90+)"].append(r.profit_abs)

        result = {}
        for label, profits in buckets.items():
            if profits:
                result[label] = {
                    "count": len(profits),
                    "win_rate": sum(1 for p in profits if p > 0) / len(profits) * 100,
                    "avg_profit": sum(profits) / len(profits),
                    "total_profit": round(sum(profits), 2),
                }
            else:
                result[label] = {"count": 0}

        return result

    def export_records(self, filepath: str = None, stock: str = None, days: int = None) -> str:
        """导出记录到文件"""
        records = self.get_records(stock=stock)
        if days:
            from datetime import timedelta
            start_date = (date.today() - timedelta(days=days)).isoformat()
            records = [r for r in records if r.date >= start_date]

        filepath = filepath or os.path.join(DATA_DIR, f"trade_export_{date.today().isoformat()}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)
        return filepath


# 全局单例
_logger: Optional[TradeLogger] = None

def get_logger() -> TradeLogger:
    global _logger
    if _logger is None:
        _logger = TradeLogger()
    return _logger
