"""
Aesthetics Brain v2 - Core Module
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.image_vectorizer import ImageVectorizer
from core.preference_engine import PreferenceEngine
from core.similarity_search import SimilaritySearch
from core.batch_processor import BatchProcessor
from core.radar_chart import RadarChartGenerator

class AestheticsBrain:
    def __init__(self, base_path="F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.vectorizer = ImageVectorizer(base_path)
        self.preference = PreferenceEngine(base_path)
        self.similarity = SimilaritySearch(base_path)
        self.batch = BatchProcessor(base_path)
        self.radar = RadarChartGenerator(base_path)
    
    def analyze_image(self, image_path: str, analysis: dict) -> dict:
        vector = self.vectorizer.vectorize_from_analysis(analysis, image_path)
        img_id = self.preference.learn_from_analysis(analysis, image_path)
        
        return {
            "success": True,
            "image_id": img_id,
            "vector_id": vector["id"],
            "features_count": len(vector["features"]),
            "message": "Analysis complete"
        }
    
    def analyze_batch(self, analyses: List[dict], image_paths: List[str] = None) -> dict:
        batch_result = self.batch.process_analyses(analyses, image_paths)
        
        vectors = []
        for i, analysis in enumerate(analyses):
            vec = self.vectorizer.vectorize_from_analysis(
                analysis, 
                image_paths[i] if image_paths and i < len(image_paths) else None
            )
            vectors.append(vec)
        
        for analysis in analyses:
            self.preference.learn_from_analysis(analysis)
        
        return {
            "success": True,
            "count": len(analyses),
            "batch_id": "batch_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "stats": batch_result["stats"],
            "vector_count": len(vectors)
        }
    
    def find_similar(self, features: List[str] = None, top_k: int = 5) -> dict:
        if features is None:
            features = []
        results = self.similarity.search_by_features(features, top_k)
        return {"query_features": features, "count": len(results), "results": results}
    
    def find_similar_to_image(self, image_id: str, top_k: int = 5) -> dict:
        results = self.similarity.search_by_image_id(image_id, top_k)
        return {"source_image": image_id, "count": len(results), "results": results}
    
    def get_preference_summary(self) -> dict:
        return self.preference.get_summary()
    
    def get_hidden_patterns(self) -> dict:
        patterns = self.preference.find_hidden_patterns()
        return {"patterns": patterns, "count": len(patterns)}
    
    def generate_radar_chart(self) -> dict:
        filepath = self.radar.save_radar_chart(self.preference)
        return {"success": True, "filepath": filepath, "url": "file://" + filepath}
    
    def get_temporal_evolution(self) -> dict:
        return self.batch.get_temporal_evolution()
    
    def get_recommendations(self, exclude_ids: List[str] = None, top_k: int = 5) -> dict:
        return self.similarity.find_recommendations(exclude_ids, top_k)
    
    def get_stats(self) -> dict:
        return {
            "vectorizer": self.vectorizer.get_vector_stats(),
            "preference": self.preference.get_stats(),
            "total_images": self.preference.preferences["total_images"]
        }