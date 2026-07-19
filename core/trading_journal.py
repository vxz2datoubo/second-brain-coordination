#!/usr/bin/env python
"""交易日志引擎 — 只追加模式, 支持事后分析"""
import sqlite3, json, os
from datetime import datetime

DB = 'F:/aidanao/data/logs/trading_journal.db'

class TradingJournal:
    def __init__(self):
        os.makedirs('F:/aidanao/data/logs', exist_ok=True)
        self.conn = sqlite3.connect(DB)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.session_id = None
    
    def start_session(self, session_type='盘中', market_day=None):
        """开新会话"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c = self.conn.execute(
            "INSERT INTO sessions (started_at, session_type, market_day) VALUES (?,?,?)",
            (now, session_type, market_day or datetime.now().strftime('%Y%m%d'))
        )
        self.session_id = c.lastrowid
        self.conn.commit()
        return self.session_id
    
    def end_session(self, summary=''):
        """关闭会话"""
        if not self.session_id: return
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.conn.execute(
            "UPDATE sessions SET ended_at=?, summary=? WHERE id=?",
            (now, summary, self.session_id)
        )
        self.conn.commit()
    
    def log_interaction(self, stock_code, stock_price, question, analysis_type, conclusion, key_data=None, confidence='中'):
        """记录一次问答"""
        if not self.session_id: self.start_session()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c = self.conn.execute(
            """INSERT INTO interactions 
               (session_id, timestamp, stock_code, stock_price, question, analysis_type, conclusion, key_data, confidence)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (self.session_id, now, stock_code, stock_price, question, analysis_type, conclusion,
             json.dumps(key_data, ensure_ascii=False) if key_data else None, confidence)
        )
        self.conn.commit()
        return c.lastrowid
    
    def log_snapshot(self, interaction_id, stock_code, price, volume=None, turnover=None,
                     big_order_net=None, chip_profit=None, chip_cost=None, poc=None,
                     phase=None, lps=None, extra=None):
        """记录数据快照"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.conn.execute(
            """INSERT INTO data_snapshots 
               (interaction_id, timestamp, stock_code, price, volume, turnover,
                big_order_net, chip_profit_rate, chip_avg_cost, poc_price, phase, lps_level, extra_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (interaction_id, now, stock_code, price, volume, turnover,
             big_order_net, chip_profit, chip_cost, poc, phase, lps, json.dumps(extra, ensure_ascii=False) if extra else None)
        )
        self.conn.commit()
    
    def log_signal(self, interaction_id, stock_code, signal_name, direction, confidence=0.5, reason=''):
        """记录交易信号"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.conn.execute(
            """INSERT INTO signals (interaction_id, timestamp, stock_code, signal_name, direction, confidence, reason)
               VALUES (?,?,?,?,?,?,?)""",
            (interaction_id, now, stock_code, signal_name, str(direction), confidence, reason)
        )
        self.conn.commit()
    
    def save_daily_summary(self, stock_code, open_p, high_p, low_p, close_p, volume, turnover,
                           big_order, chip_profit, chip_cost, poc, phase, lps, verdict, events):
        """保存日总结"""
        today = datetime.now().strftime('%Y%m%d')
        self.conn.execute("""INSERT OR REPLACE INTO daily_summary 
            (date, stock_code, open, high, low, close, volume, turnover, big_order_net,
             chip_profit_rate, chip_avg_cost, poc_price, phase, lps_level, wyckoff_verdict, key_events)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (today, stock_code, open_p, high_p, low_p, close_p, volume, turnover, big_order,
             chip_profit, chip_cost, poc, phase, lps, verdict, json.dumps(events, ensure_ascii=False)))
        self.conn.commit()
    
    def query(self, table, conditions=None, limit=20, order='timestamp DESC'):
        """通用查询"""
        sql = f"SELECT * FROM {table}"
        if conditions:
            sql += f" WHERE {conditions}"
        sql += f" ORDER BY {order} LIMIT {limit}"
        return self.conn.execute(sql).fetchall()
    
    def stats(self):
        """统计概览"""
        return {
            'sessions': self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
            'interactions': self.conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0],
            'snapshots': self.conn.execute("SELECT COUNT(*) FROM data_snapshots").fetchone()[0],
            'signals': self.conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0],
            'daily': self.conn.execute("SELECT COUNT(*) FROM daily_summary").fetchone()[0],
        }
    
    def close(self):
        self.conn.close()


# CLI
if __name__ == '__main__':
    j = TradingJournal()
    if len(sys.argv) > 1 and sys.argv[1] == 'stats':
        print(json.dumps(j.stats(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == 'recent':
        for r in j.query('interactions', limit=10):
            print(f"{r[2][:16]} [{r[6]}] {r[4][:50]} → {r[7][:50] if r[7] else ''}")
    j.close()
