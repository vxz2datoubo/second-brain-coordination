"""
Batch Processor v2
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter

class BatchProcessor:
    def __init__(self, base_path="F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.images_dir = self.base_path / "knowledge" / "aesthetics" / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def process_analyses(self, analyses: List[dict], image_paths: List[str] = None) -> dict:
        if image_paths is None:
            image_paths = [None] * len(analyses)
        
        results = []
        timestamp = datetime.now().isoformat()
        
        for i, analysis in enumerate(analyses):
            img_id = "batch_" + datetime.now().strftime("%Y%m%d%H%M%S") + "_" + str(i).zfill(3)
            
            record = {
                "id": img_id,
                "path": image_paths[i] if i < len(image_paths) else None,
                "batch_index": i,
                "timestamp": timestamp,
                "analysis": analysis
            }
            
            with open(self.images_dir / (img_id + ".json"), "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            
            results.append(record)
        
        stats = self._compute_batch_stats(analyses)
        
        return {"count": len(results), "records": results, "stats": stats, "timestamp": timestamp}
    
    def _compute_batch_stats(self, analyses: List[dict]) -> dict:
        all_features = []
        dimensions_coverage = set()
        
        for analysis in analyses:
            for dim in analysis:
                dimensions_coverage.add(dim)
                if isinstance(analysis[dim], dict):
                    for cat, val in analysis[dim].items():
                        if isinstance(val, list):
                            all_features.extend([str(v) for v in val])
                        elif isinstance(val, str):
                            all_features.append(val)
        
        feature_counts = Counter(all_features)
        
        return {
            "total_images": len(analyses),
            "dimensions_covered": list(dimensions_coverage),
            "dimension_count": len(dimensions_coverage),
            "top_features": dict(feature_counts.most_common(10)),
            "unique_features": len(set(all_features))
        }
    
    def load_batch(self, batch_id: str = None) -> List[dict]:
        records = []
        pattern = batch_id + "_*.json" if batch_id else "*.json"
        
        for img_file in self.images_dir.glob(pattern):
            with open(img_file, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        
        records.sort(key=lambda x: x.get("timestamp", ""))
        return records
    
    def get_temporal_evolution(self) -> dict:
        all_records = self.load_batch()
        
        if len(all_records) < 2:
            return {"message": "Need at least 2 images"}
        
        return {"total_images": len(all_records), "periods": 1, "evolution": []}