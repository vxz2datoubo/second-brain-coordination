"""
自进化层 · 参数自动调优器
基于历史交易记录，自动调整因子权重、置信度阈值、参数

进化策略：
  1. 因子权重自适应（Pearson相关分析）
  2. 置信度阈值优化（基于胜率）
  3. 时间窗口权重调整
  4. 市场状态适配参数
  5. 每周生成进化报告
"""

import json
import os
import math
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORK_DIR, "data")
PARAM_HISTORY = os.path.join(DATA_DIR, "param_evolution.json")

# 默认因子权重
DEFAULT_PARAMS = {
    "factor_weights": {
        "F1_VWAP": 0.25,
        "F2_RSI": 0.20,
        "F3_VOL_PROFILE": 0.20,
        "F4_MOMENTUM": 0.15,
        "F5_DELTA": 0.10,
        "F6_GAP": 0.10,
    },
    "confidence_thresholds": {
        "A++": 90,
        "A": 75,
        "B": 60,
        "C": 45,
    },
    "time_window_weights": {
        "T1": 0.10,  # 开盘处理
        "T2": 0.25,  # 上午黄金
        "T3": 0.15,
        "T4": 0.05,  # 谨慎
        "T5": 0.10,  # 下午重启
        "T6": 0.25,  # 下午黄金
        "T7": 0.05,
        "T8": 0.05,  # 收尾
    },
    "regime_params": {
        "HIGH_VOL_RANGE": {
            "enabled": True,
            "min_confidence": "C",
            "max_slots": 3,
            "profit_target_pct": 1.5,
        },
        "TREND_UP": {
            "enabled": True,
            "min_confidence": "B",
            "max_slots": 2,
            "profit_target_pct": 1.0,
        },
        "TREND_DOWN": {
            "enabled": True,
            "min_confidence": "C",
            "max_slots": 3,
            "profit_target_pct": 2.0,
        },
        "LOW_VOL_RANGE": {
            "enabled": True,
            "min_confidence": "A",
            "max_slots": 2,
            "profit_target_pct": 0.5,
        },
        "EXTREME": {
            "enabled": False,
            "min_confidence": "D",
            "max_slots": 0,
            "profit_target_pct": 0.0,
        },
    },
    "stock_params": {
        "300418": {
            "min_signal_score": 60,
            "max_holding_minutes": 120,
            "profit_target_pct": 1.2,
            "stop_loss_pct": 1.5,
        },
        "300058": {
            "min_signal_score": 65,
            "max_holding_minutes": 100,
            "profit_target_pct": 1.0,
            "stop_loss_pct": 1.5,
        },
    },
}


@dataclass
class EvolvedParams:
    """进化后的参数快照"""
    date: str
    generation: int
    params: Dict
    performance_summary: Dict
    changes: List[str]
    reasoning: str


