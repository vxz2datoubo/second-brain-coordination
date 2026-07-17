"""
mind_models.py - 顶级人类心智模型库
==========================================
整合巴菲特/芒格/达里奥/索罗斯/塔勒布等顶级思维，
让第二大脑具备真正的人类智慧深度。
"""

import json
import math
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


@dataclass
class CognitiveBias:
    name: str
    description: str
    manifestation: str
    antidote: str


@dataclass
class MentalModel:
    id: str
    name: str
    philosopher: str
    core_principle: str
    application_rules: List[str]
    questions: List[str]
    examples: List[str]
    biases_to_avoid: List[str]
    keywords: List[str]


@dataclass
class WisdomRule:
    rule: str
    source: str
    explanation: str
    exception: str = ""


COGNITIVE_BIASES = [
    CognitiveBias("损失厌恶", "损失带来的痛苦是同等收益的2-2.5倍", "亏损死拿不卖，盈利一点就跑", "预先设定止损位"),
    CognitiveBias("确认偏误", "寻找支持观点的信息，忽视反面证据", "持仓后只看到利好", "主动寻找反对意见"),
    CognitiveBias("代表性启发", "根据近期模式推断未来", "连续涨就觉得还要涨", "回到基础概率"),
    CognitiveBias("可得性启发", "容易想起最近发生的事", "最近亏钱就觉得都亏", "查看历史统计"),
    CognitiveBias("后见之明偏误", "事后认为显而易见", "卖后涨了说早知道", "记录决策理由"),
    CognitiveBias("过度自信", "高估自己的判断", "重仓单吊", "分散投资"),
    CognitiveBias("禀赋效应", "对拥有的东西估值更高", "成本价成锚点", "忘记成本"),
    CognitiveBias("锚定效应", "过度依赖第一个数字", "开盘价成锚", "独立思考"),
    CognitiveBias("群体思维", "受群体意见影响", "大家都买跟着买", "逆向思维"),
    CognitiveBias("近期偏误", "过度重视近期事件", "今天跌觉得趋势变", "看更长周期"),
    CognitiveBias("情绪化决策", "让恐惧贪婪主导", "恐慌时卖贪婪时买", "机械执行规则"),
]


