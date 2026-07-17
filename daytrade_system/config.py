"""
全局配置 — 波仔交易系统 v3

所有硬编码参数、路径、阈值集中管理
避免各模块重复定义
"""

import os

# ============================================================
# 数据路径
# ============================================================

TDX_BASE_SZ = r"F:\tongdaxin\vipdoc\sz"
TDX_BASE_SH = r"F:\tongdaxin\vipdoc\sh"
TDX_DAILY_SZ = os.path.join(TDX_BASE_SZ, "lday")
TDX_DAILY_SH = os.path.join(TDX_BASE_SH, "lday")
TDX_MIN5_SZ = os.path.join(TDX_BASE_SZ, "fzline")

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORK_DIR, "data")

# ============================================================
# 仓位管理
# ============================================================
POSITION_MAX_PCT_PER_TRADE = 0.05       # 单笔T仓上限（总资金%）
POSITION_MAX_DAILY_LOSS_PCT = 0.02      # 单日最大亏损（总资金%）
POSITION_MAX_CONSECUTIVE_LOSS = 2       # 连续亏损后降仓
POSITION_REDUCED_SLOTS = 1              # 降仓后槽位上限
POSITION_NORMAL_SLOTS = 3               # 正常槽位上限
POSITION_COOLDOWN_MINUTES = 30          # 卖出后禁手（分钟）

# ============================================================
# 止损参数
# ============================================================
STOP_LOSS_HARD_PCT = -0.02              # 硬止损：单笔亏损>2%无条件割
STOP_LOSS_TIME_MINUTES = 30             # 时间止损：持有>30分钟不盈利平推
STOP_LOSS_TREND_K_COUNT = 2             # 趋势止损：连续N根K破支撑
STOP_LOSS_CROSS_DAY_PCT = -0.02         # 跨日止损：与硬止损对齐（之前代码用-3.1%是bug）

# ============================================================
# 入场信号
# ============================================================
ENTRY_DIST_TO_RESISTANCE_MAX = 1.5      # 距压力带%以内判定为near
ENTRY_DIST_TO_RESISTANCE_HARD = 3.0     # 距压力带>%直接拒绝卖出
ENTRY_EFFICIENCY_MIN = 0.8              # 效率最低阈值
ENTRY_SCORE_THRESHOLD = 60              # 入场评分最低分

# ============================================================
# 量价效率
# ============================================================
EFF_HARD_THRESHOLD = 3.0                # 硬阻力阈值
EFF_MEDIUM_THRESHOLD = 1.5              # 中等阻力阈值
EFF_SOFT_THRESHOLD = 0.8               # 软阻力阈值
EFF_WINDOW_DAYS = 5                     # 效率计算窗口
EFF_WEIGHT_IN_SCORE = 0.6              # 效率在排名中的权重
EFF_DIST_WEIGHT_IN_SCORE = 0.4         # 距离在排名中的权重

# ============================================================
# 趋势判定 Engine A
# ============================================================
TREND_MA_FAST = 5
TREND_MA_MID = 10
TREND_MA_SLOW = 20
TREND_VOL_RATIO_HIGH = 1.5             # 放量阈值
TREND_VOL_RATIO_LOW = 0.6              # 缩量阈值
TREND_CONSECUTIVE_DAYS = 3             # 连阳/连阴天数触发信号

# ============================================================
# 日线分析
# ============================================================
DAILY_UPPER_SHADOW_WARN = 30            # 长上影%警告
DAILY_LOWER_SHADOW_WARN = 30            # 长下影%警告

# ============================================================
# 回测参数
# ============================================================
BACKTEST_SLIPPAGE = 0.001               # 滑点0.1%
BACKTEST_MIN_PROFIT_TARGET = 0.015      # 最小盈利目标1.5%
BACKTEST_MAX_HOLD_BARS = 48             # 最大持有48根5分钟K
BACKTEST_COMMISSION = 0.00025           # 佣金+印花税约万分之2.5

# ============================================================
# 股票池
# ============================================================
STOCKS = {
    "300418": {"name": "昆仑万维", "peer_codes": ["002230", "601360"]},
    "300058": {"name": "蓝色光标", "peer_codes": ["002027", "002400"]},
}

# ============================================================
# 换手率阈值
# ============================================================
TURNOVER_THRESHOLDS = {
    "300418": {"very_low": 2.0, "low": 4.0, "normal": 8.0, "high": 15.0},
    "300058": {"very_low": 1.0, "low": 3.0, "normal": 6.0, "high": 12.0},
}

# 流通股本(万股) — 用于历史换手率推算
LTGB = {"300418": 117532, "300058": 347793}

# ============================================================
# 熔断/极端行情
# ============================================================
MELTDOWN_DAILY_LOSS_PCT = 0.02          # 日亏2%触发熔断
LIMIT_UP_PCT = 0.095                    # 涨停板（±10%但实际到9.5%就开始计算）
LIMIT_DOWN_PCT = -0.095
CIRCUIT_BREAKER_ENABLED = True
