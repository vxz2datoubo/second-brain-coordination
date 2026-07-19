"""
Image Vectorizer v2
"""

import json
import os
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

class ImageVectorizer:
    DIMENSIONS = {
        "person": ["face_shape", "eyes", "hair", "expression", "body", "age_group", "skin_tone"],
        "clothing": ["style", "color", "top", "bottom", "material", "pattern"],
        "scene": ["location", "mood", "light", "time_of_day", "weather", "season"],
        "composition": ["angle", "framing", "background", "rule_of_thirds", "depth"],
        "atmosphere": ["vibe", "emotion", "color_tone", "contrast"],
        "details": ["accessories", "props", "interaction", "pose"]
    }
    
    def __init__(self, base_path="F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.vectors_dir = self.base_path / "knowledge" / "aesthetics" / "vectors"
        self.images_dir = self.base_path / "knowledge" / "aesthetics" / "images"
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
    def vectorize_from_analysis(self, analysis: dict, image_path: str = None) -> dict:
        vector_id = "v_" + datetime.now().strftime("%Y%m%d%H%M%S") + "_" + str(uuid.uuid4())[:8]
        features = self._flatten_analysis(analysis)
        
        vector = {
            "id": vector_id,
            "image_path": image_path,
            "timestamp": datetime.now().isoformat(),
            "features": features,
            "dimensions": analysis,
            "semantic_hash": self._generate_semantic_hash(features),
            "feature_count": len(features)
        }
        
        with open(self.vectors_dir / (vector_id + ".json"), "w", encoding="utf-8") as f:
            json.dump(vector, f, ensure_ascii=False, indent=2)
        
        return vector
    
    def _flatten_analysis(self, analysis: dict) -> List[str]:
        features = []
        for dim_name, dim_data in analysis.items():
            if isinstance(dim_data, dict):
                for cat_name, cat_value in dim_data.items():
                    if isinstance(cat_value, list):
                        features.extend(cat_value)
                    elif isinstance(cat_value, str):
                        features.append(dim_name + "." + cat_name + "." + cat_value)
        return features
    
    def _generate_semantic_hash(self, features: List[str]) -> str:
        sorted_features = sorted(features)
        hash_input = "|".join(sorted_features)
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    def load_all_vectors(self) -> List[dict]:
        vectors = []
        for vec_file in self.vectors_dir.glob("*.json"):
            with open(vec_file, "r", encoding="utf-8") as f:
                vectors.append(json.load(f))
        return vectors
    
    def compute_similarity(self, vec1_features: List[str], vec2_features: List[str]) -> float:
        set1 = set(vec1_features)
        set2 = set(vec2_features)
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        jaccard = intersection / union if union > 0 else 0
        return min(jaccard + 0.1, 1.0)
    
    def find_similar(self, target_features: List[str], top_k: int = 5) -> List[dict]:
        all_vectors = self.load_all_vectors()
        similarities = []
        for vec in all_vectors:
            sim = self.compute_similarity(target_features, vec.get("features", []))
            if sim > 0.2:
                similarities.append({
                    "id": vec["id"],
                    "image_path": vec.get("image_path", ""),
                    "similarity": round(sim, 3),
                    "shared_features": list(set(target_features) & set(vec.get("features", [])))
                })
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]
    
    def get_vector_stats(self) -> dict:
        vectors = self.load_all_vectors()
        return {"total": len(vectors)}