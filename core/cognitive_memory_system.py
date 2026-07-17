"""
cognitive_memory_system.py — 认知知识管理系统整合器
整合 Zettelkasten + PARA + SpacedRepetition + DecisionTree + CrossDomain + MetaCognition + Evolver
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from core.zettelkasten import Zettelkasten, get_zettelkasten
from core.para_system import PARASystem, PARA_CATEGORIES
from core.spaced_repetition import SpacedRepetition
from core.decision_tree import DecisionTreeEngine
from core.cross_domain_associator import CrossDomainAssociator, DOMAINS
from core.meta_cognition import MetaCognitionEngine, COGNITIVE_BIASES
from core.knowledge_evolver import KnowledgeEvolver


class CognitiveMemorySystem:
    """
    认知知识管理系统整合器
    
    整合五大系统:
    1. Zettelkasten — 原子化笔记 + 双向链接
    2. PARA — 知识分类 (Projects/Areas/Resources/Archives)
    3. SpacedRepetition — 间隔重复复习
    4. DecisionTree — 决策树推理
    5. CrossDomain — 跨领域联想
    6. MetaCognition — 元认知监控
    7. KnowledgeEvolver — 知识进化
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "second-brain"
        
        # 初始化各子系统
        self.zettel = get_zettelkasten(self.data_dir)
        self.para = PARASystem(self.data_dir)
        self.spaced = SpacedRepetition(self.data_dir)
        self.decision = DecisionTreeEngine(self.data_dir)
        self.cross_domain = CrossDomainAssociator(self.data_dir)
        self.meta = MetaCognitionEngine(self.data_dir)
        self.evolver = KnowledgeEvolver(self.data_dir)
    
    # ========== 原子化笔记操作 ==========
    
    def create_atomic_note(self, title: str, content: str, tags: Optional[List[str]] = None, 
                          source: str = "manual", importance: int = 3, 
                          para_category: str = "", add_to_review: bool = True) -> Tuple[str, List[str]]:
        """创建原子化笔记，并自动链接到PARA和复习系统"""
        # 创建笔记
        note_id, warnings = self.zettel.create_note(
            title=title, content=content, tags=tags, source=source,
            importance=importance, category=para_category
        )
        
        # 添加到间隔复习
        if add_to_review:
            self.spaced.add_card(note_id, title, category=para_category, importance=importance)
        
        # 添加到知识进化系统
        self.evolver.add_knowledge(title, content, category=para_category, 
                                   importance=importance, tags=tags)
        
        # 跨领域联想
        categories = [para_category] if para_category else []
        self.cross_domain.associate(content, note_id, categories)
        
        # 如果指定了PARA分类，添加到项目
        if para_category:
            self._link_to_para(note_id, para_category, title)
        
        return note_id, warnings
    
    def _link_to_para(self, note_id: str, para: str, title: str):
        """将笔记链接到PARA系统"""
        # 查找或创建对应的PARA项目
        items = self.para.get_items_by_para(para)
        if items:
            # 添加到第一个活跃项目
            for item in items:
                if item.status == "active":
                    self.para.add_item_to_list(item.id, note_id)
                    break
        else:
            # 创建新项目
            category_map = {"P": "交易计划", "A": "知识领域", "R": "研究资源", "Z": "归档"}
            item_id = self.para.create_item(
                para=para,
                category=category_map.get(para, para),
                title=title[:30],
                description=f"自动创建的项目 {datetime.now().strftime('%Y-%m-%d')}"
            )
            self.para.add_item_to_list(item_id, note_id)
    
    def search_and_link(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索并自动建立链接"""
        notes = self.zettel.search_notes(query, limit=limit)
        results = []
        
        for note in notes:
            # 获取链接笔记
            linked = self.zettel.get_linked_notes(note.id)
            backlinks = self.zettel.get_backlinks(note.id)
            
            results.append({
                "id": note.id,
                "title": note.title,
                "content": note.content[:100],
                "tags": note.tags,
                "linked_count": len(linked),
                "backlink_count": len(backlinks),
                "importance": note.importance,
                "created_at": note.created_at
            })
        
        return results
    
    def get_note_with_context(self, note_id: str) -> Dict:
        """获取笔记及其完整上下文"""
        note = self.zettel.get_note(note_id)
        if not note:
            return {"error": "Note not found"}
        
        linked = self.zettel.get_linked_notes(note_id)
        backlinks = self.zettel.get_backlinks(note_id)
        due_cards = self.spaced.get_due_cards(limit=5)
        
        # 检查元认知偏见
        meta_check = self.meta.check_cognitive_bias(
            note.content, 
            {"topic": note.title, "has_contrary_evidence": True}
        )
        
        # 检测领域
        domains = self.cross_domain.detect_domain(note.content)
        
        return {
            "note": {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "category": note.category,
                "importance": note.importance,
                "created_at": note.created_at,
                "source": note.source
            },
            "links": [{"id": n.id, "title": n.title} for n in linked],
            "backlinks": [{"id": n.id, "title": n.title} for n in backlinks],
            "domains": domains,
            "meta_check": {
                "detected_biases": meta_check.detected_biases,
                "reasoning_gaps": meta_check.reasoning_gaps,
                "confidence_adjustment": meta_check.confidence_adjustment
            },
            "review_status": "due" if any(c["note_id"] == note_id for c in due_cards) else "ok"
        }
    
    # ========== 复习操作 ==========
    
    def get_review_queue(self) -> List[Dict]:
        """获取复习队列"""
        due_cards = self.spaced.get_due_cards(limit=20)
        queue = []
        
        for card in due_cards:
            note = self.zettel.get_note(card["note_id"])
            if note:
                # 获取元认知检查
                meta_check = self.meta.check_cognitive_bias(
                    note.content,
                    {"topic": note.title, "has_contrary_evidence": True}
                )
                
                queue.append({
                    "note_id": card["note_id"],
                    "title": note.title,
                    "content": note.content,
                    "importance": card.get("importance", 3),
                    "ease_factor": card.get("ease_factor", 2.5),
                    "repetitions": card.get("repetitions", 0),
                    "cognitive_warnings": meta_check.recommendations[:2]
                })
        
        return queue
    
    def record_review(self, note_id: str, rating: int) -> Dict:
        """记录复习结果"""
        result = self.spaced.record_review(note_id, rating)
        
        # 更新知识进化系统
        success = rating >= 3
        self.evolver.access_knowledge(note_id, application_success=success)
        
        return result
    
    # ========== 决策树操作 ==========
    
    def simulate_decision(self, context: Dict) -> Dict:
        """模拟交易决策"""
        # 构建交易决策树（如果尚未构建）
        if not self.decision.current_scenario:
            self.decision.build_trading_scenario()
        
        # 执行模拟
        result = self.decision.simulate(context)
        
        # 元认知检查
        meta_check = self.meta.check_cognitive_bias(
            str(context),
            {"topic": "交易决策", "has_contrary_evidence": True}
        )
        
        result["meta_check"] = {
            "warnings": meta_check.recommendations,
            "confidence_adjustment": meta_check.confidence_adjustment
        }
        
        return result
    
    # ========== 跨领域联想操作 ==========
    
    def get_cross_domain_insights(self, topic: str, context: str = "") -> List[Dict]:
        """获取跨领域洞察"""
        domains = self.cross_domain.detect_domain(context or topic)
        insights = []
        
        if len(domains) >= 2:
            domain_list = list(domains.keys())
            concept_links = self.cross_domain.find_conceptual_links(domain_list)
            
            for d1, d2, description in concept_links:
                insights.append({
                    "source_domain": d1,
                    "target_domain": d2,
                    "description": description,
                    "strength": min(domains[d1], domains[d2])
                })
        
        return insights
    
    # ========== 知识进化操作 ==========
    
    def consolidate_knowledge(self) -> Dict:
        """整合知识"""
        return self.evolver.consolidate_knowledge()
    
    def get_knowledge_insights(self) -> Dict:
        """获取知识洞察"""
        stats = self.evolver.get_evolution_stats()
        forgotten = self.evolver.get_forgotten_knowledge()[:5]
        
        # PARA分类统计
        para_stats = self.para.get_stats()
        
        # Zettelkasten统计
        zettel_stats = self.zettel.get_stats()
        
        return {
            "evolution": stats,
            "forgotten": [{"id": n["id"], "title": n["title"]} for n in forgotten],
            "para": para_stats,
            "zettel": zettel_stats,
            "review_due": self.spaced.get_stats()["due_today"]
        }
    
    # ========== 整体报告 ==========
    
    def generate_daily_report(self) -> str:
        """生成每日认知知识报告"""
        lines = ["# 认知知识管理系统 — 每日报告", ""]
        lines.append(f"**日期**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        
        # 统计概览
        zettel_stats = self.zettel.get_stats()
        para_stats = self.para.get_stats()
        review_stats = self.spaced.get_stats()
        evolution_stats = self.evolver.get_evolution_stats()
        
        lines.append("## 📊 统计概览")
        lines.append(f"- 原子化笔记: {zettel_stats['total_notes']}个")
        lines.append(f"- 总链接数: {zettel_stats['total_links']}个")
        lines.append(f"- PARA项目: {para_stats['total']}个")
        lines.append(f"- 复习队列: {review_stats['due_today']}个")
        lines.append(f"- 知识节点: {evolution_stats['total_nodes']}个")
        lines.append("")
        
        # PARA分类
        lines.append("## 📁 PARA分类")
        for para, info in PARA_CATEGORIES.items():
            count = para_stats.get(para, {}).get("count", 0)
            lines.append(f"- [{para}] {info['icon']} {info['name']}: {count}项")
        lines.append("")
        
        # 复习提醒
        if review_stats["due_today"] > 0:
            lines.append(f"## ⏰ 复习提醒 ({review_stats['due_today']}个待复习)")
            lines.append("")
        
        # 遗忘知识
        forgotten = self.evolver.get_forgotten_knowledge()[:3]
        if forgotten:
            lines.append("## 🧠 遗忘知识")
            for node in forgotten:
                lines.append(f"- {node.get('title', '')} (掌握度: {node.get('mastery', 0):.0%})")
            lines.append("")
        
        # 跨域洞察
        lines.append("## 🔗 跨领域概念地图")
        concept_map = self.cross_domain.build_concept_map()
        lines.append(f"- 活跃领域: {len([n for n in concept_map['nodes'] if n['connections'] > 0])}")
        lines.append(f"- 概念链接: {len(concept_map['edges'])}")
        
        return "\n".join(lines)
    
    def get_full_stats(self) -> Dict:
        """获取完整统计"""
        return {
            "zettelkasten": self.zettel.get_stats(),
            "para": self.para.get_stats(),
            "spaced_repetition": self.spaced.get_stats(),
            "evolution": self.evolver.get_evolution_stats(),
            "meta_cognition": self.meta.get_overall_assessment()
        }


def get_cognitive_memory_system(data_dir: Optional[Path] = None) -> CognitiveMemorySystem:
    """获取认知记忆系统实例"""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "second-brain"
    return CognitiveMemorySystem(data_dir)