class AutoTuner:
    """
    自适应调参器
    分析最近 N 笔交易的因子分与盈利的关系
    找出最强/最弱的因子
    """

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.current_params = self._load_params()
        self.generation = self._get_generation()
        self.evolution_history: List[EvolvedParams] = []
        self._load_history()

    def _load_params(self) -> Dict:
        if os.path.exists(PARAM_HISTORY):
            try:
                with open(PARAM_HISTORY, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("current_params", DEFAULT_PARAMS)
            except Exception:
                pass
        return DEFAULT_PARAMS.copy()

    def _load_history(self):
        if os.path.exists(PARAM_HISTORY):
            try:
                with open(PARAM_HISTORY, "r", encoding="utf-8") as f:
                    data = json.load(f)
                history = data.get("history", [])
                self.evolution_history = [EvolvedParams(**h) for h in history]
            except Exception:
                pass

    def _save_params(self):
        data = {
            "current_params": self.current_params,
            "history": [asdict(h) for h in self.evolution_history],
        }
        with open(PARAM_HISTORY, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_generation(self) -> int:
        return len(self.evolution_history) + 1

    def analyze_factor_performance(self, records: List) -> Dict:
        """
        分析每个因子的表现
        计算因子分与盈利的相关性
        """
        if len(records) < 10:
            return {"note": "样本不足(<10笔)，使用默认参数"}

        factor_names = list(DEFAULT_PARAMS["factor_weights"].keys())
        results = {}

        for fname in factor_names:
            scores = []
            profits = []

            for r in records:
                # 从 signal_factors JSON 中提取
                sf = {}
                try:
                    sf = json.loads(r.signal_factors) if r.signal_factors else {}
                except Exception:
                    pass

                f_score = sf.get(fname, {}).get("score", 0)
                if f_score > 0:
                    scores.append(f_score)
                    profits.append(r.profit_pct)

            if len(scores) < 5:
                results[fname] = {"correlation": 0, "avg_profit_at_high": 0, "note": "样本不足"}
                continue

            # 计算相关系数（Pearson）
            corr = self._pearson(scores, profits)
            high_score_profit = sum(p for s, p in zip(scores, profits) if s >= 70) / max(1, sum(1 for s in scores if s >= 70))
            low_score_profit = sum(p for s, p in zip(scores, profits) if s < 40) / max(1, sum(1 for s in scores if s < 40))

            results[fname] = {
                "correlation": round(corr, 4),
                "avg_profit_at_high_score": round(high_score_profit, 4),
                "avg_profit_at_low_score": round(low_score_profit, 4),
                "sample_count": len(scores),
                "interpretation": self._interpret_corr(fname, corr, high_score_profit, low_score_profit),
            }

        return results

    def _pearson(self, xs: List[float], ys: List[float]) -> float:
        """计算皮尔逊相关系数"""
        if len(xs) != len(ys) or len(xs) < 3:
            return 0.0
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
        den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
        if den_x * den_y == 0:
            return 0.0
        return num / (den_x * den_y)

    def _interpret_corr(self, fname: str, corr: float, high_profit: float, low_profit: float) -> str:
        if corr > 0.3:
            return f"正相关(r={corr:.3f})，高分时盈利{high_profit:.3f}%>低分时{low_profit:.3f}%，应提高权重"
        elif corr < -0.2:
            return f"负相关(r={corr:.3f})，该因子预测反向，应降低权重"
        else:
            return f"相关性弱(r={corr:.3f})，维持现有权重"

    def evolve(self, records: List) -> Dict:
        """
        核心进化逻辑：分析历史 → 调整参数 → 保存新参数
        """
        changes = []
        reasoning_parts = []

        # 1. 因子权重进化
        factor_analysis = self.analyze_factor_performance(records)
        if "note" in factor_analysis:
            reasoning_parts.append("样本不足，保持现有参数")
        else:
            new_weights = self.current_params["factor_weights"].copy()
            for fname, analysis in factor_analysis.items():
                corr = analysis["correlation"]
                current_w = new_weights.get(fname, 0)

                if corr > 0.3:
                    new_w = min(current_w * 1.1, current_w + 0.05)
                    changes.append(f"{fname}: {current_w:.3f} → {new_w:.3f} (r={corr:.3f}, 提高)")
                elif corr < -0.2:
                    new_w = max(current_w * 0.85, current_w - 0.05)
                    changes.append(f"{fname}: {current_w:.3f} → {new_w:.3f} (r={corr:.3f}, 降低)")
                else:
                    new_w = current_w

                new_weights[fname] = round(new_w, 4)

            # 归一化权重
            total_w = sum(new_weights.values())
            new_weights = {k: round(v / total_w, 4) for k, v in new_weights.items()}
            self.current_params["factor_weights"] = new_weights

        # 2. 置信度阈值优化
        conf_analysis = self._optimize_confidence_thresholds(records)
        if conf_analysis.get("changed"):
            old_t = self.current_params["confidence_thresholds"].copy()
            self.current_params["confidence_thresholds"].update(conf_analysis["new_thresholds"])
            for k, v in conf_analysis["changed"].items():
                changes.append(f"置信度{k}阈值: {old_t[k]} → {v}")

        # 3. 统计摘要
        completed = [r for r in records if r.cover_price is not None]
        win_rate = sum(1 for r in completed if r.profit_abs > 0) / len(completed) if completed else 0
        total_profit = sum(r.profit_abs for r in completed)
        avg_profit = total_profit / len(completed) if completed else 0

        perf_summary = {
            "period": f"最近{len(records)}笔",
            "total_trades": len(completed),
            "win_rate": round(win_rate * 100, 2),
            "total_profit": round(total_profit, 2),
            "avg_profit": round(avg_profit, 4),
            "factor_analysis": factor_analysis,
        }

        # 4. 记录进化
        evo = EvolvedParams(
            date=date.today().isoformat(),
            generation=self.generation,
            params=self.current_params.copy(),
            performance_summary=perf_summary,
            changes=changes,
            reasoning="; ".join(reasoning_parts),
        )
        self.evolution_history.append(evo)
        self._save_params()

        return {
            "generation": self.generation,
            "changes": changes,
            "new_weights": self.current_params["factor_weights"],
            "new_thresholds": self.current_params["confidence_thresholds"],
            "performance_summary": perf_summary,
        }

    def _optimize_confidence_thresholds(self, records: List) -> Dict:
        """分析各置信度级别的表现，优化阈值"""
        completed = [r for r in records if r.cover_price is not None]
        if len(completed) < 10:
            return {"changed": {}}

        changed = {}
        new_thresholds = {}

        for conf in ["A++", "A", "B", "C"]:
            conf_records = [r for r in completed if r.confidence == conf]
            if len(conf_records) >= 3:
                avg_profit = sum(r.profit_abs for r in conf_records) / len(conf_records)
                win_rate = sum(1 for r in conf_records if r.profit_abs > 0) / len(conf_records)

                # 如果该级别胜率>70%且平均盈利>50元，考虑降低阈值
                if win_rate > 0.70 and avg_profit > 50:
                    old_t = self.current_params["confidence_thresholds"][conf]
                    # 下调5分
                    new_t = max(50, old_t - 5)
                    if new_t != old_t:
                        changed[conf] = new_t
                        new_thresholds[conf] = new_t
                elif win_rate < 0.40 and len(conf_records) >= 5:
                    # 胜率过低，上调阈值
                    old_t = self.current_params["confidence_thresholds"][conf]
                    new_t = old_t + 5
                    new_thresholds[conf] = new_t
                    changed[conf] = new_t
                else:
                    new_thresholds[conf] = self.current_params["confidence_thresholds"][conf]
            else:
                new_thresholds[conf] = self.current_params["confidence_thresholds"][conf]

        return {"changed": changed, "new_thresholds": new_thresholds}

    def get_current_params(self) -> Dict:
        return self.current_params

    def get_evolution_report(self) -> str:
        """生成进化报告"""
        lines = [
            f"# 自进化报告 · 第{self.generation}代",
            f"日期: {date.today().isoformat()}",
            f"",
            f"## 当前因子权重",
        ]
        for k, v in self.current_params["factor_weights"].items():
            lines.append(f"  {k}: {v:.4f}")

        if self.evolution_history:
            lines.append(f"")
            lines.append(f"## 最近进化记录")
            for evo in self.evolution_history[-3:]:
                lines.append(f"  第{evo.generation}代({evo.date}):")
                for c in evo.changes[:5]:
                    lines.append(f"    - {c}")
                lines.append(f"    胜率: {evo.performance_summary.get('win_rate', '?')}%")

        return "\n".join(lines)


# 全局单例
_tuner: Optional[AutoTuner] = None

def get_tuner() -> AutoTuner:
    global _tuner
    if _tuner is None:
        _tuner = AutoTuner()
    return _tuner
