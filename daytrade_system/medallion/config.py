"""medallion config — 大奖章级倒T系统 · 全局参数配置
设计原则：少做做精、严格止损、两只股票深度定制
"""

from dataclasses import dataclass
from typing import Dict

# ============================================================
# 全局约束（用户硬约束，不可改）
# ============================================================
GLOBAL_MAX_SELL_PER_DAY   = 3
GLOBAL_MAX_BUY_PER_DAY    = 3
GLOBAL_MAX_TOTAL_SLOTS    = 3
GLOBAL_AMOUNT_PER_TRADE   = 5000
GLOBAL_ALLOW_CROSS_DAY    = True

# ============================================================
# 股票配置
# ============================================================
@dataclass
class StockConfig:
    code: str
    name: str
    style: str                      # "counter"=逆势抄底(蓝) / "trend"=趋势跟随(昆)
    entry_score_threshold: float    # 开仓最低分
    b_entry_threshold: float        # B级门槛
    hard_stop_loss_pct: float       # 硬止损%
    flee_stop_pct: float           # 飞逃止损%
    time_stop_minutes: int          # 时间止损（分钟）
    min_profit_take_pct: float      # 最低止盈%
    greedy_profit_pct: float        # 贪心止盈%
    f1_vwap_weight: float
    f2_rsi_weight: float
    f3_volprofile_weight: float
    f4_momentum_weight: float
    f5_delta_weight: float
    f6_gap_weight: float
    max_trades_per_day: int
    require_intraday_high_pct: float
    allow_long_t: bool
    avg_price: float
    typical_atr_pct: float

STOCK_CONFIGS: Dict[str, StockConfig] = {
    "300418": StockConfig(code="300418", name="昆仑万维", style="trend",
        entry_score_threshold=35.0,
        b_entry_threshold=25.0,
        hard_stop_loss_pct=-1.0,
        flee_stop_pct=+2.0,
        time_stop_minutes=40,
        min_profit_take_pct=0.3,
        greedy_profit_pct=0.6,
        f1_vwap_weight=0.25, f2_rsi_weight=0.20, f3_volprofile_weight=0.20,
        f4_momentum_weight=0.12, f5_delta_weight=0.13, f6_gap_weight=0.10,
        max_trades_per_day=2,
        require_intraday_high_pct=0.8,
        allow_long_t=False,
        avg_price=0.00015, typical_atr_pct=3.5,
    ),
    "300058": StockConfig(
        code="300058", name="蓝色光标", style="counter",
        entry_score_threshold=40.0,
        b_entry_threshold=30.0,
        hard_stop_loss_pct=-1.0,
        flee_stop_pct=+2.0,
        time_stop_minutes=50,
        min_profit_take_pct=0.4,
        greedy_profit_pct=0.8,
        f1_vwap_weight=0.30, f2_rsi_weight=0.20, f3_volprofile_weight=0.15,
        f4_momentum_weight=0.15, f5_delta_weight=0.10, f6_gap_weight=0.10,
        max_trades_per_day=2,
        require_intraday_high_pct=0.5,
        allow_long_t=False,
        avg_price=0.00015, typical_atr_pct=3.0,
    ),
}

# ============================================================
# 置信度等级
# ============================================================
@dataclass
class ConfidenceLevel:
    grade: str
    min_score: float
    action: str
    limit_per_day: int

CONF_LEVELS = [
    ConfidenceLevel("A++", 90, "立即执行，立即挂限价单", 1),
    ConfidenceLevel("A",   75, "正常执行，等回调0.3%再挂", 1),
    ConfidenceLevel("B",   60, "可执行，限额1笔/天", 1),
    ConfidenceLevel("C",   45, "仅备选，谨慎执行", 0),
    ConfidenceLevel("D",    0, "不执行", 0),
]

def get_confidence(score: float) -> ConfidenceLevel:
    for c in CONF_LEVELS:
        if score >= c.min_score:
            return c
    return CONF_LEVELS[-1]

# ============================================================
# 市场状态参数
# ============================================================
REGIME_PARAMS = {
    "TREND_UP":       {"entry_mult": 1.3, "allow_new": True,  "prefer_exit": True,  "max_slots": 2},
    "TREND_DOWN":     {"entry_mult": 0.9, "allow_new": True,  "prefer_exit": False, "max_slots": 3},
    "HIGH_VOL_RANGE": {"entry_mult": 1.0, "allow_new": True,  "prefer_exit": False, "max_slots": 3},
    "LOW_VOL_RANGE":  {"entry_mult": 1.5, "allow_new": True,  "prefer_exit": True,  "max_slots": 1},
    "EXTREME":        {"entry_mult": 99,  "allow_new": False, "prefer_exit": True,  "max_slots": 0},
}

# ============================================================
# 时间窗口参数
# ============================================================
@dataclass
class TimeWindow:
    id: str; start: str; end: str; priority: int
    allow_new_entry: bool; prefer_exit: bool; notes: str

TIME_WINDOWS = [
    TimeWindow("T1","09:30","09:50",2,False,True, "开盘处理：优先接回跨日仓位"),
    TimeWindow("T2","09:50","10:30",1,True, False,"黄金窗口：方向确认后执行首笔倒T"),
    TimeWindow("T3","10:30","11:00",3,True, False,"上午延续：继续看倒T机会"),
    TimeWindow("T4","11:00","11:30",5,False,True, "谨慎期：除非强信号，否则等待"),
    TimeWindow("T5","13:00","13:30",3,True, False,"下午重启：观察下午是否有新方向"),
    TimeWindow("T6","13:30","14:00",1,True, False,"下午黄金窗口：最易出倒T机会"),
    TimeWindow("T7","14:00","14:30",2,True, True, "尾盘决策：判断当天是否还有T仓机会"),
    TimeWindow("T8","14:30","15:00",4,False,True, "强制收尾：所有未接回的T仓全部强平"),
]

def current_window(now_str: str) -> TimeWindow:
    """根据当前时间字符串'HH:MM'返回对应窗口"""
    for w in sorted(TIME_WINDOWS, key=lambda x: x.priority):
        if w.start <= now_str <= w.end:
            return w
    return TIME_WINDOWS[-1]  # 默认返回T8

# ============================================================
# 风控规则
# ============================================================
RISK_RULES = [
    ("硬止损",      "单笔亏损>1.0%",       "无条件平仓",      "hard"),
    ("飞逃止损",    "卖后继续涨>2.0%",     "立即接回止损",    "hard"),
    ("熔断",        "每日累计>2.0%",        "全天停止",        "hard"),
    ("冷却期",      "卖出后30分钟",         "不能再次卖出",    "soft"),
    ("连亏降仓",    "连亏2笔",             "降为1个槽",       "soft"),
    ("时间止损",    "持有超40/50分钟",     "强制平仓",        "hard"),
    ("极端行情",    "Regime=EXTREME",      "所有T仓平掉",     "hard"),
    ("信号消失",    "卖出后信号由A降至D",  "取消未成交单",    "soft"),
    ("尾盘强平",    "14:50前未接回",       "强制接回",        "hard"),
    ("黑天鹅",      "跌破20日线8%",        "立即平所有T仓",   "hard"),
]

# ============================================================
# 组合配置
# ============================================================
PORTFOLIO = {
    "kunlun_capital_ratio": 0.60,
    "blue_capital_ratio":   0.40,
    "slot_priority_kunlun": 1,
    "slot_priority_blue":    2,
}

# ============================================================
# 回测配置
# ============================================================
BACKTEST = {
    "slippage": 0.001,
    "commission": 0.00025,
    "lookback_daily": 20,
    "lookback_min5": 5,
}
