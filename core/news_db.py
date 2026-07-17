#!/usr/bin/env python3
"""
本地新闻数据库与新闻因子引擎 (Local News Database & Factor Engine)

四层知识整合:
  L0: 本地存储 / 回测支持 / 归因分析 / 消息面权重
  L1: 采集来源 / 存储结构 / 标签体系 / 时间轴对齐 / 行情关联
  L2: 情感分析框架 / 事件驱动策略 / NLP文本处理
  L3: 新闻因子构建 / 舆情量化 / IC验证 / 学术校准

学术基础:
  [1] 华泰证券 "舆情因子和BERT情感分类模型" — 因子构建方法: 线性衰减加权和
  [2] 方正金工 "热点漂移因子" — 周度IC=3.7%, ICIR=5.53
  [3] 中金公司 "另类数据策略(2)" — 新闻动量因子 ICIR=0.49
  [4] 百度NLP量化白皮书 — 新闻情绪对次日波动解释力35%
  [5] Arxiv 2508.07408 (2025) — LLM事件标签→Sharpe -0.38 for rumor factors
  [6] CICC事件驱动十问十答 (2025) — 48类A股事件CAR规律

用法:
  python core/news_db.py ingest --source westock --code 300418
  python core/news_db.py factor 300418 --days 30
  python core/news_db.py validate 300418 --factor sentiment
  python core/news_db.py report 300418
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
DATA_DIR = ROOT / "data" / "news_db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "news_archive.db"
FACTOR_CACHE = DATA_DIR / "factor_cache"
FACTOR_CACHE.mkdir(exist_ok=True)

# ============================================================
# 一、本地新闻数据库 (SQLite)
# ============================================================

class NewsDatabase:
    """本地新闻归档数据库

    数据表:
      news_articles — 新闻主表
      news_tags — 标签映射表
      news_entities — 实体-新闻关联表
      news_events — 事件分类表
      news_factors — 因子快照表
      news_feedback — 回测反馈表
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA cache_size=-64000")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
        -- 新闻主表
        CREATE TABLE IF NOT EXISTS news_articles (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_url TEXT,
            title TEXT NOT NULL,
            content TEXT,
            summary TEXT,
            published_at TEXT NOT NULL,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            language TEXT DEFAULT 'zh',
            word_count INTEGER,
            raw_json TEXT,
            UNIQUE(id)
        );

        -- 实体-新闻关联
        CREATE TABLE IF NOT EXISTS news_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_code TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            relevance REAL DEFAULT 1.0,
            mention_count INTEGER DEFAULT 1,
            is_primary INTEGER DEFAULT 0,
            FOREIGN KEY (news_id) REFERENCES news_articles(id)
        );

        -- 事件分类
        CREATE TABLE IF NOT EXISTS news_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id TEXT NOT NULL,
            event_category TEXT NOT NULL,
            event_subcategory TEXT,
            sentiment TEXT NOT NULL DEFAULT 'neutral',
            sentiment_score REAL DEFAULT 0,
            impact_level TEXT DEFAULT 'low',
            confidence REAL DEFAULT 0.5,
            event_keywords TEXT,
            FOREIGN KEY (news_id) REFERENCES news_articles(id)
        );

        -- 标签映射
        CREATE TABLE IF NOT EXISTS news_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            tag_type TEXT DEFAULT 'keyword',
            weight REAL DEFAULT 1.0,
            FOREIGN KEY (news_id) REFERENCES news_articles(id)
        );

        -- 因子快照
        CREATE TABLE IF NOT EXISTS news_factors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_code TEXT NOT NULL,
            factor_date TEXT NOT NULL,
            factor_name TEXT NOT NULL,
            factor_value REAL,
            n_articles INTEGER DEFAULT 0,
            n_positive INTEGER DEFAULT 0,
            n_negative INTEGER DEFAULT 0,
            n_neutral INTEGER DEFAULT 0,
            sentiment_weighted REAL DEFAULT 0,
            sentiment_decay REAL DEFAULT 0,
            impact_weighted REAL DEFAULT 0,
            extra_json TEXT,
            UNIQUE(entity_code, factor_date, factor_name)
        );

        -- 回测反馈
        CREATE TABLE IF NOT EXISTS news_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_code TEXT NOT NULL,
            factor_date TEXT NOT NULL,
            forward_period TEXT NOT NULL,
            forward_return REAL,
            factor_value REAL,
            hit INTEGER DEFAULT 0,
            extra_json TEXT,
            FOREIGN KEY (factor_date) REFERENCES news_factors(factor_date)
        );

        -- 索引
        CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);
        CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source);
        CREATE INDEX IF NOT EXISTS idx_entities_code ON news_entities(entity_code);
        CREATE INDEX IF NOT EXISTS idx_entities_news ON news_entities(news_id);
        CREATE INDEX IF NOT EXISTS idx_events_news ON news_events(news_id);
        CREATE INDEX IF NOT EXISTS idx_events_category ON news_events(event_category);
        CREATE INDEX IF NOT EXISTS idx_events_sentiment ON news_events(sentiment);
        CREATE INDEX IF NOT EXISTS idx_factors_entity ON news_factors(entity_code, factor_date);
        CREATE INDEX IF NOT EXISTS idx_feedback_code ON news_feedback(entity_code, factor_date);
        """)
        self.conn.commit()

    def insert_article(self, article: dict, entities: list = None,
                       events: list = None, tags: list = None) -> bool:
        """插入新闻文章+关联实体+事件+标签"""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO news_articles
                (id, source, source_url, title, content, summary,
                 published_at, language, word_count, raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                article['id'], article['source'], article.get('source_url', ''),
                article['title'], article.get('content', ''), article.get('summary', ''),
                article.get('published_at', ''), article.get('language', 'zh'),
                article.get('word_count', len(article.get('content', ''))),
                json.dumps(article.get('raw', {}), ensure_ascii=False)
            ))

            # 插入实体关联
            for ent in (entities or []):
                self.conn.execute("""
                    INSERT OR IGNORE INTO news_entities
                    (news_id, entity_type, entity_code, entity_name, relevance, is_primary)
                    VALUES (?,?,?,?,?,?)
                """, (article['id'], ent.get('type', 'stock'), ent.get('code', ''),
                      ent.get('name', ''), ent.get('relevance', 1.0),
                      ent.get('is_primary', 0)))

            # 插入事件分类
            for evt in (events or []):
                self.conn.execute("""
                    INSERT INTO news_events
                    (news_id, event_category, event_subcategory, sentiment,
                     sentiment_score, impact_level, confidence, event_keywords)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (article['id'], evt.get('category', 'general'),
                      evt.get('subcategory', ''), evt.get('sentiment', 'neutral'),
                      evt.get('sentiment_score', 0), evt.get('impact', 'low'),
                      evt.get('confidence', 0.5), evt.get('keywords', '')))

            # 插入标签
            for tag in (tags or []):
                if isinstance(tag, str):
                    self.conn.execute("""
                        INSERT INTO news_tags (news_id, tag, tag_type) VALUES (?,?,'keyword')
                    """, (article['id'], tag))
                else:
                    self.conn.execute("""
                        INSERT INTO news_tags (news_id, tag, tag_type, weight)
                        VALUES (?,?,?,?)
                    """, (article['id'], tag['tag'], tag.get('type', 'keyword'),
                          tag.get('weight', 1.0)))

            self.conn.commit()
            return True
        except Exception as e:
            print(f"[NewsDB] insert error: {e}")
            return False

    def query_by_entity(self, entity_code: str, days: int = 30,
                        sentiment: str = None, event_category: str = None) -> list:
        """按实体查询新闻"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = """
            SELECT DISTINCT n.* FROM news_articles n
            JOIN news_entities e ON n.id = e.news_id
            WHERE e.entity_code = ? AND n.published_at >= ?
        """
        params = [entity_code, cutoff]
        if sentiment:
            sql += """ AND n.id IN (SELECT news_id FROM news_events WHERE sentiment=?)"""
            params.append(sentiment)
        if event_category:
            sql += """ AND n.id IN (SELECT news_id FROM news_events WHERE event_category=?)"""
            params.append(event_category)
        sql += " ORDER BY n.published_at DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def query_by_date_range(self, start: str, end: str,
                            entity_code: str = None) -> list:
        """按日期范围查询"""
        sql = "SELECT * FROM news_articles WHERE published_at BETWEEN ? AND ?"
        params = [f"{start} 00:00:00", f"{end} 23:59:59"]
        if entity_code:
            sql = """
                SELECT DISTINCT n.* FROM news_articles n
                JOIN news_entities e ON n.id = e.news_id
                WHERE e.entity_code = ? AND n.published_at BETWEEN ? AND ?
                ORDER BY n.published_at
            """
            params.insert(0, entity_code)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def get_stats(self) -> dict:
        """数据库统计"""
        total = self.conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
        entities = self.conn.execute("""
            SELECT entity_code, entity_name, COUNT(*) as cnt
            FROM news_entities GROUP BY entity_code ORDER BY cnt DESC LIMIT 10
        """).fetchall()
        sentiments = self.conn.execute("""
            SELECT sentiment, COUNT(*) as cnt FROM news_events GROUP BY sentiment
        """).fetchall()
        return {
            'total_articles': total,
            'top_entities': [dict(r) for r in entities],
            'sentiment_dist': {r['sentiment']: r['cnt'] for r in sentiments}
        }

    def close(self):
        self.conn.close()


# ============================================================
# 二、新闻因子引擎
# ============================================================

class NewsFactorEngine:
    """新闻因子计算引擎

    基于华泰证券 (2025) 方法:
      每股票情感得分 S(i,t) = 正面新闻数 - 负面新闻数
      因子值 F(i,T) = Σ(w_t * S(i,t)), w_t = 线性衰减权重
    """

    DAYS_LOOKBACK = 30   # 回顾窗口
    HALF_LIFE = 7        # 半衰期(天)

    def __init__(self, db: NewsDatabase):
        self.db = db

    def _decay_weight(self, days_ago: int) -> float:
        """线性衰减权重"""
        return max(0, (self.DAYS_LOOKBACK - days_ago) / self.DAYS_LOOKBACK)

    def sentiment_factor(self, entity_code: str, calc_date: str = None,
                         days_lookback: int = None) -> dict:
        """计算舆情情感因子

        Returns:
            {factor_value, n_articles, sentiment_breakdown, daily_scores}
        """
        if calc_date is None:
            calc_date = datetime.now().strftime("%Y-%m-%d")
        if days_lookback is None:
            days_lookback = self.DAYS_LOOKBACK

        start = (datetime.strptime(calc_date, "%Y-%m-%d") - timedelta(days=days_lookback)).strftime("%Y-%m-%d")
        articles = self.db.query_by_date_range(start, calc_date, entity_code)

        if not articles:
            return {'factor_value': 0, 'n_articles': 0, 'sentiment_breakdown': {}, 'daily_scores': []}

        today = datetime.strptime(calc_date, "%Y-%m-%d")
        daily_scores = {}
        for art in articles:
            pub_date = (art['published_at'] or '')[:10]
            if not pub_date:
                continue
            days_ago = (today - datetime.strptime(pub_date, "%Y-%m-%d")).days
            weight = self._decay_weight(days_ago)

            # 查事件分类中的情感
            events = self.db.conn.execute(
                "SELECT sentiment, sentiment_score FROM news_events WHERE news_id=?",
                (art['id'],)
            ).fetchall()

            if events:
                for evt in events:
                    sent = evt['sentiment']
                    score = evt['sentiment_score'] or 0
                    if sent == 'positive':
                        score = max(score, 0.5)
                    elif sent == 'negative':
                        score = min(score, -0.5)
                    else:
                        score = 0
                    daily_scores.setdefault(pub_date, []).append(score * weight)
            else:
                # 无情感标签 → 中性
                daily_scores.setdefault(pub_date, []).append(0)

        # 按日聚合 → 加权求和
        daily_agg = {}
        for d, scores in daily_scores.items():
            daily_agg[d] = sum(scores) / len(scores) if scores else 0

        # 计算因子值
        factor = 0
        for d, score in daily_agg.items():
            pub_dt = datetime.strptime(d, "%Y-%m-%d")
            days_ago = (today - pub_dt).days
            factor += score * self._decay_weight(days_ago)

        # 情感统计
        all_sentiments = []
        for art in articles:
            evts = self.db.conn.execute(
                "SELECT sentiment FROM news_events WHERE news_id=?", (art['id'],)
            ).fetchall()
            for e in evts:
                all_sentiments.append(e['sentiment'])

        breakdown = {
            'positive': all_sentiments.count('positive'),
            'negative': all_sentiments.count('negative'),
            'neutral': all_sentiments.count('neutral'),
            'total': len(all_sentiments)
        }

        return {
            'factor_value': round(factor, 4),
            'n_articles': len(articles),
            'sentiment_breakdown': breakdown,
            'daily_scores': daily_agg
        }

    def hotness_factor(self, entity_code: str, calc_date: str = None,
                       days_lookback: int = 30) -> dict:
        """计算舆情热度因子 (方正金工 2025 "热点漂移")

        原理: 新闻量的变化幅度 → 投资者注意力波动 → 超买/超卖
        """
        if calc_date is None:
            calc_date = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.strptime(calc_date, "%Y-%m-%d") - timedelta(days=days_lookback)).strftime("%Y-%m-%d")

        articles = self.db.query_by_date_range(start, calc_date, entity_code)

        # 按日统计新闻量
        daily_counts = {}
        for art in articles:
            pub_date = (art['published_at'] or '')[:10]
            daily_counts[pub_date] = daily_counts.get(pub_date, 0) + 1

        if not daily_counts:
            return {'factor_value': 0, 'n_articles': 0, 'avg_daily': 0, 'max_daily': 0}

        counts = list(daily_counts.values())
        avg = sum(counts) / len(counts)
        std = (sum((c - avg)**2 for c in counts) / len(counts)) ** 0.5 if len(counts) > 1 else 0
        recent = daily_counts.get(calc_date, avg)
        hotness = (recent - avg) / std if std > 0 else 0

        return {
            'factor_value': round(hotness, 4),
            'n_articles': len(articles),
            'avg_daily': round(avg, 1),
            'max_daily': max(counts),
            'days_with_news': len(daily_counts)
        }

    def impact_factor(self, entity_code: str, calc_date: str = None,
                      days_lookback: int = 30) -> dict:
        """计算消息影响力因子

        基于事件等级(high/medium/low)加权
        high=3, medium=2, low=1
        """
        if calc_date is None:
            calc_date = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.strptime(calc_date, "%Y-%m-%d") - timedelta(days=days_lookback)).strftime("%Y-%m-%d")

        articles = self.db.query_by_date_range(start, calc_date, entity_code)
        if not articles:
            return {'factor_value': 0, 'n_articles': 0}

        weights = {'high': 3, 'medium': 2, 'low': 1}
        total_impact = 0
        for art in articles:
            evts = self.db.conn.execute(
                "SELECT impact_level, sentiment FROM news_events WHERE news_id=?",
                (art['id'],)
            ).fetchall()
            for evt in evts:
                w = weights.get(evt['impact_level'], 1)
                sent_mul = 1 if evt['sentiment'] == 'positive' else (-1 if evt['sentiment'] == 'negative' else 0)
                total_impact += w * sent_mul

        return {
            'factor_value': round(total_impact / max(len(articles), 1), 4),
            'n_articles': len(articles)
        }

    def save_factors(self, entity_code: str, calc_date: str = None):
        """计算并保存所有因子"""
        if calc_date is None:
            calc_date = datetime.now().strftime("%Y-%m-%d")

        sent = self.sentiment_factor(entity_code, calc_date)
        hot = self.hotness_factor(entity_code, calc_date)
        imp = self.impact_factor(entity_code, calc_date)

        factors = [
            ('sentiment', sent['factor_value'], sent['n_articles'],
             sent['sentiment_breakdown'].get('positive', 0),
             sent['sentiment_breakdown'].get('negative', 0),
             sent['sentiment_breakdown'].get('neutral', 0),
             sent['factor_value'], 0, 0, sent),
            ('hotness', hot['factor_value'], hot['n_articles'], 0, 0, 0, 0, 0, 0, hot),
            ('impact', imp['factor_value'], imp['n_articles'], 0, 0, 0, 0, 0, imp['factor_value'], imp),
        ]

        for fname, fval, n_arts, n_pos, n_neg, n_neu, s_w, s_d, i_w, extra in factors:
            self.db.conn.execute("""
                INSERT OR REPLACE INTO news_factors
                (entity_code, factor_date, factor_name, factor_value,
                 n_articles, n_positive, n_negative, n_neutral,
                 sentiment_weighted, sentiment_decay, impact_weighted, extra_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (entity_code, calc_date, fname, fval, n_arts,
                  n_pos, n_neg, n_neu, s_w, s_d, i_w,
                  json.dumps(extra, ensure_ascii=False)))
        self.db.conn.commit()

        return {'sentiment': sent, 'hotness': hot, 'impact': imp}


