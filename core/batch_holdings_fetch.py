#!/usr/bin/env python3
"""
持仓股票全维度消息批量采集与入库程序 (v2 — 1年全维度扩展)
(Batch Holdings News Fetch & Ingest Pipeline)

目标: 对当前持仓股票, 批量采集全维度相关消息, 统一结构化入库到现有消息系统
      (core/news_db.py 的 NewsDatabase + core/news_index.py 的 FTS5/指数/回测导出),
      为后续 回测 / 消息面消化 / 深度归因 提供数据底座。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
采集范围 (v2 扩展, 覆盖用户全部要求):
  1) 时间跨度: 默认 FETCH_WINDOW_DAYS=365 (≥1年)
  2) 数据范围:
     - 持仓个股直接相关: 新闻(news) + 公告(notice)
     - AI行业资讯 / 业务上下游(板块/主题/题材/业务域): 见 BUSINESS_SCOPE
  3) 机构观点: 研报(report) + 评级(rating) + 盈利预测/估值(consensus)
  4) 公司层面: 财报(finance, 年报/季报) + 临时公告(notice) + 重大事项(events)
  所有能与持仓/业务产生关联的信息都纳入。

架构约束 (重要):
  WeStock 数据只能由对话层(AI) 通过 MCP 拉取, 纯 Python 进程无法直连 MCP。
  因此本程序采用【两段式】:
    ┌── 拉取层 (AI 驱动) ──┐         ┌── 归一入库层 (本程序) ──┐
    │ 按 plan() 调 MCP 工具 │  ──JSON→ │ normalize → 去重 → 入库   │
    │ 结果写 staging/*.json │         │ → 重建FTS → 因子 → 导出   │
    └───────────────────────┘         └──────────────────────────┘
  ※ 各 MCP 源结构说明见 build_fetch_plan() 注释; 拉取层(AI)负责把
    结构化源(finance/consensus/rating/events)合成为含 title/content/time 的
    干净条目再落盘, 本程序 normalizer 只做字段兼容与标签推断。

CLI:
  python core/batch_holdings_fetch.py plan                      打印 MCP 调用清单(JSON)
  python core/batch_holdings_fetch.py ingest --file staging.json  归一并入库单个文件
  python core/batch_holdings_fetch.py ingest --dir  staging_dir  归一并入库目录下所有 *.json
  python core/batch_holdings_fetch.py report                     入库后各持仓/板块综合报告
  python core/batch_holdings_fetch.py export --days 365           导出各持仓回测就绪 CSV

staging 单文件结构:
  {"fetched_at":"...","batches":[ {"code","name","category","source_api","items":[...],
                                    "scope_relation":(业务类可选),"scope_name":(业务类可选)} ]}
  多文件模式(ingest --dir): 每个 .json 可含若干 batches。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import sys
import re
import glob
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.news_db import NewsDatabase, NewsFactorEngine, _detect_sentiment, _make_id
from core.news_index import NewsSearchEngine, BacktestExporter

STAGING_DIR = ROOT / "data" / "news_db" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 零、全局参数
# ============================================================
FETCH_WINDOW_DAYS = 365          # 默认覆盖 ≥1 年

# ============================================================
# 一、持仓配置 (可扩展: 新增持仓在此登记即可)
# ============================================================
HOLDINGS = [
    {
        "code": "300418",
        "name": "昆仑万维",
        "symbol": "sz300418",
        "industry": "传媒/AIGC",
        "sector_code": "",
        "industry_keywords": ["AIGC", "大模型", "AI应用", "传媒", "游戏出海", "短剧", "算力"],
        "themes": ["世界模型", "多模态", "人形机器人", "AI Agent", "Sora", "具身智能",
                     "WAIC", "人工智能大会", "AGI", "短剧", "AI芯片", "AI应用"],
    },
    {
        "code": "300058",
        "name": "蓝色光标",
        "symbol": "sz300058",
        "industry": "传媒/营销",
        "sector_code": "",
        "industry_keywords": ["营销", "广告", "AI营销", "传媒", "MCN", "出海营销", "数字人"],
        "themes": ["AI营销", "大模型应用", "数字人", "AIGC", "出海营销", "元宇宙", "AI Agent"],
    },
]

HOLDING_BY_CODE = {h["code"]: h for h in HOLDINGS}

# ============================================================
# 二、业务关联范围 (AI产业链上下游 + 板块/主题/题材/业务域)
#      relation: upstream(上游算力/芯片) / core(AI核心)
#                downstream(下游应用) / related(相关题材) / business(业务域)
# ============================================================
BUSINESS_SCOPE = [
    {"key": "ai_core",      "label": "人工智能",   "search": "人工智能", "relation": "core",
     "themes": ["大模型", "AGI", "多模态", "AI Agent"]},
    {"key": "ai_model",     "label": "人工智能大模型", "search": "大模型", "relation": "core",
     "themes": ["大模型", "世界模型"]},
    {"key": "compute",       "label": "AI算力芯片", "search": "算力", "relation": "upstream",
     "themes": ["算力", "算力租赁", "GPU", "IDC"]},
    {"key": "semiconductor", "label": "半导体",     "search": "半导体", "relation": "upstream",
     "themes": ["半导体", "芯片", "GPU", "CPO", "光模块"]},
    {"key": "robot",        "label": "人形机器人", "search": "人形机器人", "relation": "related",
     "themes": ["机器人", "具身智能", "特斯拉"]},
    {"key": "data",         "label": "数据要素",   "search": "数据要素", "relation": "business",
     "themes": ["数据要素", "数据确权", "语料"]},
    {"key": "media",        "label": "传媒",       "search": "传媒", "relation": "downstream",
     "themes": ["传媒", "短剧", "游戏", "影视"]},
    {"key": "marketing",    "label": "广告营销",   "search": "营销", "relation": "downstream",
     "themes": ["营销", "广告", "数字人", "AIGC"]},
]

# 解析后的板块代码 (由对话层 search --type sector 解析后固化, 保证 plan 可复现)
SECTOR_CODES = {
    "ai_core":      {"code": "pt02003800", "name": "人工智能"},
    "ai_model":     {"code": "pt02GN2228", "name": "人工智能大模型"},
    "compute":      {"code": "pt02GN2222", "name": "AI算力芯片"},
    "semiconductor": {"code": "pt01801081", "name": "半导体"},
    "robot":        {"code": "pt02GN2238", "name": "人形机器人"},
    "data":         {"code": "pt02GN2200", "name": "数据要素"},
    "media":        {"code": "pt01801760", "name": "传媒"},
    "marketing":    {"code": "pt01801765", "name": "广告营销"},
}

# ============================================================
# 三、类目常量 (v2: 10 类)
# ============================================================
CAT_STOCK_NEWS = "个股新闻"
CAT_NOTICE     = "个股公告"
CAT_RESEARCH   = "机构研报"
CAT_CONSENSUS  = "盈利预测"
CAT_FINANCE    = "财报"
CAT_EVENT      = "重大事项"
CAT_SECTOR     = "板块动态"
CAT_BUSINESS   = "业务关联"
CAT_INDUSTRY   = "行业政策"
CAT_THEME      = "主题舆情"

# 事件类别推断词典
EVENT_KEYWORDS = {
    "业绩": ["业绩", "财报", "营收", "净利", "预增", "预亏", "季报", "年报", "扭亏"],
    "研报评级": ["评级", "研报", "目标价", "买入", "增持", "跑赢", "上调", "下调", "覆盖"],
    "产品发布": ["发布", "上线", "推出", "首发", "亮相", "问世", "开源", "内测", "公测"],
    "政策监管": ["政策", "监管", "国务院", "部委", "规划", "指导意见", "备案", "牌照", "立法", "补贴"],
    "行业动态": ["行业", "板块", "赛道", "产业链", "市场规模", "渗透率", "景气"],
    "资本运作": ["定增", "减持", "增持", "回购", "并购", "股权", "融资", "质押", "解禁", "担保", "授信"],
    "合作签约": ["合作", "签约", "战略", "中标", "订单", "协议", "落地"],
    "重大事件": ["WAIC", "大会", "峰会", "论坛", "展会", "发布会", "习近平", "重磅"],
    "技术突破": ["世界模型", "多模态", "机器人", "具身", "SOTA", "突破", "领先", "参数"],
}

POSITIVE_KW = ['突破', '超预期', '增长', '利好', '大涨', '创新高', '登顶', '领先', '第一',
                '首发', '里程碑', '买入', '增持', '上调', '中标', '扭亏', '预增', '开源']
NEGATIVE_KW = ['暴跌', '亏损', '下滑', '减持', '监管', '处罚', '破发', '暴雷', '净卖出',
                '下调', '预亏', '质押', '解禁', '诉讼', '警示', '担保']
HIGH_IMPACT_KW = ['WAIC', '习近平', '发布会', '重磅', '世界模型', '机器人', '涨停', '跌停',
                   '收购', '并购', '定增', '业绩预告', '目标价', '年报', '季报']

# 业务关联 → 实体类型
RELATION_ENTITY_TYPE = {
    "upstream": "sector_up", "core": "concept", "downstream": "sector_down",
    "related": "theme", "business": "business",
}

# ============================================================
# 四、字段归一化 (兼容 WeStock 多种返回字段名)
# ============================================================
def _first(d: dict, keys, default=""):
    """从 dict 中取第一个非空字段"""
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return default


def _norm_time(raw) -> str:
    """归一化时间戳为 'YYYY-MM-DD HH:MM:SS' (兼容 秒/毫秒戳 / ISO / 中文)"""
    if raw in (None, "", 0):
        return ""
    s = str(raw).strip()
    if s.isdigit():                       # 纯数字时间戳(秒/毫秒)
        ts = int(s)
        if ts > 1e12:                  # 毫秒
            ts //= 1000
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""
    s = s.replace("T", " ").replace("/", "-")
    m = re.search(r"(\d{4}-\d{1,2}-\d{1,2})[ ]?(\d{1,2}:\d{1,2}(:\d{1,2})?)?", s)
    if m:
        date_part = m.group(1)
        y, mo, d = date_part.split("-")
        date_part = f"{y}-{int(mo):02d}-{int(d):02d}"
        time_part = m.group(2) or "00:00:00"
        if time_part.count(":") == 1:
            time_part += ":00"
        return f"{date_part} {time_part}"
    return s[:19]


def _infer_event_category(text: str, default: str) -> str:
    scores = {}
    for cat, kws in EVENT_KEYWORDS.items():
        c = sum(1 for kw in kws if kw in text)
        if c:
            scores[cat] = c
    if scores:
        return max(scores, key=scores.get)
    return default


def _infer_impact(text: str) -> str:
    hits = sum(1 for kw in HIGH_IMPACT_KW if kw in text)
    if hits >= 2:
        return "high"
    if hits == 1:
        return "medium"
    return "low"


def _sentiment_score(text: str) -> float:
    pos = sum(1 for kw in POSITIVE_KW if kw in text)
    neg = sum(1 for kw in NEGATIVE_KW if kw in text)
    if pos == neg == 0:
        return 0.0
    return round((pos - neg) / (pos + neg), 3)


class Normalizer:
    """把 干净条目(拉取层已合成) → news_db 结构化 article 记录"""

    def normalize_item(self, item: dict, code: str, category: str,
                      source_api: str, scope_relation: str = None,
                      scope_name: str = None) -> dict:
        holding = HOLDING_BY_CODE.get(code, {"name": scope_name or "", "themes": [], "industry_keywords": []})
        # 字段兼容(已合成的干净条目通常含 title/content/time, 这里兼容多源)
        title = str(_first(item, ["title", "news_title", "name", "summary", "content",
                                   "text", "org_name", "info_title"], ""))[:300]
        content = str(_first(item, ["content", "text", "abstract", "digest",
                                     "summary", "body", "info_content"], ""))
        summary = str(_first(item, ["summary", "abstract", "digest", "brief"], ""))[:500]
        pub = _norm_time(_first(item, ["published_at", "pub_time", "time", "date",
                                        "datetime", "create_time", "publish_time",
                                        "report_date", "notice_date", "ctime", "end_date"], ""))
        url = str(_first(item, ["url", "source_url", "link", "detail_url", "href"], ""))
        src = str(_first(item, ["source", "media", "org_name", "author", "site",
                                 "media_name", "from"], "")) or f"westock:{source_api}"
        text_all = f"{title} {content} {summary}"

        # 实体
        if scope_relation:
            etype = RELATION_ENTITY_TYPE.get(scope_relation, "concept")
            entities = [{
                "type": etype, "code": code, "name": scope_name or "",
                "relevance": 0.6, "is_primary": 0,
            }]
        else:
            is_core = category in (CAT_STOCK_NEWS, CAT_NOTICE, CAT_RESEARCH,
                                     CAT_CONSENSUS, CAT_FINANCE, CAT_EVENT)
            entities = [{
                "type": "stock", "code": code, "name": holding["name"],
                "relevance": 1.0 if is_core else 0.6,
                "is_primary": 1 if is_core else 0,
            }]

        # 事件
        default_cat = {
            CAT_STOCK_NEWS: "行业动态", CAT_NOTICE: "资本运作",
            CAT_RESEARCH: "研报评级", CAT_CONSENSUS: "研报评级",
            CAT_FINANCE: "业绩", CAT_EVENT: "重大事件",
            CAT_SECTOR: "行业动态", CAT_BUSINESS: "行业动态",
            CAT_INDUSTRY: "政策监管", CAT_THEME: "重大事件",
        }.get(category, "general")
        sentiment = _detect_sentiment(text_all)
        events = [{
            "category": _infer_event_category(text_all, default_cat),
            "subcategory": category,
            "sentiment": sentiment,
            "sentiment_score": _sentiment_score(text_all),
            "impact": _infer_impact(text_all),
            "confidence": 0.6,
            "keywords": ",".join([kw for kw in (POSITIVE_KW + NEGATIVE_KW)
                                   if kw in text_all][:8]),
        }]

        # 标签: 分类标签 + 命中主题词 + 行业词 + 来源类型 + (业务类)板块名
        tags = [{"tag": category, "type": "category", "weight": 1.0}]
        if scope_name:
            tags.append({"tag": scope_name, "type": "scope", "weight": 0.8})
        theme_pool = holding.get("themes", []) if not scope_relation else \
            BUSINESS_SCOPE and []
        if scope_relation:
            for sc in BUSINESS_SCOPE:
                if sc["relation"] == scope_relation and sc["label"] == scope_name:
                    theme_pool = sc["themes"]
                    break
        for th in theme_pool:
            if th in text_all:
                tags.append({"tag": th, "type": "theme", "weight": 0.9})
        if not scope_relation:
            for ik in holding.get("industry_keywords", []):
                if ik in text_all:
                    tags.append({"tag": ik, "type": "industry", "weight": 0.7})
        tags.append({"tag": f"api:{source_api}", "type": "source", "weight": 0.3})

        article = {
            "source": src,
            "source_url": url,
            "title": title or "(无标题)",
            "content": content,
            "summary": summary,
            "published_at": pub or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "language": "zh",
            "raw": item,
        }
        article["id"] = _make_id(article)
        return {"article": article, "entities": entities, "events": events, "tags": tags}


# ============================================================
# 五、入库器
# ============================================================
class Ingestor:
    def __init__(self, db: NewsDatabase = None):
        self.db = db or NewsDatabase()
        self.norm = Normalizer()
        NewsSearchEngine(self.db)        # 确保 FTS5 已建(触发器)

    def ingest_staging(self, staging: dict) -> dict:
        stats = {"total_items": 0, "inserted": 0, "duplicated": 0,
                 "by_category": {}, "by_code": {}, "errors": 0}
        for batch in staging.get("batches", []):
            code = batch.get("code", "")
            category = batch.get("category", "")
            api = batch.get("source_api", "unknown")
            rel = batch.get("scope_relation")
            sname = batch.get("scope_name")
            items = batch.get("items", []) or []
            for item in items:
                stats["total_items"] += 1
                try:
                    rec = self.norm.normalize_item(item, code, category, api, rel, sname)
                    existed = self.db.conn.execute(
                        "SELECT 1 FROM news_articles WHERE id=?",
                        (rec["article"]["id"],)).fetchone()
                    ok = self.db.insert_article(rec["article"], rec["entities"],
                                                rec["events"], rec["tags"])
                    if ok and not existed:
                        stats["inserted"] += 1
                        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
                        key = code or (sname or "?")
                        stats["by_code"][key] = stats["by_code"].get(key, 0) + 1
                    elif existed:
                        stats["duplicated"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    print(f"[Ingest] error: {e}")
        return stats

    def rebuild_fts(self):
        self.db.conn.execute("INSERT INTO news_fts(news_fts) VALUES('rebuild')")
        self.db.conn.commit()

    def compute_factors(self, codes: list):
        engine = NewsFactorEngine(self.db)
        out = {}
        for c in codes:
            out[c] = engine.save_factors(c)
        return out

    def close(self):
        self.db.close()


# ============================================================
# 六、拉取计划 (供 AI 层执行 MCP)
# ============================================================
def build_fetch_plan() -> dict:
    """
    生成 MCP 调用清单。AI 按此逐条调用, 结果写入 staging.batches。
    各源结构与落盘要点:
      data_news    symbol + type(0公告/1研报/2新闻/3全部) + limit   → 列表, 字段 id/title/time/url
      data_notice   symbol + type(0全部/1财务/2配股/3增发/4股权/5重大/6风险/7其他) + page/limit
                  → 列表, 字段 id/title/time/newstype (url 空, 需 detail 才全文)
      data_report   symbol + limit/page  → 列表, 字段 id/title/time/tzpj(评级)
      data_consensus code  → 结构化 {targetPrice, forecasts:[year,eps,venue,netProfit,pe,pb,ps,yoy...]}
                      落盘: 合成 1 条 {title, content(整合预测/估值), time(今日)}
      data_rating   code  → 结构化 {forecastInstitutions, ratingBuyCnt, ratingCnt}
                      落盘: 合成 1 条 {title, content(评级分布), time(今日)}
      data_events    code  → 结构化 {date, stocks:[{tagDescs,tagIds}]}
                      落盘: 每个 tag 合成 1 条 {title, content(事件描述), time(date)}
      data_finance   code + num(期数, 4≈1年/8≈2年)  → 结构化 balance/income/cashflow per EndDate
                      落盘: 每个报告期合成 1 条 {title, content(营收/净利/同比/EPS), time(EndDate)}
      data_sector    mode=info code=<板块码>  → 板块区间交易数据(板块动态)
      data_hot       kind=news(全市场热新闻) / board(板块热度)  → 列表
      ※ notice / news / report 无日期区间, 靠 limit+page 翻页覆盖 1 年
    """
    plan = {"generated_at": datetime.now().isoformat(),
             "fetch_window_days": FETCH_WINDOW_DAYS, "calls": []}
    # ---------- 持仓个股: 1 年全维度 ----------
    for h in HOLDINGS:
        code, sym, name = h["code"], h["symbol"], h["name"]
        # 1) 个股新闻 (近期高密, limit 120 ≈ 20 天; 全量 1 年受 API 限制, 以公告/研报/财报补全年)
        plan["calls"].append({"category": CAT_STOCK_NEWS, "code": code, "name": name,
                              "tool": "data_news",
                              "args": {"symbol": sym, "type": 3, "limit": 120}})
        # 2) 个股公告 (翻页覆盖 1 年: limit50 × 3 页 ≈ 150 条 ≈ 6~10 个月)
        for pg in (1, 2, 3):
            plan["calls"].append({"category": CAT_NOTICE, "code": code, "name": name,
                                  "tool": "data_notice",
                                  "args": {"symbol": sym, "type": "0", "page": pg, "limit": 50}})
        # 3) 机构研报 (limit 100 ≈ 1 年)
        plan["calls"].append({"category": CAT_RESEARCH, "code": code, "name": name,
                              "tool": "data_report", "args": {"symbol": sym, "limit": 100}})
        # 4) 盈利预测/估值 (consensus)
        plan["calls"].append({"category": CAT_CONSENSUS, "code": code, "name": name,
                              "tool": "data_consensus", "args": {"code": sym}})
        # 5) 机构评级 (rating)
        plan["calls"].append({"category": CAT_RESEARCH, "code": code, "name": name,
                              "tool": "data_rating", "args": {"code": sym}})
        # 6) 重大事项 (events 42 类)
        plan["calls"].append({"category": CAT_EVENT, "code": code, "name": name,
                              "tool": "data_events", "args": {"code": sym}})
        # 7) 财报 (num=4 ≈ 1 年四个季度)
        plan["calls"].append({"category": CAT_FINANCE, "code": code, "name": name,
                              "tool": "data_finance", "args": {"code": sym, "num": 4}})
    # ---------- 业务关联范围: AI产业链上下游 + 板块/主题/题材/业务域 ----------
    for sc in BUSINESS_SCOPE:
        sc_def = SECTOR_CODES.get(sc["key"])
        if not sc_def:
            continue
        plan["calls"].append({
            "category": CAT_SECTOR, "code": sc_def["code"], "name": sc_def["name"],
            "scope_relation": sc["relation"], "scope_name": sc_def["name"],
            "tool": "data_sector", "args": {"mode": "info", "code": sc_def["code"]},
        })
    # 全市场板块行情榜 (一次)
    plan["calls"].append({"category": CAT_SECTOR, "code": "", "name": "全市场板块行情榜",
                          "scope_relation": "core", "scope_name": "板块行情榜",
                          "tool": "data_sector", "args": {"mode": "ranking"}})
    # 全市场热新闻 (按业务主题词在归一时过滤 → 业务关联/主题舆情)
    plan["calls"].append({"category": CAT_BUSINESS, "code": "", "name": "全市场热新闻",
                          "scope_relation": "business", "scope_name": "全市场热新闻",
                          "tool": "data_hot", "args": {"kind": "news", "limit": 100}})
    # 板块热度排名 (题材/板块温度)
    plan["calls"].append({"category": CAT_BUSINESS, "code": "", "name": "板块热度排名",
                          "scope_relation": "core", "scope_name": "板块热度",
                          "tool": "data_hot", "args": {"kind": "board", "limit": 50}})
    return plan


# ============================================================
# 七、CLI
# ============================================================
def _load_stagings(path_or_dir):
    """读取单个文件或目录下所有 *.json, 合并 batches"""
    p = Path(path_or_dir)
    batches = []
    if p.is_dir():
        files = sorted(glob.glob(str(p / "*.json")))
    else:
        files = [str(p)]
    for f in files:
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            for b in data.get("batches", []):
                batches.append(b)
        except Exception as e:
            print(f"[load] 跳过 {f}: {e}")
    return batches


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]

    if cmd == "plan":
        print(json.dumps(build_fetch_plan(), ensure_ascii=False, indent=2))

    elif cmd == "ingest":
        fp = None
        mode = "file"
        for i, a in enumerate(sys.argv):
            if a == "--file" and i + 1 < len(sys.argv):
                fp = sys.argv[i + 1]
            if a == "--dir" and i + 1 < len(sys.argv):
                fp = sys.argv[i + 1]
                mode = "dir"
        if not fp:
            if not sys.stdin.isatty():
                staging = json.load(sys.stdin)
            else:
                print("用法: ingest --file staging.json | ingest --dir staging_dir")
                return
            batches = staging.get("batches", [])
        else:
            batches = _load_stagings(fp)
        if not batches:
            print("⚠️ 未发现任何 batch")
            return
        ing = Ingestor()
        try:
            # 包装成统一结构喂给 ingest_staging
            stats = ing.ingest_staging({"batches": batches})
            ing.rebuild_fts()
            codes = list({b.get("code") for b in batches if b.get("code")})
            ing.compute_factors(codes)
            print("\n" + "=" * 56)
            print("  批量入库完成")
            print("=" * 56)
            print(f"  批次数: {len(batches)}")
            print(f"  总条目: {stats['total_items']}  新入库: {stats['inserted']}  "
                  f"重复跳过: {stats['duplicated']}  错误: {stats['errors']}")
            print(f"  按类目: {json.dumps(stats['by_category'], ensure_ascii=False)}")
            print(f"  按代码/板块: {json.dumps(stats['by_code'], ensure_ascii=False)}")
            print(f"  已计算因子: {codes}")
            db_stats = ing.db.get_stats()
            print(f"  库内总文章数: {db_stats['total_articles']}")
        finally:
            ing.close()

    elif cmd == "report":
        days = 90
        for i, a in enumerate(sys.argv):
            if a == "--days" and i + 1 < len(sys.argv):
                days = int(sys.argv[i + 1])
        db = NewsDatabase()
        engine = NewsFactorEngine(db)
        try:
            print(f"\n{'='*56}\n  全库概览 (总文章 {db.get_stats()['total_articles']})\n{'='*56}")
            # 类目分布
            cat_dist = {}
            for r in db.conn.execute(
                    "SELECT e.event_subcategory, COUNT(*) FROM news_events e GROUP BY e.event_subcategory"
            ).fetchall():
                cat_dist[r[0] or "?"] = r[1]
            print(f"  类目分布: {json.dumps(cat_dist, ensure_ascii=False)}")
            for h in HOLDINGS:
                code = h["code"]
                arts = db.query_by_entity(code, days=days)
                sent = engine.sentiment_factor(code)
                hot = engine.hotness_factor(code)
                imp = engine.impact_factor(code)
                print(f"\n{'='*56}\n  {h['name']} ({code}) — 近{days}天 {len(arts)} 篇\n{'='*56}")
                print(f"  情感因子:{sent['factor_value']:+.4f}  "
                      f"热度因子:{hot['factor_value']:+.4f}  "
                      f"影响力因子:{imp['factor_value']:+.4f}")
                bd = sent.get("sentiment_breakdown", {})
                print(f"  情感分布: 积极{bd.get('positive',0)} "
                      f"消极{bd.get('negative',0)} 中性{bd.get('neutral',0)}")
        finally:
            db.close()

    elif cmd == "export":
        days = FETCH_WINDOW_DAYS
        for i, a in enumerate(sys.argv):
            if a == "--days" and i + 1 < len(sys.argv):
                days = int(sys.argv[i + 1])
        db = NewsDatabase()
        try:
            NewsSearchEngine(db)
            exporter = BacktestExporter(db)
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            for h in HOLDINGS:
                fp = exporter.to_csv(h["code"], start, end)
                print(f"✅ {h['name']} 回测CSV: {fp}")
        finally:
            db.close()

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
