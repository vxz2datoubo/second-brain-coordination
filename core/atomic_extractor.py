"""
atomic_extractor.py - Atomic Knowledge Extractor
Simple version without dataclass issues
"""

import json
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class AtomicExtractor:
    """Atom-level knowledge extractor"""
    
    CAUSAL_CONNECTORS = ["因为", "所以", "导致", "引起", "因此", "由于", "如果", "则", "当"]
    RULE_INDICATORS = ["必须", "应该", "禁止", "不得", "不要", "原则", "规律", "规则", "铁律", "红线"]
    EXCEPTION_INDICATORS = ["但是", "然而", "除非", "除非要", "不过", "只是"]
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.state_path = data_dir / "atomic_state.json"
        self.state = self._load()
    
    def _load(self):
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "entities": {},
                "relations": {},
                "atoms": {},
                "causal_chains": {},
                "conditionals": {},
                "meta": {"total": 0}
            }
    
    def _save(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def extract(self, text, source="manual"):
        """Extract atomic knowledge from text"""
        result = {"source": source, "atoms": [], "entities": [], "causal_chains": [], "conditionals": []}
        
        # Split into sentences
        sentences = re.split(r"[。！？；\n]+", text)
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            
            # Classify sentence type
            sent_type = self._classify(sent)
            
            # Extract tags
            tags = self._extract_tags(sent)
            
            # Create atom
            atom_id = str(uuid.uuid4())[:8]
            atom = {
                "id": atom_id,
                "content": sent,
                "type": sent_type,
                "tags": tags,
                "confidence": self._calc_confidence(sent, sent_type),
                "source": source
            }
            
            self.state["atoms"][atom_id] = atom
            result["atoms"].append(atom)
            
            # Extract causal chains
            chains = self._extract_causal_chains(sent)
            for chain in chains:
                chain_id = str(uuid.uuid4())[:8]
                self.state["causal_chains"][chain_id] = chain
                result["causal_chains"].append(chain)
            
            # Extract conditionals
            conds = self._extract_conditionals(sent)
            for cond in conds:
                cond_id = str(uuid.uuid4())[:8]
                self.state["conditionals"][cond_id] = cond
                result["conditionals"].append(cond)
        
        self.state["meta"]["total"] += 1
        self._save()
        return result
    
    def _classify(self, sent):
        if any(k in sent for k in self.RULE_INDICATORS):
            return "rule"
        if any(k in sent for k in ["如果", "当", "每当", "只要"]):
            return "conditional"
        if any(k in sent for k in self.EXCEPTION_INDICATORS):
            return "exception"
        if any(k in sent for k in self.CAUSAL_CONNECTORS):
            return "causal"
        return "fact"
    
    def _extract_tags(self, sent):
        tags = []
        if any(k in sent for k in ["风险", "亏损", "止损", "熔断"]):
            tags.append("风险")
        if any(k in sent for k in ["盈利", "收益", "赚钱", "止盈"]):
            tags.append("收益")
        if any(k in sent for k in ["买入", "卖出", "建仓", "加仓"]):
            tags.append("交易操作")
        if any(k in sent for k in ["消息", "新闻", "公告", "政策"]):
            tags.append("消息面")
        if any(k in sent for k in ["量能", "成交量", "放量", "缩量"]):
            tags.append("量价")
        if any(k in sent for k in ["追高", "追涨", "抄底", "止损"]):
            tags.append("交易原则")
        return tags[:8]
    
    def _calc_confidence(self, sent, sent_type):
        conf = 0.6
        if len(sent) >= 10 and len(sent) <= 100:
            conf += 0.1
        if any(k in sent for k in ["必须", "禁止", "铁律", "红线"]):
            conf += 0.15
        if re.search(r"\d+", sent):
            conf += 0.1
        if sent_type == "rule":
            conf += 0.1
        return min(1.0, conf)
    
    def _extract_causal_chains(self, sent):
        chains = []
        has_cause = any(k in sent for k in ["因为", "由于", "当"])
        has_effect = any(k in sent for k in ["所以", "因此", "则"])
        
        if has_cause and has_effect:
            parts = re.split(r"[因为所以由于因此当则]", sent)
            if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                chains.append({
                    "cause": parts[0].strip(),
                    "effect": parts[1].strip(),
                    "confidence": 0.8
                })
        return chains
    
    def _extract_conditionals(self, sent):
        conds = []
        if "如果" in sent or "当" in sent:
            parts = re.split(r"[如果当]", sent)
            if len(parts) >= 2:
                cond_part = parts[1].strip()
                if "则" in cond_part:
                    sub_parts = cond_part.split("则")
                    condition = sub_parts[0].strip()
                    consequence = sub_parts[1].strip() if len(sub_parts) > 1 else ""
                else:
                    condition = cond_part
                    consequence = ""
                
                unless = ""
                if "除非" in sent:
                    ex_parts = sent.split("除非")
                    if len(ex_parts) > 1:
                        unless = ex_parts[1].strip()
                
                conds.append({
                    "condition": condition,
                    "consequence": consequence,
                    "unless": unless
                })
        return conds
    
    def query(self, keyword):
        """Query knowledge"""
        results = []
        k_lower = keyword.lower()
        for atom_id, atom in self.state["atoms"].items():
            if k_lower in atom["content"].lower():
                results.append(atom)
        return results
    
    def infer(self, premise):
        """Inference from knowledge"""
        inferences = []
        for chain_id, chain in self.state["causal_chains"].items():
            if premise in chain["cause"]:
                inferences.append({
                    "type": "causal",
                    "if": chain["cause"],
                    "then": chain["effect"]
                })
        return inferences
    
    def fuse_with_graph(self, graph):
        """Fuse with knowledge graph"""
        count = 0
        for atom_id, atom in self.state["atoms"].items():
            if atom["type"] in ["rule", "conditional", "causal"]:
                node = {
                    "id": atom_id,
                    "type": "knowledge_atom",
                    "title": atom["content"][:50],
                    "content": atom["content"],
                    "category": "atomic_wisdom",
                    "tags": atom.get("tags", []),
                    "importance": int(atom["confidence"] * 5)
                }
                graph.add_node(node)
                graph.auto_link(node)
                count += 1
        graph.commit()
        return {"fused": count}
    
    def format_result(self, result):
        lines = ["=" * 50, "ATOMIC EXTRACTION RESULT", "=" * 50]
        lines.append(f"Source: {result['source']}")
        lines.append(f"Atoms: {len(result['atoms'])}")
        
        for atom in result["atoms"][:5]:
            lines.append(f"  [{atom['type']}] {atom['content'][:60]}...")
        
        if result["causal_chains"]:
            lines.append(f"\nCausal chains: {len(result['causal_chains'])}")
            for c in result["causal_chains"][:3]:
                lines.append(f"  {c['cause'][:30]}... -> {c['effect'][:30]}...")
        
        if result["conditionals"]:
            lines.append(f"\nConditionals: {len(result['conditionals'])}")
            for c in result["conditionals"][:2]:
                lines.append(f"  IF {c['condition'][:30]}... THEN {c['consequence'][:30]}...")
        
        return "\n".join(lines)
    
    def stats(self):
        return {
            "total_atoms": len(self.state["atoms"]),
            "total_chains": len(self.state["causal_chains"]),
            "total_conditionals": len(self.state["conditionals"]),
            "by_type": {
                t: sum(1 for a in self.state["atoms"].values() if a["type"] == t)
                for t in ["fact", "rule", "conditional", "exception", "causal"]
            }
        }
