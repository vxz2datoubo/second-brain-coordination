# retrieval.py
# 因果智慧大脑 - 检索引擎
# 版本: v1.0 | 日期: 2026-07-07

import json
from pathlib import Path
from typing import Dict, List, Optional

class WisdomRetriever:
    def __init__(self, base_path='F:/aidanao/wisdom-brain'):
        self.base_path = Path(base_path)
        self.index_file = self.base_path / 'knowledge' / '_index.json'
        self._load_index()
    
    def _load_index(self):
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8-sig') as f:
                self.index = json.load(f)
        else:
            self.index = {'nodes': [], 'by_category': {}, 'by_tag': {}}
    
    def retrieve(self, query, category=None, tags=None, limit=5):
        results = []
        query_lower = query.lower()
        query_keywords = set(query_lower.replace('，', ' ').replace('。', ' ').replace(',', ' ').split())
        
        for node_ref in self.index.get('nodes', []):
            node = self._load_node(node_ref['id'])
            if not node:
                continue
            
            score = 0
            
            if category and node.get('category') != category:
                continue
            
            if tags:
                node_tags = set(node.get('tags', []))
                if not node_tags.intersection(set(tags)):
                    continue
            
            content_lower = node.get('content', '').lower()
            title_lower = node.get('title', '').lower()
            
            if any(kw in title_lower for kw in query_keywords if kw):
                score += 10
            
            for kw in query_keywords:
                if kw and kw in content_lower:
                    score += 3
            
            for kw in query_keywords:
                if kw and kw in node.get('tags', []):
                    score += 5
            
            if node.get('importance') == '高':
                score += 2
            
            if score > 0:
                results.append({'node': node, 'score': score, 'matched_keywords': [kw for kw in query_keywords if kw and kw in content_lower]})
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def _load_node(self, node_id):
        categories = ['causal', 'game', 'analogy', 'counterfactual', 'worldview']
        for cat in categories:
            path = self.base_path / 'knowledge' / cat / f'{node_id}.json'
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return None
    
    def retrieve_by_category(self, category, limit=10):
        results = []
        for node_ref in self.index.get('nodes', []):
            if node_ref.get('category') == category:
                node = self._load_node(node_ref['id'])
                if node:
                    results.append(node)
        return results[:limit]
    
    def retrieve_by_tags(self, tags, limit=10):
        results = []
        target_tags = set(tags)
        for node_ref in self.index.get('nodes', []):
            node_tags = set(node_ref.get('tags', []))
            if target_tags.intersection(node_tags):
                node = self._load_node(node_ref['id'])
                if node:
                    results.append(node)
        return results[:limit]