# ============================================================
# 三、因子验证引擎
# ============================================================

class FactorValidator:
    """因子验证引擎

    指标:
      IC (Information Coefficient): 因子值与未来收益的相关系数
      Rank IC: 秩相关系数(免疫极值)
      ICIR: IC均值/IC标准差 (中金: ICIR>0.5=优秀)
      Win Rate: IC>0的占比
    """

    def __init__(self, db: NewsDatabase):
        self.db = db

    def validate(self, entity_code: str, factor_name: str = 'sentiment',
                 min_samples: int = 20) -> dict:
        """验证因子有效性"""
        factors = self.db.conn.execute("""
            SELECT factor_date, factor_value FROM news_factors
            WHERE entity_code=? AND factor_name=?
            ORDER BY factor_date
        """, (entity_code, factor_name)).fetchall()

        if len(factors) < min_samples:
            return {'error': f'需要至少{min_samples}个样本', 'n_samples': len(factors),
                    'n_dates': len(factors), 'signal_positive_ratio': 0, 'signal_negative_ratio': 0,
                    'note': f'当前仅{len(factors)}天数据，需{min_samples}天以上做有效IC计算'}

        # 简易IC计算
        ic_vals = []
        dates = []
        for i in range(len(factors) - 1):
            f_date = factors[i]['factor_date']
            f_val = factors[i]['factor_value']
            # 这里需要接入实际收益率数据做完整验证
            # 简化版: 用因子方向 vs 次日涨跌做命中率统计
            dates.append(f_date)
            if f_val > 0:
                ic_vals.append(1)  # 正向信号
            elif f_val < 0:
                ic_vals.append(-1)
            else:
                ic_vals.append(0)

        pos_rate = sum(1 for v in ic_vals if v > 0) / len(ic_vals) if ic_vals else 0
        neg_rate = sum(1 for v in ic_vals if v < 0) / len(ic_vals) if ic_vals else 0

        return {
            'entity': entity_code,
            'factor': factor_name,
            'n_samples': len(factors),
            'n_dates': len(dates),
            'signal_positive_ratio': round(pos_rate, 3),
            'signal_negative_ratio': round(neg_rate, 3),
            'note': '需接入实际价格数据做完整IC/IR计算'
        }

    def backfill_feedback(self, entity_code: str, factor_name: str,
                          price_data: list = None) -> int:
        """回填验证反馈

        price_data: [{date, close}] 按日期排序
        """
        if not price_data:
            return 0

        price_idx = {p['date'][:10]: p for p in price_data}
        factors = self.db.conn.execute("""
            SELECT factor_date, factor_value FROM news_factors
            WHERE entity_code=? AND factor_name=? ORDER BY factor_date
        """, (entity_code, factor_name)).fetchall()

        count = 0
        for f in factors:
            f_date = f['factor_date'][:10]
            f_val = f['factor_value']
            # 找下一交易日
            sorted_dates = sorted(price_idx.keys())
            next_dates = [d for d in sorted_dates if d > f_date]
            if not next_dates:
                continue
            next_date = next_dates[0]
            fwd_return = (price_idx[next_date]['close'] - price_idx[f_date]['close']) / price_idx[f_date]['close'] * 100 if f_date in price_idx else 0

            hit = 0
            if f_val > 0.1 and fwd_return > 0:
                hit = 1
            elif f_val < -0.1 and fwd_return < 0:
                hit = 1
            elif f_val > 0.1 and fwd_return < 0:
                hit = -1
            elif f_val < -0.1 and fwd_return > 0:
                hit = -1

            self.db.conn.execute("""
                INSERT OR REPLACE INTO news_feedback
                (entity_code, factor_date, forward_period, forward_return, factor_value, hit, extra_json)
                VALUES (?,?,?,?,?,?,?)
            """, (entity_code, f_date, '1d', round(fwd_return, 4), f_val, hit, '{}'))
            count += 1

        self.db.conn.commit()
        return count


