"""
live_monitor_v2.py — 大奖章T仓系统 v2（融入实战经验）

用户真实交易逻辑：
1. 开盘紧急T：开盘剧烈波动时做0.5%的高抛低吸
2. 冲高滞涨卖：涨1-3%+成交放大+开始滞涨时卖出
3. 分时均线接回：回落到均线附近买
4. 情绪过滤：利好+板块强势时不卖
5. 昆仑更重要：看好AI生成游戏的长线逻辑

系统目标：
- 系统输出信号，人工最终决策
- 不做自动下单，只做人能看懂的信号
- 实时显示：当前价格、信号强度、买卖建议、目标价
"""

import os, sys, json, time, struct, random
from datetime import datetime
from collections import defaultdict
from sentiment_monitor import SentimentMonitor, SECTOR_STOCKS

# ========== 数据加载 ==========
def load_tdx_min5(code, limit=200):
    """加载5分K数据"""
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\fzline\{market}{code}.lc5"
    if not os.path.exists(path): return []
    
    def unpack_date(w):
        y = (w // 2048) + 2004
        md = w % 2048
        m, d = md // 100, md % 100
        return f"{y:04d}{m:02d}{d:02d}"
    
    bars = []
    with open(path, "rb") as f:
        data = f.read()
    
    for i in range(len(data) // 32):
        u = struct.unpack_from("<HHfffffIHH", data, i*32)
        dw, minute = u[0], u[1]
        o, h, l, c = u[2], u[3], u[4], u[5]
        amt, vol = u[6], u[7]
        ds = unpack_date(dw)
        if ds.startswith("1970") or o == 0: continue
        
        sec = minute * 60
        hh, mm = divmod(minute, 60)
        bars.append({
            "date": ds,
            "time_sec": sec,
            "time_str": f"{hh:02d}:{mm:02d}",
            "open": o, "high": h, "low": l, "close": c,
            "volume": vol, "amount": amt,
        })
    
    return bars[-limit:] if limit else bars

def load_tdx_daily(code, limit=60):
    """加载日K数据"""
    market = "sz" if code.startswith(("0", "3")) else "sh"
    path = rf"F:\tongdaxin\vipdoc\{market}\lday\{market}{code}.day"
    if not os.path.exists(path): return []
    
    bars = []
    with open(path, "rb") as f:
        data = f.read()
    
    for i in range(len(data) // 32):
        u = struct.unpack_from("<IIIIIfII", data, i*32)
        date_int = u[0]
        if date_int < 20000000: continue
        bars.append({
            "date": str(date_int),
            "open": u[1]/100, "high": u[2]/100,
            "low": u[3]/100, "close": u[4]/100,
            "volume": u[6],
        })
    
    return bars[-limit:] if limit else bars


# ========== 信号计算（融入用户经验）==========
class SignalEngine:
    """基于用户实战经验的信号引擎"""
    
    CODES = {
        "300418": {"name": "蓝色光标", "weight": 2},
        "300058": {"name": "昆仑万维", "weight": 3},
    }
    
    def __init__(self):
        self.positions = {}  # code -> [{sell_price, sell_time}]
        self.sentiment_monitor = SentimentMonitor()
        self.sentiment_cache = None
        self.daily_stats = {}  # code -> {sells, buys, pnl, trades}
        for code in self.CODES:
            self.positions[code] = []
            self.daily_stats[code] = {"sells": 0, "buys": 0, "pnl": 0.0, "trades": []}
    
    def calc_indicators(self, min5_bars, daily_bars):
        """计算分时指标"""
        if not min5_bars: return {}
        
        now = min5_bars[-1]
        price = now["close"]
        
        # 当日VWAP
        total_vol = sum(b["volume"] for b in min5_bars)
        vwap = sum(b["close"] * b["volume"] for b in min5_bars) / max(total_vol, 1)
        
        # 分时均线
        ma5_price = sum(b["close"] for b in min5_bars[-5:]) / 5 if len(min5_bars) >= 5 else price
        ma10_price = sum(b["close"] for b in min5_bars[-10:]) / 10 if len(min5_bars) >= 10 else price
        ma20_price = sum(b["close"] for b in min5_bars[-20:]) / 20 if len(min5_bars) >= 20 else price
        
        # 日内高低点
        day_high = max(b["high"] for b in min5_bars)
        day_low = min(b["low"] for b in min5_bars)
        
        # 从高点回撤%
        pullback = (day_high - price) / day_high * 100 if day_high > 0 else 0
        
        # 距均线偏离
        ma_dev = (price - ma5_price) / ma5_price * 100 if ma5_price > 0 else 0
        
        # 成交量分析（用户经验：成交放大+滞涨）
        vols = [b["volume"] for b in min5_bars[-10:]]
        avg_vol = sum(vols) / len(vols) if vols else 1
        vol_ratio = now["volume"] / avg_vol if avg_vol > 0 else 1
        
        # 最近5分钟K涨幅
        recent_5min_change = 0
        if len(min5_bars) >= 2:
            recent_5min_change = (min5_bars[-1]["close"] - min5_bars[-2]["close"]) / min5_bars[-2]["close"] * 100
        
        # 累计涨幅（从开盘）
        first_open = min5_bars[0]["open"]
        open_to_now = (price - first_open) / first_open * 100 if first_open > 0 else 0
        
        # RSI
        if len(min5_bars) >= 15:
            gains = [max(0, min5_bars[i]["close"] - min5_bars[i-1]["close"]) for i in range(1, len(min5_bars))]
            losses = [max(0, min5_bars[i-1]["close"] - min5_bars[i]["close"]) for i in range(1, len(min5_bars))]
            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            rs = avg_gain / max(avg_loss, 0.0001)
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # 昨日收盘
        prev_close = daily_bars[-2]["close"] if len(daily_bars) >= 2 else price
        
        return {
            "price": price,
            "prev_close": prev_close,
            "vwap": vwap,
            "vwap_dev": (price - vwap) / vwap * 100 if vwap > 0 else 0,
            "ma5": ma5_price,
            "ma10": ma10_price,
            "ma20": ma20_price,
            "ma5_dev": ma_dev,
            "ma10_dev": (price - ma10_price) / ma10_price * 100 if ma10_price > 0 else 0,
            "ma20_dev": (price - ma20_price) / ma20_price * 100 if ma20_price > 0 else 0,
            "day_high": day_high,
            "day_low": day_low,
            "pullback": pullback,
            "open_to_now": open_to_now,
            "recent_5min": recent_5min_change,
            "vol_ratio": vol_ratio,
            "rsi": rsi,
            "time": now["time_str"],
        }
    
    def generate_signal(self, code, ind, sentiment_override=None):
        """生成T仓信号（融入用户实战经验+情绪过滤）"""
        # 自动获取情绪
        if sentiment_override is None:
            sentiment_override = self.sentiment_monitor.get_sentiment()
        """
        生成T仓信号（融入用户实战经验）
        
        用户经验总结：
        1. 开盘紧急T：0.5%的波动就做
        2. 冲高滞涨卖：涨1-3%+成交放大+滞涨
        3. 分时均线接回：回落均线附近买
        4. 情绪过滤：利好+板块强时不卖
        """
        cfg = self.CODES[code]
        price = ind.get("price", 0)
        if price <= 0:
            return {"code": code, "name": cfg["name"], "status": "no_data"}
        
        now_time = ind.get("time", "09:30")
        h, m = int(now_time.split(":")[0]), int(now_time.split(":")[1])
        mins = h * 60 + m
        
        sig = {
            "code": code, "name": cfg["name"],
            "price": round(price, 3),
            "time": now_time,
            "status": "watch",
            "recommendation": "观望",
            "confidence": 0,
            "sell_target": None,
            "buy_target": None,
            "stop_loss": None,
            "reason": [],
            "signals": {},
            "scores": {"sell": 0, "buy": 0},
            "open_slots": len(self.positions[code]),
            "daily_sells": self.daily_stats[code]["sells"],
            "daily_pnl": round(self.daily_stats[code]["pnl"], 3),
            "sentiment": sentiment_override or "normal",
        }
        
        pullback = ind.get("pullback", 0)
        open_to_now = ind.get("open_to_now", 0)
        vol_ratio = ind.get("vol_ratio", 1)
        recent_5min = ind.get("recent_5min", 0)
        ma5_dev = ind.get("ma5_dev", 0)
        ma5 = ind.get("ma5", price)
        vwap = ind.get("vwap", price)
        rsi = ind.get("rsi", 50)
        prev_close = ind.get("prev_close", price)
        day_high = ind.get("day_high", price)
        day_low = ind.get("day_low", price)
        
        # ===== 情绪过滤 =====
        if sentiment_override == "bullish":
            sig["sentiment"] = "强势"
            sig["reason"].append("情绪强势(利好+板块强)")
        elif sentiment_override == "bearish":
            sig["sentiment"] = "弱势"
            sig["reason"].append("情绪弱势")
        else:
            sig["sentiment"] = "normal"
        
        # ===== 持仓检查 =====
        pos = self.positions[code]
        open_count = len(pos)
        
        if open_count > 0:
            # 有持仓：计算盈亏和接回建议
            entry_price = pos[0]["sell_price"]
            loss_pct = (price - entry_price) / entry_price * 100
            recovery_pct = (entry_price - price) / entry_price * 100
            
            sig["sell_target"] = round(entry_price, 3)
            sig["stop_loss"] = round(entry_price * 1.01, 3)  # 1%止损
            
            # 接回条件1：回到均线附近
            if price <= ma5 * 1.001:
                sig["status"] = "buy_signal"
                sig["recommendation"] = "接回"
                sig["buy_target"] = round(price, 3)
                sig["reason"].append(f"价格已回到MA5({ma5:.3f})附近")
                sig["scores"]["buy"] = 80
            # 接回条件2：回到卖出价
            elif price <= entry_price * 0.999:
                sig["status"] = "buy_signal"
                sig["recommendation"] = "接回"
                sig["buy_target"] = round(price, 3)
                sig["reason"].append(f"已低于卖出价{entry_price:.3f}，盈利{recovery_pct:.2f}%")
                sig["scores"]["buy"] = 70
            # 接回条件3：超跌
            elif loss_pct > 1.5:
                sig["status"] = "buy_signal"
                sig["recommendation"] = "考虑接回"
                sig["buy_target"] = round(price, 3)
                sig["reason"].append(f"浮亏{loss_pct:.2f}%，超跌可接")
                sig["scores"]["buy"] = 50
            else:
                # 亏损中，等一等
                sig["status"] = "holding"
                sig["recommendation"] = "持仓观察"
                sig["reason"].append(f"浮亏{loss_pct:.2f}%，耐心等待")
                sig["scores"]["buy"] = 20
            
            sig["scores"]["sell"] = 0
            return sig
        
        # ===== 无持仓：检查卖出机会 =====
        stats = self.daily_stats[code]
        
        if stats["sells"] >= 3:
            sig["status"] = "no_quota"
            sig["recommendation"] = "今日额度用完"
            sig["reason"].append("已卖3笔，等接回")
            return sig
        
        # ==== 信号评估 ====
        sell_score = 0
        sell_reasons = []
        
        # 信号1：开盘紧急T机会（用户经验：一开盘剧烈波动）
        if mins < 9 * 60 + 45:  # 开盘15分钟内
            # 开盘涨幅超过0.5%
            if abs(open_to_now) > 0.5:
                if open_to_now > 0:
                    sell_score += 40
                    sell_reasons.append(f"开盘涨{open_to_now:.2f}%(紧急T机会)")
                else:
                    # 开盘大跌：不做卖，等接
                    sig["status"] = "watch"
                    sig["recommendation"] = "开盘大跌，观望"
                    sig["reason"].append(f"开盘跌{open_to_now:.2f}%，不追卖")
                    return sig
        
        # 信号2：冲高滞涨（用户核心经验）
        # 条件：累计涨1-3%，成交量放大，5分钟K开始滞涨
        if 1.0 <= open_to_now <= 3.5:
            score = 30 + (open_to_now - 1.0) * 10  # 1%→30分，2%→40分，3%→50分
            sell_score += score
            sell_reasons.append(f"冲高{open_to_now:.2f}%")
        
        # 信号2b：成交量放大+滞涨（用户经验）
        if vol_ratio > 1.3 and recent_5min < 0.1:
            sell_score += 25
            sell_reasons.append(f"放量滞涨(vol={vol_ratio:.1f}x)")
        elif vol_ratio > 1.5:
            sell_score += 15
            sell_reasons.append(f"量能放大({vol_ratio:.1f}x)")
        
        # 信号3：价格远高于均线（用户经验：均线太远先卖）
        if ma5_dev > 1.5:
            sell_score += 20
            sell_reasons.append(f"偏离MA5+{ma5_dev:.2f}%")
        
        # 信号4：RSI超买
        if rsi > 72:
            sell_score += 20
            sell_reasons.append(f"RSI={rsi:.0f}超买")
        elif rsi > 68:
            sell_score += 10
            sell_reasons.append(f"RSI={rsi:.0f}偏高")
        
        # 信号5：VWAP偏离
        vwap_dev = ind.get("vwap_dev", 0)
        if vwap_dev > 1.0:
            sell_score += 15
            sell_reasons.append(f"VWAP偏离+{vwap_dev:.2f}%")
        
        # ==== 情绪过滤（用户经验：利好时不卖）====
        if sentiment_override == "bullish" and sell_score > 0:
            sell_score = int(sell_score * 0.5)  # 情绪好时降低卖出信号
            sell_reasons.append("情绪强势，降权")
        
        # ==== 置信度 ====
        if sell_score >= 70:
            conf = "A++"
        elif sell_score >= 55:
            conf = "A"
        elif sell_score >= 40:
            conf = "B"
        elif sell_score >= 25:
            conf = "C"
        else:
            conf = "D"
        
        sig["scores"]["sell"] = sell_score
        sig["confidence"] = conf
        
        # ==== 生成建议 ====
        if sell_score >= 50:
            sig["status"] = "sell_signal"
            sig["recommendation"] = "建议卖出"
            sig["sell_target"] = round(price, 3)
            # 接回目标：回落均线附近
            sig["buy_target"] = round(ma5 * 0.999, 3)
            sig["stop_loss"] = round(price * 1.01, 3)
            sig["reason"] = sell_reasons
        elif sell_score >= 30:
            sig["status"] = "watch"
            sig["recommendation"] = "关注机会"
            sig["reason"] = sell_reasons if sell_reasons else ["信号偏弱，继续观察"]
        else:
            sig["status"] = "watch"
            sig["recommendation"] = "观望"
            sig["reason"] = ["等待更好的机会"]
        
        return sig
    
    def execute_sell(self, code, price, time_str):
        """记录卖出"""
        stats = self.daily_stats[code]
        if stats["sells"] >= 3:
            return False
        self.positions[code].append({
            "sell_price": price,
            "sell_time": time_str,
        })
        stats["sells"] += 1
        return True
    
    def execute_buyback(self, code, price, time_str):
        """记录接回"""
        pos = self.positions[code]
        if not pos:
            return None
        slot = pos.pop(0)
        profit = (slot["sell_price"] - price) / slot["sell_price"] * 100
        stats = self.daily_stats[code]
        stats["buys"] += 1
        stats["pnl"] += profit
        stats["trades"].append({
            "sell_time": slot["sell_time"],
            "sell_price": slot["sell_price"],
            "buy_time": time_str,
            "buy_price": price,
            "profit": profit,
        })
        return profit
    
    def get_status(self):
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


