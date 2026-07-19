#!/usr/bin/env python3
"""
合成层: 把 data/news_db/staging/_raw/*.json (MCP 原始响应) → 正式 staging/*.json
供 core/batch_holdings_fetch.py ingest --dir 归一入库。
纯本地运行(无需 MCP); 重跑幂等。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "news_db" / "staging" / "_raw"
OUT = ROOT / "data" / "news_db" / "staging"
TODAY = "2026-07-15"
RANK_PATH = Path(r"C:/Users/Administrator/.workbuddy/projects/f-aidanao/e4341908-6fb5-479b-913a-f9d578558264/tool-results/chatcmpl-tool-b6f178dfb5fc2798.txt")


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✎ wrote {name}")


def yiyuan(yuan):
    """元 → 亿元"""
    try:
        return round(float(yuan) / 1e8, 2)
    except Exception:
        return yuan


def yiwan(wan):
    """万元 → 亿元 (consensus forecast 的 revenue/netProfit 单位为万元)"""
    try:
        return round(float(wan) / 1e4, 2)
    except Exception:
        return wan


# ========== 1) 蓝标公告 (4页, ~200条) ==========
notice = []
for pg in (1, 2, 3, 4):
    d = load(f"300058_notice_p{pg}.json")
    notice.extend(d.get("items", []))
save("phase3_300058_notice.json", {
    "fetched_at": f"{TODAY}T00:00:00", "source": "westock-mcp",
    "batches": [{"code": "300058", "name": "蓝色光标", "category": "个股公告",
                 "source_api": "data_notice",
                 "items": [{"title": i["title"], "time": i["time"]} for i in notice]}]})
print(f"  · 蓝标公告: {len(notice)} 条 (2024-06 ~ 2026-06)")

# ========== 2) 蓝标研报 (100条) ==========
rep = load("300058_report.json").get("items", [])
rep_items = [{"title": i["title"], "time": i["time"],
              "content": (f"评级: {i['tzpj']}" if i.get("tzpj") else "")} for i in rep]
save("phase3_300058_report.json", {
    "fetched_at": f"{TODAY}T00:00:00", "stock": "300058",
    "batches": [{"code": "300058", "name": "蓝色光标", "category": "机构研报",
                 "source_api": "data_report", "items": rep_items}]})
print(f"  · 蓝标研报: {len(rep_items)} 条")

# ========== 3) consensus / finance / events / rating (两股) ==========
def consensus_batch(code, name, raw):
    d = raw["data"]
    tp = d.get("targetPrice", 0)
    fcs = sorted(d.get("forecasts", []), key=lambda x: x.get("year", 0))
    lines = [f"目标价: {float(tp):.2f} 元" if tp else "目标价: 暂无(机构未给)"]
    for f in fcs:
        y = f.get("year")
        lines.append(
            f"{y}E: EPS {f.get('eps')}  营收 {yiwan(f.get('revenue', 0))}亿  "
            f"归母净利 {yiwan(f.get('netProfit', 0))}亿  PE {f.get('pe')}  "
            f"营收同比 {f.get('revenueYoy')}%  净利同比 {f.get('netProfitYoy')}%")
    return {"code": code, "name": name, "category": "盈利预测", "source_api": "data_consensus",
            "items": [{"title": f"{name} 机构一致预期/盈利预测(截至{TODAY})",
                       "content": "\n".join(lines), "time": TODAY}]}


def finance_batch(code, name, raw):
    items = []
    for r in raw.get("income", []):
        ed = r.get("EndDate", "")
        is_year = ed.endswith("-12-31")
        label = f"{ed[:4]}年报" if is_year else f"{ed[:4]}年{int(ed[5:7])}季报"
        content = (f"营收: {yiyuan(r.get('OperatingRevenue', 0))}亿; "
                   f"归母净利润: {yiyuan(r.get('NPParentCompanyOwners', 0))}亿; "
                   f"基本EPS: {r.get('BasicEPS')}")
        items.append({"title": f"{name} {label}财报(营收/归母净利/EPS)",
                     "content": content, "time": ed})
    return {"code": code, "name": name, "category": "财报", "source_api": "data_finance", "items": items}


def events_batch(code, name, raw):
    d = raw["data"]
    date = d.get("date", TODAY)
    items = []
    for s in d.get("stocks", []):
        tids = s.get("tagIds") or [None]
        for idx, td in enumerate(s.get("tagDescs", [])):
            tid = tids[idx] if idx < len(tids) else None
            items.append({"title": td,
                          "content": f"重大事项(事件类别{tid}): {td}", "time": date})
    return {"code": code, "name": name, "category": "重大事项", "source_api": "data_events", "items": items}


def rating_batch(code, name, raw):
    d = raw["data"]
    parts = [f"覆盖机构数: {d.get('forecastInstitutions', 0)}", f"评级总数: {d.get('ratingCnt', 0)}"]
    if d.get("ratingBuyCnt"):
        parts.append(f"买入: {d.get('ratingBuyCnt')}")
    if d.get("ratingHoldCnt"):
        parts.append(f"持有: {d.get('ratingHoldCnt')}")
    if d.get("ratingSellCnt"):
        parts.append(f"卖出: {d.get('ratingSellCnt')}")
    return {"code": code, "name": name, "category": "机构研报", "source_api": "data_rating",
            "items": [{"title": f"{name} 机构评级分布", "content": "; ".join(parts), "time": TODAY}]}


for code, name, c, f, e, r in [
    ("300418", "昆仑万维", "300418_consensus.json", "300418_finance.json", "300418_events.json", "300418_rating.json"),
    ("300058", "蓝色光标", "300058_consensus.json", "300058_finance.json", "300058_events.json", "300058_rating.json"),
]:
    save(f"phase3_{code}_consensus.json", {"fetched_at": f"{TODAY}T00:00:00", "batches": [consensus_batch(code, name, load(c))]})
    save(f"phase3_{code}_finance.json", {"fetched_at": f"{TODAY}T00:00:00", "batches": [finance_batch(code, name, load(f))]})
    save(f"phase3_{code}_events.json", {"fetched_at": f"{TODAY}T00:00:00", "batches": [events_batch(code, name, load(e))]})
    save(f"phase3_{code}_rating.json", {"fetched_at": f"{TODAY}T00:00:00", "batches": [rating_batch(code, name, load(r))]})
    print(f"  · {name}: consensus/finance/events/rating 合成完成")

# ========== 4) 板块动态 (5个GN概念板块 + 全市场行情榜) ==========
SECTOR_MAP = {
    "ai_core": ("core", "人工智能"),
    "ai_model": ("core", "人工智能大模型"),
    "compute": ("upstream", "AI算力芯片"),
    "robot": ("related", "人形机器人"),
    "data": ("business", "数据要素"),
}
sector_batches = []
for key, (rel, sname) in SECTOR_MAP.items():
    d = load(f"sector_{key}.json")
    m = d.get("metrics", {})
    content = (f"成分股数: {m.get('StockCnt')}; 总市值: {m.get('TotalCap')}亿; "
               f"TTM营收: {m.get('RevTTM')}亿; TTM净利: {m.get('NetTTM')}亿; "
               f"盈利股占比: {m.get('ProfitStockRatio')}%; "
               f"营收TTM环比: {m.get('RevTTMqoq')}%; 净利TTM环比: {m.get('NetTTMqoq')}%")
    sector_batches.append({"code": d.get("code"), "name": sname, "category": "板块动态",
                          "source_api": "data_sector", "scope_relation": rel, "scope_name": sname,
                          "items": [{"title": f"{sname} 板块行情动态", "content": content, "time": TODAY}]})

# 全市场板块行情榜 (plate/concept 的 top/bottom)
rank = json.loads(RANK_PATH.read_text(encoding="utf-8"))["data"]["fundflow"]
rank_items = []
for grp in ("plate", "concept"):
    for side in ("top", "bottom"):
        for z in rank.get(grp, {}).get(side, []):
            nm, cd = z.get("name"), z.get("code")
            lzg = z.get("lzg", {}) or {}
            block = (f"涨跌幅: {z.get('zdf')}%; 成交额: {z.get('cje')}万; 换手: {z.get('hsl')}%; "
                     f"主力净流入: {z.get('zljlr')}万; 主力净流入5日: {z.get('zljlr_d5')}万; "
                     f"20日: {z.get('zljlr_d20')}万; 领涨股: {lzg.get('name')}({lzg.get('zdf')}%)")
            rank_items.append({"title": f"{nm}({cd}) 板块行情 {z.get('zdf')}% 主力净流入{z.get('zljlr')}万",
                              "content": block, "time": TODAY})
sector_batches.append({"code": "", "name": "全市场板块行情榜", "category": "板块动态",
                      "source_api": "data_sector", "scope_relation": "core", "scope_name": "板块行情榜",
                      "items": rank_items})
save("phase3_sectors.json", {"fetched_at": f"{TODAY}T00:00:00", "batches": sector_batches})
print(f"  · 板块动态: {len(sector_batches)} 批 (含行情榜 {len(rank_items)} 条)")

# ========== 5) 全市场热新闻 (业务关联/主题舆情 筛选) ==========
hot = load("data_hot_news.json")["data"]["rankResult"]
RELEVANT = ["算力", "半导体", "芯片", "AI", "AIGC", "大模型", "机器人", "具身", "光模块", "PCB", "覆铜板",
             "封测", "存储", "长鑫", "长电", "通富", "华天", "数据中心", "Meta", "英伟达", "黄仁勋", "SK海力士",
             "光纤", "通信", "商业航天", "星舰", "传媒", "营销", "游戏", "短剧", "影视", "数字人", "液冷", "CPO",
             "设备", "封装", "有色金属", "锂业", "券商", "ETF", "A股", "创业板", "股指", "牛市", "杠杆", "融资",
             "业绩", "中报", "预增", "扭亏", "科技", "光通信", "AI应用", "AI服务器", "Optimus", "英伟达"]
hot_items = []
for h in hot:
    t = h.get("news_title", "")
    rk = h.get("rank")
    keep = (rk and int(rk) <= 10) or any(k in t for k in RELEVANT)
    if not keep:
        continue
    hot_items.append({"title": t, "time": str(h.get("publish_time")), "source": h.get("source", "")})
save("phase3_market_hot.json", {"fetched_at": f"{TODAY}T00:00:00", "batches": [{
    "code": "", "name": "全市场热新闻", "category": "业务关联", "source_api": "data_hot",
    "scope_relation": "business", "scope_name": "全市场热新闻", "items": hot_items}]})
print(f"  · 全市场热新闻(业务关联筛选): {len(hot_items)} 条 (原始 {len(hot)})")

print("\n✅ 合成完成。下一步: python core/batch_holdings_fetch.py ingest --dir data/news_db/staging")
