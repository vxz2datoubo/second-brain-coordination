"""
Aesthetics Brain v2 - Demo
"""

import sys
sys.path.insert(0, "F:/aidanao/wisdom-brain")

from core.aesthetics_brain import AestheticsBrain

def demo():
    print("")
    print("=" * 50)
    print("Aesthetics Brain v2 - Demo")
    print("=" * 50)
    print("")
    
    brain = AestheticsBrain()
    
    # Demo 1: Single analysis
    print("[1] Single Image Analysis")
    analysis = {
        "person": {"face_shape": "oval", "eyes": "large", "hair": "long"},
        "clothing": {"style": "casual", "color": ["black", "white"]},
        "scene": {"location": "cafe", "mood": "warm"}
    }
    result = brain.analyze_image("demo.jpg", analysis)
    print("    Image ID: " + result["image_id"])
    print("    Features: " + str(result["features_count"]))
    print("")
    
    # Demo 2: Batch analysis
    print("[2] Batch Analysis (5 images)")
    analyses = [
        {"person": {"face_shape": "oval", "hair": "long"}, "clothing": {"style": "casual"}},
        {"person": {"face_shape": "round", "hair": "short"}, "clothing": {"style": "sporty"}},
        {"person": {"face_shape": "square", "hair": "curly"}, "clothing": {"style": "formal"}},
        {"person": {"face_shape": "oval", "hair": "long"}, "clothing": {"style": "sweet"}},
        {"person": {"face_shape": "oval", "hair": "long"}, "clothing": {"style": "minimal"}}
    ]
    batch_result = brain.analyze_batch(analyses)
    print("    Processed: " + str(batch_result["count"]) + " images")
    print("")
    
    # Demo 3: Similar search
    print("[3] Similar Image Search")
    features = ["person.face_shape.oval", "person.hair.long"]
    similar = brain.find_similar(features, top_k=3)
    print("    Found: " + str(similar["count"]) + " similar images")
    print("")
    
    # Demo 4: Preference summary
    print("[4] Preference Summary")
    summary = brain.get_preference_summary()
    print("    Total images: " + str(summary["total_images"]))
    print("    Radar: " + str(summary["radar"]))
    print("")
    
    # Demo 5: Radar chart
    print("[5] Generate Radar Chart")
    radar = brain.generate_radar_chart()
    print("    File: " + radar["filepath"])
    print("")
    
    # Demo 6: Stats
    print("[6] System Stats")
    stats = brain.get_stats()
    print("    Total vectors: " + str(stats["vectorizer"]["total"]))
    print("    Total images: " + str(stats["total_images"]))
    print("")
    
    print("=" * 50)
    print("Demo Complete!")
    print("=" * 50)


if __name__ == "__main__":
    demo()