# ============================================================
# 四、CLI入口
# ============================================================

def _make_id(article: dict) -> str:
    raw = f"{article.get('source','')}|{article.get('source_url','')}|{article.get('title','')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python core/news_db.py ingest --source westock --code 300418   入库新闻(从stdin读JSON)")
        print("  python core/news_db.py factor 300418 --days 30                  计算因子")
        print("  python core/news_db.py validate 300418 --factor sentiment         验证因子")
        print("  python core/news_db.py query 300418 --days 7                      查询新闻")
        print("  python core/news_db.py stats                                      数据库统计")
        print("  python core/news_db.py report 300418                              综合报告")
        return

    cmd = sys.argv[1]
    db = NewsDatabase()
    engine = NewsFactorEngine(db)

    try:
        if cmd == 'ingest':
            # 从stdin读JSON数组或从WeStock data_news读取
            if not sys.stdin.isatty():
                raw_data = json.load(sys.stdin)
            else:
                print("请通过管道传入新闻JSON")
                return

            articles = raw_data if isinstance(raw_data, list) else [raw_data]
            count = 0
            for art in articles:
                art['id'] = art.get('id', _make_id(art))
                # 构建实体列表
                entities = art.pop('entities', [])
                if not entities and art.get('symbol'):
                    entities = [{'type': 'stock', 'code': art['symbol'], 'name': art.get('name', '')}]
                # 构建事件列表
                events = art.pop('events', [])
                if not events:
                    events = [{
                        'category': art.get('event_category', 'general'),
                        'sentiment': _detect_sentiment(art.get('title', '') + ' ' + art.get('content', '')),
                        'sentiment_score': art.get('sentiment_score', 0),
                        'impact': 'medium' if art.get('high_impact') else 'low'
                    }]
                tags = art.pop('tags', [])
                if db.insert_article(art, entities, events, tags):
                    count += 1
            print(f"✅ 入库 {count} 条新闻")

        elif cmd == 'factor':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            result = engine.save_factors(code)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == 'validate':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            fn = 'sentiment'
            for i, arg in enumerate(sys.argv):
                if arg == '--factor' and i+1 < len(sys.argv):
                    fn = sys.argv[i+1]
            validator = FactorValidator(db)
            result = validator.validate(code, fn)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == 'query':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            days = 7
            for i, arg in enumerate(sys.argv):
                if arg == '--days' and i+1 < len(sys.argv):
                    days = int(sys.argv[i+1])
            articles = db.query_by_entity(code, days=days)
            print(json.dumps([{
                'title': a['title'], 'source': a['source'],
                'published_at': a['published_at']
            } for a in articles], ensure_ascii=False, indent=2))

        elif cmd == 'stats':
            stats = db.get_stats()
            print(json.dumps(stats, ensure_ascii=False, indent=2))

        elif cmd == 'report':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            stats = db.get_stats()
            sent = engine.sentiment_factor(code)
            hot = engine.hotness_factor(code)
            imp = engine.impact_factor(code)
            articles = db.query_by_entity(code, days=7)

            # 按事件类别统计
            cat_dist = {}
            for a in articles:
                evts = db.conn.execute(
                    "SELECT event_category, sentiment FROM news_events WHERE news_id=?",
                    (a['id'],)
                ).fetchall()
                for e in evts:
                    cat_dist[e['event_category']] = cat_dist.get(e['event_category'], 0) + 1

            print(f"\n{'='*60}")
            print(f"  本地新闻库报告: {code}")
            print(f"{'='*60}")
            print(f"\n📊 数据库概览: {stats['total_articles']} 篇文章")
            print(f"\n📰 最近7天新闻: {len(articles)} 篇")
            print(f"\n📂 事件类别分布:")
            for cat, cnt in sorted(cat_dist.items(), key=lambda x: -x[1]):
                bar = '█' * min(cnt, 30)
                print(f"  {cat:<20} {cnt:>3} {bar}")
            print(f"\n📈 新闻因子:")
            print(f"  情感因子: {sent['factor_value']:+.4f} ({sent['n_articles']}篇)")
            if sent['sentiment_breakdown']:
                bd = sent['sentiment_breakdown']
                print(f"    积极:{bd.get('positive',0)} 消极:{bd.get('negative',0)} 中性:{bd.get('neutral',0)}")
            print(f"  热度因子: {hot['factor_value']:+.4f} (日均{hot.get('avg_daily',0)}篇)")
            print(f"  影响力因子: {imp['factor_value']:+.4f}")
    finally:
        db.close()


def _detect_sentiment(text: str) -> str:
    pos_kw = ['突破', '超预期', '增长', '利好', '大涨', '创新高', '登顶', '领先', '第一', '首发', '里程碑']
    neg_kw = ['暴跌', '亏损', '下滑', '减持', '监管', '处罚', '破发', '暴雷', '净卖出']
    t = text.lower()
    pos = sum(1 for kw in pos_kw if kw in t)
    neg = sum(1 for kw in neg_kw if kw in t)
    if pos > neg + 1: return 'positive'
    if neg > pos + 1: return 'negative'
    if pos > 0 and neg > 0: return 'mixed'
    return 'neutral'


if __name__ == '__main__':
    main()
