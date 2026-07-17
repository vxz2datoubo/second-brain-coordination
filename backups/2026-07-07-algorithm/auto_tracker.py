"""auto_tracker.py — 全自动追踪中枢 v2

一键四维分析: 量价剖面 + 供应测试 + CMF资金流 + 吸筹检测
用法: python auto_tracker.py 300418 [价格]
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quad_lens import quad_analysis, format_report
from behavioral_check import detect_biases, load_trades


def auto_full_report(code, price=None, high=None, low=None, open_p=None, prev=None):
    if price is None:
        from medallion.tdx_connector import TDXConnector
        tdx = TDXConnector(offline=True)
        quote = tdx.get_quote(code)
        if not quote or not quote.get("now"):
            return "无法获取实时数据"
        price = quote["now"]
        high = quote.get("high", price * 1.02)
        low = quote.get("low", price * 0.98)
        open_p = quote.get("open", price)
        prev = quote.get("pre_close", price)
    high = high or price * 1.02
    low = low or price * 0.98
    open_p = open_p or price
    prev = prev or price
    r = quad_analysis(code, price, high, low, open_p, prev)
    format_report(r)

    # 行为偏差检测
    trades = load_trades()
    if trades["trades"]:
        biases = detect_biases([price], [])
        if biases:
            print(f"  ┌─ 🧠 行为偏差检测 ──────────────────┐")
            for b in biases[:2]:
                print(f"  │ ⚠️ {b[0]} [{b[1]}]")
                print(f"  │   {b[2][:60]}")
                print(f"  │   来源: {b[3]}")
            print(f"  └──────────────────────────────────────┘")

    return r


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("code")
    p.add_argument("price", nargs="?", type=float, default=None)
    args = p.parse_args()
    auto_full_report(args.code, price=args.price)
