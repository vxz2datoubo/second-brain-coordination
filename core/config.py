# A股进化交易系统核心
import json
import os
from datetime import datetime, date
from pathlib import Path

BASE = Path(r'F:\aidanao')
BRAIN = BASE / 'second-brain'
KNOWLEDGE = BASE / 'knowledge'
LOGS = BASE / 'core' / 'logs'
LOGS.mkdir(parents=True, exist_ok=True)

STOCKS = {
    'kunlun': {'code': '300418', 'name': '昆仑', 'priority': 1, 'ratio': 0.6},
    'lanbiao': {'code': '300058', 'name': '蓝标', 'priority': 2, 'ratio': 0.4},
}

TRADING = {
    'min_amount': 10000,
    'max_position_pct': 0.035,
    'max_open_trades': 3,
    'daily_pnl_target': 5000,
    'profit_target': 0.03,
    'loss_cut': 0.07,
}

class Config:
    pass

Config.STOCKS = STOCKS
Config.TRADING = TRADING
Config.BASE = BASE
Config.BRAIN = BRAIN
Config.KNOWLEDGE = KNOWLEDGE
Config.LOGS = LOGS
