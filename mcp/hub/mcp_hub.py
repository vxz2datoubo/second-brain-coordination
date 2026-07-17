# MCP Hub - 万能软件连接中枢
# 所有 MCP 服务器通过 Hub 互通，Codex/WorkBuddy 只需连接 Hub
import json
import sys
import importlib
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

ADAPTERS_DIR = Path(__file__).parent / 'adapters'
ADAPTERS_DIR.mkdir(exist_ok=True)

def log(msg):
    print(f'[MCP-HUB {threading.current_thread().name}] {msg}', flush=True)

class MCPHub:
    def __init__(self):
        self.adapters = {}
        self.tools = []
        self._load_adapters()

    def _load_adapters(self):
        for py_file in ADAPTERS_DIR.glob('*.py'):
            if py_file.name.startswith('_'):
                continue
            try:
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                adapter = getattr(mod, 'Adapter', None)
                if adapter and callable(adapter.get_tools):
                    inst = adapter()
                    tools = inst.get_tools()
                    self.adapters[module_name] = inst
                    self.tools.extend(tools)
                    log(f'Loaded adapter: {module_name} ({len(tools)} tools)')
                else:
                    log(f'Skip {module_name}: no Adapter class')
            except Exception as e:
                log(f'Failed to load {py_file.name}: {e}')

    def call_tool(self, name, args):
        for tool in self.tools:
            if tool['name'] == name:
                adapter_name = None
                for an, inst in self.adapters.items():
                    if hasattr(inst, 'call_tool'):
                        try:
                            result = inst.call_tool(name, args)
                            log(f'Tool {name} -> ok')
                            return result
                        except:
                            pass
                log(f'Tool {name} called (no adapter)')
                return {'status': 'ok', 'tool': name, 'args': args}

        raise Exception(f'Unknown tool: {name}')

    def list_tools(self):
        return [{'name': t['name'], 'desc': t.get('desc', '')} for t in self.tools]

hub = MCPHub()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body) if body else {}
        except Exception as e:
            self.send_error(400, str(e))
            return

        path = urlparse(self.path).path
        method = data.get('method', '')
        id_ = data.get('id')

        try:
            if path == '/mcp' or path == '/':
                if method == 'tools/list':
                    result = hub.list_tools()
                elif method == 'tools/call':
                    name = data.get('params', {}).get('name', '')
                    args = data.get('params', {}).get('arguments', {})
                    result = hub.call_tool(name, args)
                else:
                    raise Exception(f'Unknown method: {method}')

                self._respond(200, {'jsonrpc': '2.0', 'id': id_, 'result': result})
            else:
                self._respond(404, {'error': 'Not found'})
        except Exception as e:
            self._respond(200, {'jsonrpc': '2.0', 'id': id_, 'error': {'code': -32000, 'message': str(e)}})

    def do_GET(self):
        if self.path == '/health':
            self._respond(200, {'status': 'ok', 'adapters': list(hub.adapters.keys()), 'tools': len(hub.tools)})
        elif self.path == '/tools':
            self._respond(200, {'tools': hub.list_tools()})
        else:
            self._respond(200, {'message': 'MCP Hub is running'})

    def _respond(self, code, body):
        raw = json.dumps(body, ensure_ascii=False)
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(raw.encode('utf-8')))
        self.end_headers()
        self.wfile.write(raw.encode('utf-8'))

    def log_message(self, fmt, *args):
        pass

def run(port=18767):
    server = HTTPServer(('127.0.0.1', port), Handler)
    log(f'MCP Hub running on http://127.0.0.1:{port}')
    log(f'Loaded {len(hub.adapters)} adapters, {len(hub.tools)} tools')
    log('Endpoints: POST /mcp | GET /health | GET /tools')
    server.serve_forever()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18767
    run(port)
