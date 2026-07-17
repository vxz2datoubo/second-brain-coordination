"""
para_system.py — PARA分类体系实现
Projects / Areas / Resources / Archives
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


# PARA分类定义
PARA_CATEGORIES = {
    "P": {"name": "Projects", "desc": "当前进行的项目/交易计划", "color": "blue", "icon": "📋"},
    "A": {"name": "Areas", "desc": "需要持续关注的领域", "color": "green", "icon": "🎯"},
    "R": {"name": "Resources", "desc": "学习资料和研究资源", "color": "yellow", "icon": "📚"},
    "Z": {"name": "Archives", "desc": "已完成/归档的内容", "color": "gray", "icon": "📦"}
}

# 交易专用分类映射
TRADING_PARAMS = {
    "P_projects": ["交易计划", "策略开发", "回测项目", "今日操作"],
    "A_areas": ["规则库", "教训总结", "股票监控", "风控管理"],
    "R_resources": ["技术分析", "基本面", "市场研究", "量化工具"],
    "Z_archives": ["历史交易", "已结束项目", "过时策略"]
}


@dataclass
class PARAItem:
    id: str
    para: str  # P/A/R/Z
    category: str
    title: str
    description: str
    items: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: str = "active"  # active/paused/completed/archived
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""
    metadata: Dict = field(default_factory=dict)


class PARASystem:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "second-brain" / "para"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.data_dir / "para_index.json"
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"P": {}, "A": {}, "R": {}, "Z": {}, "items": {}, "stats": {"total": 0}}
    
    def _save_index(self):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def create_item(self, para: str, category: str, title: str, description: str = "", tags: Optional[List[str]] = None) -> str:
        import uuid
        item_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        item = PARAItem(id=item_id, para=para, category=category, title=title, description=description, tags=tags or [], created_at=now, updated_at=now)
        
        if para not in self.index:
            self.index[para] = {}
        self.index[para][item_id] = asdict(item)
        self.index["items"][item_id] = asdict(item)
        self.index["stats"]["total"] = len(self.index["items"])
        
        self._save_index()
        return item_id
    
    def add_item_to_list(self, para_item_id: str, note_id: str) -> bool:
        if para_item_id in self.index["items"]:
            self.index["items"][para_item_id].setdefault("items", []).append(note_id)
            self.index["items"][para_item_id]["updated_at"] = datetime.now().isoformat()
            self._save_index()
            return True
        return False
    
    def get_items_by_para(self, para: str) -> List[PARAItem]:
        items = []
        for item_id, item_data in self.index.get(para, {}).items():
            items.append(PARAItem(**item_data))
        return items
    
    def archive_item(self, item_id: str) -> bool:
        if item_id in self.index["items"]:
            item = self.index["items"][item_id]
            para = item["para"]
            old_para = para
            
            # 移动到Z分类
            item["para"] = "Z"
            item["status"] = "archived"
            item["updated_at"] = datetime.now().isoformat()
            
            # 从原分类移除
            if item_id in self.index.get(old_para, {}):
                del self.index[old_para][item_id]
            
            # 添加到Z分类
            self.index.setdefault("Z", {})[item_id] = item
            
            self._save_index()
            return True
        return False
    
    def get_stats(self) -> Dict:
        stats = {}
        for para in ["P", "A", "R", "Z"]:
            stats[para] = {"count": len(self.index.get(para, {})), "name": PARA_CATEGORIES[para]["name"]}
        stats["total"] = self.index["stats"]["total"]
        return stats
    
    def generate_report(self) -> str:
        lines = ["# PARA知识分类报告", ""]
        for para in ["P", "A", "R", "Z"]:
            info = PARA_CATEGORIES[para]
            count = len(self.index.get(para, {}))
            lines.append(f"## {info['icon']} {info['name']} ({para}) - {count}项")
            lines.append(f"*{info['desc']}*")
            for item_id, item in self.index.get(para, {}).items():
                lines.append(f"- {item.get('title', '')}: {item.get('description', '')[:50]}")
            lines.append("")
        return "\n".join(lines)
