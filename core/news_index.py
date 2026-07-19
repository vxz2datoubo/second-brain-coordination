#!/usr/bin/env python3
"""
消息面指数系统 (News Composite Index System)

统一整合:
  - 本地存储 (SQLite + FTS5全文搜索)
  - 结构化指数 (日频因子, 回测就绪格式)
  - 多维搜索 (时间/关键词/来源/实体)
  - 溯源链路 (指数值→原始新闻)
  - 回测导出 (CSV/JSON, 与backtest_engine兼容)

学术基础:
  [1] Arxiv 2505.16136 (2025) — 日情感指数构建: S_t, σ_t, ArticleImpact, 滞后特征
  [2] 国泰海通 2025 — 舆情领先性1-2天, 动态权重调整
  [3] 华泰证券 2025 — 线性衰减加权和 + BERT情感分类
  [4] CICC 另类数据策略 — 新闻因子IC/IR验证框架

使用:
  python core/news_index.py search 300418 --keyword "世界模型" --days 30
  python core/news_index.py index 300418 --start 2026-07-01 --end 2026-07-14
  python core/news_index.py trace 300418 2026-07-14 --index sentiment
  python core/news_index.py export 300418 --start 2026-07-01 --end 2026-07-14 --format csv
"""

import json
import sqlite3
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.news_db import NewsDatabase, NewsFactorEngine, _detect_sentiment

DATA_DIR = ROOT / "data" / "news_index"
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


# ============================================================
# 一、FTS5 全文搜索扩展
# ============================================================

