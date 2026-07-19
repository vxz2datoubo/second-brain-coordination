#!/usr/bin/env python3
# 第二大脑 MCP Server - 原生 stdio 协议
import json, sys
from pathlib import Path
from datetime import datetime
 
BRAIN_DIR = Path(r'F:\aidanao\second-brain')
LOG_DIR = Path(r'F:\aidanao\core\logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
 
def log(msg):
print(f'[Brain {datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)
 
TOOLS = [
{"name": "brain_search", "description": "搜索知识库", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query"]}},
{"name": "brain_consult", "description": "决策前查询教训和红线", "inputSchema": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}},
{"name": "brain_digest", "description": "存入新知识", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "title": {"type": "string"}, "source": {"type": "string"}}, "required": ["text"]}},
{"name": "brain_trade_log", "description": "记录交易", "inputSchema": {"type": "object", "properties": {"stock": {"type": "string"}, "action": {"type": "string"}, "price": {"type": "number"}, "amount": {"type": "integer"}, "pnl": {"type": "number"}, "conditions": {"type": "array"}, "notes": {"type": "string"}}, "required": ["stock", "action", "price"]}},
{"name": "brain_read_rules", "description": "读取规则和教训库", "inputSchema": {"type": "object", "properties": {}}},
{"name": "brain_evolve", "description": "运行进化引擎", "inputSchema": {"type": "object", "properties": {}}},
{"name": "brain_status", "description": "获取系统状态", "inputSchema": {"type": "object", "properties": {}}},
]
 
def load_kb():
kb = {'rules': '', 'lessons': '', 'log': ''}
rules_file = BRAIN_DIR / 'rules.md'
lessons_file = BRAIN_DIR / 'lessons.md'
log_file = BRAIN_DIR / 'daily_log.md'
if rules_file.exists(): kb['rules'] = rules_file.read_text(encoding='utf-8')
if lessons_file.exists(): kb['lessons'] = lessons_file.read_text(encoding='utf-8')
if log_file.exists(): kb['log'] = log_file.read_text(encoding='utf-8')
return kb
 
def search(query, top_k=8):
kb = load_kb()
q = query.lower()
results = []
for src, text in [('rules', kb['rules']), ('lessons', kb['lessons'])]:
for line in text.split('\n'):
line = line.strip()
if q in line.lower() and len(line) > 10 and not line.startswith('#'):
results.append({'type': src, 'content': line})
log(f'search: {query} -> {len(results)}')
return {'query': query, 'results': results[:top_k], 'total': len(results)}
 
def consult(topic):
kb = load_kb()
text = kb['rules'] + '\n' + kb['lessons']
findings = [l.strip() for l in text.split('\n')
if topic.lower() in l.lower() and len(l.strip()) > 5
and any(k in l for k in ['红线','禁止','止损','亏损','仓位','必须','注意'])]
log(f'consult: {topic} -> {len(findings)} findings')
return {'topic': topic, 'findings': findings[:20], 'count': len(findings)}
 
def digest(text, title='', source='manual'):
entry_file = LOG_DIR / (f'digest_{datetime.now().strftime("%Y%m%d")}.md')
entry = f'\n---\n# {title or "Digest"}\nSource: {source}\nTime: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n{text}\n'
entry_file.write_text(entry, encoding='utf-8', append=True)
log(f'digest: {title or text[:50]}')
return {'success': True, 'file': str(entry_file)}
 
def trade_log(stock, action, price, amount=None, pnl=0, conditions=None, notes=''):
log_file = BRAIN_DIR / 'daily_log.md'
today = datetime.now().strftime('%Y-%m-%d')
t = datetime.now().strftime('%H:%M')
cond_str = '|'.join(conditions or [])
row = f'| {today} | {stock} | {action} | {amount or ""} | {price} | {t} | {pnl} | {notes} | {cond_str} |'
content = log_file.read_text(encoding='utf-8', errors='ignore') + '\n' + row
log_file.write_text(content, encoding='utf-8')
log(f'trade_log: {stock} {action} @ {price} pnl={pnl}')
return {'success': True, 'row': row}
 
def read_rules():
kb = load_kb()
return {'rules': kb['rules'], 'lessons': kb['lessons'], 'log': kb['log']}
 
def evolve():
kb = load_kb()
trades = [l for l in kb['log'].split('\n') if '|' in l and len(l) > 50]
suggestions = []
if len(trades) >= 5:
wins = 0
for t in trades:
try: wins += 1 if float(t.split('|')[-3].strip()) > 0 else 0
except: pass
wr = wins / len(trades)
suggestions.append(f'历史胜率: {wr*100:.1f}% ({wins}/{len(trades)}笔)')
suggestions.append('建议: ' + ('继续当前策略' if wr > 0.5 else '需要审视当前规则'))
return {'suggestions': suggestions, 'trade_count': len(trades)}
 
def get_status():
kb = load_kb()
trades = [l for l in kb['log'].split('\n') if '|' in l and len(l) > 50]
if not trades:
return {'status': '初始化中，暂无交易数据', 'total_trades': 0}
pnl_sum = 0
wins = 0
for t in trades:
parts = t.split('|')
if len(parts) > 6:
try:
pnl = float(parts[-3].strip())
pnl_sum += pnl
if pnl > 0: wins += 1
except: pass
return {'status': f'总交易{len(trades)}笔 | 胜率{wins/len(trades)*100:.0f}% | 累计收益{pnl_sum:.0f}元',
'total_trades': len(trades), 'win_rate': f'{wins/len(trades)*100:.0f}%', 'total_pnl': pnl_sum}
 
def read_msg():
h = b''
while b'\r\n\r\n' not in h:
chunk = sys.stdin.buffer.read(1)
if not chunk: return None
h += chunk
for line in h.decode().split('\r\n'):
if line.lower().startswith('content-length:'):
cl = int(line.split(':')[1].strip())
return json.loads(sys.stdin.buffer.read(cl).decode())
 
def send(id_, r):
body = json.dumps(r, ensure_ascii=False).encode()
sys.stdout.write(f'Content-Length: {len(body)}\r\n\r\n')
sys.stdout.buffer.write(body)
sys.stdout.flush()
 
def main():
log('Second Brain MCP started')
while True:
msg = read_msg()
if msg is None: break
method = msg.get('method',''); id_ = msg.get('id')
params = msg.get('params',{}); args = params.get('arguments',{}); name = params.get('name','')
try:
if method == 'initialize':
send(id_, {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'brain-mcp', 'version': '1.0'}})
elif method == 'tools/list':
send(id_, {'tools': TOOLS})
elif method == 'tools/call':
if name == 'brain_search': send(id_, search(args.get('query',''), args.get('top_k', 8)))
elif name == 'brain_consult': send(id_, consult(args.get('topic','')))
elif name == 'brain_digest': send(id_, digest(args.get('text',''), args.get('title',''), args.get('source','manual')))
elif name == 'brain_trade_log': send(id_, trade_log(args.get('stock',''), args.get('action',''), args.get('price',0), args.get('amount'), args.get('pnl',0), args.get('conditions'), args.get('notes','')))
elif name == 'brain_read_rules': send(id_, read_rules())
elif name == 'brain_evolve': send(id_, evolve())
elif name == 'brain_status': send(id_, get_status())
else: send(id_, {'error': f'unknown: {name}'})
elif method == 'notifications/initialized': pass
except Exception as e: send(id_, {'error': str(e)})
 
if __name__ == '__main__': main()
