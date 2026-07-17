#!/usr/bin/env python3
"""
消息关联分析系统 (Message Correlation Analysis System)

基于现有消息追踪系统扩展:
  - 消息检索: 多源搜索 + 去重 + 定向过滤
  - 日志记录: SQLite 自动记录 + 历史对比
  - 回测分析: 消息↔信号关联检测
  - 分析输出: 相关性强度评估 + 规律总结

设计约束:
  - 与 trading_journal.py 共用数据库
  - 与 alert_engine.py 评分体系兼容
  - 通过 data_pipeline_orchestrator 拉取历史数据
  - MCP 调用由对话层驱动, 本引擎只处理结构化数据

使用:
  python core/message_correlation.py search 300418 --days 7
  python core/message_correlation.py backtest 300418 --start 2026-07-01 --end 2026-07-14
  python core/message_correlation.py analyze 300418
  python core/message_correlation.py report 300418
"""

import json
import sqlite3
import hashlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "message_correlation"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "message_correlation.db"
SCRAPE_CACHE = DATA_DIR / "scrape_cache"
SCRAPE_CACHE.mkdir(exist_ok=True)

# ============================================================
# 一、SQLite 数据库
# ============================================================

class MessageDB:
    """消息关联分析专用数据库"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
        -- 消息主表: 所有检索到的消息
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,                          -- SHA256 hash of (source+url+title) 组成唯一ID
            target_code TEXT NOT NULL,                    -- 关联标的(300418/300058/板块码)
            target_name TEXT,                             -- 标的名称
            title TEXT NOT NULL,                          -- 消息标题
            content TEXT,                                 -- 消息内容摘要
            source TEXT NOT NULL,                         -- 来源: westock/tdx/tushare/websearch/sina
            source_url TEXT,                              -- 原始链接
            published_at TEXT,                            -- 发布时间 ISO8601
            fetched_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            msg_type TEXT DEFAULT 'news',                 -- 类型: news/announcement/report/event/rumor
            sentiment TEXT DEFAULT 'neutral',             -- 情绪: positive/negative/neutral/mixed
            relevance_score REAL DEFAULT 0,               -- 关联度分数 (0-100)
            impact_score REAL DEFAULT 0,                  -- 影响度分数 (0-100)
            keywords TEXT,                                -- 关键词 (逗号分隔)
            correlation_id TEXT,                          -- 关联批次ID
            extra_json TEXT,                              -- 额外JSON
            UNIQUE(id)
        );

        -- 关联分析结果表
        CREATE TABLE IF NOT EXISTS correlations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,                     -- 关联的消息ID
            signal_type TEXT NOT NULL,                    -- 信号类型: price/volume/fund_flow/ddx/vwap/macd/kdj
            signal_direction TEXT,                        -- 信号方向: up/down/neutral
            signal_strength REAL,                         -- 信号强度
            pre_value REAL,                               -- 消息前值
            post_value REAL,                              -- 消息后值
            change_pct REAL,                              -- 变化百分比
            time_window TEXT,                             -- 时间窗口: 5min/30min/1h/1d/3d/5d
            correlation_coef REAL,                        -- 皮尔逊相关系数
            z_score REAL,                                 -- Z-score
            significance TEXT,                            -- 显著性: significant/weak/none
            lag_minutes INTEGER,                          -- 滞后分钟数
            analyzed_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            extra_json TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        );

        -- 规律发现表
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT NOT NULL,                   -- 规律名称
            pattern_desc TEXT,                            -- 规律描述
            message_pattern TEXT,                         -- 消息模式 (JSON)
            signal_pattern TEXT,                          -- 信号模式 (JSON)
            occurrence_count INTEGER DEFAULT 1,           -- 出现次数
            hit_rate REAL DEFAULT 0,                      -- 命中率
            avg_impact REAL DEFAULT 0,                    -- 平均影响
            confidence REAL DEFAULT 0,                    -- 置信度
            first_seen TEXT,                              -- 首次发现
            last_seen TEXT,                               -- 最近一次
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        -- 回测批次表
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_code TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            message_count INTEGER,
            signal_count INTEGER,
            correlation_count INTEGER,
            pattern_count INTEGER,
            summary TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        -- 索引
        CREATE INDEX IF NOT EXISTS idx_messages_target ON messages(target_code, published_at);
        CREATE INDEX IF NOT EXISTS idx_messages_sentiment ON messages(sentiment, relevance_score);
        CREATE INDEX IF NOT EXISTS idx_correlations_message ON correlations(message_id, signal_type);
        CREATE INDEX IF NOT EXISTS idx_correlations_significant ON correlations(significance);
        CREATE INDEX IF NOT EXISTS idx_patterns_hitrate ON patterns(hit_rate DESC);
        """)
        self.conn.commit()

    def insert_message(self, msg: dict) -> bool:
        """插入消息, 自动去重"""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO messages
                (id, target_code, target_name, title, content, source, source_url,
                 published_at, msg_type, sentiment, relevance_score, impact_score,
                 keywords, correlation_id, extra_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                msg['id'], msg['target_code'], msg.get('target_name', ''),
                msg['title'], msg.get('content', ''), msg['source'],
                msg.get('source_url', ''), msg.get('published_at', ''),
                msg.get('msg_type', 'news'), msg.get('sentiment', 'neutral'),
                msg.get('relevance_score', 0), msg.get('impact_score', 0),
                msg.get('keywords', ''), msg.get('correlation_id', ''),
                json.dumps(msg.get('extra', {}), ensure_ascii=False)
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[MessageDB] insert error: {e}")
            return False

    def insert_correlation(self, corr: dict):
        """插入关联分析结果"""
        self.conn.execute("""
            INSERT INTO correlations
            (message_id, signal_type, signal_direction, signal_strength,
             pre_value, post_value, change_pct, time_window,
             correlation_coef, z_score, significance, lag_minutes, extra_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            corr['message_id'], corr['signal_type'],
            corr.get('signal_direction', ''), corr.get('signal_strength', 0),
            corr.get('pre_value', 0), corr.get('post_value', 0),
            corr.get('change_pct', 0), corr.get('time_window', '1d'),
            corr.get('correlation_coef', 0), corr.get('z_score', 0),
            corr.get('significance', 'none'), corr.get('lag_minutes', 0),
            json.dumps(corr.get('extra', {}), ensure_ascii=False)
        ))
        self.conn.commit()

    def insert_pattern(self, pattern: dict):
        """插入/更新规律"""
        existing = self.conn.execute(
            "SELECT id, occurrence_count FROM patterns WHERE pattern_name=?",
            (pattern['pattern_name'],)
        ).fetchone()
        if existing:
            self.conn.execute("""
                UPDATE patterns SET occurrence_count=?, hit_rate=?, avg_impact=?,
                confidence=?, last_seen=?, updated_at=datetime('now','localtime')
                WHERE id=?
            """, (
                existing['occurrence_count'] + 1,
                pattern.get('hit_rate', 0),
                pattern.get('avg_impact', 0),
                pattern.get('confidence', 0),
                pattern.get('last_seen', ''),
                existing['id']
            ))
        else:
            self.conn.execute("""
                INSERT INTO patterns (pattern_name, pattern_desc, message_pattern,
                signal_pattern, occurrence_count, hit_rate, avg_impact, confidence,
                first_seen, last_seen)
                VALUES (?,?,?,?,1,?,?,?,?,?)
            """, (
                pattern['pattern_name'], pattern.get('pattern_desc', ''),
                json.dumps(pattern.get('message_pattern', {}), ensure_ascii=False),
                json.dumps(pattern.get('signal_pattern', {}), ensure_ascii=False),
                pattern.get('hit_rate', 0), pattern.get('avg_impact', 0),
                pattern.get('confidence', 0),
                pattern.get('first_seen', ''), pattern.get('last_seen', '')
            ))
        self.conn.commit()

    def query_messages(self, target_code: str, days: int = 7,
                       sentiment: Optional[str] = None,
                       min_relevance: float = 0) -> list:
        """查询消息"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = "SELECT * FROM messages WHERE target_code=? AND published_at>=?"
        params = [target_code, cutoff]
        if sentiment and sentiment != 'all':
            sql += " AND sentiment=?"
            params.append(sentiment)
        if min_relevance > 0:
            sql += " AND relevance_score>=?"
            params.append(min_relevance)
        sql += " ORDER BY published_at DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def query_correlations(self, message_id: Optional[str] = None,
                           target_code: Optional[str] = None,
                           min_significance: str = 'weak') -> list:
        """查询关联分析"""
        if message_id:
            rows = self.conn.execute(
                "SELECT * FROM correlations WHERE message_id=? AND significance>=?",
                (message_id, min_significance)
            ).fetchall()
        elif target_code:
            rows = self.conn.execute("""
                SELECT c.* FROM correlations c
                JOIN messages m ON c.message_id = m.id
                WHERE m.target_code=? AND c.significance>=?
                ORDER BY c.correlation_coef DESC
            """, (target_code, min_significance)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM correlations WHERE significance>=? ORDER BY correlation_coef DESC",
                (min_significance,)
            ).fetchall()
        return [dict(r) for r in rows]

    def query_patterns(self, min_hit_rate: float = 0.3) -> list:
        """查询规律"""
        rows = self.conn.execute(
            "SELECT * FROM patterns WHERE hit_rate>=? ORDER BY confidence DESC",
            (min_hit_rate,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self, target_code: str) -> dict:
        """统计概览"""
        msgs = self.conn.execute(
            "SELECT COUNT(*) as cnt, AVG(relevance_score) as avg_rel FROM messages WHERE target_code=?",
            (target_code,)
        ).fetchone()
        corrs = self.conn.execute("""
            SELECT COUNT(*) as cnt, AVG(ABS(correlation_coef)) as avg_corr
            FROM correlations c JOIN messages m ON c.message_id=m.id
            WHERE m.target_code=?
        """, (target_code,)).fetchone()
        patterns = self.conn.execute("SELECT COUNT(*) as cnt FROM patterns").fetchone()
        return {
            'message_count': msgs['cnt'] or 0,
            'avg_relevance': round(msgs['avg_rel'] or 0, 1),
            'correlation_count': corrs['cnt'] or 0,
            'avg_correlation': round(corrs['avg_corr'] or 0, 3),
            'pattern_count': patterns['cnt'] or 0
        }

    def close(self):
        self.conn.close()


# ============================================================
# 二、消息检索器 — 多源融合
# ============================================================

def _make_id(source: str, url: str, title: str) -> str:
    """生成消息唯一ID"""
    raw = f"{source}|{url}|{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _timestamp_str(dt=None) -> str:
    return (dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")


# 持仓与板块关键词配置
TARGET_CONFIG = {
    "300418": {
        "name": "昆仑万维",
        "aliases": ["昆仑", "昆仑万维", "天工AI", "Matrix-Game", "SkyReels", "DramaWave", "Mureka"],
        "sector_keywords": ["AI", "大模型", "世界模型", "具身智能", "短剧", "AI应用", "人形机器人", "AGI"],
        "watch_sectors": ["84301", "AI应用", "人工智能"]
    },
    "300058": {
        "name": "蓝色光标",
        "aliases": ["蓝色光标", "蓝标", "BlueFocus", "BlueAI"],
        "sector_keywords": ["AI营销", "数字营销", "出海", "广告", "TikTok"],
        "watch_sectors": ["广告营销", "AI应用", "数字媒体"]
    }
}

# 消息情绪关键词
SENTIMENT_KW = {
    'positive': ['突破', '超预期', '增长', '利好', '大涨', '创新高', '登顶', '领先', '第一', '首发', '里程碑', '盈利', '净买入'],
    'negative': ['暴跌', '亏损', '下滑', '减持', '监管', '处罚', '诉讼', '退市', '暴雷', '违约', '净卖出', '破发'],
}

def _detect_sentiment(title: str, content: str = "") -> str:
    """检测消息情绪"""
    text = f"{title} {content}".lower()
    pos = sum(1 for kw in SENTIMENT_KW['positive'] if kw.lower() in text)
    neg = sum(1 for kw in SENTIMENT_KW['negative'] if kw.lower() in text)
    if pos > neg + 1:
        return 'positive'
    elif neg > pos + 1:
        return 'negative'
    elif pos > 0 and neg > 0:
        return 'mixed'
    return 'neutral'


def _calc_relevance(title: str, target: dict) -> tuple:
    """计算消息与目标标的的关联度"""
    score = 0
    matched = []
    text = title.lower()
    # 直接名称匹配
    for alias in target['aliases']:
        if alias.lower() in text:
            score += 30
            matched.append(alias)
            break
    # 板块关键词匹配
    for kw in target['sector_keywords']:
        if kw.lower() in text:
            score += 10
            matched.append(kw)
    # 股票代码匹配
    code_clean = target.get('code', '')
    if code_clean in title:
        score += 50
        matched.append(code_clean)
    return min(score, 100), ','.join(matched)


def search_messages(db: MessageDB, target_code: str,
                    messages_raw: list,  # 外部传入的原始消息列表
                    source: str = "manual",
                    correlation_id: str = "") -> int:
    """批量检索并入库消息

    Args:
        db: MessageDB 实例
        target_code: 目标标的代码
        messages_raw: 原始消息列表，每条包含: {title, content?, url?, published_at?, source?}
        source: 数据源标签
        correlation_id: 关联批次ID
    Returns:
        入库消息数
    """
    target = TARGET_CONFIG.get(target_code, {"name": target_code, "aliases": [target_code], "sector_keywords": []})
    count = 0

    for raw in messages_raw:
        title = raw.get('title', '')
        content = raw.get('content', '')
        url = raw.get('url', raw.get('source_url', ''))
        published = raw.get('published_at', raw.get('time', _timestamp_str()))
        msg_source = raw.get('source', source)

        # 关联度计算
        relevance, keywords = _calc_relevance(title, target)

        # 跳过完全不相关的消息 (至少命中1个关键词)
        if relevance < 10:
            continue

        # 情绪检测
        sentiment = _detect_sentiment(title, content)

        msg = {
            'id': _make_id(msg_source, url, title),
            'target_code': target_code,
            'target_name': target.get('name', target_code),
            'title': title,
            'content': content[:2000] if content else '',
            'source': msg_source,
            'source_url': url,
            'published_at': published,
            'msg_type': raw.get('type', 'news'),
            'sentiment': sentiment,
            'relevance_score': relevance,
            'impact_score': raw.get('impact_score', 0),
            'keywords': keywords,
            'correlation_id': correlation_id,
            'extra': raw.get('extra', {})
        }
        if db.insert_message(msg):
            count += 1
    return count


# ============================================================
# 三、回测分析器
# ============================================================

def backtest_correlation(db: MessageDB, target_code: str,
                         start_date: str, end_date: str,
                         price_data: list = None,
                         fund_flow_data: list = None,
                         signal_data: list = None) -> dict:
    """回测消息与信号的关联

    Args:
        db: 数据库实例
        target_code: 目标标的
        start_date, end_date: 日期范围
        price_data: [{date, open, high, low, close, volume}]
        fund_flow_data: [{date, main_net_flow, jumbo_net_flow, block_net_flow}]
        signal_data: [{timestamp, signal_name, direction, confidence}]

    Returns:
        回测结果 dict
    """
    # 1. 获取消息
    messages = db.conn.execute("""
        SELECT * FROM messages
        WHERE target_code=? AND published_at BETWEEN ? AND ?
        ORDER BY published_at
    """, (target_code, f"{start_date} 00:00:00", f"{end_date} 23:59:59")).fetchall()
    messages = [dict(m) for m in messages]

    if not messages:
        return {'error': f'No messages found for {target_code} in {start_date}~{end_date}'}

    # 2. 准备价格数据索引
    price_idx = {}
    if price_data:
        for p in price_data:
            price_idx[p.get('date', '')[:10]] = p

    # 3. 逐消息分析关联
    correlations = []
    sig_map = {'significant': 0, 'weak': 0, 'none': 0}

    for msg in messages:
        msg_date = (msg['published_at'] or '')[:10]
        sentiment = msg['sentiment']

        # --- 价格关联 ---
        if price_idx and msg_date in price_idx:
            p = price_idx[msg_date]
            # 查找消息日前后3天的价格变化
            pre_dates = [d for d in sorted(price_idx.keys()) if d < msg_date]
            post_dates = [d for d in sorted(price_idx.keys()) if d > msg_date]

            if pre_dates and post_dates:
                pre_close = price_idx[pre_dates[-1]]['close']
                post_close_1d = price_idx[post_dates[0]]['close']
                post_close_3d = price_idx[post_dates[min(2, len(post_dates)-1)]]['close']
                post_close_5d = price_idx[post_dates[min(4, len(post_dates)-1)]]['close']

                for label, post_val in [('1d', post_close_1d), ('3d', post_close_3d), ('5d', post_close_5d)]:
                    chg = (post_val - pre_close) / pre_close * 100
                    # 判断方向一致性
                    if sentiment == 'positive' and chg > 0:
                        sig = 'significant' if chg > 2 else 'weak'
                    elif sentiment == 'negative' and chg < 0:
                        sig = 'significant' if abs(chg) > 2 else 'weak'
                    elif sentiment == 'positive' and chg < 0:
                        sig = 'weak'  # 背离
                    else:
                        sig = 'none'

                    corr = {
                        'message_id': msg['id'],
                        'signal_type': 'price',
                        'signal_direction': 'up' if chg > 0 else 'down',
                        'signal_strength': abs(chg),
                        'pre_value': pre_close,
                        'post_value': post_val,
                        'change_pct': round(chg, 2),
                        'time_window': label,
                        'correlation_coef': round(chg / 10, 3) if sentiment != 'neutral' else 0,  # 简化
                        'z_score': round(chg / 5, 3) if abs(chg) < 25 else 3,
                        'significance': sig,
                        'lag_minutes': 0
                    }
                    db.insert_correlation(corr)
                    correlations.append(corr)
                    sig_map[sig] += 1

        # --- 资金流关联 ---
        if fund_flow_data:
            ff_idx = {}
            for f in fund_flow_data:
                ff_idx[f.get('date', '')[:10]] = f
            if msg_date in ff_idx:
                ff = ff_idx[msg_date]
                mnf = ff.get('main_net_flow', 0) or 0
                # 主力净流与消息情绪的一致性
                if sentiment == 'positive' and mnf > 1e8:
                    sig = 'significant'
                elif sentiment == 'negative' and mnf < -1e8:
                    sig = 'significant'
                elif sentiment == 'positive' and mnf > 0:
                    sig = 'weak'
                else:
                    sig = 'none'

                corr = {
                    'message_id': msg['id'],
                    'signal_type': 'fund_flow',
                    'signal_direction': 'up' if mnf > 0 else 'down',
                    'signal_strength': abs(mnf) / 1e8,
                    'pre_value': 0,
                    'post_value': mnf,
                    'change_pct': round(mnf / 1e8, 2),
                    'time_window': '1d',
                    'correlation_coef': round(mnf / 1e10, 4),
                    'z_score': round(abs(mnf) / 5e8, 3),
                    'significance': sig,
                    'lag_minutes': 0
                }
                db.insert_correlation(corr)
                correlations.append(corr)
                sig_map[sig] += 1

    # 4. 发现规律
    patterns = _discover_patterns(db, messages, correlations)
    for p in patterns:
        db.insert_pattern(p)

    # 5. 记录回测批次
    db.conn.execute("""
        INSERT INTO backtest_runs (target_code, start_date, end_date,
        message_count, signal_count, correlation_count, pattern_count, summary)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        target_code, start_date, end_date,
        len(messages), len(price_data or []),
        len(correlations), len(patterns),
        json.dumps(sig_map, ensure_ascii=False)
    ))
    db.conn.commit()

    return {
        'target': target_code,
        'date_range': f"{start_date} ~ {end_date}",
        'messages_analyzed': len(messages),
        'correlations_found': len(correlations),
        'significance_distribution': sig_map,
        'patterns_discovered': len(patterns),
        'patterns': patterns
    }


def _discover_patterns(db: MessageDB, messages: list, correlations: list) -> list:
    """自动发现消息-信号关联规律"""
    patterns = []

    # 规律1: 消息情绪 vs 次日价格方向
    sentiment_price = {'positive': {'up': 0, 'down': 0}, 'negative': {'up': 0, 'down': 0}}
    for c in correlations:
        if c.get('signal_type') == 'price' and c.get('time_window') == '1d':
            msg_sent = ''
            for m in messages:
                if m['id'] == c['message_id']:
                    msg_sent = m['sentiment']
                    break
            if msg_sent in sentiment_price:
                sentiment_price[msg_sent][c.get('signal_direction', 'down')] += 1

    for sent, dirs in sentiment_price.items():
        total = dirs['up'] + dirs['down']
        if total >= 3:
            hrate = dirs['up'] / total if sent == 'positive' else dirs['down'] / total
            if hrate >= 0.6:
                patterns.append({
                    'pattern_name': f'{sent}_消息→1日价格',
                    'pattern_desc': f'{sent}消息发布后1个交易日价格同向变动命中率{hrate:.0%}',
                    'message_pattern': {'sentiment': sent},
                    'signal_pattern': {'type': 'price', 'window': '1d'},
                    'hit_rate': round(hrate, 3),
                    'avg_impact': 0,
                    'confidence': round(hrate * 0.8, 3),
                    'first_seen': _timestamp_str(),
                    'last_seen': _timestamp_str(),
                })

    # 规律2: 利好消息+主力净流入→价格推动
    pos_msgs = [m for m in messages if m['sentiment'] == 'positive']
    pos_corrs = [c for c in correlations
                 if c.get('signal_type') == 'fund_flow' and c.get('significance') in ('significant', 'weak')]
    if len(pos_msgs) >= 2 and len(pos_corrs) >= 2:
        sig_count = sum(1 for c in pos_corrs if c['significance'] == 'significant')
        patterns.append({
            'pattern_name': '利好+主力净流入共振',
            'pattern_desc': f'利好消息出现时，{sig_count}/{len(pos_corrs)}次伴随主力净流入',
            'message_pattern': {'sentiment': 'positive'},
            'signal_pattern': {'type': 'fund_flow', 'direction': 'positive'},
            'hit_rate': round(sig_count / max(len(pos_corrs), 1), 3),
            'avg_impact': 0,
            'confidence': round(sig_count / max(len(pos_corrs), 1) * 0.9, 3),
            'first_seen': _timestamp_str(),
            'last_seen': _timestamp_str(),
        })

    # 规律3: 重大新闻日成交量异常
    high_impact = [m for m in messages if m.get('relevance_score', 0) > 80]
    vol_corrs = [c for c in correlations if c.get('signal_type') == 'price' and c.get('time_window') == '1d']
    if len(high_impact) >= 2:
        strong_moves = sum(1 for c in vol_corrs if abs(c.get('change_pct', 0)) > 3)
        patterns.append({
            'pattern_name': '高关联消息→价格波动放大',
            'pattern_desc': f'关联度>80的消息日，{strong_moves}/{len(vol_corrs)}次出现>3%的价格变动',
            'message_pattern': {'relevance_score': '>80'},
            'signal_pattern': {'type': 'price', 'volatility': '>3%'},
            'hit_rate': round(strong_moves / max(len(vol_corrs), 1), 3),
            'avg_impact': 0,
            'confidence': round(strong_moves / max(len(vol_corrs), 1) * 0.7, 3),
            'first_seen': _timestamp_str(),
            'last_seen': _timestamp_str(),
        })

    return patterns


# ============================================================
# 四、分析输出
# ============================================================

def generate_report(db: MessageDB, target_code: str) -> dict:
    """生成完整关联分析报告"""
    stats = db.get_stats(target_code)
    messages = db.query_messages(target_code, days=30)
    correlations = db.query_correlations(target_code=target_code, min_significance='weak')
    patterns = db.query_patterns()

    # 消息来源分布
    source_dist = {}
    for m in messages:
        src = m['source']
        source_dist[src] = source_dist.get(src, 0) + 1

    # 情绪分布
    sent_dist = {}
    for m in messages:
        s = m['sentiment']
        sent_dist[s] = sent_dist.get(s, 0) + 1

    # 关联强度排名
    top_corrs = sorted(
        [c for c in correlations if abs(c.get('correlation_coef', 0)) > 0],
        key=lambda x: abs(x.get('correlation_coef', 0)), reverse=True
    )[:10]

    # 信号类型分布
    signal_types = {}
    for c in correlations:
        st = c['signal_type']
        signal_types[st] = signal_types.get(st, 0) + 1

    return {
        'target': target_code,
        'target_name': TARGET_CONFIG.get(target_code, {}).get('name', target_code),
        'stats': stats,
        'message_count': len(messages),
        'source_distribution': source_dist,
        'sentiment_distribution': sent_dist,
        'correlation_count': len(correlations),
        'signal_type_distribution': signal_types,
        'top_correlations': top_corrs,
        'patterns': patterns,
        'generated_at': _timestamp_str()
    }


def print_report(report: dict):
    """格式化打印报告"""
    print(f"\n{'='*70}")
    print(f"  消息关联分析报告: {report['target_name']} ({report['target']})")
    print(f"  生成时间: {report['generated_at']}")
    print(f"{'='*70}")

    print(f"\n📊 概览")
    print(f"  消息总量: {report['stats']['message_count']} 条")
    print(f"  平均关联度: {report['stats']['avg_relevance']}")
    print(f"  关联分析: {report['stats']['correlation_count']} 项")
    print(f"  发现规律: {report['stats']['pattern_count']} 条")

    print(f"\n📰 消息来源分布")
    for src, cnt in sorted(report['source_distribution'].items(), key=lambda x: -x[1]):
        bar = '█' * min(cnt, 40)
        print(f"  {src:<15} {cnt:>4} {bar}")

    print(f"\n😊 情绪分布")
    for s, cnt in sorted(report['sentiment_distribution'].items(), key=lambda x: -x[1]):
        emoji = {'positive': '🟢', 'negative': '🔴', 'neutral': '⚪', 'mixed': '🟡'}.get(s, '❓')
        print(f"  {emoji} {s:<10} {cnt:>4}")

    print(f"\n📈 信号关联分布")
    for st, cnt in sorted(report['signal_type_distribution'].items(), key=lambda x: -x[1]):
        print(f"  {st:<15} {cnt:>4}")

    if report['top_correlations']:
        print(f"\n🔗 最强关联 Top{len(report['top_correlations'])}")
        for i, c in enumerate(report['top_correlations'], 1):
            print(f"  {i}. [{c['signal_type']}/{c['time_window']}] "
                  f"coef={c['correlation_coef']:.3f} "
                  f"chg={c.get('change_pct',0):+.1f}% "
                  f"sig={c['significance']}")

    if report['patterns']:
        print(f"\n💡 发现的规律")
        for i, p in enumerate(report['patterns'], 1):
            conf_bar = '█' * int(p['confidence'] * 10)
            print(f"  {i}. {p['pattern_name']}")
            print(f"     {p['pattern_desc']}")
            print(f"     命中率:{p['hit_rate']:.0%} 置信度:{p['confidence']:.2f} {conf_bar}")


# ============================================================
# 五、CLI 入口
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python core/message_correlation.py search <code>            检索消息(从stdin读JSON)")
        print("  python core/message_correlation.py backtest <code> --start YYYY-MM-DD --end YYYY-MM-DD  回测分析")
        print("  python core/message_correlation.py eventstudy <code> <date>          事件研究CAR")
        print("  python core/message_correlation.py leakdetect <code> <date>         泄露检测")
        print("  python core/message_correlation.py analyze <code>                  生成报告JSON")
        print("  python core/message_correlation.py report <code>                   打印报告")
        print("  python core/message_correlation.py stats <code>                    统计概览")
        return

    cmd = sys.argv[1]
    db = MessageDB()

    try:
        if cmd == 'search':
            # 消息检索: 从 stdin 读取 JSON 或从文件读取
            target = sys.argv[2] if len(sys.argv) > 2 else '300418'
            source = "cli"
            cid = f"manual-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # 尝试从 stdin 读取 JSON
            if not sys.stdin.isatty():
                raw = json.load(sys.stdin)
            else:
                print("请通过管道传入消息 JSON (stdin)")
                return

            count = search_messages(db, target, raw if isinstance(raw, list) else [raw],
                                    source=source, correlation_id=cid)
            print(f"✅ 入库 {count} 条消息 (target={target})")

        elif cmd == 'backtest':
            target = sys.argv[2] if len(sys.argv) > 2 else '300418'
            start = "2026-07-01"
            end = "2026-07-14"
            # 解析参数
            for i, arg in enumerate(sys.argv):
                if arg == '--start' and i+1 < len(sys.argv):
                    start = sys.argv[i+1]
                if arg == '--end' and i+1 < len(sys.argv):
                    end = sys.argv[i+1]

            # 尝试加载现有价格/资金流数据
            price_data = _try_load_price_data(target, start, end)
            fund_flow_data = _try_load_fund_flow_data(target, start, end)

            result = backtest_correlation(db, target, start, end,
                                          price_data=price_data,
                                          fund_flow_data=fund_flow_data)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == 'analyze':
            target = sys.argv[2] if len(sys.argv) > 2 else '300418'
            report = generate_report(db, target)
            out_file = DATA_DIR / f"correlation_report_{target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"✅ 报告已保存: {out_file}")

        elif cmd == 'report':
            target = sys.argv[2] if len(sys.argv) > 2 else '300418'
            report = generate_report(db, target)
            print_report(report)

        elif cmd == 'stats':
            target = sys.argv[2] if len(sys.argv) > 2 else '300418'
            stats = db.get_stats(target)
            print(json.dumps(stats, ensure_ascii=False, indent=2))

        else:
            print(f"未知命令: {cmd}")

    finally:
        db.close()


# ============================================================
# 五+ 事件研究法 (Event Study) — 学术级CAR计算
# ============================================================

def event_study_car(price_series: list, event_idx: int,
                    market_returns: list = None,
                    est_window: int = 120,
                    event_windows: list = None) -> dict:
    """事件研究法计算CAR (Cumulative Abnormal Return)

    基于市场模型: E(Rᵢ,ₜ) = αᵢ + βᵢ × Rₘ,ₜ
    源: Huang et al. 2019 (RFS), 中金 2025

    Args:
        price_series: [{date, close}] 按日期排序
        event_idx: 事件日在 price_series 中的索引
        market_returns: [{date, return_pct}] 市场收益(沪深300), 可选
        est_window: 估计窗口长度(默认120)
        event_windows: 事件窗口列表 [(start, end, label), ...]
                       默认: [(-1,1,'即时'), (1,5,'短期'), (1,10,'中期'), (1,30,'长期')]

    Returns:
        {car_by_window, ar_series, t_stats, significance}
    """
    if event_windows is None:
        event_windows = [(-1, 1, '即时[-1,+1]'), (0, 2, '即时[0,+2]'),
                         (1, 5, '短期[+1,+5]'), (1, 10, '中期[+1,+10]'),
                         (1, 30, '长期[+1,+30]')]

    closes = [p['close'] for p in price_series]
    stock_returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes))]

    est_start = max(0, event_idx - est_window)
    est_end = event_idx - 20  # 排除事件日前后各20天干扰
    if est_end <= est_start:
        est_end = event_idx - 2

    # 计算市场β (如果提供了市场收益)
    beta = 1.0
    alpha = 0.0
    if market_returns and len(market_returns) >= est_end:
        mr = [market_returns[i]['return_pct'] for i in range(est_start, est_end) if i < len(market_returns)]
        sr = stock_returns[est_start:min(est_end, len(stock_returns))]
        if len(mr) > 10 and len(sr) > 10:
            n = min(len(mr), len(sr))
            mr_mean = sum(mr[:n]) / n
            sr_mean = sum(sr[:n]) / n
            cov = sum((mr[i] - mr_mean) * (sr[i] - sr_mean) for i in range(n)) / n
            var_m = sum((m - mr_mean)**2 for m in mr[:n]) / n
            beta = cov / var_m if var_m > 0 else 1.0
            alpha = sr_mean - beta * mr_mean

    # 计算异常收益 (AR)
    ar_series = []
    for i in range(len(stock_returns)):
        expected = alpha + beta * (market_returns[i]['return_pct'] if market_returns and i < len(market_returns) else 0)
        ar = stock_returns[i] - expected
        ar_series.append({'date': price_series[i+1]['date'], 'ar': round(ar, 4)})

    # 计算CAR
    car_results = {}
    for ws, we, label in event_windows:
        s = max(0, event_idx + ws)
        e = min(len(ar_series) - 1, event_idx + we)
        car = sum(ar_series[i]['ar'] for i in range(s, e+1))
        n = e - s + 1
        # t-检验
        if n > 0:
            se = (sum((ar_series[i]['ar'] - car/n)**2 for i in range(s, e+1)) / n) ** 0.5
            t_stat = (car / n) / se * (n ** 0.5) if se > 0 else 0
            sig = 'significant' if abs(t_stat) > 1.96 else ('weak' if abs(t_stat) > 1.0 else 'none')
        else:
            t_stat = 0
            sig = 'none'

        car_results[label] = {
            'car': round(car, 4),
            'n_days': n,
            't_stat': round(t_stat, 3),
            'significance': sig
        }

    return {
        'car': car_results,
        'ar': ar_series[event_idx-5:event_idx+15] if len(ar_series) > event_idx+15 else ar_series,
        'alpha': round(alpha, 4),
        'beta': round(beta, 4)
    }


def leak_detection(target_code: str, first_news_date: str,
                   fund_flow_data: list = None, price_data: list = None) -> dict:
    """泄露/内幕检测 — 资金是否在消息前就动了

    Args:
        target_code: 标的代码
        first_news_date: First News 发布日
        fund_flow_data: [{date, main_net_flow, ...}] 包含消息日前N天的数据
        price_data: [{date, close}] 包含消息日前N天的数据

    Returns:
        {leak_level, evidence, pre_event_car}
    """
    from datetime import datetime, timedelta
    t0 = datetime.strptime(first_news_date[:10], "%Y-%m-%d")

    evidence = []
    leak_score = 0

    # 1. 资金流前置检测
    if fund_flow_data:
        ff_idx = {}
        for f in fund_flow_data:
            ff_idx[f.get('date', '')[:10]] = f

        pre_flows = []
        for d in range(1, 6):
            check_date = (t0 - timedelta(days=d)).strftime("%Y-%m-%d")
            if check_date in ff_idx:
                ff = ff_idx[check_date]
                mnf = ff.get('main_net_flow', 0) or 0
                pre_flows.append({'date': check_date, 'main_net_flow': mnf})

        if pre_flows:
            avg_flow = sum(abs(f['main_net_flow']) for f in pre_flows) / len(pre_flows)
            for f in pre_flows:
                deviation = abs(f['main_net_flow']) / avg_flow if avg_flow > 0 else 0
                if deviation > 2.0:
                    evidence.append(f"🔴 {f['date']}: 主力净流{abs(f['main_net_flow'])/1e8:.1f}亿, 偏离均值{deviation:.1f}倍")
                    leak_score += 30
                elif deviation > 1.5:
                    evidence.append(f"🟠 {f['date']}: 主力净流偏离{deviation:.1f}倍")
                    leak_score += 15
                elif deviation > 1.2:
                    evidence.append(f"🟡 {f['date']}: 轻微异常")
                    leak_score += 5

    # 2. 价格前置检测
    pre_car = 0
    if price_data:
        price_idx = {p.get('date', '')[:10]: p for p in price_data}
        pre_dates = sorted([d for d in price_idx.keys() if d < first_news_date[:10]])
        if len(pre_dates) >= 5:
            pre_5 = pre_dates[-5]
            pre_close_5 = price_idx[pre_5].get('close', 0)
            if pre_dates and pre_dates[-1] != first_news_date[:10]:
                pre_close_1 = price_idx[pre_dates[-1]].get('close', 0)
            else:
                pre_close_1 = pre_close_5
            if pre_close_5 > 0:
                pre_car = (pre_close_1 - pre_close_5) / pre_close_5 * 100
                if abs(pre_car) > 3:
                    evidence.append(f"🔴 T₀前5日CAR={pre_car:+.2f}%, 疑似提前反应")
                    leak_score += 25
                elif abs(pre_car) > 1.5:
                    evidence.append(f"🟡 T₀前5日CAR={pre_car:+.2f}%")
                    leak_score += 10

    # 3. 判定泄露等级
    if leak_score >= 40:
        leak_level = '🔴 确认泄露'
    elif leak_score >= 20:
        leak_level = '🟠 强疑似'
    elif leak_score >= 10:
        leak_level = '🟡 弱疑似'
    else:
        leak_level = '🟢 无泄露'

    return {
        'leak_level': leak_level,
        'leak_score': leak_score,
        'evidence': evidence,
        'pre_event_car_pct': round(pre_car, 2),
        'days_checked': 5
    }


def _try_load_price_data(target_code: str, start: str, end: str) -> list:
    """尝试从数据管道加载价格数据"""
    try:
        pipe_path = ROOT / "core" / "data_pipeline_orchestrator.py"
        if not pipe_path.exists():
            return []
        # 简化: 读取 WeStock 快照 (如果存在)
        snap = ROOT / "data" / "unified" / "snapshots" / "kline" / f"{target_code}_daily.json"
        if snap.exists():
            with open(snap) as f:
                data = json.load(f)
            return [d for d in data if d.get('date', '')[:10] >= start and d.get('date', '')[:10] <= end]
    except Exception:
        pass
    return []


def _try_load_fund_flow_data(target_code: str, start: str, end: str) -> list:
    """尝试加载资金流数据"""
    try:
        ff = ROOT / "data" / "raw" / "tushare" / f"moneyflow_{target_code}.json"
        if ff.exists():
            with open(ff) as f:
                data = json.load(f)
            return [d for d in data if d.get('date', '')[:10] >= start and d.get('date', '')[:10] <= end]
    except Exception:
        pass
    return []


if __name__ == '__main__':
    main()
