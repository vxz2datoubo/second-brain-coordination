"""live_runner.py — 大奖章系统生产运行器

每5分钟调用一次（由外部定时器或手动触发），输出决策建议供人工最终确认。

核心流程：
  1. 连接TDX获取实时数据
  2. 计算六因子信号
  3. 市场状态分类
  4. 板块情绪监测（可跳过）
  5. 组合槽位决策
  6. 输出格式化决策单

决策等级：
  A++: 立即执行（置信度极高）
  A:   正常执行
  B:   可执行，限额1笔
  C:   谨慎/观察
  D:   不执行

日志输出到 medallion/data/live_log_{date}.json
"""

import sys, os, json, logging
from datetime import datetime, date
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from medallion.config import STOCK_CONFIGS, get_confidence, PORTFOLIO
from medallion.signal_pipeline import SignalPipeline, format_signal
from medallion.regime_clf import RegimeClassifier
from medallion.portfolio_controller import PortfolioController
from medallion.sentiment_monitor import SentimentMonitor, NewsSource
from medallion.tdx_connector import TDXConnector


# ============================================================
# 日志配置
# ============================================================

LOG_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, f"live_log_{date.today().isoformat()}.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("medallion")


# ============================================================
# 主运行器
# ============================================================

class MedallionRunner:
    """
    大奖章系统生产运行器

    用法（每5分钟调用）：
      runner = MedallionRunner()
      decisions = runner.run()
      for d in decisions:
          print(d.format())
          # 人工确认后手动执行
    """

    def __init__(self, offline: bool = True):
        self.offline = offline
        self.conn = TDXConnector(offline=offline)
        self.portfolio = PortfolioController()

        # 初始化各模块
        self.signals: Dict[str, SignalPipeline] = {}
        self.regimes: Dict[str, RegimeClassifier] = {}
        for code in ["300418", "300058"]:
            cfg = STOCK_CONFIGS[code]
            self.signals[code] = SignalPipeline(code, cfg)
            self.regimes[code] = RegimeClassifier(code)

        self.sentiment = SentimentMonitor()
        self.sentiment.set_related_sectors({
            "300418": ["AI应用", "营销", "游戏", "数据中心", "ChatGPT"],
            "300058": ["AI大模型", "游戏", "社交", "投资", "算力"],
        })

        # 加载跨日仓位
        self._load_carried_positions()
        self._ensure_today_reset()

        log.info("大奖章系统初始化完成 | 离线模式=%s", offline)

    def run(self) -> List[Dict]:
        """
        主运行函数（每5分钟调用一次）
        返回决策列表
        """
        current_time = datetime.now().strftime("%H:%M")
        current_date = date.today().isoformat()

        # 开盘前 / 收盘后：跳过
        if current_time < "09:25" or current_time > "15:05":
            log.info("非交易时间，跳过: %s", current_time)
            return []

        decisions = []
        stock_data = {}

        for code in ["300058", "300418"]:  # 昆仑优先
            cfg = STOCK_CONFIGS[code]
            name = cfg.name

            # 获取数据
            quote = self.conn.get_quote(code)
            if not quote:
                log.warning("[%s] 无法获取行情", name)
                continue

            prev_close = quote["pre_close"]
            open_today = quote["open"]
            current_price = quote["now"]

            # 获取今日5分K
            min5_bars = self.conn.get_today_min5(code)
            min5_kbars = [_dict_to_kbar(b) for b in min5_bars]

            # 获取日K（最近30天）
            daily_bars = self.conn.get_daily(code, days=35)
            daily_kbars = [_dict_to_kbar(b) for b in daily_bars]

            # 市场状态分类
            regime_result = self.regimes[code].classify(
                daily_kbars[-30:], min5_kbars, prev_close
            )
            regime = regime_result["regime"]

            # 计算六因子信号
            signal = self.signals[code].evaluate(
                current_price=current_price,
                min5_bars=min5_kbars,
                daily_bars=daily_kbars[-30:],
                prev_close=prev_close,
                regime=regime,
            )

            stock_data[code] = {
                "quote": quote,
                "signal": signal,
                "regime": regime_result,
                "min5_kbars": min5_kbars,
                "daily_kbars": daily_kbars,
            }

            # 日志输出
            log.info(
                "[%s] 时间=%s 现价=%.4f 涨跌=%+.2f%% 信号=%s(%.0f分) 置信度=%s Regime=%s",
                name, current_time, current_price,
                (current_price / prev_close - 1) * 100,
                signal.reason[:30], signal.total_score,
                signal.confidence, regime,
            )

        if not stock_data:
            return []

        # 组合决策（仅在有时间窗口时执行新仓）
        kl_data = stock_data.get("300058", {})
        bl_data = stock_data.get("300418", {})

        kl_signal = kl_data.get("signal")
        bl_signal = bl_data.get("signal")

        kl_price = kl_data.get("quote", {}).get("now", 0)
        bl_price = bl_data.get("quote", {}).get("now", 0)
        kl_prev  = kl_data.get("quote", {}).get("pre_close", 0)
        bl_prev  = bl_data.get("quote", {}).get("pre_close", 0)
        kl_open  = kl_data.get("quote", {}).get("open", 0)
        bl_open  = bl_data.get("quote", {}).get("open", 0)

        # 槽位检查
        portfolio_decisions = self.portfolio.evaluate(
            kunlun_price=kl_price, blue_price=bl_price,
            kunlun_signal_score=kl_signal.total_score if kl_signal else 0,
            blue_signal_score=bl_signal.total_score if bl_signal else 0,
            kunlun_signal_reason=kl_signal.reason if kl_signal else "",
            blue_signal_reason=bl_signal.reason if bl_signal else "",
            kunlun_prev_close=kl_prev, blue_prev_close=bl_prev,
            kunlun_open_today=kl_open, blue_open_today=bl_open,
            current_time=current_time,
        )

        # 格式化输出
        for pd in portfolio_decisions:
            decision = self._format_decision(pd, stock_data, current_time)
            decisions.append(decision)
            self._log_decision(decision)

        # 输出状态
        if not decisions:
            readiness = self.portfolio.get_signal_readiness()
            log.info(
                "无操作 | 昆仑剩余=%d 蓝色剩余=%d 总剩余=%d",
                readiness["kunlun"]["available"],
                readiness["blue"]["available"],
                readiness["total_remaining"],
            )

        # 打印决策单
        if decisions:
            print(self._render_decision_sheet(decisions, stock_data, current_time))

        return decisions

    # ============================================================
    # 决策格式化
    # ============================================================

    def _format_decision(self, pd, stock_data: Dict, current_time: str) -> Dict:
        """将PortfolioDecision转为可执行字典"""
        sd = pd.slot_decision
        code = "300058" if "kunlun" in pd.priority else "300418"
        name = STOCK_CONFIGS[code].name

        signal = stock_data.get(code, {}).get("signal")
        quote = stock_data.get(code, {}).get("quote", {})

        current_price = quote.get("now", sd.price)
        prev_close = quote.get("pre_close", current_price)
        chg_pct = (current_price / prev_close - 1) * 100 if prev_close else 0

        # 估算盈亏（对已开仓）
        pnl_estimate = 0.0
        if "buy_back" in pd.action and hasattr(pd.slot_decision, "slot_id"):
            # 从槽位获取开仓价估算
            controller = self.portfolio.kunlun if code == "300058" else self.portfolio.blue
            for slot in controller.slots:
                if slot.id == sd.slot_id and slot.is_open:
                    pnl_estimate = slot.unrealized_pnl(current_price)

        # 置信度
        conf = get_confidence(signal.total_score if signal else 50) if signal else None

        return {
            "timestamp": datetime.now().isoformat(),
            "action": pd.action,
            "code": code,
            "name": name,
            "direction": "倒T卖出" if "sell" in pd.action else ("倒T接回" if "buy_back" in pd.action else "清仓"),
            "price": round(sd.price or current_price, 4),
            "current_price": round(current_price, 4),
            "chg_pct": round(chg_pct, 2),
            "pnl_estimate": round(pnl_estimate, 2),
            "reason": pd.reason,
            "slot_id": sd.slot_id,
            "urgency": pd.urgency,
            "confidence": conf.grade if conf else "N/A",
            "action_label": conf.action if conf else sd.reason,
            "time_window": _get_time_window(current_time),
        }

    def _render_decision_sheet(self, decisions: List[Dict],
                                 stock_data: Dict, current_time: str) -> str:
        """渲染美观的决策单"""
        lines = [
            "",
            "=" * 60,
            f"  大奖章决策单  {datetime.now().strftime('%H:%M:%S')}  {_get_time_window(current_time)}",
            "=" * 60,
        ]

        urgency_icons = {"high": "[立即]", "normal": "[执行]", "low": "[观察]"}
        direction_icons = {
            "倒T卖出": "▼ 卖出",
            "倒T接回": "▲ 接回",
            "清仓": "■ 清仓",
        }

        for i, d in enumerate(decisions, 1):
            icon = urgency_icons.get(d["urgency"], "")
            dir_icon = direction_icons.get(d["direction"], d["direction"])

            lines.append("")
            lines.append(f"  [{i}] {icon} {d['name']}({d['code']}) {dir_icon}")
            lines.append(f"      价格: {d['price']:.4f} (现价 {d['current_price']:.4f} {d['chg_pct']:+.2f}%)")
            if d["pnl_estimate"]:
                lines.append(f"      预估盈亏: {d['pnl_estimate']:+.2f}%")
            lines.append(f"      置信度: {d['confidence']}  {d['action_label']}")
            lines.append(f"      理由: {d['reason']}")
            lines.append(f"      槽位: #{d['slot_id']}")

        lines.append("")
        lines.append("-" * 60)

        # 槽位状态
        kl = self.portfolio.kunlun
        bl = self.portfolio.blue
        lines.append(
            f"  槽位 | 昆仑: 卖{kl.daily_sell_count}/{kl.cfg.max_trades_per_day} "
            f"开{[s.id for s in kl.open_slots]} "
            f"| 蓝色: 卖{bl.daily_sell_count}/{bl.cfg.max_trades_per_day} "
            f"开{[s.id for s in bl.open_slots]}"
        )
        lines.append(
            f"  日盈亏 | 昆仑: {kl.daily_pnl:+.2f}% "
            f"| 蓝色: {bl.daily_pnl:+.2f}% "
            f"| 合计: {kl.daily_pnl + bl.daily_pnl:+.2f}%"
        )
        if self.portfolio.is_portfolio_meltdown:
            lines.append("  [!] 联合熔断中，全天停止操作")
        if self.portfolio.is_red_alert:
            lines.append("  [!] 红色警报：两只同跌，停止开新仓")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _log_decision(self, decision: Dict):
        """写JSON日志"""
        log_path = os.path.join(LOG_DIR, f"decisions_{date.today().isoformat()}.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision, ensure_ascii=False) + "\n")

    # ============================================================
    # 辅助
    # ============================================================

    def _load_carried_positions(self):
        """次日开盘加载跨日仓位"""
        carry_file = os.path.join(LOG_DIR, "carried_positions.json")
        if os.path.exists(carry_file):
            try:
                with open(carry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.portfolio.carried_kunlun = data.get("kunlun", [])
                    self.portfolio.carried_blue = data.get("blue", [])
                    self.portfolio.load_carried()
                    log.info("加载跨日仓位: 昆仑=%d 蓝色=%d",
                             len(self.portfolio.carried_kunlun),
                             len(self.portfolio.carried_blue))
            except Exception as e:
                log.warning("加载跨日仓位失败: %s", e)

    def _ensure_today_reset(self):
        """确保新的一天重置状态"""
        today = date.today().isoformat()
        if self.portfolio.today != today:
            self.portfolio.reset_day()
            log.info("新的一天，重置状态: %s", today)

    def carry_over_and_save(self):
        """收盘：保存跨日仓位"""
        self.portfolio.carry_over()
        carry_file = os.path.join(LOG_DIR, "carried_positions.json")
        with open(carry_file, "w", encoding="utf-8") as f:
            json.dump({
                "kunlun": self.portfolio.carried_kunlun,
                "blue": self.portfolio.carried_blue,
                "date": date.today().isoformat(),
            }, f, ensure_ascii=False)
        log.info("跨日仓位已保存: 昆仑=%d 蓝色=%d",
                 len(self.portfolio.carried_kunlun),
                 len(self.portfolio.carried_blue))

    def get_status(self) -> str:
        """获取当前状态"""
        return self.portfolio.status()


# ============================================================
# 工具函数
# ============================================================

def _dict_to_kbar(d: Dict):
    """将字典转KBar"""
    from engine.indicators import KBar
    return KBar(
        date=d.get("date", ""),
        time_sec=d.get("time_sec", 0),
        open=float(d.get("open", 0)),
        high=float(d.get("high", 0)),
        low=float(d.get("low", 0)),
        close=float(d.get("close", 0)),
        amount=float(d.get("amount", 0)),
        volume=float(d.get("volume", 0)),
    )


def _get_time_window(t: str) -> str:
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    mins = h * 60 + m
    if mins < 9 * 60 + 50: return "T1开盘"
    elif mins < 10 * 60 + 30: return "T2黄金"
    elif mins < 11 * 60: return "T3上午"
    elif mins < 11 * 60 + 30: return "T4谨慎"
    elif mins < 13 * 60 + 30: return "T5下午重启"
    elif mins < 14 * 60: return "T6下午黄金"
    elif mins < 14 * 60 + 30: return "T7尾盘决策"
    else: return "T8强制收尾"


# ============================================================
# 快速测试
# ============================================================

if __name__ == "__main__":
    print("大奖章系统 v4.0 — 生产运行器")
    print("=" * 50)

    runner = MedallionRunner(offline=True)
    runner.run()
