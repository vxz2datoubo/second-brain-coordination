"""
reason_engine.py — 跨领域推理引擎
让AI大脑能够发现不同领域知识点之间的隐藏关联

核心机制:
1. 概念映射 (Concept Mapping): 识别不同领域之间的相似概念
2. 知识迁移 (Knowledge Transfer): 将一个领域的知识应用到另一个领域
3. 推理链构建 (Reasoning Chain): 构建跨领域的逻辑推理链
4. 隐喻识别 (Metaphor Recognition): 识别跨领域的隐喻关系
"""

import json
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Set
from collections import defaultdict


class ReasonEngine:
    """跨领域推理引擎"""
    
    # 领域关键词映射
    DOMAIN_KEYWORDS = {
        "finance": ["股票", "交易", "投资", "仓位", "止损", "盈利", "大盘", "K线", "MACD", "RSI", "波动"],
        "technology": ["AI", "代码", "系统", "算法", "数据", "模型", "机器学习", "深度学习", "神经网络"],
        "psychology": ["心理", "情绪", "认知", "偏见", "决策", "行为", "习惯", "思维", "记忆"],
        "economics": ["市场", "供需", "周期", "通胀", "利率", "政策", "趋势", "风险"],
        "philosophy": ["本质", "规律", "矛盾", "辩证", "因果", "逻辑", "认识", "实践"],
        "biology": ["进化", "适应", "竞争", "生态", "系统", "反馈", "平衡", "自然选择"],
    }
    
    # 跨领域类比模式
    ANALOGY_PATTERNS = [
        {"source": "biology", "target": "economy", "mapping": {"进化": "竞争", "适应": "调整", "自然选择": "市场淘汰"}},
        {"source": "psychology", "target": "finance", "mapping": {"恐惧": "止损", "贪婪": "追高", "认知偏见": "决策失误"}},
        {"source": "technology", "target": "biology", "mapping": {"迭代": "进化", "系统": "有机体", "反馈": "刺激-反应"}},
        {"source": "philosophy", "target": "strategy", "mapping": {"辩证": "分析", "矛盾": "问题", "对立统一": "权衡利弊"}},
    ]
    
    def __init__(self, graph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.state_path = data_dir / "reason_state.json"
        self.state = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"discovered_analogies": [], "reasoning_chains": [], "cross_domain_insights": []}
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def reason(
        self,
        topic: str,
        context_nodes: Optional[List[dict]] = None,
        depth: int = 3,
    ) -> dict:
        """执行跨领域推理
        
        Args:
            topic: 推理主题
            context_nodes: 上下文节点
            depth: 推理深度
        
        Returns:
            推理结果，包含类比、迁移知识、推理链
        """
        result = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "discovered_domains": [],
            "analogies": [],
            "knowledge_transfer": [],
            "reasoning_chain": [],
            "insights": [],
        }
        
        # 1. 识别主题涉及的领域
        domains = self._identify_domains(topic, context_nodes)
        result["discovered_domains"] = domains
        
        if len(domains) < 2:
            # 单领域，只做深度推理
            result["insights"].append(f"主题 '{topic}' 主要涉及 {domains[0] if domains else '未知'} 领域")
            return result
        
        # 2. 发现跨领域类比
        analogies = self._discover_analogies(domains, topic)
        result["analogies"] = analogies
        
        # 3. 知识迁移
        transfers = self._knowledge_transfer(domains, topic, analogies)
        result["knowledge_transfer"] = transfers
        
        # 4. 构建推理链
        chain = self._build_cross_domain_chain(topic, domains, analogies, transfers)
        result["reasoning_chain"] = chain
        
        # 5. 生成洞察
        insights = self._generate_insights(topic, domains, analogies, transfers)
        result["insights"] = insights
        
        # 保存状态
        self.state["discovered_analogies"].extend(analogies)
        self.state["reasoning_chains"].append({"topic": topic, "chain": chain})
        self._save()
        
        return result
    
    def _identify_domains(self, topic: str, context_nodes: Optional[List[dict]] = None) -> List[str]:
        """识别主题涉及的领域"""
        text = topic
        if context_nodes:
            for node in context_nodes:
                text += " " + node.get("title", "") + " " + node.get("content", "")
        text = text.lower()
        
        domains = []
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                domains.append((domain, score))
        
        domains.sort(key=lambda x: x[1], reverse=True)
        return [d[0] for d in domains[:3]]
    
    def _discover_analogies(self, domains: List[str], topic: str) -> List[dict]:
        """发现跨领域类比"""
        analogies = []
        
        for pattern in self.ANALOGY_PATTERNS:
            if pattern["source"] in domains and pattern["target"] in domains:
                analogy = {
                    "from": pattern["source"],
                    "to": pattern["target"],
                    "mappings": [],
                }
                for src_concept, tgt_concept in pattern["mapping"].items():
                    if src_concept in topic or tgt_concept in topic:
                        analogy["mappings"].append({
                            "source_concept": src_concept,
                            "target_concept": tgt_concept,
                            "relevance": "high",
                        })
                    else:
                        analogy["mappings"].append({
                            "source_concept": src_concept,
                            "target_concept": tgt_concept,
                            "relevance": "medium",
                        })
                
                if analogy["mappings"]:
                    analogies.append(analogy)
        
        # 如果没有预设类比，尝试从知识图谱中发现
        if not analogies and len(domains) >= 2:
            analogies.append({
                "from": domains[0],
                "to": domains[1] if len(domains) > 1 else domains[0],
                "mappings": [{"source_concept": topic, "target_concept": topic, "relevance": "potential"}],
                "note": "基于领域共性推断",
            })
        
        return analogies
    
    def _knowledge_transfer(
        self,
        domains: List[str],
        topic: str,
        analogies: List[dict],
    ) -> List[dict]:
        """知识迁移：将一个领域的知识应用到另一个领域"""
        transfers = []
        
        # 基于类比的知识迁移
        for analogy in analogies:
            from_domain = analogy["from"]
            to_domain = analogy["to"]
            
            # 搜索知识图谱中相关节点
            if self.graph:
                # 搜索源领域的知识
                src_nodes = self.graph.search_nodes(topic, field="title")
                for node in src_nodes[:3]:
                    transfers.append({
                        "knowledge": node.get("title", ""),
                        "from_domain": from_domain,
                        "to_domain": to_domain,
                        "application": f"将{from_domain}领域的 '{node.get('title', '')}' 应用于{to_domain}领域的{topic}",
                        "confidence": 0.7,
                    })
        
        return transfers
    
    def _build_cross_domain_chain(
        self,
        topic: str,
        domains: List[str],
        analogies: List[dict],
        transfers: List[dict],
    ) -> List[dict]:
        """构建跨领域推理链"""
        chain = []
        
        # 起点：问题陈述
        chain.append({
            "step": 1,
            "type": "problem",
            "content": f"问题：{topic}",
            "domains": domains,
        })
        
        # 第二步：领域分析
        chain.append({
            "step": 2,
            "type": "domain_analysis",
            "content": f"涉及领域：{' + '.join(domains)}",
            "details": [{"domain": d, "relevance": 1.0 / (i + 1)} for i, d in enumerate(domains)],
        })
        
        # 第三步：类比发现
        if analogies:
            chain.append({
                "step": 3,
                "type": "analogy",
                "content": f"发现{len(analogies)}个跨领域类比",
                "details": [{"from": a["from"], "to": a["to"]} for a in analogies[:2]],
            })
        
        # 第四步：知识迁移
        if transfers:
            chain.append({
                "step": 4,
                "type": "transfer",
                "content": f"知识迁移：{len(transfers)}条可应用知识",
                "details": [{"knowledge": t["knowledge"], "to_domain": t["to_domain"]} for t in transfers[:3]],
            })
        
        # 第五步：综合结论
        chain.append({
            "step": 5,
            "type": "synthesis",
            "content": "综合多领域知识得出结论",
        })
        
        return chain
    
    def _generate_insights(
        self,
        topic: str,
        domains: List[str],
        analogies: List[dict],
        transfers: List[dict],
    ) -> List[str]:
        """生成洞察"""
        insights = []
        
        # 基于领域的洞察
        if "finance" in domains and "psychology" in domains:
            insights.append("金融决策深受心理因素影响，需警惕认知偏见")
        
        if "biology" in domains and "technology" in domains:
            insights.append("技术系统的进化与生物进化有相似的迭代规律")
        
        if "economics" in domains and "psychology" in domains:
            insights.append("经济现象往往源于个体心理的集体效应")
        
        # 基于类比的洞察
        for analogy in analogies:
            insight = f"通过{analogy['from']}与{analogy['to']}的类比，可以获得新视角"
            insights.append(insight)
        
        # 基于迁移的洞察
        for transfer in transfers[:2]:
            insight = f"将'{transfer['knowledge']}'从{transfer['from_domain']}迁移到{transfer['to_domain']}"
            insights.append(insight)
        
        if not insights:
            insights.append(f"主题 '{topic}' 主要涉及 {', '.join(domains)} 领域，建议深耕单一领域")
        
        return insights
    
    def format_reasoning(self, result: dict) -> str:
        """格式化推理输出"""
        lines = []
        lines.append(f"🔮 跨领域推理报告")
        lines.append(f"{'='*50}")
        lines.append(f"主题: {result['topic']}")
        lines.append(f"发现领域: {', '.join(result['discovered_domains'])}")
        lines.append("")
        
        if result['analogies']:
            lines.append("🔗 跨领域类比:")
            for analogy in result['analogies']:
                lines.append(f"  {analogy['from']} ↔ {analogy['to']}")
                for m in analogy.get('mappings', [])[:3]:
                    lines.append(f"    {m['source_concept']} → {m['target_concept']} ({m['relevance']})")
            lines.append("")
        
        if result['reasoning_chain']:
            lines.append("📋 推理链:")
            for step in result['reasoning_chain']:
                lines.append(f"  {step['step']}. [{step['type']}] {step['content']}")
            lines.append("")
        
        if result['insights']:
            lines.append("💡 洞察:")
            for insight in result['insights']:
                lines.append(f"  • {insight}")
        
        return "\n".join(lines)
    
    def get_cross_domain_knowledge(self, node_id: str) -> dict:
        """获取某个知识点的跨领域关联"""
        if not self.graph:
            return {}
        
        node = self.graph.get_node(node_id)
        if not node:
            return {}
        
        # 获取邻居节点
        neighbors = self.graph.get_neighbors(node_id, depth=1)
        
        # 识别邻居节点的领域
        domain_nodes = defaultdict(list)
        for nid, neighbor in neighbors.get("nodes", {}).items():
            text = neighbor.get("title", "") + " " + neighbor.get("content", "")
            for domain, keywords in self.DOMAIN_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    domain_nodes[domain].append(neighbor)
        
        return {
            "node_id": node_id,
            "node_title": node.get("title", ""),
            "cross_domain_connections": dict(domain_nodes),
            "domains_connected": list(domain_nodes.keys()),
        }
