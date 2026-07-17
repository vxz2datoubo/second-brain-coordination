#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二大脑 · 主动预警推送引擎 alert_engine
输入: WeStock 拉取的 news/hot/events/calendar 原始数据 (JSON)
处理: 价值评估 (impact × urgency × relevance) + 关键词甄别
输出: 落盘 alerts/pending.json (待推送) + alerts/history.json (去重)
查询: query_pending(days) 供被动查询 + 主动播报

设计哲学 (复用第二大脑铁律):
  - 无真实反馈不标完成: 每条预警必须来自真实拉取数据, 不臆造
  - 去重: history 记录已推送, 不重复轰炸用户
  - 双模式: 主动(pending 等待播报) + 被动(query 即时返回)
"""
import json, os, time
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALERT_DIR = os.path.join(BASE, "alerts")
PENDING = os.path.join(ALERT_DIR, "pending.json")
HISTORY = os.path.join(ALERT_DIR, "history.json")
RULES = os.path.join(ALERT_DIR, "rules.json")

DEFAULT_RULES = {
    "score_threshold": 55,
    "urgency_days": 7,
    "keyword_preview": ["将于", "预告", "下周", "即将", "计划于", "拟于", "拟",
                        "即将召开", "前瞻", "提前", "下月", "未来", "拟于"],
    "keyword_major": ["突发", "重磅", "利好突袭", "打击", "关闭", "暴增", "暴跌",
                       "大涨", "重组", "停牌", "复牌", "解禁", "财报", "业绩预告",
                       "发射", "回收", "试飞", "制裁", "冲突", "降息", "加息",
                       "议息", "签约", "中标", "获批"],
    "type_weights": {
        "12": 95, "34": 90, "36": 80, "19": 85, "20": 88,
        "29": 70, "32": 65, "39": 92, "14": 75, "16": 75,
        "31": 90, "38": 88, "17": 60, "18": 55, "25": 60, "27": 60
    },
    "holdings": {
        "core": [
            {"name": "昆仑万维", "code": "300418"},
            {"name": "蓝色光标", "code": "300058"}
        ],
        "related": [
            {"name": "科大讯飞", "code": "002230"},
            {"name": "三六零", "code": "601360"},
            {"name": "分众传媒", "code": "002027"},
            {"name": "省广集团", "code": "002400"}
        ],
        "sectors": ["AI智能体", "ChatGPT", "AIGC", "游戏", "传媒", "多模态", "算力", "芯片", "半导体", "CPO", "商业航天", "军工", "新能源", "锂电池", "创新药", "CRO", "中药"]
    }
}


def load_rules():
    if os.path.exists(RULES):
        try:
            r = json.load(open(RULES, encoding="utf-8"))
            merged = dict(DEFAULT_RULES)
            for k, v in r.items():
                if k == "type_weights" and isinstance(v, dict):
                    merged[k] = dict(DEFAULT_RULES.get(k, {}))
                    merged[k].update(v)
                else:
                    merged[k] = v
            return merged
        except Exception:
            pass
    return dict(DEFAULT_RULES)


def ts_to_str(ts):
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def days_until(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (d - datetime.now().date()).days
    except Exception:
        return None


def load_json(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def relevance_for(title, code, name, rules):
    """持仓优先 + 板块 + 全市场基线。返回 (relevance分值, tags)"""
    hl = rules.get("holdings", {})
    text = " ".join([title or "", name or ""])
    code = code or ""
    # 主仓 (昆仑万维/蓝色光标)
    for h in hl.get("core", []):
        nm, cd = h.get("name"), h.get("code")
        if (nm and nm in text) or (cd and cd in (text + " " + code)):
            return 100, ["持仓相关"]
    # 关联股 (科大讯飞/三六零/分众/省广)
    for h in hl.get("related", []):
        nm, cd = h.get("name"), h.get("code")
        if (nm and nm in text) or (cd and cd in (text + " " + code)):
            return 90, ["持仓相关"]
    # 关注板块
    for s in hl.get("sectors", []):
        if s in text:
            return 75, ["板块相关"]
    return 55, []


def evaluate_news(items, rules):
    """items: data_hot kind=news 的 rankResult 列表 (全市场热新闻流)"""
    alerts = []
    for it in (items or []):
        title = it.get("news_title") or ""
        if not title:
            continue
        prop = int(it.get("property") or 0)
        pub = it.get("publish_time")
        src = it.get("source") or ""
        nid = it.get("news_id") or ""
        # 影响力: property 热度权重归一 (338186 为样本高值)
        impact = min(100, int(prop / 338186.0 * 100)) if prop else 20
        # 时效性: 发布时间新鲜度 (每天 -20 分, 最低 10)
        urgency = 100
        if pub:
            age_h = (time.time() - int(pub)) / 3600.0
            urgency = max(10, 100 - int(age_h / 24.0 * 20))
        # 关键词甄别
        kw_major = any(k in title for k in rules["keyword_major"])
        kw_preview = any(k in title for k in rules["keyword_preview"])
        # 关联度: 持仓优先 + 全市场重大基线 (接持仓加权)
        rel_base, rel_tags = relevance_for(title, "", "", rules)
        relevance = rel_base
        if kw_major:
            relevance = max(relevance, 75)
            if "持仓相关" not in rel_tags and "板块相关" not in rel_tags:
                rel_tags.append("全市场重大")
        if kw_preview and "预告" not in rel_tags:
            rel_tags.append("预告")
        score = int(impact * 0.4 + urgency * 0.35 + relevance * 0.25)
        if "持仓相关" in rel_tags:
            score = min(100, score + 18)   # 持仓命中强优先
        elif kw_preview or kw_major:
            score = min(100, score + 8)    # 预告/重大类加权
        if score >= rules["score_threshold"]:
            alerts.append({
                "id": "news_%s" % nid,
                "type": "news",
                "title": title,
                "source": src,
                "publish_time": ts_to_str(pub),
                "score": score,
                "impact": impact,
                "urgency": urgency,
                "relevance": relevance,
                "tags": rel_tags,
                "first_seen": time.time()
            })
    return alerts


def evaluate_events(items, rules):
    """items: 标准化事件列表 (type_id/name/code/date/desc), 来自 tool_event/data_events"""
    alerts = []
    for it in (items or []):
        etype = str(it.get("type_id") or it.get("id") or "")
        name = it.get("name") or it.get("title") or ""
        code = it.get("code") or it.get("symbol") or ""
        edate = it.get("date") or it.get("event_date") or ""
        desc = it.get("desc") or ""
        w = rules["type_weights"].get(etype, 50)
        du = days_until(edate) if edate else None
        if du is None:
            urgency = 60
        elif du < 0:
            urgency = 10
        elif du <= rules["urgency_days"]:
            urgency = 100 - du * 5
        else:
            urgency = max(20, 70 - (du - rules["urgency_days"]))
        rel_base, rel_tags = relevance_for("", code, name, rules)
        relevance = max(70, rel_base)  # 确定性事件本身即高关联, 持仓命中再拉高
        score = int(w * 0.5 + urgency * 0.35 + relevance * 0.15)
        if "持仓相关" in rel_tags:
            score = min(100, score + 15)
        if score >= rules["score_threshold"]:
            alerts.append({
                "id": "event_%s_%s_%s" % (code, etype, edate),
                "type": "event",
                "title": ("%s (%s)" % (name, code)) if code else name,
                "event_date": edate,
                "desc": desc,
                "score": score,
                "impact": w,
                "urgency": int(urgency),
                "relevance": relevance,
                "tags": ["确定性预告"] + rel_tags + (["T+%d天" % du] if du is not None else []),
                "first_seen": time.time()
            })
    return alerts


def store(alerts):
    pending = load_json(PENDING, [])
    history = load_json(HISTORY, [])
    hist_ids = {h["id"] for h in history}
    new_count = 0
    for a in alerts:
        if a["id"] in hist_ids:
            continue  # 已推送过, 跳过 (去重, 不重复轰炸)
        pending.append(a)
        history.append(a)
        hist_ids.add(a["id"])
        new_count += 1
    pending.sort(key=lambda x: x["score"], reverse=True)
    cutoff = time.time() - 30 * 86400
    pending = [p for p in pending if p.get("first_seen", 0) > cutoff]
    save_json(PENDING, pending)
    save_json(HISTORY, history[-2000:])
    return new_count, len(pending)


def query_pending(days=7):
    pending = load_json(PENDING, [])
    cutoff = time.time() - days * 86400
    recent = [p for p in pending if p.get("first_seen", 0) > cutoff]
    recent.sort(key=lambda x: x["score"], reverse=True)
    return recent


def format_summary(alerts):
    if not alerts:
        return "📭 当前无高价值预警（近7天）。"
    lines = ["🚨 高价值消息汇总 (%d 条, 按影响力排序):" % len(alerts), ""]
    for i, a in enumerate(alerts[:15], 1):
        tag = " ".join("[%s]" % t for t in a.get("tags", []) if t)
        lines.append("%d. 【%d分】%s %s" % (i, a["score"], a["title"], tag))
        meta = []
        if a.get("source"):
            meta.append("来源:%s" % a["source"])
        if a.get("publish_time"):
            meta.append("时间:%s" % a["publish_time"])
        if a.get("event_date"):
            meta.append("事件日:%s" % a["event_date"])
        if meta:
            lines.append("   └ " + " | ".join(meta))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "scan":
        inp = sys.argv[2] if len(sys.argv) > 2 else None
        if inp and os.path.exists(inp):
            data = json.load(open(inp, encoding="utf-8"))
        elif not sys.stdin.isatty():
            data = json.load(sys.stdin)
        else:
            data = {}
        # 兼容 MCP 原始格式 {"ok":true,"data":{"rankResult":[...]}}
        news = data.get("news")
        if news is None:
            if isinstance(data.get("data"), dict) and "rankResult" in data["data"]:
                news = data["data"]["rankResult"]
            elif "rankResult" in data:
                news = data["rankResult"]
        events = data.get("events")
        rules = load_rules()
        alerts = []
        if news:
            alerts += evaluate_news(news, rules)
        if events:
            alerts += evaluate_events(events, rules)
        n, total = store(alerts)
        print("✅ 扫描完成: 新预警 %d 条, pending 共 %d 条" % (n, total), flush=True)
        for a in alerts[:5]:
            print("   +%d %s" % (a["score"], a["title"][:50]), flush=True)
    elif cmd == "query":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        use_json = "--json" in sys.argv
        alerts = query_pending(days)
        if use_json:
            # 结构化输出，方便 AI 解析后附加深度解读
            print(json.dumps(alerts, ensure_ascii=False, indent=2), flush=True)
        else:
            print(format_summary(alerts), flush=True)
    elif cmd == "pending":
        use_json = "--json" in sys.argv
        alerts = load_json(PENDING, [])
        if use_json:
            print(json.dumps(alerts, ensure_ascii=False, indent=2), flush=True)
        else:
            print(format_summary(alerts), flush=True)
    else:
        print("用法: alert_engine.py [scan <input.json|stdin> | query [days] | pending]")