class NewsSearchEngine:
    """基于SQLite FTS5的全文搜索引擎"""

    def __init__(self, db: NewsDatabase):
        self.db = db
        self._ensure_fts()

    def _ensure_fts(self):
        """创建FTS5虚拟表(如果不存在)"""
        self.db.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
                title, content, summary,
                content='news_articles',
                content_rowid='rowid'
            )
        """)
        # 增量更新触发器
        self.db.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS news_ai_fts AFTER INSERT ON news_articles BEGIN
                INSERT INTO news_fts(rowid, title, content, summary)
                VALUES (new.rowid, new.title, new.content, new.summary);
            END
        """)
        self.db.conn.commit()

    def search(self, keyword: str, limit: int = 50) -> list:
        """全文搜索"""
        rows = self.db.conn.execute("""
            SELECT n.*, rank FROM news_fts f
            JOIN news_articles n ON f.rowid = n.rowid
            WHERE news_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (keyword, limit)).fetchall()
        return [dict(r) for r in rows]

    def search_by_entity_and_keyword(self, entity_code: str, keyword: str,
                                     days: int = 30, limit: int = 50) -> list:
        """按实体+关键词组合搜索"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self.db.conn.execute("""
            SELECT DISTINCT n.*, rank FROM news_fts f
            JOIN news_articles n ON f.rowid = n.rowid
            JOIN news_entities e ON n.id = e.news_id
            WHERE e.entity_code = ? AND news_fts MATCH ?
            AND n.published_at >= ?
            ORDER BY rank LIMIT ?
        """, (entity_code, keyword, cutoff, limit)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 二、新闻综合指数 (News Composite Index)
# ============================================================

class NewsCompositeIndex:
    """日频新闻综合指数

    基于 Arxiv 2505.16136 (2025) 方法:
      S_t = Σ(sentiment_scores) / N_t
      σ_t = sentiment dispersion
      AI_t = S_t × log(1 + N_t)  ← 文章影响力
      ΔS_t = MA5(S) - MA20(S)    ← 情绪加速度
    """

    def __init__(self, db: NewsDatabase):
        self.db = db

    def compute_daily(self, entity_code: str, calc_date: str) -> dict:
        """计算单日新闻综合指数

        Returns 15个维度:
          mean_sentiment, sentiment_dispersion, n_articles, log_volume,
          article_impact, positive_ratio, negative_ratio,
          ma5_sentiment, ma20_sentiment, sentiment_acceleration,
          mean_impact_level, high_impact_count,
          unique_sources, event_category_entropy, composite_index
        """
        # 获取当日新闻
        start = f"{calc_date} 00:00:00"
        end = f"{calc_date} 23:59:59"
        articles = self.db.query_by_date_range(calc_date, calc_date, entity_code)

        if not articles:
            return {
                'date': calc_date, 'entity': entity_code,
                'n_articles': 0, 'composite_index': 0,
                'status': 'no_news'
            }

        # 提取情感分数
        scores = []
        impacts = []
        sources = set()
        categories = []
        for art in articles:
            evts = self.db.conn.execute(
                "SELECT sentiment, sentiment_score, impact_level, event_category FROM news_events WHERE news_id=?",
                (art['id'],)
            ).fetchall()
            for e in evts:
                s = e['sentiment_score'] or 0
                if e['sentiment'] == 'positive' and s == 0:
                    s = 0.5
                elif e['sentiment'] == 'negative' and s == 0:
                    s = -0.5
                scores.append(s)
                impacts.append(e['impact_level'])
                categories.append(e['event_category'])
            if art.get('source'):
                sources.add(art['source'])

        N = len(scores)
        if N == 0:
            return {'date': calc_date, 'entity': entity_code, 'n_articles': len(articles),
                    'composite_index': 0, 'status': 'no_sentiment'}

        # 基础统计
        mean_sent = sum(scores) / N
        dispersion = (sum((s - mean_sent)**2 for s in scores) / N) ** 0.5 if N > 1 else 0
        log_vol = __import__('math').log(1 + N)

        # 文章影响力
        article_impact = mean_sent * log_vol

        # 比率
        pos_ratio = sum(1 for s in scores if s > 0.1) / N
        neg_ratio = sum(1 for s in scores if s < -0.1) / N

        # 影响力等级均值
        impact_weights = {'high': 3, 'medium': 2, 'low': 1}
        mean_impact = sum(impact_weights.get(i, 1) for i in impacts) / N

        # 高影响力新闻数
        high_impact_count = sum(1 for i in impacts if i == 'high')

        # 事件类别熵 (多样性)
        from collections import Counter
        cat_counts = Counter(categories)
        total_cat = sum(cat_counts.values())
        entropy = -sum((c/total_cat) * __import__('math').log(c/total_cat + 1e-10)
                       for c in cat_counts.values()) / (__import__('math').log(total_cat) + 1e-10)

        # 综合指数 = 0.35×情感 + 0.15×影响力 + 0.15×文章影响 + 0.15×正比率 + 0.10×高影响 + 0.10×熵
        composite = (
            0.35 * mean_sent +
            0.15 * (mean_impact / 3) +
            0.15 * (article_impact / 3) +
            0.15 * pos_ratio +
            0.10 * (high_impact_count / max(N, 1)) +
            0.10 * entropy
        )
        # 缩放到[-1, 1]
        composite = max(-1, min(1, composite * 1.5))

        return {
            'date': calc_date,
            'entity': entity_code,
            'n_articles': len(articles),
            'n_sentiment_scores': N,
            'unique_sources': len(sources),
            'mean_sentiment': round(mean_sent, 4),
            'sentiment_dispersion': round(dispersion, 4),
            'log_volume': round(log_vol, 4),
            'article_impact': round(article_impact, 4),
            'positive_ratio': round(pos_ratio, 4),
            'negative_ratio': round(neg_ratio, 4),
            'mean_impact_level': round(mean_impact, 4),
            'high_impact_count': high_impact_count,
            'event_entropy': round(entropy, 4),
            'composite_index': round(composite, 4),
            'article_ids': [a['id'] for a in articles],
            'status': 'ok'
        }

    def compute_range(self, entity_code: str, start_date: str,
                      end_date: str) -> list:
        """计算日期范围内的日频指数序列"""
        results = []
        current = datetime.strptime(start_date[:10], "%Y-%m-%d")
        end = datetime.strptime(end_date[:10], "%Y-%m-%d")
        while current <= end:
            d = current.strftime("%Y-%m-%d")
            result = self.compute_daily(entity_code, d)
            results.append(result)
            current += timedelta(days=1)
        return results

    def add_moving_averages(self, series: list, windows: list = [5, 20]) -> list:
        """添加移动平均和加速度到序列"""
        for w in windows:
            key = f'ma{w}_sentiment'
            key_acc = f'sentiment_acceleration_{w}'
            for i in range(len(series)):
                window_data = series[max(0, i-w+1):i+1]
                valid = [d['mean_sentiment'] for d in window_data if d['status'] == 'ok']
                if len(valid) >= max(1, w // 2):
                    series[i][key] = round(sum(valid) / len(valid), 4)
                else:
                    series[i][key] = 0

        # 情绪加速度 = MA5 - MA20
        for i in range(len(series)):
            ma5 = series[i].get('ma5_sentiment', 0)
            ma20 = series[i].get('ma20_sentiment', 0)
            series[i]['sentiment_acceleration'] = round(ma5 - ma20, 4)

        # 滞后特征
        for lag in [1, 2, 3]:
            key = f'lag{lag}_sentiment'
            key_comp = f'lag{lag}_composite'
            for i in range(len(series)):
                if i >= lag and series[i-lag]['status'] == 'ok':
                    series[i][key] = series[i-lag]['mean_sentiment']
                    series[i][key_comp] = series[i-lag].get('composite_index', 0)
                else:
                    series[i][key] = 0
                    series[i][key_comp] = 0

        return series


# ============================================================
# 三、溯源链路
# ============================================================

class TraceEngine:
    """从指数值反向追溯到原始新闻"""

    def __init__(self, db: NewsDatabase):
        self.db = db

    def trace(self, entity_code: str, date: str, index_name: str = 'all') -> dict:
        """追溯某日指数的构成来源

        Returns:
          {index_values, contributing_articles, source_breakdown}
        """
        nci = NewsCompositeIndex(self.db)
        daily = nci.compute_daily(entity_code, date)

        if daily.get('status') != 'ok':
            return {'error': f'{date} 无有效新闻数据'}

        article_ids = daily.get('article_ids', [])
        articles = []
        for aid in article_ids:
            art = self.db.conn.execute(
                "SELECT * FROM news_articles WHERE id=?", (aid,)
            ).fetchone()
            if art:
                art_dict = dict(art)
                # 附加事件信息
                evts = self.db.conn.execute(
                    "SELECT * FROM news_events WHERE news_id=?", (aid,)
                ).fetchall()
                art_dict['events'] = [dict(e) for e in evts]
                entities = self.db.conn.execute(
                    "SELECT * FROM news_entities WHERE news_id=?", (aid,)
                ).fetchall()
                art_dict['entities'] = [dict(e) for e in entities]
                articles.append(art_dict)

        # 来源分布
        source_breakdown = {}
        for art in articles:
            src = art.get('source', 'unknown')
            source_breakdown[src] = source_breakdown.get(src, 0) + 1

        # 情感贡献排名
        sentiment_contributions = []
        for art in articles:
            for evt in art.get('events', []):
                sentiment_contributions.append({
                    'title': art['title'][:60],
                    'source': art['source'],
                    'sentiment': evt['sentiment'],
                    'score': evt['sentiment_score'],
                    'impact': evt['impact_level'],
                    'category': evt['event_category']
                })
        sentiment_contributions.sort(key=lambda x: abs(x.get('score', 0)), reverse=True)

        return {
            'date': date,
            'entity': entity_code,
            'index_summary': {
                'composite': daily['composite_index'],
                'mean_sentiment': daily['mean_sentiment'],
                'n_articles': daily['n_articles'],
                'positive_ratio': daily['positive_ratio']
            },
            'contributing_articles': articles,
            'source_breakdown': source_breakdown,
            'sentiment_contributions': sentiment_contributions[:10],
            'total_contributions': len(sentiment_contributions)
        }


# ============================================================
# 四、回测导出
# ============================================================

class BacktestExporter:
    """导出回测就绪的数据格式"""

    COLUMNS = [
        'date', 'entity_code',
        'composite_index', 'mean_sentiment', 'sentiment_dispersion',
        'n_articles', 'log_volume', 'article_impact',
        'positive_ratio', 'negative_ratio',
        'mean_impact_level', 'high_impact_count', 'unique_sources',
        'ma5_sentiment', 'ma20_sentiment', 'sentiment_acceleration',
        'lag1_sentiment', 'lag2_sentiment', 'lag3_sentiment',
        'lag1_composite', 'lag2_composite', 'lag3_composite',
        'event_entropy'
    ]

    def __init__(self, db: NewsDatabase):
        self.db = db

    def export(self, entity_code: str, start_date: str, end_date: str) -> list:
        """导出为字典列表"""
        nci = NewsCompositeIndex(self.db)
        series = nci.compute_range(entity_code, start_date, end_date)
        series = nci.add_moving_averages(series)
        return series

    def to_csv(self, entity_code: str, start_date: str, end_date: str,
               filepath: str = None) -> str:
        """导出为CSV"""
        series = self.export(entity_code, start_date, end_date)
        if not filepath:
            filepath = str(EXPORT_DIR / f"news_index_{entity_code}_{start_date}_{end_date}.csv")

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=self.COLUMNS, extrasaction='ignore')
            writer.writeheader()
            for row in series:
                row['entity_code'] = entity_code
                writer.writerow(row)

        return filepath

    def to_json(self, entity_code: str, start_date: str, end_date: str,
                filepath: str = None) -> str:
        """导出为JSON"""
        series = self.export(entity_code, start_date, end_date)
        if not filepath:
            filepath = str(EXPORT_DIR / f"news_index_{entity_code}_{start_date}_{end_date}.json")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({'entity': entity_code, 'range': [start_date, end_date],
                       'columns': self.COLUMNS, 'data': series},
                      f, ensure_ascii=False, indent=2)

        return filepath


# ============================================================
# 五、CLI
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python core/news_index.py search <code> --keyword '关键词' --days 30")
        print("  python core/news_index.py index <code> --start YYYY-MM-DD --end YYYY-MM-DD")
        print("  python core/news_index.py trace <code> <date>")
        print("  python core/news_index.py export <code> --start YYYY-MM-DD --end YYYY-MM-DD --format csv")
        return

    cmd = sys.argv[1]
    db = NewsDatabase()
    search_engine = NewsSearchEngine(db)

    try:
        if cmd == 'search':
            code = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
            keyword = None
            days = 30
            for i, arg in enumerate(sys.argv):
                if arg == '--keyword' and i+1 < len(sys.argv):
                    keyword = sys.argv[i+1]
                if arg == '--days' and i+1 < len(sys.argv):
                    days = int(sys.argv[i+1])

            if not keyword:
                print("请指定 --keyword")
                return

            if code:
                results = search_engine.search_by_entity_and_keyword(code, keyword, days)
            else:
                results = search_engine.search(keyword)

            print(f"🔍 搜索 '{keyword}': {len(results)} 条结果")
            for r in results[:20]:
                print(f"  [{r.get('published_at','')[:10]}] {r.get('source','')} | {r['title'][:70]}")

        elif cmd == 'index':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            start = "2026-07-01"
            end = "2026-07-14"
            for i, arg in enumerate(sys.argv):
                if arg == '--start' and i+1 < len(sys.argv):
                    start = sys.argv[i+1]
                if arg == '--end' and i+1 < len(sys.argv):
                    end = sys.argv[i+1]

            nci = NewsCompositeIndex(db)
            series = nci.compute_range(code, start, end)
            series = nci.add_moving_averages(series)

            print(f"\n📊 新闻综合指数: {code} ({start} ~ {end})")
            print(f"{'日期':<12} {'综合':>6} {'情感':>6} {'篇数':>4} {'影响力':>6} {'加速度':>6}")
            print("-" * 48)
            for d in series:
                if d['status'] == 'ok':
                    print(f"{d['date']:<12} {d['composite_index']:>+6.3f} {d['mean_sentiment']:>+6.3f} "
                          f"{d['n_articles']:>4d} {d['article_impact']:>+6.3f} "
                          f"{d.get('sentiment_acceleration',0):>+6.3f}")

        elif cmd == 'trace':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            date = sys.argv[3] if len(sys.argv) > 3 else datetime.now().strftime("%Y-%m-%d")
            tracer = TraceEngine(db)
            result = tracer.trace(code, date)

            if 'error' in result:
                print(f"❌ {result['error']}")
                return

            print(f"\n🔗 溯源: {code} @ {date}")
            print(f"  综合指数: {result['index_summary']['composite']:+.3f}")
            print(f"  情感均值: {result['index_summary']['mean_sentiment']:+.3f}")
            print(f"  文章数: {result['index_summary']['n_articles']}")
            print(f"\n📰 贡献文章 Top5:")
            for i, sc in enumerate(result['sentiment_contributions'][:5], 1):
                s_emo = {'positive':'🟢','negative':'🔴','neutral':'⚪','mixed':'🟡'}.get(sc['sentiment'],'')
                print(f"  {i}. {s_emo} [{sc['impact']}] {sc['title']}")
                print(f"     来源:{sc['source']} 情感:{sc['score']:+.2f} 类别:{sc['category']}")
            print(f"\n📂 来源分布: {result['source_breakdown']}")

        elif cmd == 'export':
            code = sys.argv[2] if len(sys.argv) > 2 else '300418'
            start = "2026-07-01"
            end = "2026-07-14"
            fmt = "csv"
            for i, arg in enumerate(sys.argv):
                if arg == '--start' and i+1 < len(sys.argv):
                    start = sys.argv[i+1]
                if arg == '--end' and i+1 < len(sys.argv):
                    end = sys.argv[i+1]
                if arg == '--format' and i+1 < len(sys.argv):
                    fmt = sys.argv[i+1]

            exporter = BacktestExporter(db)
            if fmt == 'csv':
                fp = exporter.to_csv(code, start, end)
            else:
                fp = exporter.to_json(code, start, end)
            print(f"✅ 导出完成: {fp}")

        else:
            print(f"未知命令: {cmd}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
