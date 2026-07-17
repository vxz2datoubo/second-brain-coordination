"""
Aesthetics Brain HTTP Server
"""

import json
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys

sys.path.insert(0, str(Path(__file__).parent))

from core.aesthetics_brain import AestheticsBrain

class AestheticsHandler(BaseHTTPRequestHandler):
    brain = AestheticsBrain()
    
    def log_message(self, format, *args):
        print("[" + datetime.now().strftime("%H:%M:%S") + "] " + str(args[0]))
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/":
            self.send_json({
                "name": "Aesthetics Brain v2",
                "version": "2.0",
                "endpoints": ["/stats", "/summary", "/radar", "/patterns", "/evolution"]
            })
        elif path == "/stats":
            self.send_json(self.brain.get_stats())
        elif path == "/summary":
            self.send_json(self.brain.get_preference_summary())
        elif path == "/patterns":
            self.send_json(self.brain.get_hidden_patterns())
        elif path == "/evolution":
            self.send_json(self.brain.get_temporal_evolution())
        elif path == "/radar":
            result = self.brain.generate_radar_chart()
            self.send_json({"filepath": result["filepath"], "url": result["url"]})
        else:
            self.send_json({"error": "Not Found"}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return
        
        try:
            if path == "/analyze":
                result = self.brain.analyze_image(data.get("path", ""), data.get("analysis", {}))
                self.send_json(result)
            elif path == "/batch":
                result = self.brain.analyze_batch(data.get("analyses", []), data.get("paths"))
                self.send_json(result)
            elif path == "/similar":
                result = self.brain.find_similar(features=data.get("features", []), top_k=data.get("top_k", 5))
                self.send_json(result)
            else:
                self.send_json({"error": "Not Found"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)


def run_server(port=8768):
    print("")
    print("=" * 45)
    print("     Aesthetics Brain v2 - HTTP Server")
    print("=" * 45)
    print("     Port: " + str(port))
    print("     URL: http://localhost:" + str(port))
    print("=" * 45)
    print("")
    server = HTTPServer(("localhost", port), AestheticsHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", type=int, default=8768)
    args = parser.parse_args()
    run_server(args.port)