MENTAL_MODELS = [
    MentalModel("moat", "护城河思维", "巴菲特",
        "投资有宽护城河的公司",
        ["识别品牌/技术/网络效应护城河", "护城河是否在扩大", "竞争壁垒是否可持续"],
        ["竞争优势是什么?", "5年后对手能否复制?", "护城河在变宽还是变窄?"],
        ["茅台品牌护城河", "腾讯社交网络"], ["近期偏误", "过度自信"],
        ["竞争优势", "护城河", "壁垒", "品牌"]),
    
    MentalModel("intrinsic_value", "内在价值", "巴菲特",
        "价格围绕价值波动，最终回归价值",
        ["保守估算内在价值", "安全边际买入", "等待大幅低估时买入"],
        ["股票值多少钱?", "价格是否有安全边际?", "市场为什么给这个价?"],
        ["2013年茅台120元远低于内在价值"], ["锚定效应", "禀赋效应"],
        ["内在价值", "安全边际", "估值", "低估"]),
    
    MentalModel("long_term", "长期主义", "巴菲特",
        "时间是优秀公司的朋友",
        ["用闲钱投资", "忽略短期波动", "复利需要时间"],
        ["5年后公司会怎样?", "决定5年后还有意义吗?", "能持有10年吗?"],
        ["持有可口可乐30年"], ["近期偏误", "情绪化决策"],
        ["长期", "持有", "复利", "5年"]),
    
    MentalModel("bear_case_first", "逆向分析", "芒格",
        "先分析下跌风险，再看上涨空间",
        ["投资前想会亏多少", "最坏情况能接受吗", "什么会让投资失败"],
        ["能跌多少?", "什么会让归零?", "历史上有类似失败吗?"],
        ["买入前先看最大回撤"], ["过度自信", "损失厌恶"],
        ["下跌风险", "最坏情况", "压力测试"]),
    
    MentalModel("inversion", "倒置思维", "芒格",
        "想成功，先想如何失败，然后避免",
        ["想盈利先想亏钱", "列出失败方式避免", "成功=避免愚蠢错误"],
        ["可能失败的方式?", "犯过什么愚蠢错误?", "别人怎么亏钱的?"],
        ["不要做空不要借钱炒股"], ["过度自信", "近期偏误"],
        ["逆向", "避免失败", "愚蠢"]),
    
    MentalModel("multi_models", "多元思维", "芒格",
        "用多学科思维模型交叉验证",
        ["不只用金融模型", "引入心理学/工程学视角", "不同模型结论一致更可信"],
        ["还有什么角度?", "物理学家怎么看?", "历史类似案例?"],
        ["用物理学理解均衡", "用心理学理解泡沫"], ["确认偏误", "群体思维"],
        ["多学科", "交叉验证", "多角度"]),
    
    MentalModel("shock_test", "压力测试", "达里奥",
        "把未来所有情境推演一遍",
        ["不只考虑基准情景", "考虑乐观/悲观/黑天鹅", "为每种情景准备预案"],
        ["最坏情况会怎样?", "如果暴跌50%呢?", "有什么没想到的风险?"],
        ["情景规划", "风险平价"], ["过度自信", "近期偏误"],
        ["压力测试", "最坏情况", "情景"]),
    
    MentalModel("reflexivity", "反身性", "索罗斯",
        "市场参与创造现实，而非反映现实",
        ["理解情绪影响基本面", "识别自我强化循环", "趋势早期介入顶部前退出"],
        ["主流偏见是什么?", "价格如何影响基本面?", "趋势在自我强化吗?"],
        ["2007房地产泡沫", "2015A股泡沫"], ["近期偏误", "锚定效应"],
        ["反身性", "自我强化", "偏见", "趋势"]),
    
    MentalModel("boom_bust", "繁荣崩溃", "索罗斯",
        "每个泡沫有相似生命周期",
        ["识别泡沫早期", "不可持续时退出", "不预测何时破裂"],
        ["这是泡沫吗?", "趋势是否过度?", "何时该恐惧?"],
        ["郁金香泡沫", "南海泡沫"], ["过度自信", "损失厌恶"],
        ["泡沫", "繁荣", "崩溃"]),
    
    MentalModel("barbell", "杠铃策略", "塔勒布",
        "极端保守+极端激进，避开中间",
        ["90%极度保守", "10%极度冒险", "中间地带最危险"],
        ["极端情况是什么?", "能承受最大损失吗?", "有非线性收益吗?"],
        ["卖出虚值期权做彩票"], ["过度自信", "损失厌恶"],
        ["杠铃", "极端", "保守", "高赔率"]),
    
    MentalModel("antifragile", "反脆弱", "塔勒布",
        "能从冲击混乱中获益",
        ["寻找能从中获益的策略", "避免脆弱系统", "让时间成为朋友"],
        ["系统在压力下怎样?", "能从意外获益吗?", "谁是脆弱的?"],
        ["长期持有期权"], ["过度自信"],
        ["反脆弱", "压力", "混乱", "黑天鹅"]),
    
    MentalModel("first_principles", "第一性原理", "马斯克",
        "从最基本真理出发推理",
        ["剥去表象回本质", "不接受大家都这么做", "问本质是什么"],
        ["本质是什么?", "能拆解到最基本吗?", "假设有错误吗?"],
        ["特斯拉从物理成本定价"], ["群体思维", "锚定效应"],
        ["本质", "拆解", "假设", "第一性"]),
    
    MentalModel("zero_sum", "零和博弈", "博弈论",
        "一方所得必为另一方所失",
        ["短线交易你赚谁亏的", "问你凭什么能赢", "考虑对手策略"],
        ["谁在亏钱?", "我的优势是什么?", "对手在想什么?"],
        ["短线交易是零和"], ["过度自信"],
        ["零和", "对手", "优势"]),
    
    MentalModel("chicken_game", "斗鸡博弈", "博弈论",
        "两方对峙，谁先退让谁输",
        ["识别虚张声势", "确认对方会退让时出击", "不在悬崖边前进"],
        ["对方真会硬撑吗?", "谁最后退让?", "我该退还是坚持?"],
        ["多空关键位博弈"], ["过度自信", "损失厌恶"],
        ["对峙", "突破", "虚张声势"]),
    
    MentalModel("staghunt", "智猪博弈", "博弈论",
        "小猪等大猪后搭便车",
        ["大资金后跟进", "等待明确信号再行动", "不冲最前面"],
        ["有大资金在后面吗?", "信号确认了吗?", "我该先动还是等?"],
        ["跟随机构", "等突破确认"], ["过度自信", "规划谬误"],
        ["跟随", "搭便车", "等待信号"]),
]


