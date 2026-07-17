"""
Preference Engine v2
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter, defaultdict

class PreferenceEngine:
    DIMENSION_WEIGHTS = {
        "person": 1.0,
        "clothing": 1.2,
        "scene": 0.8,
        "composition": 0.9,
        "atmosphere": 1.1,
        "details": 0.7
    }
    
    def __init__(self, base_path="F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.prefs_dir = self.base_path / "knowledge" / "aesthetics" / "preferences"
        self.hidden_dir = self.base_path / "knowledge" / "aesthetics" / "hidden_features"
        self.images_dir = self.base_path / "knowledge" / "aesthetics" / "images"
        
        self.prefs_dir.mkdir(parents=True, exist_ok=True)
        self.hidden_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        self._load_preferences()
    
    def _load_preferences(self):
        prefs_file = self.prefs_dir / "_stats.json"
        if prefs_file.exists():
            with open(prefs_file, "r", encoding="utf-8-sig") as f:
                self.preferences = json.load(f)
        else:
            self.preferences = {
                "total_images": 0,
                "dimensions": {
                    "person": {},
                    "clothing": {},
                    "scene": {},
                    "composition": {},
                    "atmosphere": {},
                    "details": {}
                },
                "time_series": [],
                "last_updated": None
            }
    
    def _save_preferences(self):
        self.preferences["last_updated"] = datetime.now().isoformat()
        with open(self.prefs_dir / "_stats.json", "w", encoding="utf-8") as f:
            json.dump(self.preferences, f, ensure_ascii=False, indent=2)
    
    def learn_from_analysis(self, analysis: dict, image_path: str = None, timestamp: str = None):
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        img_id = "img_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        image_record = {
            "id": img_id,
            "path": image_path,
            "timestamp": timestamp,
            "analysis": analysis
        }
        with open(self.images_dir / (img_id + ".json"), "w", encoding="utf-8") as f:
            json.dump(image_record, f, ensure_ascii=False, indent=2)
        
        self._update_preferences(analysis, timestamp)
        self._save_preferences()
        
        return img_id
    
    def _update_preferences(self, analysis: dict, timestamp: str):
        self.preferences["total_images"] += 1
        
        for dim_name, dim_data in analysis.items():
            if dim_name not in self.preferences["dimensions"]:
                self.preferences["dimensions"][dim_name] = {}
            
            if isinstance(dim_data, dict):
                for cat_name, cat_value in dim_data.items():
                    if cat_name not in self.preferences["dimensions"][dim_name]:
                        self.preferences["dimensions"][dim_name][cat_name] = {}
                    
                    if isinstance(cat_value, list):
                        for item in cat_value:
                            key = item if isinstance(item, str) else str(item)
                            self.preferences["dimensions"][dim_name][cat_name][key] = self.preferences["dimensions"][dim_name][cat_name].get(key, 0) + 1
                    elif isinstance(cat_value, str):
                        self.preferences["dimensions"][dim_name][cat_name][cat_value] = self.preferences["dimensions"][dim_name][cat_name].get(cat_value, 0) + 1
        
        self.preferences["time_series"].append({
            "timestamp": timestamp,
            "features": self._extract_features(analysis)
        })
        
        if len(self.preferences["time_series"]) > 100:
            self.preferences["time_series"] = self.preferences["time_series"][-100:]
    
    def _extract_features(self, analysis: dict) -> List[str]:
        features = []
        for dim_name, dim_data in analysis.items():
            if isinstance(dim_data, dict):
                for cat_name, cat_value in dim_data.items():
                    if isinstance(cat_value, list):
                        features.extend([str(v) for v in cat_value])
                    elif isinstance(cat_value, str):
                        features.append(dim_name + "." + cat_value)
        return features
    
    def get_radar_data(self) -> dict:
        total = self.preferences["total_images"]
        if total == 0:
            return {dim: 0.0 for dim in self.DIMENSION_WEIGHTS}
        
        radar = {}
        for dim_name in self.DIMENSION_WEIGHTS:
            dim_data = self.preferences["dimensions"].get(dim_name, {})
            if isinstance(dim_data, dict):
                coverage = sum(len(counter) for counter in dim_data.values() if isinstance(counter, dict))
                radar[dim_name] = min(coverage / 3, 1.0)
            else:
                radar[dim_name] = 0.0
        
        return radar
    
    def get_top_preferences(self, top_k: int = 5) -> dict:
        top_prefs = {}
        
        for dim_name, dim_data in self.preferences["dimensions"].items():
            if isinstance(dim_data, dict):
                all_items = []
                for cat_name, counter in dim_data.items():
                    if isinstance(counter, dict):
                        for item, count in counter.items():
                            all_items.append({"item": item, "count": count, "category": cat_name})
                
                all_items.sort(key=lambda x: x["count"], reverse=True)
                top_prefs[dim_name] = all_items[:top_k]
        
        return top_prefs
    
    def find_hidden_patterns(self) -> List[dict]:
        patterns = []
        
        if self.preferences["total_images"] < 3:
            return [{"type": "insufficient_data", "message": "Need at least 3 images"}]
        
        # Co-occurrence patterns
        all_features = []
        for dim_data in self.preferences["dimensions"].values():
            if isinstance(dim_data, dict):
                for counter in dim_data.values():
                    if isinstance(counter, dict):
                        for feature in counter:
                            all_features.append(feature)
        
        feature_counts = Counter(all_features)
        frequent = []
        for feat, count in feature_counts.most_common(5):
            if count >= 2:
                frequent.append({"feature": feat, "count": count})
        
        if frequent:
            patterns.append({"type": "frequent_hidden", "title": "Frequent features", "patterns": frequent})
        
        return patterns
    
    def get_summary(self) -> dict:
        return {
            "total_images": self.preferences["total_images"],
            "radar": self.get_radar_data(),
            "top_preferences": self.get_top_preferences(),
            "hidden_patterns": self.find_hidden_patterns(),
            "last_updated": self.preferences.get("last_updated")
        }
    
    def get_stats(self) -> dict:
        return {
            "total_images": self.preferences["total_images"],
            "dimensions_covered": len([d for d in self.preferences["dimensions"].values() if d]),
            "time_series_points": len(self.preferences["time_series"])
        }