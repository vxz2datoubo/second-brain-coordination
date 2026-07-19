"""
zettelkasten.py — 原子化知识节点系统 (Zettelkasten Method)
基于 Niklas Luhmann 的卡片盒方法，实现知识网络化存储
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class AtomicNote:
    id: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    backlinks: List[str] = field(default_factory=list)
    source: str = ""
    source_url: str = ""
    created_at: str = ""
    updated_at: str = ""
    importance: int = 3
    mastery: float = 0.0
    review_count: int = 0
    last_reviewed: str = ""
    next_review: str = ""
    category: str = ""
    metadata: Dict = field(default_factory=dict)


class Zettelkasten:
    NOTE_DIR = Path(__file__).parent.parent / "second-brain" / "notes"
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "second-brain"
        self.notes_dir = self.data_dir / "notes"
        self.index_file = self.data_dir / "zettelkasten_index.json"
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.index = self._load_index()
        self._id_counter = self._init_counter()
    
    def _load_index(self) -> Dict:
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"notes": {}, "tags": {}, "links": {}, "backlinks": {}, "categories": {}, "by_date": {}, "stats": {"total_notes": 0, "total_links": 0}}
    
    def _save_index(self):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def _init_counter(self) -> int:
        max_seq = 0
        for note_id in self.index.get("notes", {}).keys():
            if "-" in note_id:
                try:
                    seq = int(note_id.split("-")[-1])
                    max_seq = max(max_seq, seq)
                except:
                    pass
        return max_seq + 1
    
    def _generate_id(self) -> str:
        now = datetime.now()
        ts = now.strftime("%Y%m%d%H%M%S")
        note_id = f"{ts}-{self._id_counter:03d}"
        self._id_counter += 1
        return note_id
    
    def _compute_hash(self, title: str, content: str) -> str:
        text = f"{title}|{content}"
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    
    def create_note(self, title: str, content: str, tags: Optional[List[str]] = None, source: str = "manual", source_url: str = "", importance: int = 3, category: str = "", auto_link: bool = True) -> Tuple[str, List[str]]:
        warnings = []
        note_hash = self._compute_hash(title, content)
        for nid, meta in self.index.get("notes", {}).items():
            if meta.get("hash") == note_hash:
                warnings.append(f"发现重复笔记: {nid}")
                return nid, warnings
        
        import re
        wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content) if auto_link else []
        tag_pattern = r"#(\w+)"
        extracted_tags = list(set(re.findall(tag_pattern, content + " " + title)))
        if tags:
            extracted_tags.extend(tags)
        extracted_tags = list(set(extracted_tags))
        
        note_id = self._generate_id()
        now = datetime.now().isoformat()
        
        note = AtomicNote(id=note_id, title=title[:50], content=content, tags=extracted_tags, links=[], backlinks=[], source=source, source_url=source_url, created_at=now, updated_at=now, importance=importance, category=category, metadata={"hash": note_hash})
        
        note_file = self.notes_dir / f"{note_id}.json"
        with open(note_file, "w", encoding="utf-8") as f:
            json.dump(asdict(note), f, ensure_ascii=False, indent=2)
        
        self._update_index(note, wikilinks)
        return note_id, warnings
    
    def _update_index(self, note: AtomicNote, wikilinks: List[str]):
        self.index.setdefault("notes", {})[note.id] = {"id": note.id, "title": note.title, "hash": note.metadata.get("hash", ""), "tags": note.tags, "source": note.source, "created_at": note.created_at, "importance": note.importance, "category": note.category}
        
        for tag in note.tags:
            self.index.setdefault("tags", {}).setdefault(tag, []).append(note.id)
        
        if note.category:
            self.index.setdefault("categories", {}).setdefault(note.category, []).append(note.id)
        
        date_key = note.created_at[:10]
        self.index.setdefault("by_date", {}).setdefault(date_key, []).append(note.id)
        
        self._resolve_wikilinks(note.id, wikilinks)
        self.index["stats"]["total_notes"] = len(self.index.get("notes", {}))
        self._save_index()
    
    def _resolve_wikilinks(self, source_id: str, wikilinks: List[str]):
        for link_text in wikilinks:
            matched_id = self._find_note_by_title(link_text)
            if matched_id and matched_id != source_id:
                self._add_link(source_id, matched_id)
    
    def _find_note_by_title(self, title: str) -> Optional[str]:
        for note_id, meta in self.index.get("notes", {}).items():
            if title in meta.get("title", ""):
                return note_id
        return None
    
    def _add_link(self, source_id: str, target_id: str):
        self.index.setdefault("links", {}).setdefault(source_id, [])
        if target_id not in self.index["links"][source_id]:
            self.index["links"][source_id].append(target_id)
        
        self.index.setdefault("backlinks", {}).setdefault(target_id, [])
        if source_id not in self.index["backlinks"][target_id]:
            self.index["backlinks"][target_id].append(source_id)
            self.index["stats"]["total_links"] += 1
        
        note_file = self.notes_dir / f"{source_id}.json"
        if note_file.exists():
            with open(note_file, "r", encoding="utf-8") as f:
                note_data = json.load(f)
            if target_id not in note_data.get("links", []):
                note_data.setdefault("links", []).append(target_id)
            with open(note_file, "w", encoding="utf-8") as f:
                json.dump(note_data, f, ensure_ascii=False, indent=2)
    
    def get_note(self, note_id: str) -> Optional[AtomicNote]:
        note_file = self.notes_dir / f"{note_id}.json"
        if not note_file.exists():
            return None
        with open(note_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AtomicNote(**data)
    
    def get_backlinks(self, note_id: str) -> List[AtomicNote]:
        backlink_ids = self.index.get("backlinks", {}).get(note_id, [])
        return [self.get_note(nid) for nid in backlink_ids if self.get_note(nid)]
    
    def get_linked_notes(self, note_id: str) -> List[AtomicNote]:
        linked_ids = self.index.get("links", {}).get(note_id, [])
        return [self.get_note(nid) for nid in linked_ids if self.get_note(nid)]
    
    def search_notes(self, query: str, limit: int = 20) -> List[AtomicNote]:
        results = []
        query_lower = query.lower()
        for note_id, meta in self.index.get("notes", {}).items():
            title = meta.get("title", "").lower()
            score = 1.0 if query_lower in title else 0.5 if any(query_lower in tag.lower() for tag in meta.get("tags", [])) else 0
            if score > 0:
                note = self.get_note(note_id)
                if note:
                    results.append((note, score))
        results.sort(key=lambda x: -x[1])
        return [r[0] for r in results[:limit]]
    
    def update_note(self, note_id: str, **kwargs) -> bool:
        note = self.get_note(note_id)
        if not note:
            return False
        for key, value in kwargs.items():
            if hasattr(note, key):
                setattr(note, key, value)
        note.updated_at = datetime.now().isoformat()
        note_file = self.notes_dir / f"{note_id}.json"
        with open(note_file, "w", encoding="utf-8") as f:
            json.dump(asdict(note), f, ensure_ascii=False, indent=2)
        return True
    
    def get_stats(self) -> Dict:
        return {"total_notes": self.index["stats"]["total_notes"], "total_links": self.index["stats"]["total_links"], "categories": {k: len(v) for k, v in self.index.get("categories", {}).items()}, "top_tags": [(t, len(ids)) for t, ids in list(self.index.get("tags", {}).items())[:10]]}


def get_zettelkasten(data_dir: Optional[Path] = None) -> Zettelkasten:
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "second-brain"
    return Zettelkasten(data_dir)