WISDOM_RULES = [
    WisdomRule("别人贪婪时恐惧，别人恐惧时贪婪", "巴菲特", "大众情绪是反向指标", "不要过早逆向"),
    WisdomRule("第一原则：永远不要亏钱", "巴菲特", "保护本金是复利基础", "短期波动不等于亏钱"),
    WisdomRule("如果不想持有十年，就不要持有一分钟", "巴菲特", "长期逻辑是持仓基础", "短线T仓是另一套"),
    WisdomRule("想成功先想如何失败，然后避免", "芒格", "识别风险比追逐收益更重要", ""),
    WisdomRule("知道什么不知道的比聪明更重要", "芒格", "能力圈边界清晰更重要", ""),
    WisdomRule("痛苦+反思=进步", "达里奥", "亏损是学习机会", ""),
    WisdomRule("最坏情况的代价比你想的要高", "达里奥", "低估风险是失败常见原因", ""),
    WisdomRule("错误不可怕，不能及时纠正才可怕", "索罗斯", "及时止损承认错误", ""),
    WisdomRule("重要的是对时赚多少，错时亏多少", "索罗斯", "不对称性是核心", ""),
    WisdomRule("赚钱不需预测，只需等待机会下注", "塔勒布", "耐心等待极端机会", ""),
    WisdomRule("真正的风险是你想象不到的", "塔勒布", "黑天鹅思维", ""),
]


