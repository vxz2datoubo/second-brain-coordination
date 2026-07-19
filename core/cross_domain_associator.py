"""
cross_domain_associator.py — 跨领域联想引擎
发现不同领域知识点之间的隐藏关联
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Association:
    source_id: str
    target_id: str
    source_domain: str
    target_domain: str
    association_type: str  # "conceptual" | "analogical" | "causal" | "temporal"
    strength: float  # 0-1
    description: str = ""
    metadata: Dict = field(default_factory=dict)


# 领域定义
DOMAINS = {
    "trading": {"name": "交易", "keywords": ["买入", "卖出", "止损", "仓位", "T仓", "追高", "回调"]},
    "psychology": {"name": "心理", "keywords": ["恐惧", "贪婪", "心态", "情绪", "压力", "冷静"]},
    "math": {"name": "数学", "keywords": ["概率", "期望", "均值", "方差", "分布", "统计"]},
    "physics": {"name": "物理", "keywords": ["惯性", "动量", "能量", "震荡", "趋势", "突破"]},
    "biology": {"name": "生物", "keywords": ["进化", "适应", "生存", "竞争", "生态", "平衡"]},
    "game": {"name": "博弈", "keywords": ["对手", "策略", "均衡", "信息", "竞合", "博弈"]},
    "systems": {"name": "系统", "keywords": ["反馈", "循环", "稳定", "混沌", "涌现", "自适应"]}
}


class CrossDomainAssociator:
    """跨领域联想引擎"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "second-brain"
        self.associations_file = self.data_dir / "cross_domain_associations.json"
        self.associations = self._load_associations()
        self._build_keyword_index()
    
    def _load_associations(self) -> List[Dict]:
        try:
            with open(self.associations_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def _save_associations(self):
        self.associations_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.associations_file, "w", encoding="utf-8") as f:
            json.dump(self.associations, f, ensure_ascii=False, indent=2)
    
    def _build_keyword_index(self):
        """构建关键词索引"""
        self.keyword_index = defaultdict(list)
        for domain, info in DOMAINS.items():
            for keyword in info["keywords"]:
                self.keyword_index[keyword].append(domain)
    
    def detect_domain(self, text: str) -> Dict[str, float]:
        """检测文本涉及的领域及其强度"""
        text_lower = text.lower()
        scores = defaultdict(float)
        
        for domain, info in DOMAINS.items():
            matches = sum(1 for kw in info["keywords"] if kw in text_lower)
            if matches > 0:
                scores[domain] = matches / len(info["keywords"])
        
        return dict(scores)
    
    def find_conceptual_links(self, domains: List[str]) -> List[Tuple[str, str]]:
        """查找跨领域的概念链接"""
        links = []
        
        # 预定义的概念映射
        conceptual_map = {
            ("trading", "psychology"): "交易中的情绪管理类似心理博弈",
            ("trading", "math"): "交易期望值与概率统计相关",
            ("trading", "physics"): "价格动量类似物理惯性",
            ("trading", "game"): "交易是零和博弈",
            ("psychology", "biology"): "心理防御机制类似生物适应性",
            ("math", "physics"): "物理定律可用数学描述",
            ("game", "systems"): "博弈论是复杂系统的一部分"
        }
        
        for i, d1 in enumerate(domains):
            for d2 in domains[i+1:]:
                if (d1, d2) in conceptual_map:
                    links.append((d1, d2, conceptual_map[(d1, d2)]))
                elif (d2, d1) in conceptual_map:
                    links.append((d1, d2, conceptual_map[(d2, d1)]))
        
        return links
    
    def associate(self, note_content: str, note_id: str, categories: List[str]) -> List[Association]:
        """分析笔记并生成跨领域联想"""
        associations = []
        domains = self.detect_domain(note_content)
        
        if len(domains) >= 2:
            # 找到跨领域关联
            domain_list = list(domains.keys())
            concept_links = self.find_conceptual_links(domain_list)
            
            for d1, d2, description in concept_links:
                strength = min(domains[d1], domains[d2])
                
                # 检查是否已存在
                exists = any(
                    a.get("source_domain") == d1 and a.get("target_domain") == d2
                    for a in self.associations
                )
                
                if not exists:
                    assoc = Association(
                        source_id=note_id,
                        target_id="",
                        source_domain=d1,
                        target_domain=d2,
                        association_type="conceptual",
                        strength=strength,
                        description=description
                    )
                    self.associations.append(assoc.__dict__)
                    associations.append(assoc)
        
        if associations:
            self._save_associations()
        
        return associations
    
    def get_related_notes_by_domain(self, note_id: str, note_domains: List[str]) -> List[Dict]:
        """根据领域获取相关笔记"""
        related = []
        
        for assoc in self.associations:
            if assoc["source_domain"] in note_domains:
                related.append({
                    "domain": assoc["target_domain"],
                    "type": assoc["association_type"],
                    "description": assoc["description"],
                    "strength": assoc["strength"]
                })
        
        return related
    
    def generate_insight(self, domains: List[str], context: str) -> str:
        """基于跨领域联想生成洞察"""
        if len(domains) < 2:
            return ""
        
        insights = []
        
        for d1, d2, description in self.find_conceptual_links(domains):
            insight = f"【跨域联想】{DOMAINS[d1]['name']} + {DOMAINS[d2]['name']}: {description}"
            insights.append(insight)
        
        return "\n".join(insights)
    
    def build_concept_map(self) -> Dict:
        """构建概念地图"""
        domain_connections = defaultdict(list)
        
        for assoc in self.associations:
            d1 = assoc["source_domain"]
            d2 = assoc["target_domain"]
            domain_connections[d1].append(d2)
            domain_connections[d2].append(d1)
        
        nodes = []
        for domain, info in DOMAINS.items():
            nodes.append({
                "id": domain,
                "name": info["name"],
                "connections": len(set(domain_connections[domain]))
            })
        
        edges = []
        seen = set()
        for assoc in self.associations:
            key = tuple(sorted([assoc["source_domain"], assoc["target_domain"]]))
            if key not in seen:
                seen.add(key)
                edges.append({
                    "source": assoc["source_domain"],
                    "target": assoc["target_domain"],
                    "strength": assoc["strength"]
                })
        
        return {"nodes": nodes, "edges": edges}
    
    def get_stats(self) -> Dict:
        return {
            "total_associations": len(self.associations),
            "domain_coverage": {d: sum(1 for a in self.associations if d in [a["source_domain"], a["target_domain"]]) for d in DOMAINS.keys()},
            "concept_map": self.build_concept_map()
        }
