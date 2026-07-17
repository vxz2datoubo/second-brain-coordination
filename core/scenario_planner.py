"""
scenario_planner.py — 多路径情景推演引擎
==========================================
顶级人类思维的核心：面对不确定的未来，不是预测一条路，而是
推演所有可能的情景，评估每个情景的概率和影响，制定相应策略。
这是大奖章基金和桥水达里奥的核心方法论之一。

核心理论：
1. 情景规划 (Scenario Planning)：达里奥的"有意义的工作和有意义的人际关系"
2. 蒙特卡洛模拟：概率分布的未来模拟
3. 决策树分析：多阶段决策的路径优化
4. 反脆弱思维：考虑极端情况和黑天鹅

设计理念：
- 像将军一样思考：战前推演所有可能的战场情况
- 像经济学家一样思考：考虑多种宏观情景
- 像科学家一样思考：假设-验证-迭代
"""

import json
import uuid
import math
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Scenario:
    """情景"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    probability: float = 0.0  # 主观概率 0-1
    impact: float = 0.0       # 影响程度 0-1
    triggers: List[str] = field(default_factory=list)  # 触发条件
    timeline: str = ""        # 时间线
    indicators: List[str] = field(default_factory=list)  # 观察指标
    actions: Dict[str, str] = field(default_factory=dict)  # 触发后的行动


@dataclass
class ScenarioPlan:
    """情景推演计划"""
    base_case: Scenario = None
    bull_case: Scenario = None
    bear_case: Scenario = None
    black_swan: Scenario = None
    scenarios: List[Scenario] = field(default_factory=list)
    recommended_strategy: str = ""
    risk_limit: str = ""
    monitoring_plan: List[dict] = field(default_factory=list)


@dataclass
class DecisionNode:
    """决策树节点"""
    decision_id: str = ""
    description: str = ""
    options: List[dict] = field(default_factory=list)  # {label, probability, payoff}
    expected_value: float = 0.0
    best_option: str = ""
    risk_adjusted_score: float = 0.0


class ScenarioPlanner:
    """多路径情景推演引擎
    
    核心能力：
    1. 情景生成 — 基于当前市场状态生成多种可能情景
    2. 概率评估 — 评估每个情景的主观概率
    3. 影响分析 — 分析每个情景对持仓的影响
    4. 策略制定 — 为每个情景制定应对策略
    5. 决策树分析 — 多阶段决策的最优路径
    6. 蒙特卡洛模拟 — 大规模随机模拟验证
    7. 指标监控 — 设定观察指标，实时监控情景演变
    """
    
    # 典型情景模板
    TEMPLATES = {
        "bull_market": {
            "name": "牛市情景",
            "description": "市场持续上涨，赚钱效应明显",
            "typical_triggers": ["政策利好", "资金入场", "业绩超预期"],
            "typical_actions": ["持有或加仓", "减少做T", "扩大止盈位"]
        },
        "bear_market": {
            "name": "熊市情景",
            "description": "市场持续下跌，亏钱效应明显",
            "typical_triggers": ["政策利空", "资金出逃", "业绩不及预期"],
            "typical_actions": ["减仓或清仓", "增加做T", "收窄止损位"]
        },
        "range_bound": {
            "name": "震荡情景",
            "description": "市场区间震荡，无明显趋势",
            "typical_triggers": ["无重大消息", "多空平衡", "资金观望"],
            "typical_actions": ["高抛低吸", "增加交易频率", "控制仓位"]
        },
        "breakout_up": {
            "name": "向上突破情景",
            "description": "股价突破关键阻力，打开上涨空间",
            "typical_triggers": ["放量突破", "板块轮动", "龙头效应"],
            "typical_actions": ["顺势加仓", "持有待涨", "追击涨停"]
        },
        "breakout_down": {
            "name": "向下突破情景",
            "description": "股价跌破关键支撑，进入下跌通道",
            "typical_triggers": ["放量破位", "恐慌抛售", "利空配合"],
            "typical_actions": ["止损减仓", "等待企稳", "不要抄底"]
        },
        "black_swan": {
            "name": "黑天鹅情景",
            "description": "极端事件导致市场剧烈波动",
            "typical_triggers": ["战争", "疫情", "金融危机", "政策突变"],
            "typical_actions": ["立即止损", "保留现金", "等待机会"]
        }
    }
    
    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.state_path = data_dir / "scenario_planner_state.json"
        self.state = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "scenario_plans": {},  # stock -> plan
                "decision_trees": [],   # 决策树记录
                "monte_carlo_results": [], # 蒙特卡洛结果
                "meta": {"total_plans": 0, "total_decisions": 0}
            }
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    # ========== 核心推演方法 ==========
    
    def create_scenario_plan(
        self,
        stock: str,
        current_price: float,
        market_state: dict,
        position: Optional[dict] = None
    ) -> ScenarioPlan:
        """创建情景推演计划
        
        Args:
            stock: 股票代码
            current_price: 当前价格
            market_state: 市场状态 {trend, volatility, sentiment}
            position: 持仓情况（可选）
        
        Returns:
            ScenarioPlan: 情景推演计划
        """
        plan = ScenarioPlan()
        
        # 1. 分析当前状态
        trend = market_state.get("trend", "neutral")
        volatility = market_state.get("volatility", "medium")
        sentiment = market_state.get("sentiment", "neutral")
        
        # 2. 生成基础情景
        scenarios = self._generate_scenarios(trend, volatility, sentiment)
        
        # 3. 评估概率
        scenarios = self._assess_probabilities(scenarios, market_state)
        
        # 4. 评估影响
        scenarios = self._assess_impacts(scenarios, current_price, position)
        
        # 5. 分类情景
        for s in scenarios:
            if s.name == "基准情景":
                plan.base_case = s
            elif s.name == "牛市情景":
                plan.bull_case = s
            elif s.name == "熊市情景":
                plan.bear_case = s
            elif s.name == "黑天鹅":
                plan.black_swan = s
        
        plan.scenarios = scenarios
        
        # 6. 制定策略
        plan.recommended_strategy = self._generate_strategy(scenarios, position)
        plan.risk_limit = self._generate_risk_limit(scenarios, position)
        plan.monitoring_plan = self._generate_monitoring_plan(scenarios)
        
        # 记录
        self.state["scenario_plans"][stock] = {
            "timestamp": datetime.now().isoformat(),
            "current_price": current_price,
            "scenarios": [
                {"name": s.name, "prob": s.probability, "impact": s.impact}
                for s in scenarios
            ],
            "strategy": plan.recommended_strategy
        }
        self.state["meta"]["total_plans"] += 1
        self._save()
        
        return plan
    
    def _generate_scenarios(
        self,
        trend: str,
        volatility: str,
        sentiment: str
    ) -> List[Scenario]:
        """生成情景"""
        scenarios = []
        
        # 基准情景
        base = Scenario(
            name="基准情景",
            description="最可能的情况：延续当前趋势",
            probability=0.5,
            timeline="1-5天"
        )
        scenarios.append(base)
        
        # 基于趋势选择情景
        if trend == "up":
            # 上涨趋势
            bull = Scenario(
                name="牛市情景",
                description="持续上涨，突破前高",
                triggers=["政策利好", "业绩超预期", "资金持续流入"],
                timeline="5-20天"
            )
            scenarios.append(bull)
            
            # 回撤情景
            pullback = Scenario(
                name="回撤情景",
                description="上涨后回撤整固",
                triggers=["获利了结", "技术性调整"],
                timeline="3-10天"
            )
            scenarios.append(pullback)
        
        elif trend == "down":
            # 下跌趋势
            bear = Scenario(
                name="熊市情景",
                description="持续下跌，跌破支撑",
                triggers=["业绩下滑", "资金出逃", "利空消息"],
                timeline="5-20天"
            )
            scenarios.append(bear)
            
            # 反弹情景
            rebound = Scenario(
                name="反弹情景",
                description="超跌后技术性反弹",
                triggers=["超卖信号", "抄底资金入场"],
                timeline="1-5天"
            )
            scenarios.append(rebound)
        
        else:
            # 震荡
            range_up = Scenario(
                name="区间上沿",
                description="向上触及区间上沿后回落",
                triggers=["触及压力位", "量能不足"],
                timeline="1-3天"
            )
            scenarios.append(range_up)
            
            range_down = Scenario(
                name="区间下沿",
                description="向下触及区间下沿后反弹",
                triggers=["触及支撑位", "资金抄底"],
                timeline="1-3天"
            )
            scenarios.append(range_down)
        
        # 黑天鹅（总是要考虑的）
        black_swan = Scenario(
            name="黑天鹅",
            description="极端事件导致剧烈波动",
            triggers=["战争", "疫情", "政策突变", "金融危机"],
            timeline="随时"
        )
        scenarios.append(black_swan)
        
        return scenarios
    
    def _assess_probabilities(
        self,
        scenarios: List[Scenario],
        market_state: dict
    ) -> List[Scenario]:
        """评估概率"""
        total = 0
        for s in scenarios:
            prob = self._calculate_scenario_probability(s, market_state)
            s.probability = prob
            total += prob
        
        # 归一化
        if total > 0:
            for s in scenarios:
                s.probability = round(s.probability / total, 2)
        
        return scenarios
    
    def _calculate_scenario_probability(
        self,
        scenario: Scenario,
        market_state: dict
    ) -> float:
        """计算情景概率"""
        base_prob = 0.25
        
        trend = market_state.get("trend", "neutral")
        volatility = market_state.get("volatility", "medium")
        
        if scenario.name == "基准情景":
            prob = 0.45
            if trend == "up":
                prob += 0.05
            elif trend == "down":
                prob -= 0.05
        
        elif scenario.name == "牛市情景":
            prob = 0.2
            if trend == "up":
                prob += 0.15
            if volatility == "high":
                prob += 0.1
        
        elif scenario.name == "熊市情景":
            prob = 0.2
            if trend == "down":
                prob += 0.15
            if volatility == "high":
                prob += 0.1
        
        elif scenario.name == "黑天鹅":
            prob = 0.05  # 低概率但高影响
            if volatility == "high":
                prob += 0.05
        
        else:
            prob = base_prob
        
        return max(0.01, min(0.8, prob))
    
    def _assess_impacts(
        self,
        scenarios: List[Scenario],
        current_price: float,
        position: Optional[dict] = None
    ) -> List[Scenario]:
        """评估影响"""
        if not position:
            # 无持仓，简化评估
            for s in scenarios:
                if "牛" in s.name:
                    s.impact = 0.3
                elif "熊" in s.name:
                    s.impact = -0.3
                elif "黑天鹅" in s.name:
                    s.impact = -0.5
                else:
                    s.impact = 0.1
            return scenarios
        
        # 有持仓时评估
        holding = position.get("shares", 0)
        cost = position.get("cost", current_price)
        if holding == 0:
            return scenarios
        
        for s in scenarios:
            if "牛" in s.name:
                # 牛市情景：盈利
                expected_gain = position.get("expected_gain", 0.05)
                s.impact = expected_gain
            elif "熊" in s.name:
                # 熊市情景：亏损
                expected_loss = position.get("expected_loss", -0.05)
                s.impact = expected_loss
            elif "回撤" in s.name:
                # 回撤：中等亏损
                s.impact = -0.03
            elif "反弹" in s.name:
                # 反弹：中等盈利
                s.impact = 0.03
            elif "黑天鹅" in s.name:
                # 黑天鹅：重大亏损
                s.impact = -0.15
            else:
                # 基准：小幅盈利
                s.impact = 0.02
        
        return scenarios
    
    def _generate_strategy(
        self,
        scenarios: List[Scenario],
        position: Optional[dict] = None
    ) -> str:
        """生成策略"""
        # 加权期望收益
        expected_return = sum(s.probability * s.impact for s in scenarios)
        
        # 最大损失
        max_loss = min(s.impact for s in scenarios)
        
        # 最大收益
        max_gain = max(s.impact for s in scenarios)
        
        # 基于期望值和风险生成策略
        if expected_return > 0.05:
            if max_loss > -0.1:
                return "持有为主，可适当加仓"
            else:
                return "持有，控制仓位"
        elif expected_return > 0:
            return "谨慎持有，减少操作"
        elif max_loss < -0.1:
            return "减仓或清仓，等待机会"
        else:
            return "观望为主，等待明确信号"
    
    def _generate_risk_limit(
        self,
        scenarios: List[Scenario],
        position: Optional[dict] = None
    ) -> str:
        """生成风险限制"""
        # 找出黑天鹅情景
        black_swan = next((s for s in scenarios if "黑天鹅" in s.name), None)
        
        limits = []
        
        if black_swan and black_swan.probability > 0.05:
            limits.append(f"黑天鹅情景概率{black_swan.probability:.0%}，需设止损线")
        
        # 最大可承受损失
        if position:
            max_loss = position.get("max_acceptable_loss", 0.02)
            limits.append(f"单日最大损失不超过{max_loss:.0%}")
        
        if not limits:
            return "风险可控，无需特别限制"
        
        return "; ".join(limits)
    
    def _generate_monitoring_plan(
        self,
        scenarios: List[Scenario]
    ) -> List[dict]:
        """生成监控计划"""
        plan = []
        
        for s in scenarios:
            if s.probability > 0.1:
                plan.append({
                    "scenario": s.name,
                    "probability": s.probability,
                    "triggers": s.triggers,
                    "indicators": s.indicators,
                    "action": s.actions.get("default", "观察")
                })
        
        return plan
    
    # ========== 决策树分析 ==========
    
    def analyze_decision_tree(
        self,
        decision_points: List[dict],
        current_state: dict
    ) -> DecisionNode:
        """分析决策树
        
        Args:
            decision_points: 决策点列表 [{id, description, options: [{label, probability, payoff}]}]
            current_state: 当前状态
        
        Returns:
            DecisionNode: 决策树根节点
        """
        if not decision_points:
            return DecisionNode(description="无决策点")
        
        root = DecisionNode(
            decision_id="root",
            description="初始决策"
        )
        
        # 递归分析
        self._analyze_node(root, decision_points, 0)
        
        self.state["decision_trees"].append({
            "timestamp": datetime.now().isoformat(),
            "root": root.decision_id,
            "expected_value": root.expected_value
        })
        self.state["meta"]["total_decisions"] += 1
        self._save()
        
        return root
    
    def _analyze_node(
        self,
        node: DecisionNode,
        decision_points: List[dict],
        depth: int
    ):
        """递归分析决策节点"""
        if depth >= len(decision_points):
            return
        
        point = decision_points[depth]
        node.decision_id = point.get("id", f"d{depth}")
        node.description = point.get("description", "")
        
        options = point.get("options", [])
        for opt in options:
            label = opt.get("label", "")
            prob = opt.get("probability", 0.5)
            payoff = opt.get("payoff", 0)
            
            # 计算期望值
            node.options.append({
                "label": label,
                "probability": prob,
                "payoff": payoff,
                "expected_contribution": prob * payoff
            })
        
        # 计算最优选项
        best = max(node.options, key=lambda x: x["expected_contribution"])
        node.best_option = best["label"]
        
        # 累计期望值
        node.expected_value = sum(o["expected_contribution"] for o in node.options)
        
        # 风险调整分数 (考虑方差)
        if len(node.options) > 1:
            payouts = [o["payoff"] for o in node.options]
            probas = [o["probability"] for o in node.options]
            
            # 期望
            mean = sum(p * pp for p, pp in zip(payouts, probas))
            # 方差
            variance = sum(probas[i] * (payouts[i] - mean) ** 2 for i in range(len(payouts)))
            # 风险调整 = 期望 - 0.5 * 方差（风险厌恶系数）
            node.risk_adjusted_score = mean - 0.5 * variance
        else:
            node.risk_adjusted_score = node.expected_value
    
    # ========== 蒙特卡洛模拟 ==========
    
    def monte_carlo_simulation(
        self,
        initial_capital: float,
        position_size: float,
        num_simulations: int = 10000,
        time_horizon_days: int = 20,
        daily_volatility: float = 0.02,
        daily_drift: float = 0.0005
    ) -> dict:
        """蒙特卡洛模拟
        
        模拟未来可能的价格路径，评估风险和收益分布
        
        Args:
            initial_capital: 初始资金
            position_size: 仓位比例
            num_simulations: 模拟次数
            time_horizon_days: 模拟天数
            daily_volatility: 日波动率
            daily_drift: 日漂移（均值）
        
        Returns:
            dict: 模拟结果统计
        """
        results = []
        
        for _ in range(num_simulations):
            capital = initial_capital
            position_value = capital * position_size
            
            for _ in range(time_horizon_days):
                # 随机价格变动（几何布朗运动）
                daily_return = daily_drift + daily_volatility * random.gauss(0, 1)
                position_value *= (1 + daily_return)
                
                # 模拟T仓收益（简化）
                if random.random() < 0.3:  # 30%概率做T
                    t_profit = position_value * 0.01 * random.choice([-1, 1])
                    position_value += t_profit
            
            final_value = (initial_capital - capital * position_size) + position_value
            total_return = (final_value - initial_capital) / initial_capital
            results.append({
                "final_value": final_value,
                "total_return": total_return
            })
        
        # 统计分析
        returns = [r["total_return"] for r in results]
        returns.sort()
        
        # 计算分位数
        percentiles = {
            "p5": returns[int(len(returns) * 0.05)],
            "p25": returns[int(len(returns) * 0.25)],
            "p50": returns[int(len(returns) * 0.50)],
            "p75": returns[int(len(returns) * 0.75)],
            "p95": returns[int(len(returns) * 0.95)]
        }
        
        # VaR (Value at Risk)
        var_5 = returns[int(len(returns) * 0.05)]
        
        # 胜率
        win_rate = sum(1 for r in returns if r > 0) / len(returns)
        
        # 平均收益
        avg_return = sum(returns) / len(returns)
        
        # 最大回撤估计
        max_loss = min(returns)
        
        result = {
            "num_simulations": num_simulations,
            "time_horizon_days": time_horizon_days,
            "initial_capital": initial_capital,
            "position_size": position_size,
            "percentiles": percentiles,
            "var_5": var_5,
            "win_rate": win_rate,
            "avg_return": avg_return,
            "max_loss": max_loss,
            "sharpe_estimate": avg_return / (daily_volatility * math.sqrt(time_horizon_days)) if daily_volatility > 0 else 0
        }
        
        self.state["monte_carlo_results"].append({
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
        
        return result
    
    # ========== 格式化输出 ==========
    
    def format_scenario_plan(self, plan: ScenarioPlan) -> str:
        """格式化情景计划"""
        lines = []
        lines.append(f"🎯 多路径情景推演")
        lines.append(f"{'='*50}")
        lines.append("")
        
        # 情景汇总
        lines.append("📊 情景概率与影响:")
        for s in plan.scenarios:
            impact_str = f"+{s.impact:.1%}" if s.impact > 0 else f"{s.impact:.1%}"
            lines.append(f"  {s.name}: 概率{s.probability:.0%} | 影响{impact_str}")
        lines.append("")
        
        # 基准情景
        if plan.base_case:
            base = plan.base_case
            lines.append(f"📌 基准情景:")
            lines.append(f"  {base.description}")
            lines.append(f"  触发条件: {', '.join(base.triggers) if base.triggers else '无'}")
            lines.append("")
        
        # 牛市情景
        if plan.bull_case:
            bull = plan.bull_case
            lines.append(f"🐂 牛市情景 ({bull.probability:.0%}):")
            lines.append(f"  {bull.description}")
            lines.append(f"  触发条件: {', '.join(bull.triggers)}")
            lines.append("")
        
        # 熊市情景
        if plan.bear_case:
            bear = plan.bear_case
            lines.append(f"🐻 熊市情景 ({bear.probability:.0%}):")
            lines.append(f"  {bear.description}")
            lines.append(f"  触发条件: {', '.join(bear.triggers)}")
            lines.append("")
        
        # 黑天鹅
        if plan.black_swan:
            swan = plan.black_swan
            lines.append(f"🦢 黑天鹅 ({swan.probability:.0%}):")
            lines.append(f"  {swan.description}")
            lines.append("")
        
        # 策略
        lines.append(f"💡 推荐策略:")
        lines.append(f"  {plan.recommended_strategy}")
        lines.append("")
        
        # 风险限制
        lines.append(f"⚠️ 风险限制:")
        lines.append(f"  {plan.risk_limit}")
        lines.append("")
        
        # 监控计划
        if plan.monitoring_plan:
            lines.append("👁️ 监控计划:")
            for item in plan.monitoring_plan[:3]:
                lines.append(f"  • {item['scenario']}: 概率{item['probability']:.0%}")
                lines.append(f"    观察指标: {', '.join(item.get('indicators', [])) or '无'}")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_monte_carlo(self, result: dict) -> str:
        """格式化蒙特卡洛结果"""
        lines = []
        lines.append(f"🎲 蒙特卡洛模拟结果")
        lines.append(f"{'='*50}")
        lines.append(f"模拟次数: {result['num_simulations']:,}")
        lines.append(f"时间范围: {result['time_horizon_days']}天")
        lines.append(f"初始资金: {result['initial_capital']:,.0f}")
        lines.append("")
        
        lines.append("📊 收益分布:")
        for pct, value in result["percentiles"].items():
            pct_str = pct.replace("p", "P")
            lines.append(f"  {pct_str}: {value:.2%}")
        lines.append("")
        
        lines.append(f"📉 风险指标:")
        lines.append(f"  VaR(5%): {result['var_5']:.2%}")
        lines.append(f"  最大损失: {result['max_loss']:.2%}")
        lines.append("")
        
        lines.append(f"📈 收益指标:")
        lines.append(f"  平均收益: {result['avg_return']:.2%}")
        lines.append(f"  胜率: {result['win_rate']:.1%}")
        lines.append(f"  预估夏普比: {result['sharpe_estimate']:.2f}")
        
        return "\n".join(lines)
    
    # ========== 统计 ==========
    
    def get_stats(self) -> dict:
        """获取统计"""
        return {
            "total_plans": self.state["meta"]["total_plans"],
            "total_decisions": self.state["meta"]["total_decisions"],
            "recent_plans": len(self.state.get("scenario_plans", {})),
            "monte_carlo_runs": len(self.state["monte_carlo_results"])
        }
