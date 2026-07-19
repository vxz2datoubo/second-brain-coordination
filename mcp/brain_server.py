# 第二大脑 MCP 服务器
import json
import os
import re
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

BRAIN_DIR = Path(r'F:\aidanao\second-brain')
LOG_DIR = Path(r'F:\aidanao\core\logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    with open(LOG_DIR / 'brain_server.log', 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def load_knowledge():
    kb = {'nodes': [], 'edges': [], 'rules': '', 'lessons': ''}
    rules_file = BRAIN_DIR / 'rules.md'
    lessons_file = BRAIN_DIR / 'lessons.md'
    if rules_file.exists():
        kb['rules'] = rules_file.read_text(encoding='utf-8')
    if lessons_file.exists():
        kb['lessons'] = lessons_file.read_text(encoding='utf-8')
    return kb

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body) if body else {}
        except:
            self.send_error(400, 'Invalid JSON')
            return

        path = self.path
        if path == '/api/brain/search':
            result = brain_search(data.get('query', ''))
        elif path == '/api/brain/consult':
            result = brain_consult(data.get('topic', ''))
        elif path == '/api/brain/digest':
            result = brain_digest(data)
        elif path == '/api/brain/read':
            result = brain_read(data.get('node_id'))
        elif path == '/api/trade/log':
            result = trade_log(data)
        elif path == '/api/trade/daily_summary':
            result = daily_summary()
        else:
            self.send_error(404, 'Unknown endpoint')
            return

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        result = brain_read(None)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

    def log_message(self, fmt, *args):
        log(fmt % args)

def brain_search(query):
    kb = load_knowledge()
    q = query.lower()
    results = []

    if kb['rules']:
        for line in kb['rules'].split('\n'):
            if q in line.lower() and len(line) > 10:
                results.append({'type': 'rule', 'content': line.strip(), 'source': 'rules.md'})

    if kb['lessons']:
        for line in kb['lessons'].split('\n'):
            if q in line.lower() and len(line) > 10:
                results.append({'type': 'lesson', 'content': line.strip(), 'source': 'lessons.md'})

    log(f'search: "{query}" -> {len(results)} results')
    return {'query': query, 'results': results[:10], 'total': len(results)}

def brain_consult(topic):
    kb = load_knowledge()
    rules_text = kb.get('rules', '') or ''
    lessons_text = kb.get('lessons', '') or ''

    lines = []
    for line in (rules_text + '\n' + lessons_text).split('\n'):
        if topic.lower() in line.lower() and any(k in line for k in ['红线', '禁止', '止损', '亏损', '仓位']):
            lines.append(line.strip())

    log(f'consult: "{topic}" -> {len(lines)} findings')
    return {'topic': topic, 'findings': lines[:20], 'count': len(lines)}

def brain_digest(data):
    text = data.get('text', '')
    title = data.get('title', '')
    source = data.get('source', 'manual')

    if not text:
        return {'success': False, 'error': 'text is required'}

    log_file = LOG_DIR / f'brain_digest_{datetime.now().strftime("%Y%m%d")}.md'
    entry = f'\n---\n# {title or "Digest Entry"}\nSource: {source}\nDate: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n{text}\n'
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(entry)

    log(f'digest: "{title or text[:50]}" from {source}')
    return {'success': True, 'saved_to': str(log_file), 'title': title}

def brain_read(node_id):
    kb = load_knowledge()
    return {
        'rules': kb.get('rules', ''),
        'lessons': kb.get('lessons', ''),
        'status': 'ok'
    }

def trade_log(data):
    log_file = BRAIN_DIR / 'daily_log.md'
    d = datetime.now().strftime('%Y-%m-%d')
    row = data.get('row', '')
    if row:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f'\n| {d} | {row} |')
    log(f'trade_log: {row}')
    return {'success': True}

def daily_summary():
    log_file = BRAIN_DIR / 'daily_log.md'
    if log_file.exists():
        content = log_file.read_text(encoding='utf-8')
        today = datetime.now().strftime('%Y-%m-%d')
        lines = [l for l in content.split('\n') if today in l]
        return {'date': today, 'lines': lines}
    return {'date': datetime.now().strftime('%Y-%m-%d'), 'lines': []}

if __name__ == '__main__':
    PORT = 8767
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    log(f'Second Brain MCP server running on port {PORT}')
    server.serve_forever()
