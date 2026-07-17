"""
Similarity Search v2
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter

class SimilaritySearch:
    def __init__(self, base_path="F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.vectors_dir = self.base_path / "knowledge" / "aesthetics" / "vectors"
        self.images_dir = self.base_path / "knowledge" / "aesthetics" / "images"
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def search_by_features(self, features: List[str], top_k: int = 5, min_similarity: float = 0.2) -> List[dict]:
        all_vectors = self._load_all_vectors()
        
        if not all_vectors:
            return [{"message": "No vectors found"}]
        
        results = []
        query_set = set(features)
        
        for vec in all_vectors:
            vec_features = set(vec.get("features", []))
            
            if not vec_features:
                continue
            
            intersection = len(query_set & vec_features)
            union = len(query_set | vec_features)
            jaccard = intersection / union if union > 0 else 0
            
            if jaccard >= min_similarity:
                results.append({
                    "id": vec["id"],
                    "image_path": vec.get("image_path", ""),
                    "similarity": round(jaccard, 3),
                    "shared_features": list(query_set & vec_features)
                })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    
    def search_by_image_id(self, image_id: str, top_k: int = 5) -> List[dict]:
        vec_file = self.vectors_dir / (image_id + ".json")
        
        if not vec_file.exists():
            return [{"error": "Image not found"}]
        
        with open(vec_file, "r", encoding="utf-8") as f:
            target_vec = json.load(f)
        
        return self.search_by_features(target_vec.get("features", []), top_k)
    
    def _load_all_vectors(self) -> List[dict]:
        vectors = []
        for vec_file in self.vectors_dir.glob("*.json"):
            with open(vec_file, "r", encoding="utf-8") as f:
                vectors.append(json.load(f))
        return vectors
    
    def find_recommendations(self, exclude_ids: List[str] = None, top_k: int = 5) -> dict:
        all_vectors = self._load_all_vectors()
        
        if exclude_ids is None:
            exclude_ids = []
        
        candidates = [v for v in all_vectors if v["id"] not in exclude_ids]
        
        if not candidates:
            return {"message": "No recommendations"}
        
        all_features = []
        for vec in candidates:
            all_features.extend(vec.get("features", []))
        
        feature_counts = Counter(all_features)
        top_features = [f for f, _ in feature_counts.most_common(10)]
        
        return {"based_on_features": top_features, "recommendations": self.search_by_features(top_features, top_k, 0.15)}