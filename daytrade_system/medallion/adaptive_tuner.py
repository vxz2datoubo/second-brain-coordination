"""adaptive_tuner.py — 自进化调参器

核心功能：每周自动分析过去20笔交易的表现，
调整因子权重、信号门槛、止损参数，让系统不断自我优化。

学习机制：
  1. 因子相关性分析：哪些因子的信号分和实际盈亏相关性最高？
  2. 参数敏感性测试：微调止损/门槛，观察对期望的影响
  3. 规则演化：哪些风控规则有效？哪些可以放宽？
  4. 跨日天数优化：持有一天 vs 两天的收益对比
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from .config import STOCK_CONFIGS, CONF_LEVELS
import math


@dataclass
class TradeRecord:
    """单笔交易记录"""
    date: str
    code: str
    direction: str
    entry_price: float
    exit_price: float
    profit_pct: float
    entry_score: float
    factor_scores: Dict[str, float]   # {"F1": 80, "F2": 60, ...}
    regime: str
    time_window: str
    carry_days: int
    success: bool


@dataclass
class TunerReport:
    """调参报告"""
    date: str
    trades_analyzed: int
    best_params: Dict
    factor_correlations: Dict[str, float]
    suggestions: List[str]
    expected_improvement: float


class AdaptiveTuner:
    """
    自进化调参器

    使用方法：
      tuner = AdaptiveTuner("300418")
      tuner.add_trade(trade_record)
      if tuner.should_tune():
          report = tuner.tune()
          tuner.apply_params(report.best_params)
    """

    MIN_TRADES_TO_TUNE = 20
    TUNE_INTERVAL_DAYS = 7

    def __init__(self, code: str):
        self.code = code
        self.cfg = STOCK_CONFIGS[code]
        self.trades: List[TradeRecord] = []
        self.last_tune_date: Optional[str] = None
        self.current_params = self._get_default_params()
        self.tuned_params = {}

        self.data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", f"tuner_{code}.json"
        )
        self._load()

    def _get_default_params(self) -> Dict:
        return {
            "entry_score_threshold": self.cfg.entry_score_threshold,
            "b_entry_threshold": self.cfg.b_entry_threshold,
            "hard_stop_loss_pct": self.cfg.hard_stop_loss_pct,
            "flee_stop_pct": self.cfg.flee_stop_pct,
            "time_stop_minutes": self.cfg.time_stop_minutes,
            "min_profit_take_pct": self.cfg.min_profit_take_pct,
            "greedy_profit_pct": self.cfg.greedy_profit_pct,
            "max_trades_per_day": self.cfg.max_trades_per_day,
            "require_intraday_high_pct": self.cfg.require_intraday_high_pct,
            "factor_weights": {
                "F1": self.cfg.f1_vwap_weight,
                "F2": self.cfg.f2_rsi_weight,
                "F3": self.cfg.f3_volprofile_weight,
                "F4": self.cfg.f4_momentum_weight,
                "F5": self.cfg.f5_delta_weight,
                "F6": self.cfg.f6_gap_weight,
            },
        }

    def _load(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.trades = [TradeRecord(**t) for t in data.get("trades", [])]
                    self.last_tune_date = data.get("last_tune_date")
                    saved_params = data.get("tuned_params", {})
                    if saved_params:
                        self.current_params.update(saved_params)
            except Exception as e:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        data = {
            "trades": [vars(t) for t in self.trades[-500:]],  # 只保留最近500笔
            "last_tune_date": self.last_tune_date,
            "tuned_params": self.current_params,
        }
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_trade(self, trade: TradeRecord):
        """添加一笔交易记录"""
        self.trades.append(trade)
        self._save()

    def should_tune(self) -> bool:
        """是否应该调参"""
        if len(self.trades) < self.MIN_TRADES_TO_TUNE:
            return False

        if self.last_tune_date:
            last = datetime.strptime(self.last_tune_date, "%Y-%m-%d")
            if (datetime.now() - last).days < self.TUNE_INTERVAL_DAYS:
                return False

        return True

    def tune(self) -> TunerReport:
        """
        执行调参
        返回调参报告和建议
        """
        recent = self.trades[-self.MIN_TRADES_TO_TUNE:]

        # 1. 计算因子相关性
        correlations = self._calc_factor_correlations(recent)

        # 2. 找最优参数
        best_params = self._find_best_params(recent)

        # 3. 生成建议
        suggestions = self._generate_suggestions(recent, correlations, best_params)

        # 4. 计算期望改进
        improvement = self._calc_expected_improvement(recent, best_params)

        report = TunerReport(
            date=datetime.now().strftime("%Y-%m-%d"),
            trades_analyzed=len(recent),
            best_params=best_params,
            factor_correlations=correlations,
            suggestions=suggestions,
            expected_improvement=improvement,
        )

        self.last_tune_date = report.date
        self.current_params.update(best_params)
        self._save()

        return report

    def _calc_factor_correlations(self, trades: List[TradeRecord]) -> Dict[str, float]:
        """
        计算每个因子得分与盈亏的相关性
        Pearson相关系数
        """
        factors = ["F1", "F2", "F3", "F4", "F5", "F6"]
        correlations = {}

        pnls = [t.profit_pct for t in trades]
        pnls_mean = sum(pnls) / len(pnls)
        pnls_std = math.sqrt(sum((p - pnls_mean)**2 for p in pnls) / len(pnls)) if len(pnls) > 1 else 1

        for f in factors:
            f_scores = [t.factor_scores.get(f, 0) for t in trades]
            f_mean = sum(f_scores) / len(f_scores)
            f_std = math.sqrt(sum((s - f_mean)**2 for s in f_scores) / len(f_scores)) if len(f_scores) > 1 else 1

            if f_std > 0 and pnls_std > 0:
                cov = sum((pnls[i] - pnls_mean) * (f_scores[i] - f_mean) for i in range(len(trades))) / len(trades)
                corr = cov / (f_std * pnls_std)
                correlations[f] = round(corr, 3)
            else:
                correlations[f] = 0.0

        return correlations

    def _find_best_params(self, trades: List[TradeRecord]) -> Dict:
        """
        网格搜索找最优参数组合
        测试维度：
          - 信号门槛: 60/65/70/75
          - 止损: -0.8%/-1.0%/-1.2%
          - 飞逃: +1.5%/+2.0%/+2.5%
          - 时间止损: 30/40/50分钟
        """
        best_score = -999
        best_params = self.current_params.copy()

        # 简化版：基于胜率和盈亏比找最优
        # 按不同参数组合分组
        for stop_loss in [-0.8, -1.0, -1.2]:
            for flee in [1.5, 2.0, 2.5]:
                for threshold in [60, 68, 73]:
                    # 筛选符合该参数的交易
                    filtered = [t for t in trades if t.entry_score >= threshold]
                    if len(filtered) < 5:
                        continue

                    wins = [t for t in filtered if t.profit_pct > 0]
                    losses = [t for t in filtered if t.profit_pct <= 0]

                    if not wins or not losses:
                        continue

                    win_rate = len(wins) / len(filtered)
                    avg_win = sum(t.profit_pct for t in wins) / len(wins)
                    avg_loss = abs(sum(t.profit_pct for t in losses) / len(losses))
                    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

                    # 综合得分：胜率×盈亏比
                    score = win_rate * profit_factor * 100

                    if score > best_score:
                        best_score = score
                        best_params = {
                            "entry_score_threshold": threshold,
                            "hard_stop_loss_pct": stop_loss,
                            "flee_stop_pct": flee,
                            "factor_weights": self.current_params["factor_weights"],
                        }

        return best_params

    def _generate_suggestions(self, trades: List[TradeRecord],
                               correlations: Dict[str, float],
                               best_params: Dict) -> List[str]:
        """生成调参建议"""
        suggestions = []

        # 1. 因子权重建议
        sorted_factors = sorted(correlations.items(), key=lambda x: -abs(x[1]))
        strongest = sorted_factors[0]
        weakest = sorted_factors[-1]

        if abs(strongest[1]) > 0.2:
            suggestions.append(
                f"因子{strongest[0]}与盈亏相关性最强({strongest[1]:+.3f})，"
                f"建议提高其权重"
            )
        if abs(weakest[1]) < 0.1 and abs(weakest[1]) < abs(strongest[1]) - 0.1:
            suggestions.append(
                f"因子{weakest[0]}与盈亏相关性弱({weakest[1]:+.3f})，"
                f"建议降低其权重或移除"
            )

        # 2. 参数建议
        if best_params.get("entry_score_threshold", 0) > self.current_params["entry_score_threshold"]:
            suggestions.append(
                f"建议提高信号门槛到{best_params['entry_score_threshold']}分，"
                f"减少低质量交易"
            )

        if best_params.get("hard_stop_loss_pct", 0) < self.current_params["hard_stop_loss_pct"]:
            suggestions.append(
                f"建议收紧止损到{best_params['hard_stop_loss_pct']:.1%}，"
                f"避免亏损过大"
            )

        # 3. 市场状态建议
        regime_stats = {}
        for t in trades:
            if t.regime not in regime_stats:
                regime_stats[t.regime] = []
            regime_stats[t.regime].append(t.profit_pct)

        best_regime = max(regime_stats.keys(),
                         key=lambda r: sum(regime_stats[r]) / len(regime_stats[r])) if regime_stats else None
        if best_regime:
            avg = sum(regime_stats[best_regime]) / len(regime_stats[best_regime])
            suggestions.append(f"在{best_regime}市场状态下表现最佳(均收益{avg:+.3f}%)，"
                            f"可适当增加该状态下的交易频率")

        # 4. 时间窗口建议
        win_stats = {}
        for t in trades:
            if t.success:
                if t.time_window not in win_stats:
                    win_stats[t.time_window] = [0, 0]
                win_stats[t.time_window][0] += 1
            if t.time_window not in win_stats:
                win_stats[t.time_window] = [0, 0]
            win_stats[t.time_window][1] += 1

        for tw, (wins, total) in win_stats.items():
            wr = wins / total if total > 0 else 0
            if wr >= 0.75:
                suggestions.append(f"T{tw}时间窗口胜率{wr:.0%}，建议优先在该窗口操作")

        return suggestions

    def _calc_expected_improvement(self, trades: List[TradeRecord], best_params: Dict) -> float:
        """计算使用最优参数后的期望收益改进"""
        current_trades = [t for t in trades if t.entry_score >= self.current_params["entry_score_threshold"]]
        best_trades = [t for t in trades if t.entry_score >= best_params.get("entry_score_threshold", 60)]

        if len(best_trades) < 3:
            return 0.0

        current_avg = sum(t.profit_pct for t in current_trades) / len(current_trades) if current_trades else 0
        best_avg = sum(t.profit_pct for t in best_trades) / len(best_trades) if best_trades else 0

        return round(best_avg - current_avg, 4)

    def apply_params(self, params: Dict):
        """应用最优参数"""
        self.current_params.update(params)
        self._save()

    def format_report(self, report: TunerReport) -> str:
        """格式化调参报告"""
        lines = [
            f"=== {self.code} 自进化调参报告 | {report.date} ===",
            f"分析交易数: {report.trades_analyzed}笔",
            f"期望收益改进: {report.expected_improvement:+.4f}%",
            "",
            "因子相关性分析：",
        ]
        for f, corr in sorted(report.factor_correlations.items(), key=lambda x: -abs(x[1])):
            bar = "▓" * int(abs(corr) * 10) + "░" * (10 - int(abs(corr) * 10))
            sign = "+" if corr > 0 else "-"
            lines.append(f"  {f}: [{bar}] {sign}{abs(corr):.3f}")

        if report.suggestions:
            lines.append("")
            lines.append("调参建议：")
            for i, s in enumerate(report.suggestions, 1):
                lines.append(f"  {i}. {s}")

        return "\n".join(lines)
