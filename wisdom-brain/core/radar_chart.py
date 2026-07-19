"""
Radar Chart Generator
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class RadarChartGenerator:
    DIMENSIONS = ["person", "clothing", "scene", "composition", "atmosphere", "details"]
    
    DIMENSION_LABELS = {
        "person": "Person",
        "clothing": "Style",
        "scene": "Scene",
        "composition": "Composition",
        "atmosphere": "Atmosphere",
        "details": "Details"
    }
    
    def __init__(self, base_path="F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.output_dir = self.base_path / "knowledge" / "aesthetics"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_radar_data(self, preference_engine) -> dict:
        radar_raw = preference_engine.get_radar_data()
        
        labels = []
        values = []
        
        for dim in self.DIMENSIONS:
            labels.append(self.DIMENSION_LABELS.get(dim, dim))
            values.append(radar_raw.get(dim, 0.0))
        
        return {
            "labels": labels,
            "datasets": [{
                "label": "Preferences",
                "data": values,
                "backgroundColor": "rgba(79, 195, 247, 0.2)",
                "borderColor": "rgba(79, 195, 247, 1)",
                "borderWidth": 2
            }]
        }
    
    def generate_html(self, radar_data: dict, title: str = "Aesthetic Preferences") -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        labels_json = json.dumps(radar_data["labels"])
        data_json = json.dumps(radar_data["datasets"][0]["data"])
        
        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>""" + title + """</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
    color: #fff;
}
h1 { font-size: 24px; margin-bottom: 10px; color: #4fc3f7; }
.subtitle { font-size: 14px; color: #888; margin-bottom: 30px; }
.chart-container {
    width: 500px; max-width: 90vw;
    background: rgba(255,255,255,0.05);
    border-radius: 20px; padding: 30px;
}
</style>
</head>
<body>
<h1>""" + title + """</h1>
<div class="subtitle">Updated """ + now + """</div>
<div class="chart-container">
<canvas id="radarChart"></canvas>
</div>
<script>
const ctx = document.getElementById("radarChart").getContext("2d");
new Chart(ctx, {
    type: "radar",
    data: {
        labels: """ + labels_json + """,
        datasets: [{
            label: "Preferences",
            data: """ + data_json + """,
            backgroundColor: "rgba(79, 195, 247, 0.2)",
            borderColor: "rgba(79, 195, 247, 1)",
            borderWidth: 2
        }]
    },
    options: {
        responsive: true,
        scales: {
            r: {
                beginAtZero: true, max: 1,
                ticks: { stepSize: 0.2, color: "#888" },
                grid: { color: "rgba(255,255,255,0.1)" },
                angleLines: { color: "rgba(255,255,255,0.1)" },
                pointLabels: { color: "#fff" }
            }
        },
        plugins: { legend: { display: false } }
    }
});
</script>
</body>
</html>"""
        return html
    
    def save_radar_chart(self, preference_engine, filename: str = "radar_chart.html") -> str:
        radar_data = self.generate_radar_data(preference_engine)
        html = self.generate_html(radar_data)
        
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        
        return str(filepath)