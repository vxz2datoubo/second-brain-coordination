"""
spaced_repetition.py — 间隔重复复习系统
基于艾宾浩斯遗忘曲线，智能安排知识复习
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


# 艾宾浩斯复习间隔（天数）
EBBINGHAUS_INTERVALS = [1, 2, 4, 7, 15, 30, 60, 90]


@dataclass
class ReviewCard:
    note_id: str
    note_title: str
    category: str
    importance: int
    interval_index: int = 0  # 当前在间隔序列中的位置
    ease_factor: float = 2.5  # 容易度因子
    repetitions: int = 0  # 重复次数
    next_review: str = ""  # ISO格式日期
    last_reviewed: str = ""
    created_at: str = ""


@dataclass
class ReviewResult:
    note_id: str
    rating: int  # 1-5 质量评分
    reviewed_at: str = ""
    time_spent: float = 0  # 秒


class SpacedRepetition:
    """间隔重复复习系统"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "second-brain"
        self.cards_file = self.data_dir / "review_cards.json"
        self.history_file = self.data_dir / "review_history.json"
        self.cards = self._load_cards()
        self.history = self._load_history()
    
    def _load_cards(self) -> Dict[str, Dict]:
        try:
            with open(self.cards_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def _save_cards(self):
        self.cards_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cards_file, "w", encoding="utf-8") as f:
            json.dump(self.cards, f, ensure_ascii=False, indent=2)
    
    def _load_history(self) -> Dict:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"reviews": [], "stats": {"total_reviews": 0, "average_rating": 0}}
    
    def _save_history(self):
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def add_card(self, note_id: str, note_title: str, category: str = "", importance: int = 3) -> str:
        if note_id in self.cards:
            return note_id
        
        card = ReviewCard(note_id=note_id, note_title=note_title, category=category, importance=importance, next_review=datetime.now().strftime("%Y-%m-%d"), created_at=datetime.now().isoformat())
        
        self.cards[note_id] = asdict(card)
        self._save_cards()
        return note_id
    
    def remove_card(self, note_id: str) -> bool:
        if note_id in self.cards:
            del self.cards[note_id]
            self._save_cards()
            return True
        return False
    
    def get_due_cards(self, limit: int = 20) -> List[Dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        due_cards = []
        
        for note_id, card in self.cards.items():
            next_review = card.get("next_review", "")
            if next_review <= today:
                due_cards.append(card)
        
        # 按重要度和重复次数排序
        due_cards.sort(key=lambda x: (-x.get("importance", 3), x.get("repetitions", 0)))
        return due_cards[:limit]
    
    def record_review(self, note_id: str, rating: int, time_spent: float = 0) -> Dict:
        if note_id not in self.cards:
            return {"error": "Card not found"}
        
        card = self.cards[note_id]
        now = datetime.now()
        now_iso = now.isoformat()
        
        # SM-2算法核心
        quality = rating  # 1-5
        repetitions = card.get("repetitions", 0)
        ease_factor = card.get("ease_factor", 2.5)
        interval_index = card.get("interval_index", 0)
        
        if quality >= 3:  # 正确
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = round(card.get("last_interval", 1) * ease_factor)
            
            repetitions += 1
            interval_index = min(interval_index + 1, len(EBBINGHAUS_INTERVALS) - 1)
        else:  # 错误
            repetitions = 0
            interval_index = 0
            interval = 1
        
        # 更新容易度
        ease_factor = max(1.3, ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        
        # 计算下次复习日期
        next_review = (now + timedelta(days=interval)).strftime("%Y-%m-%d")
        
        # 更新卡片
        card["repetitions"] = repetitions
        card["ease_factor"] = round(ease_factor, 2)
        card["interval_index"] = interval_index
        card["next_review"] = next_review
        card["last_reviewed"] = now_iso
        card["last_interval"] = interval
        
        self._save_cards()
        
        # 记录历史
        result = ReviewResult(note_id=note_id, rating=rating, reviewed_at=now_iso, time_spent=time_spent)
        self.history.setdefault("reviews", []).append(asdict(result))
        self.history["stats"]["total_reviews"] += 1
        
        # 计算平均评分
        ratings = [r["rating"] for r in self.history["reviews"][-100:]]
        self.history["stats"]["average_rating"] = sum(ratings) / len(ratings) if ratings else 0
        
        self._save_history()
        
        return {"success": True, "next_review": next_review, "interval": interval, "ease_factor": ease_factor}
    
    def get_stats(self) -> Dict:
        today = datetime.now().strftime("%Y-%m-%d")
        due_today = sum(1 for c in self.cards.values() if c.get("next_review", "") <= today)
        
        return {
            "total_cards": len(self.cards),
            "due_today": due_today,
            "total_reviews": self.history["stats"]["total_reviews"],
            "average_rating": round(self.history["stats"]["average_rating"], 2),
            "mastery_distribution": self._get_mastery_distribution()
        }
    
    def _get_mastery_distribution(self) -> Dict[str, int]:
        dist = {"new": 0, "learning": 0, "reviewing": 0, "mastered": 0}
        for card in self.cards.values():
            reps = card.get("repetitions", 0)
            if reps == 0:
                dist["new"] += 1
            elif reps < 3:
                dist["learning"] += 1
            elif reps < 6:
                dist["reviewing"] += 1
            else:
                dist["mastered"] += 1
        return dist
    
    def generate_schedule(self, days: int = 7) -> Dict[str, int]:
        schedule = {}
        today = datetime.now()
        
        for i in range(days):
            date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            count = 0
            for card in self.cards.values():
                if card.get("next_review", "") == date:
                    count += 1
            schedule[date] = count
        
        return schedule
    
    def get_forgotten_notes(self, days: int = 7) -> List[str]:
        """获取最近被遗忘的笔记（评分低的）"""
        forgotten = []
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        for review in reversed(self.history.get("reviews", [])):
            if review["reviewed_at"] < cutoff:
                break
            if review["rating"] <= 2:
                forgotten.append(review["note_id"])
        
        return list(set(forgotten))
