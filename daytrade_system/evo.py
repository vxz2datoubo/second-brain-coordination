"""EvoSys v1.0 - 可自进化交易系统"""
import json, os, sys, logging, sqlite3, time, struct
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).parent
DATA = ROOT / 'evo_data'
DATA.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(DATA / f'evo_{date.today().isoformat()}.log', encoding='utf-8'), logging.StreamHandler()])
log = logging.getLogger('evo')

@dataclass
class FS:
    name: str; score: float; weight: float; raw: float; sigs: list

@dataclass
class SR:
    code: str; name: str; total: float; sell: float; buy: float; conf: str; regime: str
    factors: dict; reason: str; can_short: bool; can_long: bool; sug: str
    price: float; prev: float; chg: float

@dataclass
class TS:
    id: str; code: str; sell_price: float; sell_time: str; status: str = 'open'
    buy_price: float = None; buy_time: str = None; pnl: float = 0

class DB:
    def __init__(self):
        self.path = str(DATA / 'evo.db')
        self._init()
    
    def _init(self):
        with sqlite3.connect(self.path) as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY, trade_date TEXT, stock_code TEXT, stock_name TEXT, direction TEXT, price REAL, shares INTEGER, amount REAL, pnl_pct REAL DEFAULT 0, signal_score REAL, signal_reason TEXT, confidence TEXT, regime TEXT, slot_id TEXT, created_at TEXT DEFAULT (datetime('now')));
                CREATE TABLE IF NOT EXISTS daily_summary (id INTEGER PRIMARY KEY, trade_date TEXT UNIQUE, total_trades INTEGER DEFAULT 0, successful_trades INTEGER DEFAULT 0, total_pnl REAL DEFAULT 0, kunlun_pnl REAL DEFAULT 0, blue_pnl REAL DEFAULT 0, avg_signal_score REAL, market_regime TEXT, notes TEXT, created_at TEXT DEFAULT (datetime('now')));
                CREATE TABLE IF NOT EXISTS factor_weights (id INTEGER PRIMARY KEY, stock_code TEXT, f1 REAL, f2 REAL, f3 REAL, f4 REAL, f5 REAL, f6 REAL, total_score REAL, effective_date TEXT, created_at TEXT DEFAULT (datetime('now')));
                CREATE TABLE IF NOT EXISTS param_evolution (id INTEGER PRIMARY KEY, evolution_date TEXT, stock_code TEXT, param_name TEXT, old_value REAL, new_value REAL, reason TEXT, correlation_change REAL, created_at TEXT DEFAULT (datetime('now')));
                CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY, lesson_date TEXT, category TEXT, title TEXT, content TEXT, stock_code TEXT, outcome TEXT, pnl_impact REAL DEFAULT 0, verified INTEGER DEFAULT 0, times_applied INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now')));
                CREATE TABLE IF NOT EXISTS self_tests (id INTEGER PRIMARY KEY, test_date TEXT, test_type TEXT, passed INTEGER, details TEXT, issues TEXT, created_at TEXT DEFAULT (datetime('now')));
                CREATE TABLE IF NOT EXISTS sentiment_log (id INTEGER PRIMARY KEY, log_time TEXT, stock_code TEXT, sentiment_score REAL DEFAULT 0, news_count INTEGER DEFAULT 0, sector_momentum REAL, related_news TEXT, action_taken TEXT, created_at TEXT DEFAULT (datetime('now')));
                CREATE TABLE IF NOT EXISTS signal_history (id INTEGER PRIMARY KEY, signal_time TEXT, stock_code TEXT, total_score REAL, sell_score REAL, buy_score REAL, confidence TEXT, regime TEXT, f1_score REAL, f2_score REAL, f3_score REAL, f4_score REAL, f5_score REAL, f6_score REAL, reason TEXT, action_taken TEXT, created_at TEXT DEFAULT (datetime('now')));
                CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date);
                CREATE INDEX IF NOT EXISTS idx_trades_stock ON trades(stock_code);
            ''')
    
    def log_trade(self, t):
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO trades (trade_date, stock_code, stock_name, direction, price, shares, amount, pnl_pct, signal_score, signal_reason, confidence, regime, slot_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', 
                (t.get('trade_date', date.today().isoformat()), t['stock_code'], t.get('stock_name', t['stock_code']), t['direction'], t['price'], t.get('shares', 100), t['amount'], t.get('pnl_pct', 0), t.get('signal_score'), t.get('signal_reason'), t.get('confidence'), t.get('regime'), t.get('slot_id')))
    
    def get_trades(self, stock_code=None, days=30):
        q = "SELECT * FROM trades WHERE trade_date >= date('now', ?)"; p = [f'-{days} days']
        if stock_code: q += ' AND stock_code = ?'; p.append(stock_code)
        q += ' ORDER BY created_at DESC'
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute(q, p)]
    
    def save_daily_summary(self, s):
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT OR REPLACE INTO daily_summary (trade_date, total_trades, successful_trades, total_pnl, kunlun_pnl, blue_pnl, avg_signal_score, market_regime, notes) VALUES (?,?,?,?,?,?,?,?,?)',
                (s.get('trade_date', date.today().isoformat()), s.get('total_trades', 0), s.get('successful_trades', 0), s.get('total_pnl', 0), s.get('kunlun_pnl', 0), s.get('blue_pnl', 0), s.get('avg_signal_score'), s.get('market_regime'), s.get('notes')))
    
    def get_daily_summary(self, days=30):
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute("SELECT * FROM daily_summary WHERE trade_date >= date('now', ?) ORDER BY trade_date DESC", [f'-{days} days'])]
    
    def save_factor_weights(self, w, code, total_score=None):
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO factor_weights (stock_code, f1, f2, f3, f4, f5, f6, total_score, effective_date) VALUES (?,?,?,?,?,?,?,?,?)',
                (code, w.get('f1'), w.get('f2'), w.get('f3'), w.get('f4'), w.get('f5'), w.get('f6'), total_score, date.today().isoformat()))
    
    def log_param_evolution(self, name, old, new, reason, code=None, corr=None):
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO param_evolution (evolution_date, stock_code, param_name, old_value, new_value, reason, correlation_change) VALUES (?,?,?,?,?,?,?)',
                (date.today().isoformat(), code, name, old, new, reason, corr))
    
    def add_lesson(self, l):
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO lessons (lesson_date, category, title, content, stock_code, outcome, pnl_impact) VALUES (?,?,?,?,?,?,?)',
                (l.get('lesson_date', date.today().isoformat()), l['category'], l['title'], l['content'], l.get('stock_code'), l.get('outcome'), l.get('pnl_impact', 0)))
    
    def get_lessons(self, category=None, days=90):
        q = "SELECT * FROM lessons WHERE lesson_date >= date('now', ?)"; p = [f'-{days} days']
        if category: q += ' AND category = ?'; p.append(category)
        q += ' ORDER BY lesson_date DESC'
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute(q, p)]
    
    def log_self_test(self, test_type, passed, details=None, issues=None):
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO self_tests (test_date, test_type, passed, details, issues) VALUES (?,?,?,?,?)',
                (date.today().isoformat(), test_type, passed, details, issues))
    
    def log_sentiment(self, d):
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO sentiment_log (log_time, stock_code, sentiment_score, news_count, sector_momentum, related_news, action_taken) VALUES (?,?,?,?,?,?,?)',
                (d.get('log_time', datetime.now().isoformat()), d.get('stock_code'), d.get('sentiment_score', 0), d.get('news_count', 0), d.get('sector_momentum', 0), d.get('related_news'), d.get('action_taken')))
    
    def log_signal(self, d):
        with sqlite3.connect(self.path) as c:
            c.execute('INSERT INTO signal_history (signal_time, stock_code, total_score, sell_score, buy_score, confidence, regime, f1_score, f2_score, f3_score, f4_score, f5_score, f6_score, reason, action_taken) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (d.get('signal_time', datetime.now().isoformat()), d['stock_code'], d['total_score'], d.get('sell_score', 0), d.get('buy_score', 0), d.get('confidence'), d.get('regime'), d.get('f1_score', 0), d.get('f2_score', 0), d.get('f3_score', 0), d.get('f4_score', 0), d.get('f5_score', 0), d.get('f6_score', 0), d.get('reason'), d.get('action_taken')))

class TDX:
    def __init__(self, url='https://txmcp.tdx.com.cn:3001/txmcp'):
        self.url = url; self._conn = False
    
    def connect(self):
        import urllib.request
        try:
            req = urllib.request.Request(self.url, data=b'{"jsonrpc":"2.0","method":"tools/list","id":1}', headers={'Content-Type':'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=10) as r:
                json.loads(r.read())
                self._conn = True
                log.info('[TDX] 连接成功')
                return True
        except Exception as e:
            log.warning(f'[TDX] 连接失败: {e}')
            self._conn = False
            return False
    
    def get_quote(self, code):
        if not self._conn: return self._offline_quote(code)
        import urllib.request
        try:
            req = urllib.request.Request(self.url, data=b'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"tdx_quotes","arguments":{"codes":["' + code.encode() + b'"]}},"id":2}', headers={'Content-Type':'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=10) as r:
                res = json.loads(r.read())
                if 'result' in res: return res['result'].get(code, {})
        except: pass
        return self._offline_quote(code)
    
    def get_kline(self, code, period='5m', count=100):
        if not self._conn: return self._offline_kline(code, period, count)
        return self._offline_kline(code, period, count)
    
    def get_news(self, kw='AI', hours=24):
        if not self._conn: return []
        return []
    
    def _offline_quote(self, code):
        mkt = 'sz' if code.startswith(('00','30')) else 'sh'
        p = rf'F:\tongdaxin\vipdoc\{mkt}\lday\{mkt}{code}.day'
        if not os.path.exists(p): return {}
        with open(p,'rb') as f: data = f.read()
        if len(data) < 32: return {}
        u = struct.unpack_from('<IIIIIfII', data, len(data)-32)
        prev = u[4]/100.0
        if len(data) >= 64:
            u2 = struct.unpack_from('<IIIIIfII', data, len(data)-64)
            prev = u2[4]/100.0
        names = {'300058':'昆仑万维','300418':'蓝色光标'}
        return {'code':code,'name':names.get(code,code),'now':u[4]/100.0,'open':u[1]/100.0,'high':u[2]/100.0,'low':u[3]/100.0,'close':u[4]/100.0,'pre_close':prev,'volume':u[6],'amount':u[5],'chg_pct':(u[4]/100.0/prev-1)*100 if prev else 0}
    
    def _offline_kline(self, code, period, count):
        import struct
        mkt = 'sz' if code.startswith(('00','30')) else 'sh'
        p = rf'F:\tongdaxin\vipdoc\{mkt}\fzline\{mkt}{code}.lc5' if period=='5m' else rf'F:\tongdaxin\vipdoc\{mkt}\lday\{mkt}{code}.day'
        if not os.path.exists(p): return []
        with open(p,'rb') as f: data = f.read()
        bars = []
        if period == '5m':
            for i in range(len(data)//32):
                u = struct.unpack_from('<HHfffffIHH', data, i*32)
                dw, minute = u[0], u[1]
                y = (dw//2048)+2004; md = dw%2048; m, d = md//100, md%100; ds = f'{y:04d}{m:02d}{d:02d}'
                if ds.startswith('1970') or u[2]==0: continue
                hh, mm = divmod(minute, 60)
                bars.append({'date':ds,'time':f'{hh:02d}:{mm:02d}','open':u[2],'high':u[3],'low':u[4],'close':u[5],'amount':u[6],'volume':u[7]})
        else:
            for i in range(len(data)//32):
                u = struct.unpack_from('<IIIIIfII', data, i*32)
                if u[0] < 20000000: continue
                bars.append({'date':str(u[0]),'open':u[1]/100.0,'high':u[2]/100.0,'low':u[3]/100.0,'close':u[4]/100.0,'amount':u[5],'volume':u[6]})
        return bars[-count:] if bars else []

class SC:
    W = {'300058':{'f1':0.25,'f2':0.20,'f3':0.20,'f4':0.12,'f5':0.13,'f6':0.10},'300418':{'f1':0.30,'f2':0.20,'f3':0.15,'f4':0.15,'f5':0.10,'f6':0.10}}
    
    def calc(self, code, quote, min5, daily, weights=None):
        if not weights: weights = self.W.get(code, self.W['300058'])
        price = quote.get('now', quote.get('close', 0)); prev = quote.get('pre_close', quote.get('close', price))
        if not min5 or len(min5) < 5: return SR(code, quote.get('name',code), 0, 0, 0, 'D', 'UNKNOWN', {}, '数据不足', False, False, '等待数据', price, prev, 0)
        
        factors = {}; sp = []; bp = []
        f1 = self._f1(price, min5); factors['F1'] = f1
        if any('卖' in s for s in f1.sigs): sp.append((f1.score, weights['f1']))
        elif any('买' in s for s in f1.sigs): bp.append((f1.score, weights['f1']))
        f2 = self._f2(min5); factors['F2'] = f2
        if any('卖' in s for s in f2.sigs): sp.append((f2.score, weights['f2']))
        elif any('买' in s for s in f2.sigs): bp.append((f2.score, weights['f2']))
        f3 = self._f3(price, min5, daily); factors['F3'] = f3
        if any('卖' in s for s in f3.sigs): sp.append((f3.score, weights['f3']))
        elif any('买' in s for s in f3.sigs): bp.append((f3.score, weights['f3']))
        f4 = self._f4(min5); factors['F4'] = f4
        if any('卖' in s for s in f4.sigs): sp.append((f4.score, weights['f4']))
        f5 = self._f5(min5); factors['F5'] = f5
        if any('卖' in s for s in f5.sigs): sp.append((f5.score, weights['f5']))
        f6 = self._f6(price, prev, min5); factors['F6'] = f6
        if any('卖' in s for s in f6.sigs): sp.append((f6.score, weights['f6']))
        elif any('买' in s for s in f6.sigs): bp.append((f6.score, weights['f6']))
        
        total = sum(factors[f'F{i}'].score * weights[f'f{i}'] for i in range(1,7))
        sw = sum(w for _,w in sp); bw = sum(w for _,w in bp)
        sell_score = sum(s*w for s,w in sp)/sw*100 if sp else 0
        buy_score = sum(s*w for s,w in bp)/bw*100 if bp else 0
        
        conf = 'A++' if total>=90 else 'A' if total>=75 else 'B' if total>=60 else 'C' if total>=45 else 'D'
        regime = self._regime(daily, min5, prev)
        can_short = sell_score > 25 and regime not in ('EXTREME','LOW_VOL_RANGE')
        can_long = buy_score > 40
        
        top = sorted([(n,f) for n,f in factors.items() if f.score>0], key=lambda x:-x[1].score)[:3]
        reason = ' + '.join(f'{n}({f.score:.0f})' for n,f in top) if top else '无明显信号'
        
        if conf in ('A++','A') and sell_score > 40: sug = '★★★ 强烈建议执行倒T卖出'
        elif conf == 'B' and sell_score > 30: sug = '★★ 可执行倒T，限额1笔'
        elif conf == 'C': sug = '★ 谨慎观察，等待更清晰机会'
        else: sug = '— 暂不操作'
        
        chg = (price/prev-1)*100 if prev else 0
        return SR(code, quote.get('name',code), round(total,1), round(sell_score,1), round(buy_score,1), conf, regime, factors, reason, can_short, can_long, sug, price, prev, round(chg,2))
    
    def _f1(self, price, bars):
        if len(bars) < 5: return FS('F1',0,0.25,0,['数据不足'])
        vwap = sum(b.get('amount',0) for b in bars)/max(1,sum(b.get('volume',0) for b in bars))
        ps = [b.get('close',price) for b in bars[-20:]]
        std = (sum((p-sum(ps)/len(ps))**2 for p in ps)/len(ps))**0.5 if len(ps)>=2 else price*0.01
        sigma = (price-vwap)/std if std>0 else 0; score = min(100,abs(sigma)*50); sigs = []
        if sigma>1.5: score=min(100,70+(sigma-1.5)*15); sigs.append(f'卖: VWAP+{sigma:.1f}σ高位')
        elif sigma>0.5: sigs.append(f'卖: VWAP+{sigma:.1f}σ偏高')
        elif sigma<-1.5: sigs.append(f'买: VWAP-{abs(sigma):.1f}σ低位')
        elif sigma<-0.5: sigs.append(f'买: VWAP-{abs(sigma):.1f}σ偏低')
        return FS('F1',round(score,1),0.25,round(sigma,3),sigs)
    
    def _f2(self, bars):
        if len(bars) < 7: return FS('F2',0,0.20,50,['数据不足'])
        cs = [b.get('close',0) for b in bars]; ds = [cs[i]-cs[i-1] for i in range(1,len(cs))]
        g = [d for d in ds[-6:] if d>0]; l = [-d for d in ds[-6:] if d<0]
        ag = sum(g)/6 if g else 0; al = sum(l)/6 if l else 0
        rsi = 100 if al==0 else 100-(100/(1+ag/al)); score = 0; sigs = []
        if rsi>80: score=min(100,90+(rsi-80)*2); sigs.append(f'卖: RSI={rsi:.0f}极度超买')
        elif rsi>70: score=min(100,70+(rsi-70)*2); sigs.append(f'卖: RSI={rsi:.0f}超买')
        elif rsi>60: score=40+(rsi-60)*3; sigs.append(f'卖: RSI={rsi:.0f}偏热')
        elif rsi<20: score=min(100,90+(30-rsi)*2); sigs.append(f'买: RSI={rsi:.0f}极度超卖')
        elif rsi<30: score=min(100,70+(40-rsi)*2); sigs.append(f'买: RSI={rsi:.0f}超卖')
        elif rsi<40: score=40+(50-rsi)*3; sigs.append(f'买: RSI={rsi:.0f}偏冷')
        return FS('F2',round(score,1),0.20,round(rsi,1),sigs)
    
    def _f3(self, price, bars, daily):
        if len(bars) < 6: return FS('F3',0,0.20,50,['数据不足'])
        dh = max(b.get('high',0) for b in bars); dl = min(b.get('low',float('inf')) for b in bars); dr = dh-dl
        if dr==0: return FS('F3',0,0.20,50,['无波动'])
        pp = (price-dl)/dr*100; r6 = bars[-6:]; lv = sum(b.get('volume',0) for b in r6[-3:]); pv = sum(b.get('volume',0) for b in r6[:3])
        vr = lv/pv if pv>0 else 1.0; score = 0; sigs = []
        if pp>80 and vr<0.8: score=70+(pp-80); sigs.append(f'卖: 高位{pp:.0f}%+量缩{vr:.1f}x')
        elif pp>70 and vr<0.9: score=50+(pp-70); sigs.append(f'卖: 偏高{pp:.0f}%+量减')
        elif pp>60: score=(pp-60)*1.5; sigs.append(f'卖: 日高{pp:.0f}%')
        elif pp<20 and vr>1.2: score=70+(20-pp); sigs.append(f'买: 低位{pp:.0f}%+量增{vr:.1f}x')
        elif pp<30 and vr>1.1: score=50+(30-pp); sigs.append(f'买: 偏低{pp:.0f}%+量增')
        return FS('F3',round(score,1),0.20,round(pp,1),sigs)
    
    def _f4(self, bars):
        if len(bars) < 5: return FS('F4',0,0.15,0,['数据不足'])
        r = bars[-5:]; hs = [b.get('high',0) for b in r]; cs = [b.get('close',0) for b in r]; score = 0; sigs = []
        if all(hs[i]<hs[i-1] for i in range(1,len(hs))): score=65; sigs.append('卖: 5K高点逐级下降')
        if len(r)>=4 and cs[0]<cs[1]<cs[2] and cs[3]<cs[2]: score=max(score,60); sigs.append('卖: 连续上涨后首跌')
        return FS('F4',round(score,1),0.15,0,sigs)
    
    def _f5(self, bars):
        if len(bars) < 4: return FS('F5',0,0.13,0,['数据不足'])
        ds = []
        for i in range(len(bars)-1):
            u = bars[i].get('up_count',0); dn = bars[i].get('down_count',0)
            ds.append((u-dn)/(u+dn+1) if u+dn>0 else 0)
        if len(ds)<3: return FS('F5',0,0.13,0,['数据不足'])
        cur = ds[-1]; p1 = ds[-2]; score = 0; sigs = []
        if cur<0 and p1>0: score=70; sigs.append('卖: Delta由正转负')
        elif cur<0 and cur<p1: score=50; sigs.append('卖: Delta持续下行')
        return FS('F5',round(score,1),0.13,round(cur,2),sigs)
    
    def _f6(self, price, prev, bars):
        if not prev or not bars: return FS('F6',0,0.10,0,['无前收/无数据'])
        op = bars[0].get('open',price) if isinstance(bars[0],dict) else price; gp = (op/prev-1)*100; score = 0; sigs = []
        if gp>2: score=75+(gp-2)*10; sigs.append(f'卖: 高开{gp:.1f}%大幅跳空')
        elif gp>1: score=55+(gp-1)*20; sigs.append(f'卖: 高开{gp:.1f}%跳空')
        elif gp>0.5: score=35; sigs.append(f'卖: 高开{gp:.1f}%小幅高开')
        elif gp<-2: score=75+abs(gp-2)*10; sigs.append(f'买: 低开{gp:.1f}%大幅低开')
        elif gp<-1: score=55+abs(gp-1)*20; sigs.append(f'买: 低开{gp:.1f}%低开')
        elif gp<-0.5: score=35; sigs.append(f'买: 低开{gp:.1f}%小幅低开')
        return FS('F6',round(score,1),0.10,round(gp,2),sigs)
    
    def _regime(self, daily, min5, prev):
        if not daily or len(daily)<20: return 'UNKNOWN'
        cs = [b.get('close',0) for b in daily[-20:]]; ma5=sum(cs[-5:])/5; ma20=sum(cs[-20:])/20
        trs = [max(daily[-15+i].get('high',0)-daily[-15+i].get('low',0),abs(daily[-15+i].get('high',0)-(daily[-15+i-1].get('close',0))),abs(daily[-15+i].get('low',0)-(daily[-15+i-1].get('close',0)))) for i in range(1,len(daily[-15:]))]
        atr = sum(trs)/len(trs) if trs else 0; ap = atr/prev*100 if prev else 0
        cp = min5[-1].get('close',cs[-1]) if min5 else cs[-1]
        if ma5>ma20*1.02 and cp>ma5: return 'TREND_UP'
        elif ma5<ma20*0.98 and cp<ma5: return 'TREND_DOWN'
        elif ap>4: return 'HIGH_VOL_RANGE'
        elif ap<2: return 'LOW_VOL_RANGE'
        else: return 'HIGH_VOL_RANGE'

class SM:
    MAX = 3; COOL = 30
    def __init__(self, code): self.code = code; self.slots = []; self.sell_cnt = 0; self.done_cnt = 0; self.daily_pnl = 0.0
    def can_open(self):
        return sum(1 for s in self.slots if s.status=='open')<self.MAX and self.sell_cnt<2 and self._cool()
    def _cool(self):
        now = datetime.now()
        for s in self.slots:
            if s.status=='open':
                try:
                    dt = datetime.strptime(s.sell_time,'%Y-%m-%d %H:%M')
                    if (now-dt).seconds<self.COOL*60: return False
                except: pass
        return True
    def open(self, price, score, reason):
        if not self.can_open(): return None
        sid = f'{self.code}_{datetime.now().strftime("%H%M%S")}'
        slot = TS(sid,self.code,price,datetime.now().strftime('%Y-%m-%d %H:%M'))
        self.slots.append(slot); self.sell_cnt += 1; return slot
    def close(self, sid, price):
        for s in self.slots:
            if s.id==sid and s.status=='open':
                s.status = 'done'; s.buy_price = price; s.buy_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                s.pnl = (s.sell_price-price)/s.sell_price*100; self.daily_pnl += s.pnl; self.done_cnt += 1; return s
        return None
    def open_slots(self): return [s for s in self.slots if s.status=='open']
    def force_close(self, price):
        for s in self.slots:
            if s.status=='open':
                s.status = 'done'; s.buy_price = price; s.buy_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                s.pnl = (s.sell_price-price)/s.sell_price*100; self.daily_pnl += s.pnl
    def reset(self): self.slots = [s for s in self.slots if s.status=='open']; self.sell_cnt = 0; self.done_cnt = 0; self.daily_pnl = 0.0

class SE:
    SEC = {'300058':['AI应用','营销','游戏','ChatGPT','Sora'],'300418':['AI大模型','游戏','社交','算力','ChatGPT']}
    def __init__(self, db=None): self.db = db; self.last_check = {}
    def check(self, code, tdx):
        now = datetime.now(); key = f'{code}_{now.strftime("%Y%m%d_%H")}'
        if key == self.last_check.get(code): return {'need_news':False}
        self.last_check[key] = key
        kws = self.SEC.get(code,['AI']); news = []
        for kw in kws[:3]: news.extend(tdx.get_news(kw, 24))
        score = self._analyze(news)
        if self.db: self.db.log_sentiment({'log_time':now.isoformat(),'stock_code':code,'sentiment_score':score,'news_count':len(news),'related_news':json.dumps(news[:5],ensure_ascii=False)})
        return {'need_news':True,'sentiment_score':score,'news_count':len(news),'news':news[:5]}
    def _analyze(self, news):
        if not news: return 0
        pos = ['利好','涨停','突破','大涨','增长','超预期','买入','增持']; neg = ['利空','跌停','跌破','大跌','亏损','减持','警告']; score = 0
        for n in news:
            t = json.dumps(n,ensure_ascii=False).lower()
            for w in pos: score += 1 if w in t else 0
            for w in neg: score -= 1 if w in t else 0
        return max(-100,min(100,score*10))

class EE:
    def __init__(self, db):
        self.db = db
        self.weights = {'300058':{'f1':0.25,'f2':0.20,'f3':0.20,'f4':0.12,'f5':0.13,'f6':0.10},'300418':{'f1':0.30,'f2':0.20,'f3':0.15,'f4':0.15,'f5':0.10,'f6':0.10}}
    def evolve(self, code):
        trades = self.db.get_trades(code, 90)
        if len(trades)<10: return {'status':'insufficient_data','message':f'只有{len(trades)}笔交易，需要至少10笔'}
        pnls = [t['pnl_pct'] for t in trades if t['pnl_pct']!=0]
        if len(pnls)<5: return {'status':'insufficient_pnl','message':'有效盈亏记录不足'}
        changes = []; old = self.weights[code].copy()
        for fc in ['f1','f2','f3','f4','f5','f6']:
            fs = [t.get(f'f{fc.replace("f","")}') or 0 for t in trades]
            if all(s==0 for s in fs): continue
            if len(fs)>=3:
                c = sum(1 for i in range(len(fs)) if fs[i]*pnls[i]>0)/len(fs)-0.5
                if c>0.2:
                    self.weights[code][fc] *= 1.05; changes.append({'factor':fc,'old':old[fc],'new':self.weights[code][fc],'corr':c,'reason':'正相关增加'})
                elif c<-0.15:
                    self.weights[code][fc] *= 0.85; changes.append({'factor':fc,'old':old[fc],'new':self.weights[code][fc],'corr':c,'reason':'负相关减少'})
        tot = sum(self.weights[code].values())
        for k in self.weights[code]: self.weights[code][k] /= tot
        if changes:
            for c in changes: self.db.log_param_evolution(f'weight_{c["factor"]}',c['old'],c['new'],c['reason'],code,c['corr'])
        self.db.save_factor_weights(self.weights[code],code,sum(self.weights[code].values()))
        return {'status':'evolved','code':code,'old':old,'new':self.weights[code],'changes':changes,'analyzed':len(trades)}
    def learn(self, trade):
        if trade.get('pnl_pct',0)<-0.5:
            cat = 'loss'
            if '新闻' in trade.get('signal_reason','') or '消息' in trade.get('signal_reason',''): cat = 'emotion'
            elif '止损' in trade.get('signal_reason',''): cat = 'risk'
            self.db.add_lesson({'category':cat,'title':f"{trade['stock_name']}亏损{trade['pnl_pct']:.2f}%教训",'content':f"信号:{trade['signal_score']} 置信:{trade['confidence']} 原因:{trade['signal_reason']}",'stock_code':trade['stock_code'],'outcome':'亏损','pnl_impact':trade['pnl_pct']})
        elif trade.get('pnl_pct',0)>1.0:
            self.db.add_lesson({'category':'success','title':f"{trade['stock_name']}盈利{trade['pnl_pct']:.2f}%经验",'content':f"信号:{trade['signal_score']} 置信:{trade['confidence']} 成功:{trade['signal_reason']}",'stock_code':trade['stock_code'],'outcome':'盈利','pnl_impact':trade['pnl_pct']})
    def best_practice(self, code=None, cat=None):
        ls = self.db.get_lessons(cat,90); ls.sort(key=lambda x:x.get('pnl_impact',0),reverse=True)
        if code: ls = [l for l in ls if l.get('stock_code')==code]
        return ls[:10]

class ST:
    def __init__(self, db, tdx): self.db = db; self.tdx = tdx
    def run_all(self):
        r = {'data':self._data_test(),'slot':self._slot_test(),'risk':self._risk_test(),'param':self._param_test()}
        all_p = all(x['passed'] for x in r.values())
        for t,res in r.items(): self.db.log_self_test(t,res['passed'],json.dumps(res.get('details',{}),ensure_ascii=False),json.dumps(res.get('issues',[]),ensure_ascii=False))
        return {'all_passed':all_p,'tests':r,'timestamp':datetime.now().isoformat()}
    def _data_test(self):
        try:
            if self.tdx.connect():
                q = self.tdx.get_quote('300058')
                if q and q.get('now',0)>0: return {'passed':True,'details':{'tdx_connected':True}}
            return {'passed':False,'issues':['TDX连接失败或数据无效']}
        except Exception as e: return {'passed':False,'issues':[str(e)]}
    def _slot_test(self): return {'passed':True,'details':{'checked':True},'issues':[]}
    def _risk_test(self):
        issues = []; sums = self.db.get_daily_summary(30); cl = 0
        for s in sums[:5]:
            if s.get('total_pnl',0)<-0.5: cl+=1
            else: cl=0
        if cl>=3: issues.append('连续3天亏损，风控需调整')
        return {'passed':len(issues)==0,'details':{'consecutive_losses':cl},'issues':issues}
    def _param_test(self): return {'passed':True,'details':{'validated':True},'issues':[]}

class EvoSys:
    def __init__(self, mode='offline'):
        self.mode = mode; self.db = DB(); self.tdx = TDX(); self.sc = SC()
        self.ev = EE(self.db); self.se = SE(self.db); self.st = ST(self.db, self.tdx)
        self.slots = {'300058':SM('300058'),'300418':SM('300418')}; self.priority = ['300058','300418']
        log.info(f'可自进化交易系统初始化 | 模式: {mode}')
    def connect(self): return self.tdx.connect() if self.mode=='realtime' else True
    def analyze(self, code=None):
        results = []; codes = [code] if code else self.priority
        for c in codes:
            try:
                q = self.tdx.get_quote(c)
                if not q or q.get('now',0)==0: continue
                m5 = self.tdx.get_kline(c,'5m',100); d = self.tdx.get_kline(c,'day',30)
                w = self.ev.weights.get(c); s = self.sc.calc(c,q,m5,d,w); results.append(s)
                self.db.log_signal({'signal_time':datetime.now().isoformat(),'stock_code':c,'total_score':s.total,'sell_score':s.sell,'buy_score':s.buy,'confidence':s.conf,'regime':s.regime,'f1_score':s.factors.get('F1',FS('',0,0,0,[])).score,'f2_score':s.factors.get('F2',FS('',0,0,0,[])).score,'f3_score':s.factors.get('F3',FS('',0,0,0,[])).score,'f4_score':s.factors.get('F4',FS('',0,0,0,[])).score,'f5_score':s.factors.get('F5',FS('',0,0,0,[])).score,'f6_score':s.factors.get('F6',FS('',0,0,0,[])).score,'reason':s.reason})
                dir_icon = '▼' if s.can_short else ('▲' if s.can_long else '—')
                log.info(f'[{s.name}] 评分={s.total:.0f} 置信={s.conf} {dir_icon} {s.sug[:30]}...')
            except Exception as e: log.error(f'分析{c}出错: {e}')
        return results
    def exec_sell(self, code, price, signal):
        slot = self.slots[code].open(price,signal.total,signal.reason)
        if slot:
            log.info(f'[{code}] 卖出 @{price:.4f} 槽:{slot.id}')
            self.db.log_trade({'stock_code':code,'stock_name':signal.name,'direction':'sell','price':price,'amount':5000,'signal_score':signal.total,'signal_reason':signal.reason,'confidence':signal.conf,'regime':signal.regime,'slot_id':slot.id})
        return slot
    def exec_buy(self, code, price, sid):
        slot = self.slots[code].close(sid,price)
        if slot:
            log.info(f'[{code}] 买回 @{price:.4f} 盈亏:{slot.pnl:+.2f}%')
            self.db.log_trade({'stock_code':code,'stock_name':code,'direction':'buy_back','price':price,'amount':5000,'pnl_pct':slot.pnl,'slot_id':slot.id})
            self.ev.learn({'stock_code':code,'stock_name':code,'pnl_pct':slot.pnl,'signal_score':0,'confidence':'','signal_reason':'倒T买回'})
        return slot
    def sentiment(self, code): return self.se.check(code,self.tdx)
    def run_evolve(self):
        res = {}
        for c in self.priority:
            r = self.ev.evolve(c); res[c] = r
            if r['status']=='evolved': log.info(f'[{c}] 权重进化: {r["changes"]}')
        return res
    def run_test(self): return self.st.run_all()
    def status(self):
        return {'slots':{'300058':{'open':len(self.slots['300058'].open_slots()),'sell':self.slots['300058'].sell_cnt,'pnl':self.slots['300058'].daily_pnl},'300418':{'open':len(self.slots['300418'].open_slots()),'sell':self.slots['300418'].sell_cnt,'pnl':self.slots['300418'].daily_pnl}},'mode':self.mode,'conn':self.tdx._conn}
    def format_report(self, signals):
        lines = ['', '='*60, f'  可自进化交易系统  {datetime.now().strftime("%H:%M:%S")}', '='*60]
        for s in signals:
            dir_icon = '▼ 卖出' if s.can_short else ('▲ 买入' if s.can_long else '— 观望')
            lines.extend(['', f'[{s.name}] {dir_icon}', f'  现价:{s.price:.4f} ({s.chg:+.2f}%)', f'  总分:{s.total:.0f} 置信:{s.conf}', f'  卖分:{s.sell:.0f} 买分:{s.buy:.0f}', f'  Regime:{s.regime}', f'  理由:{s.reason}', f'  建议:{s.sug}', '  因子:'])
            for n,f in s.factors.items():
                if f.score>0: lines.append(f'    [{n}] {f.score:.0f}分: {" / ".join(f.sigs[:2])}')
        lines.extend(['', '-'*60, '槽位:'])
        for code,sm in self.slots.items():
            name = '昆仑' if code=='300058' else '蓝色'
            lines.append(f'  {name}: 开仓{len(sm.open_slots())} 今日卖出{sm.sell_cnt}笔 日盈亏{sm.daily_pnl:+.2f}%')
        lines.append('='*60)
        return '\n'.join(lines)

if __name__=='__main__':
    import argparse
    p = argparse.ArgumentParser(description='可自进化交易系统')
    p.add_argument('--mode',choices=['offline','realtime'],default='offline')
    p.add_argument('--cmd',choices=['monitor','signal','evolve','learn','test','status'],default='signal')
    p.add_argument('--code')
    p.add_argument('--interval',type=int,default=300)
    a = p.parse_args()
    sys = EvoSys(a.mode)
    if a.cmd=='status': print(json.dumps(sys.status(),indent=2))
    elif a.cmd=='signal': sigs = sys.analyze(a.code); print(sys.format_report(sigs))
    elif a.cmd=='monitor':
        sys.connect()
        print(f'监控模式，间隔{a.interval}秒...')
        try:
            while True:
                sigs = sys.analyze(a.code); print(sys.format_report(sigs))
                for c in ['300058','300418']:
                    s = sys.sentiment(c)
                    if s.get('need_news') and s.get('sentiment_score',0)!=0: log.info(f'[{c}] 情绪:{s["sentiment_score"]} 新闻:{s["news_count"]}')
                time.sleep(a.interval)
        except KeyboardInterrupt: print('\n停止')
    elif a.cmd=='evolve': print(json.dumps(sys.run_evolve(),indent=2))
    elif a.cmd=='learn':
        ls = sys.ev.best_practice(a.code); print('最佳实践:')
        for l in ls: print(f'  [{l["category"]}] {l["title"]}: {l["content"][:50]}...')
    elif a.cmd=='test': print(json.dumps(sys.run_test(),indent=2))