# -*- coding: utf-8 -*-
"""
系统初始化脚本
自动创建 data 目录，初始化槽位/风控状态
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live.slot_manager import SlotManager
from live.risk_controller import RiskController
from live.trade_logger import get_logger

def init_system():
    print("=== 自进化交易系统初始化 ===")
    
    # 槽位管理器
    sm = SlotManager()
    print(f"  槽位管理: OK")
    for code in ["300418", "300058"]:
        s = sm.get_status_summary(code)
        print(f"    {code}: 今日卖出{s['today_sold']}/3, 未回笼{s['open_count']}, "
              f"可开{'是' if s['can_open'] else '否'}")
    
    # 风控
    rc = RiskController()
    rc.reset_day()
    print(f"  风控状态: 重置完成")
    print(f"    熔断: {rc.state['is_circuit_break']} | "
          f"黑天鹅: {rc.state['is_black_swan']} | "
          f"降仓: {rc.state['reduced_slots']}")
    
    # 交易记录
    logger = get_logger()
    stats = logger.get_profit_stats(days=30)
    print(f"  历史统计(30天): {stats['total_trades']}笔, "
          f"胜率{stats['win_rate']}%, "
          f"总盈利{stats['total_profit']}元, "
          f"均笔{stats['avg_profit']}元")
    
    # 数据路径验证
    TDX_BASE = r"F:\tongdaxin\vipdoc"
    paths = {
        "深证日K": os.path.join(TDX_BASE, "sz", "lday", "sz300418.day"),
        "深证5分K": os.path.join(TDX_BASE, "sz", "fzline", "sz300418.lc5"),
    }
    print(f"  数据路径检查:")
    all_ok = True
    for name, path in paths.items():
        exists = os.path.exists(path)
        status = "OK" if exists else "MISSING"
        print(f"    {name}: {status}")
        if not exists:
            all_ok = False
    
    if all_ok:
        print(f"  所有数据路径就绪")
    else:
        print(f"  警告: 部分数据路径缺失，请检查通达信安装")
    
    print("")
    print("初始化完成，系统就绪")
    return True

if __name__ == "__main__":
    init_system()