class MentalModelLibrary:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.state_path = data_dir / "mind_models_state.json"
        self.state = self._load()
        self._build_index()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"usage_history": [], "model_effectiveness": {}, "biases_detected": {}, "meta": {"total_uses": 0, "insights_applied": 0}}
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def _build_index(self):
        self.keyword_index = defaultdict(list)
        for model in MENTAL_MODELS:
            for kw in model.keywords:
                self.keyword_index[kw].append(model.id)
    
    def select_models(self, situation: str, context: Optional[dict] = None) -> List[tuple]:
        scores = defaultdict(float)
        situation_lower = situation.lower()
        
        for model in MENTAL_MODELS:
            keyword_matches = sum(1 for kw in model.keywords if kw in situation_lower)
            if keyword_matches > 0:
                scores[model.id] += keyword_matches * 0.3
            
            if model.id in self.state.get("model_effectiveness", {}):
                scores[model.id] += self.state["model_effectiveness"][model.id] * 0.1
        
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(self.get_model(mid), score) for mid, score in ranked if score > 0][:5]
    
    def get_model(self, model_id: str) -> Optional[MentalModel]:
        for model in MENTAL_MODELS:
            if model.id == model_id:
                return model
        return None
    
    def apply_model(self, model_id: str, situation: str, data: Optional[dict] = None) -> dict:
        model = self.get_model(model_id)
        if not model:
            return {"error": f"未找到模型: {model_id}"}
        
        result = {
            "model_id": model.id, "model_name": model.name, "philosopher": model.philosopher,
            "core_principle": model.core_principle, "answers": [], "warnings": [],
            "action_recommendation": self._synthesize_action(model)
        }
        
        for question in model.questions:
            result["answers"].append({"question": question, "guidance": "需要根据当前情况思考"})
        
        for bias_name in model.biases_to_avoid:
            bias = self._get_bias(bias_name)
            if bias:
                result["warnings"].append({"bias": bias_name, "description": bias.description, "antidote": bias.antidote})
        
        return result
    
    def _get_bias(self, bias_name: str) -> Optional[CognitiveBias]:
        for bias in COGNITIVE_BIASES:
            if bias.name == bias_name:
                return bias
        return None
    
    def _synthesize_action(self, model: MentalModel) -> str:
        action_map = {
            "bear_case_first": "风险优先：先评估最大损失",
            "long_term": "长期视角：忽略短期波动",
            "moat": "护城河视角：评估竞争优势",
            "inversion": "逆向思考：先想如何失败",
            "reflexivity": "反身性视角：关注市场情绪",
            "barbell": "杠铃策略：要么极度保守要么极度激进",
            "first_principles": "第一性原理：回归本质"
        }
        return action_map.get(model.id, f"应用{model.name}原则决策")
    
    def detect_bias(self, situation: str) -> List[dict]:
        detected = []
        situation_lower = situation.lower()
        
        bias_signals = {
            "近期偏误": ["最近", "这几天", "今天大涨"],
            "过度自信": ["很有把握", "肯定", "一定", "绝对"],
            "损失厌恶": ["不想亏", "害怕", "死拿"],
            "确认偏误": ["我觉得", "我相信"],
            "锚定效应": ["开盘价", "成本价"],
            "群体思维": ["大家都在买", "都说会涨"]
        }
        
        for bias_name, signals in bias_signals.items():
            for signal in signals:
                if signal in situation_lower:
                    bias = self._get_bias(bias_name)
                    if bias:
                        detected.append({"bias": bias_name, "signal": signal, "description": bias.description, "antidote": bias.antidote})
                        self.state["biases_detected"][bias_name] = self.state["biases_detected"].get(bias_name, 0) + 1
                        break
        
        self._save()
        return detected
    
    def analyze_with_wisdom(self, situation: str) -> List[dict]:
        results = []
        situation_lower = situation.lower()
        
        for rule in WISDOM_RULES:
            if any(kw in situation_lower for kw in ["贪婪", "恐惧", "恐慌", "乐观", "悲观"]):
                if "贪婪" in rule.rule or "恐惧" in rule.rule:
                    results.append({"rule": rule.rule, "source": rule.source, "explanation": rule.explanation})
            
            if any(kw in situation_lower for kw in ["风险", "亏损", "亏钱"]):
                if "亏" in rule.rule or "风险" in rule.source:
                    results.append({"rule": rule.rule, "source": rule.source, "explanation": rule.explanation})
        
        return results[:5]
    
    def multi_perspective_analysis(self, situation: str, num_perspectives: int = 5) -> List[dict]:
        perspectives = []
        models = self.select_models(situation)[:num_perspectives]
        
        for model, score in models:
            analysis = self.apply_model(model.id, situation)
            perspectives.append({
                "model_name": model.name, "philosopher": model.philosopher,
                "core_principle": model.core_principle, "analysis": analysis, "relevance_score": score
            })
        
        return perspectives
    
    def record_outcome(self, model_id: str, was_correct: bool):
        if model_id not in self.state["model_effectiveness"]:
            self.state["model_effectiveness"][model_id] = 0.0
        
        old_score = self.state["model_effectiveness"][model_id]
        n = self.state["meta"]["total_uses"] + 1
        new_score = (old_score * (n - 1) + (1.0 if was_correct else 0.0)) / n
        self.state["model_effectiveness"][model_id] = new_score
        self.state["meta"]["total_uses"] += 1
        if was_correct:
            self.state["meta"]["insights_applied"] += 1
        self._save()
    
    def format_analysis(self, situation: str, perspectives: List[dict]) -> str:
        lines = [f"多角度心智模型分析", f"{'='*50}", f"情境: {situation}", ""]
        
        for i, p in enumerate(perspectives, 1):
            lines.append(f"视角{i}: {p['philosopher']} - {p['model_name']}")
            lines.append(f"  核心: {p['core_principle']}")
            
            if p.get('analysis', {}).get('warnings'):
                lines.append("  需警惕的认知偏差:")
                for w in p['analysis']['warnings'][:2]:
                    lines.append(f"    - {w['bias']}: {w['antidote']}")
            
            if p.get('analysis', {}).get('action_recommendation'):
                lines.append(f"  建议: {p['analysis']['action_recommendation']}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_stats(self) -> dict:
        return {
            "total_models": len(MENTAL_MODELS),
            "total_biases": len(COGNITIVE_BIASES),
            "total_wisdom_rules": len(WISDOM_RULES),
            "most_used_models": sorted(self.state.get("model_effectiveness", {}).items(), key=lambda x: x[1], reverse=True)[:5],
            "model_accuracy": self.state["meta"]["insights_applied"] / max(self.state["meta"]["total_uses"], 1)
        }