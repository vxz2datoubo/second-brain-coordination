#!/usr/bin/env python3
# 通达信 MCP Server - 原生 stdio 协议
# Codex/MaiBot 直连，无需中间层
import json, sys
from pathlib import Path
sys.path.insert(0, r'F:\tongdaxin\PYPlugins\user')
try:
import tqcenter as tq
TQ = True
tq.initialize(r'F:\tongdaxin')
except Exception as e:
TQ = False
print(f'[TDX MCP] TQ not available: {e}', file=sys.stderr)
 
TOOLS = [
{"name": "tdx_quote", "description": "获取股票实时行情", "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
{"name": "tdx_batch_quotes", "description": "批量获取多只股票行情", "inputSchema": {"type": "object", "properties": {"codes": {"type": "array", "items": {"type": "string"}}}}},
{"name": "tdx_kline", "description": "获取K线数据", "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}, "period": {"type": "string"}, "count": {"type": "integer"}}, "required": ["code", "period"]}},
{"name": "tdx_market_sentiment", "description": "大盘情绪", "inputSchema": {"type": "object", "properties": {}}},
{"name": "tdx_calculate_indicator", "description": "计算技术指标", "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}, "indicator": {"type": "string"}, "period": {"type": "string"}}, "required": ["code", "indicator"]}},
{"name": "tdx_sector_momentum", "description": "板块动量", "inputSchema": {"type": "object", "properties": {}}},
]
 
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
 
def get_quote(code):
if not TQ: return {'error': 'not init'}
try:
d = tq.get_realtime_data([code], count=1)
if d: d = d[0]
return {'code': code, 'name': d.get('Name',''), 'price': float(d.get('Close',0)), 'open': float(d.get('Open',0)), 'high': float(d.get('High',0)), 'low': float(d.get('Low',0)), 'vol': float(d.get('Volume',0)), 'change_pct': float(d.get('ZD',0)), 'time': d.get('Time','')}
except Exception as e: return {'error': str(e)}
 
def get_batch(codes):
if not TQ: return [{'error': 'not init'}]
try:
res = tq.get_realtime_data(codes, count=1)
return [{'code': d.get('Code',''), 'name': d.get('Name',''), 'price': float(d.get('Close',0)), 'change_pct': float(d.get('ZD',0))} for d in res]
except Exception as e: return [{'error': str(e)}]
 
def get_kline(code, period='1d', count=100):
if not TQ: return {'error': 'not init'}
try:
pm = {'1d':'day','1w':'week','5':'5','15':'15','30':'30','60':'60'}
res = tq.get_history_data(code, count=count, period=pm.get(period,'day'))
return {'code':code,'period':period,'klines':[{'date':d.get('Date',''),'open':float(d.get('Open',0)),'high':float(d.get('High',0)),'low':float(d.get('Low',0)),'close':float(d.get('Close',0)),'vol':float(d.get('Volume',0))} for d in res]}
except Exception as e: return {'error': str(e)}
 
def ema(data, n):
k = 2/(n+1); r = [data[0]]
for v in data[1:]: r.append(v*k + r[-1]*(1-k))
return r
 
def calc_macd(closes):
dif = [a-b for a,b in zip(ema(closes,12), ema(closes,26))]
dea = ema(dif, 9)
macd = [(d-s)*2 for d,s in zip(dif,dea)]
return dif, dea, macd
 
def calc_indicator(code, ind='macd', period='1d'):
if not TQ: return {'error': 'not init'}
try:
kl = get_kline(code, period, 60)
if 'error' in kl: return kl
closes = [k['close'] for k in kl['klines']]
result = {'code': code, 'indicator': ind, 'period': period}
if ind == 'macd':
dif, dea, macd = calc_macd(closes)
cross = 'gold' if dif[-1]>dea[-1] and dif[-2]<=dea[-2] else 'dead' if dif[-1]<dea[-1] and dif[-2]>=dea[-2] else 'none'
result.update({'dif': round(dif[-1],4), 'dea': round(dea[-1],4), 'macd': round(macd[-1],4), 'cross': cross})
elif ind == 'ma':
def ma(d,n): return [sum(d[max(0,i-n+1):i+1])/min(i+1,n) for i in range(len(d))]
m5,m10,m20 = ma(closes,5), ma(closes,10), ma(closes,20)
result.update({'ma5': round(m5[-1],2), 'ma10': round(m10[-1],2), 'ma20': round(m20[-1],2), 'price': closes[-1], 'above_ma5': closes[-1]>m5[-1]})
elif ind == 'rsi':
g,l = [],[]
for i in range(1,len(closes)):
d=closes[i]-closes[i-1]; g.append(max(d,0)); l.append(max(-d,0))
def rsi(g,l,n):
r=[]
for i in range(len(g)):
ag=sum(g[max(0,i-n+1):i+1])/min(i+1,n); al=sum(l[max(0,i-n+1):i+1])/min(i+1,n)
r.append(100-100/(1+ag/al) if al>0 else 50)
return r
rs=rsi(g,l,14)
result.update({'rsi': round(rs[-1],2), 'overbought': rs[-1]>70, 'oversold': rs[-1]<30})
return result
except Exception as e: return {'error': str(e)}
 
def market_sentiment():
if not TQ: return {'error': 'not init'}
try:
q = get_batch(['000001.SZ','399001.SZ','399006.SZ'])
up = sum(1 for x in q if 'error' not in x and x.get('change_pct',0)>0)
return {'quotes': q, 'up_leading': up > len(q)/2, 'sentiment': 'bullish' if up > len(q)/2 else 'bearish'}
except Exception as e: return {'error': str(e)}
 
def sector_momentum():
if not TQ: return {'error': 'not init'}
try:
b = tq.get_block_list()
r = [{'name':x.get('name',''),'change':float(x.get('change',0))} for x in b if float(x.get('change',0))>1]
f = [{'name':x.get('name',''),'change':float(x.get('change',0))} for x in b if float(x.get('change',0))<-1]
r.sort(key=lambda x: -x['change']); f.sort(key=lambda x: x['change'])
return {'rising': r[:10], 'falling': f[:10]}
except Exception as e: return {'error': str(e)}
 
def main():
while True:
msg = read_msg()
if msg is None: break
method = msg.get('method',''); id_ = msg.get('id')
params = msg.get('params',{}); args = params.get('arguments',{}); name = params.get('name','')
try:
if method == 'initialize':
send(id_, {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'tdx-mcp', 'version': '1.0'}})
elif method == 'tools/list':
send(id_, {'tools': TOOLS})
elif method == 'tools/call':
if name == 'tdx_quote': send(id_, get_quote(args.get('code','')))
elif name == 'tdx_batch_quotes': send(id_, {'quotes': get_batch(args.get('codes',[]))})
elif name == 'tdx_kline': send(id_, get_kline(args.get('code',''), args.get('period','1d'), args.get('count',100)))
elif name == 'tdx_market_sentiment': send(id_, market_sentiment())
elif name == 'tdx_calculate_indicator': send(id_, calc_indicator(args.get('code',''), args.get('indicator','macd'), args.get('period','1d')))
elif name == 'tdx_sector_momentum': send(id_, sector_momentum())
else: send(id_, {'error': f'unknown: {name}'})
elif method == 'notifications/initialized': pass
except Exception as e: send(id_, {'error': str(e)})
 
if __name__ == '__main__': main()
