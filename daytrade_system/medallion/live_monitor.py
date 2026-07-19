"""
live_monitor.py — 大奖章实时盯盘系统 v1.0

系统架构:
  1. signal_generator.py   - 实时信号生成（从TDX数据）
  2. app.py              - Web仪表盘（显示信号+持仓）
  3. sentiment_monitor.py - 板块情绪监测
  4. live_runner.py       - 启动入口

启动方式:
  python live_monitor.py
  然后打开 http://localhost:8767

设计原则:
  - 系统输出信号，人工最终决策
  - 不做自动下单，只做人能看懂的信号
  - 信号包含：卖出价、接回价、止损价、置信度、建议理由
"""

import os, sys, json, time
from datetime import datetime
from pathlib import Path

# ========== 信号生成器 ==========
class SignalGenerator:
    """基于分时数据生成T仓信号"""
    
    CODES = {
        "300418": {"name": "蓝色光标", "style": "counter", "entry_thresh": 50, "weight": 2},
        "300058": {"name": "昆仑万维", "style": "trend",   "entry_thresh": 40, "weight": 3},
    }
    
    def __init__(self):
        self.signals = {}  # code -> Signal
        self.positions = {}  # code -> {sell_price, sell_time, slot_id}
        self.daily_stats = {}  # code -> {sells_today, buys_today, pnl}
        self.max_per_day = 3
        
        for code in self.CODES:
            self.positions[code] = []
            self.daily_stats[code] = {"sells": 0, "buys": 0, "pnl": 0.0, "trades": []}
    
    def load_tdx_data(self, code: str):
        """从TDX二进制文件加载数据"""
        import struct
        
        market = "sz" if code.startswith(("0", "3")) else "sh"
        day_path = rf"F:\tongdaxin\vipdoc\{market}\lday\{market}{code}.day"
        min5_path = rf"F:\tongdaxin\vipdoc\{market}\fzline\{market}{code}.lc5"
        
        # 读日K
        daily = []
        if os.path.exists(day_path):
            with open(day_path, "rb") as f:
                data = f.read()
            for i in range(len(data) // 32):
                u = struct.unpack_from("<IIIIIfII", data, i*32)
                date_int = u[0]
                if date_int < 20000000: continue
                daily.append({
                    "date": str(date_int),
                    "open": u[1]/100, "high": u[2]/100,
                    "low": u[3]/100, "close": u[4]/100,
                    "volume": u[6],
                })
        
        # 读5分K
        min5 = []
        if os.path.exists(min5_path):
            def unpack_date(w):
                y = (w // 2048) + 2004
                md = w % 2048
                m, d = md // 100, md % 100
                return f"{y:04d}{m:02d}{d:02d}"
            
            with open(min5_path, "rb") as f:
                data = f.read()
            for i in range(len(data) // 32):
                u = struct.unpack_from("<HHfffffIHH", data, i*32)
                dw, minute = u[0], u[1]
                ds = unpack_date(dw)
                if ds.startswith("1970") or u[2] == 0: continue
                
                sec = minute * 60
                bars = {
                    "date": ds, "time_sec": sec,
                    "open": u[2], "high": u[3], "low": u[4], "close": u[5],
                    "volume": u[7],
                }
                min5.append(bars)
        
        return daily, min5
    
    def calc_indicators(self, min5_bars: list, daily_bars: list):
        """计算分时指标"""
        if not min5_bars:
            return {}
        
        now_bar = min5_bars[-1]
        price = now_bar["close"]
        
        # 当日VWAP
        total_vol = sum(b["volume"] for b in min5_bars)
        vwap = sum(b["close"] * b["volume"] for b in min5_bars) / max(total_vol, 1)
        
        # 距VWAP偏离
        vwap_dev = (price - vwap) / vwap * 100 if vwap > 0 else 0
        
        # 日内高点
        day_high = max(b["high"] for b in min5_bars)
        day_low = min(b["low"] for b in min5_bars)
        
        # 从高点回撤
        pullback = (day_high - price) / day_high * 100 if day_high > 0 else 0
        
        # 分时均线
        ma_list = [5, 10, 20]
        ma_values = {}
        for n in ma_list:
            if len(min5_bars) >= n:
                ma = sum(b["close"] for b in min5_bars[-n:]) / n
                ma_values[f"ma{n}"] = ma
                ma_values[f"ma{n}_dev"] = (price - ma) / ma * 100
        
        # RSI (简化)
        if len(min5_bars) >= 14:
            gains = [max(0, min5_bars[i]["close"] - min5_bars[i-1]["close"]) for i in range(1, len(min5_bars))]
            losses = [max(0, min5_bars[i-1]["close"] - min5_bars[i]["close"]) for i in range(1, len(min5_bars))]
            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            rs = avg_gain / max(avg_loss, 0.001)
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # 最近N分钟涨跌
        recent = min5_bars[-6:] if len(min5_bars) >= 6 else min5_bars
        recent_change = (recent[-1]["close"] - recent[0]["open"]) / recent[0]["open"] * 100 if recent else 0
        
        # 昨日收盘
        prev_close = daily_bars[-2]["close"] if len(daily_bars) >= 2 else price
        
        return {
            "price": price,
            "vwap": vwap,
            "vwap_dev": vwap_dev,
            "day_high": day_high,
            "day_low": day_low,
            "pullback": pullback,
            "rsi": rsi,
            "recent_change": recent_change,
            "prev_close": prev_close,
            **ma_values,
        }
    
    def generate_signal(self, code: str, indicators: dict, current_time: str = None) -> dict:
        """生成T仓信号"""
        cfg = self.CODES[code]
        price = indicators.get("price", 0)
        if price <= 0:
            return {"code": code, "name": cfg["name"], "status": "no_data"}
        
        sig = {
            "code": code, "name": cfg["name"],
            "price": round(price, 3),
            "time": current_time or datetime.now().strftime("%H:%M"),
            "signals": [],
            "scores": {},
            "recommendation": "观望",
            "confidence": 0,
            "sell_target": None,
            "buy_target": None,
            "stop_loss": None,
            "reason": "",
            "status": "watch",
        }
        
        h, m = int((current_time or "09:30").split(":")[0]), int((current_time or "09:30").split(":")[1])
        mins = h * 60 + m
        
        # === 卖出信号评估 ===
        sell_score = 0
        reasons = []
        
        # F1: VWAP偏离 (蓝色逆势/昆仑趋势)
        vwap_dev = indicators.get("vwap_dev", 0)
        if vwap_dev > 0.5:
            score = min(40, vwap_dev * 20)
            sell_score += score * 0.3
            reasons.append(f"VWAP偏离+{vwap_dev:.2f}%")
        
        # F2: RSI超买
        rsi = indicators.get("rsi", 50)
        if rsi > 70:
            score = min(40, (rsi - 70) * 2)
            sell_score += score * 0.2
            reasons.append(f"RSI={rsi:.0f}超买")
        elif rsi > 65:
            sell_score += 10 * 0.2
            reasons.append(f"RSI={rsi:.0f}偏高")
        
        # F3: 从高点回撤 (至少0.5%回撤才考虑卖)
        pullback = indicators.get("pullback", 0)
        if pullback >= 0.5:
            score = min(30, pullback * 15)
            sell_score += score * 0.15
            reasons.append(f"高点回撤{pullback:.2f}%")
        
        # F4: 价格高于均线
        ma5_dev = indicators.get("ma5_dev", 0)
        ma20_dev = indicators.get("ma20_dev", 0)
        if ma5_dev > 0.3:
            sell_score += min(20, ma5_dev * 20) * 0.15
            reasons.append(f"MA5偏离+{ma5_dev:.2f}%")
        
        # F5: 近期涨幅
        recent = indicators.get("recent_change", 0)
        if recent > 0.5:
            sell_score += min(20, recent * 10) * 0.1
            reasons.append(f"5分K涨+{recent:.2f}%")
        
        # === 接回信号评估 ===
        buy_score = 0
        buy_reasons = []
        
        if vwap_dev < -0.5:
            buy_score += min(30, abs(vwap_dev) * 15) * 0.3
            buy_reasons.append(f"VWAP偏离{vwap_dev:.2f}%")
        
        if pullback >= 1.0:
            buy_score += min(30, pullback * 10) * 0.2
            buy_reasons.append(f"回撤{pullback:.1f}%")
        
        if rsi < 35:
            buy_score += min(30, (35 - rsi) * 2) * 0.2
            buy_reasons.append(f"RSI={rsi:.0f}超卖")
        
        # === 置信度 ===
        if sell_score >= 60:
            sig["confidence"] = "A++"
        elif sell_score >= 45:
            sig["confidence"] = "A"
        elif sell_score >= 30:
            sig["confidence"] = "B"
        elif sell_score >= 20:
            sig["confidence"] = "C"
        else:
            sig["confidence"] = "D"
        
        sig["scores"]["sell"] = round(sell_score, 1)
        sig["scores"]["buy"] = round(buy_score, 1)
        
        # === 生成建议 ===
        sell_threshold = cfg["entry_thresh"]
        
        # 检查是否已有T仓持仓
        pos = self.positions[code]
        open_slots = len(pos)
        
        if open_slots > 0:
            # 有持仓：检查是否该接回
            best_pos = max(pos, key=lambda x: x["sell_price"])
            entry_price = best_pos["sell_price"]
            
            # 接回条件：价格 <= 卖出价 * 0.999
            if price <= entry_price * 0.999:
                sig["recommendation"] = "接回"
                sig["buy_target"] = round(price, 3)
                sig["sell_target"] = round(entry_price, 3)
                sig["reason"] = f"价格{price:.3f}已低于卖出价{entry_price:.3f}，可接回"
                sig["status"] = "buy_signal"
            elif price <= entry_price:
                sig["recommendation"] = "关注接回"
                sig["buy_target"] = round(entry_price * 0.999, 3)
                sig["sell_target"] = round(entry_price, 3)
                sig["reason"] = f"接近接回价，需等{((entry_price - price)/entry_price*100):.2f}%回落"
                sig["status"] = "watch"
            else:
                # 亏损中
                loss_pct = (price - entry_price) / entry_price * 100
                sig["recommendation"] = "持仓观察"
                sig["sell_target"] = round(entry_price, 3)
                sig["stop_loss"] = round(entry_price * 1.01, 3)  # 1%止损
                sig["reason"] = f"浮亏{loss_pct:+.2f}%，不追加"
                sig["status"] = "holding"
        else:
            # 无持仓：检查是否该卖出
            stats = self.daily_stats[code]
            
            if stats["sells"] >= self.max_per_day:
                sig["recommendation"] = "今日额度用完"
                sig["reason"] = f"已卖{stats['sells']}笔，等待接回"
                sig["status"] = "no_quota"
            elif sell_score >= sell_threshold and pullback >= 0.3:
                sig["recommendation"] = "建议卖出"
                sig["sell_target"] = round(price, 3)
                sig["buy_target"] = round(price * 0.997, 3)  # 预期回落0.3%接回
                sig["stop_loss"] = round(price * 1.01, 3)   # 1%止损
                sig["reason"] = " + ".join(reasons[:3])
                sig["status"] = "sell_signal"
            elif sell_score >= sell_threshold * 0.8:
                sig["recommendation"] = "关注卖出机会"
                sig["reason"] = f"信号分{sell_score:.0f}，需等待更清晰"
                sig["status"] = "watch"
            else:
                sig["recommendation"] = "观望"
                sig["reason"] = f"信号分{sell_score:.0f}，未达门槛{sell_threshold}"
                sig["status"] = "watch"
        
        sig["signals"] = reasons[:3]
        sig["open_slots"] = open_slots
        sig["daily_sells"] = self.daily_stats[code]["sells"]
        sig["daily_pnl"] = round(self.daily_stats[code]["pnl"], 3)
        
        return sig
    
    def execute_sell(self, code: str, price: float, current_time: str):
        """记录卖出"""
        stats = self.daily_stats[code]
        if stats["sells"] >= self.max_per_day:
            return False
        
        self.positions[code].append({
            "sell_price": price,
            "sell_time": current_time,
            "slot_id": len(self.positions[code]) + 1,
        })
        stats["sells"] += 1
        return True
    
    def execute_buyback(self, code: str, price: float, current_time: str):
        """记录接回"""
        pos = self.positions[code]
        if not pos:
            return None
        
        # 接回最早的
        slot = pos.pop(0)
        profit = (slot["sell_price"] - price) / slot["sell_price"] * 100
        
        stats = self.daily_stats[code]
        stats["buys"] += 1
        stats["pnl"] += profit
        stats["trades"].append({
            "sell_time": slot["sell_time"],
            "sell_price": slot["sell_price"],
            "buy_time": current_time,
            "buy_price": price,
            "profit": profit,
        })
        
        return profit
    
    def get_portfolio_status(self) -> dict:
        """获取组合状态"""
        total_pnl = sum(s["pnl"] for s in self.daily_stats.values())
        total_trades = sum(len(s["trades"]) for s in self.daily_stats.values())
        total_slots = sum(len(p) for p in self.positions.values())
        
        return {
            "total_pnl": round(total_pnl, 3),
            "total_trades": total_trades,
            "total_open_slots": total_slots,
            "remaining_slots": 3 - total_slots,
            "stocks": {
                code: {
                    "name": cfg["name"],
                    "open_positions": len(self.positions[code]),
                    "daily_sells": self.daily_stats[code]["sells"],
                    "daily_pnl": round(self.daily_stats[code]["pnl"], 3),
                }
                for code, cfg in self.CODES.items()
            }
        }


# ========== Web服务 ==========
def create_app(generator: SignalGenerator):
    """创建Flask应用"""
    try:
        from flask import Flask, render_template_string, jsonify, request
        from flask_cors import CORS
    except ImportError:
        print("需要安装: pip install flask flask-cors")
        return None
    
    app = Flask(__name__)
    CORS(app)
    
    HTML = open(r"F:\aidanao\daytrade_system\medallion\templates\dashboard.html", "r", encoding="utf-8").read()
    
    @app.route("/")
    def index():
        return render_template_string(HTML)
    
    @app.route("/api/signals")
    def get_signals():
        result = {}
        for code in generator.CODES:
            daily, min5 = generator.load_tdx_data(code)
            
            today = datetime.now().strftime("%Y%m%d")
            today_min5 = [b for b in min5 if b["date"] == today]
            
            if today_min5:
                ind = generator.calc_indicators(today_min5, daily)
                sig = generator.generate_signal(code, ind, today_min5[-1]["time_sec"] // 60 * 60)
            else:
                ind = {}
                sig = generator.generate_signal(code, ind)
            
            result[code] = sig
        
        portfolio = generator.get_portfolio_status()
        return jsonify({"signals": result, "portfolio": portfolio})
    
    @app.route("/api/execute", methods=["POST"])
    def execute():
        data = request.json
        action = data.get("action")
        code = data.get("code")
        price = float(data.get("price", 0))
        time = data.get("time", datetime.now().strftime("%H:%M"))
        
        if action == "sell":
            ok = generator.execute_sell(code, price, time)
            return jsonify({"ok": ok})
        elif action == "buyback":
            profit = generator.execute_buyback(code, price, time)
            return jsonify({"ok": profit is not None, "profit": profit})
        
        return jsonify({"ok": False})
    
    @app.route("/api/reset")
    def reset():
        for code in generator.CODES:
            generator.positions[code] = []
            generator.daily_stats[code] = {"sells": 0, "buys": 0, "pnl": 0.0, "trades": []}
        return jsonify({"ok": True})
    
    return app


def main():
    print("=" * 50)
    print("大奖章实时盯盘系统 v1.0")
    print("=" * 50)
    
    generator = SignalGenerator()
    
    # 测试数据加载
    for code in generator.CODES:
        daily, min5 = generator.load_tdx_data(code)
        today = datetime.now().strftime("%Y%m%d")
        today_min5 = [b for b in min5 if b["date"] == today]
        if today_min5:
            ind = generator.calc_indicators(today_min5, daily)
            sig = generator.generate_signal(code, ind, today_min5[-1]["time_sec"] // 60 * 60)
            print(f"\n{sig['name']}({code}):")
            print(f"  价格: {sig['price']}")
            print(f"  建议: {sig['recommendation']} ({sig['confidence']})")
            print(f"  信号分: 卖出={sig['scores']['sell']}, 接回={sig['scores']['buy']}")
            print(f"  原因: {sig['reason']}")
        else:
            print(f"\n{generator.CODES[code]['name']}({code}): 无今日数据")
    
    # 启动Web服务
    app = create_app(generator)
    if app:
        print(f"\n启动Web服务: http://localhost:8767")
        print("按 Ctrl+C 停止")
        app.run(host="0.0.0.0", port=8767, debug=False, use_reloader=False)
    else:
        print("\n无法启动Web服务，仅显示信号")


if __name__ == "__main__":
    main()
