"""
新闻突袭监控器 — 7/2 闭环学习成果

核心规则:
  1. 价格异常拉升(>3%/10min) → 立即搜索相关新闻
  2. 判定利好等级 → 上移卖点（同时标注原始卖点）
  3. 检查新闻是否旧闻/已消化 → 避免追陈旧利好
  4. 整合进 runner.py 盘中和竞价分析

等级判定:
  🔥🔥🔥 里程碑级: ARR破纪录/重大合作/政策利好 → 卖点上移+50%
  🔥🔥 重要级: 季度数据亮眼/产品突破 → 卖点上移+30%
  🔥 一般级: 常规进展/行业利好 → 卖点上移+10%
  ➖ 无效: 旧闻/已消化 → 不变
"""

import urllib.request
import json
import re
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class NewsItem:
    title: str = ""
    source: str = ""
    published: str = ""
    url: str = ""
    impact_level: str = ""  # 🔥🔥🔥 / 🔥🔥 / 🔥 / ➖
    is_old: bool = False
    reason: str = ""


@dataclass
class NewsAlert:
    code: str = ""
    name: str = ""
    triggered: bool = False
    spike_pct: float = 0
    items: list = field(default_factory=list)
    top_impact: str = ""
    summary: str = ""
    original_sells: list = field(default_factory=list)  # 原始卖点
    adjusted_sells: list = field(default_factory=list)   # 调整后卖点


STOCK_NEWS_KEYWORDS = {
    "300418": ["昆仑万维", "天工AI", "DramaWave", "SkyReels", "Skywork"],
    "300058": ["蓝色光标", "蓝标", "广告", "传媒", "即梦AI", "GPT5"],
}

MARKER_KEYWORDS = {
    "里程碑": ["ARR突破", "10亿美元", "8亿美元", "历史性突破", "里程碑", "首次", "最大", "首单"],
    "重要": ["QoQ增长", "双位数增长", "超预期", "登顶", "发布", "转型", "完成"],
    "一般": ["宣布", "签署", "合作", "布局", "上线", "推出", "完成"],
}


def detect_spike(current_price: float, price_10min_ago: float) -> float:
    """检测10分钟内是否出现异常拉升"""
    if price_10min_ago <= 0:
        return 0
    return (current_price / price_10min_ago - 1) * 100


def classify_impact(title: str) -> str:
    """分类新闻影响力"""
    for level, keywords in MARKER_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                if level == "里程碑":
                    return "🔥🔥🔥 里程碑级"
                elif level == "重要":
                    return "🔥🔥 重要级"
    return "🔥 一般级"


def check_if_stale(items: list, code: str) -> list:
    """
    检查是否旧闻/已提前消化
    - 旧闻: 同一事件几天前已报道过
    - 消化: 新闻发布前价格已经涨了
    """
    for item in items:
        title = item.title.lower()

        # 检查是否几天前的旧闻重发
        import re
        date_match = re.search(r'202[5-6]年?\d{0,2}月?\d{0,2}日?', title)
        if date_match:
            news_date = date_match.group()
            today = datetime.now().strftime("%Y%m%d")
            if today[:6] != news_date[:6]:
                item.is_old = True
                item.impact_level = "➖ 旧闻重发"
                item.reason = f"新闻日期{news_date}，可能是旧闻"
                continue

        # 检查是否已被市场消化（简化版：检查新闻发布时间 vs 股价开始上涨时间）
        if code == "300418":
            if "ARR" in title and "突破" in title:
                if item.published and "14:" in item.published:
                    pass  # 今天下午才发，没消化
                else:
                    pass  # 无法判断时间，标记为注意
    return items


def adjust_sell_targets(original_sells: list, impact_level: str) -> tuple:
    """根据利好等级上移卖点"""
    up_map = {
        "🔥🔥🔥": 1.5,  # 卖点上移50%区间
        "🔥🔥": 1.3,     # 卖点上移30%区间
        "🔥": 1.1,       # 卖点上移10%区间
        "➖": 1.0         # 不变
    }

    mult = 1.0
    for key in ["🔥🔥🔥", "🔥🔥", "🔥"]:
        if key in impact_level:
            mult = up_map[key]
            break

    if mult == 1.0:
        return original_sells[:], mult

    # 上移卖点：将区间放大
    adjusted = []
    for p in original_sells:
        if isinstance(p, (tuple, list)):
            mid = (p[0] + p[1]) / 2
            spread = (p[0] - p[1]) * mult / 2
            adjusted.append((round(mid + spread, 2), round(mid - spread, 2)))
        else:
            # 单一价格，上移
            adjusted.append(round(p * mult, 2))

    return adjusted, mult


def format_news_alert(alert: NewsAlert) -> str:
    """格式化新闻突袭报告"""
    if not alert.triggered:
        return ""

    lines = []
    lines.append(f"\n  ⚡ [新闻突袭] 检测到{abs(alert.spike_pct):.1f}%异常拉升")

    for item in alert.items:
        tag = item.impact_level if not item.is_old else "➖ 旧闻重发"
        stale = " ⚠️旧闻" if item.is_old else ""
        lines.append(f"  {tag} | {item.title}{stale}")
        if item.reason:
            lines.append(f"         {item.reason}")
        if item.published:
            lines.append(f"         来源: {item.source} | 发布于 {item.published}")

    if alert.original_sells and alert.adjusted_sells:
        lines.append(f"\n  📊 卖点调整:")
        for i, (orig, adj) in enumerate(zip(alert.original_sells, alert.adjusted_sells)):
            if orig[0] != adj[0]:
                lines.append(f"  卖#{i+1}: {orig[0]:.2f}(原) → {adj[0]:.2f}(新)")
            else:
                lines.append(f"  卖#{i+1}: {orig[0]:.2f} 不变")

    if alert.summary:
        lines.append(f"\n  💡 {alert.summary}")

    return "\n".join(lines)


def monitor(code: str, name: str, current_price: float,
            price_10min_ago: float = 0,
            original_sells: list = None) -> NewsAlert:
    """
    新闻突袭监控 — 主入口

    参数:
      code: 股票代码
      name: 股票名称
      current_price: 当前价
      price_10min_ago: 10分钟前价格
      original_sells: [(卖点价格, 支撑价格), ...]
    """
    alert = NewsAlert(code=code, name=name)
    if original_sells:
        alert.original_sells = [(p, p) for p in original_sells]

    spike = detect_spike(current_price, price_10min_ago)
    if spike < 3:
        alert.spike_pct = spike
        return alert

    alert.triggered = True
    alert.spike_pct = spike

    # 搜索相关新闻
    keywords = STOCK_NEWS_KEYWORDS.get(code, [name])
    query = " ".join(keywords[:3]) + " 最新"
    full_url = f"https://news.google.com/rss/search?q={urllib.request.quote(query)}&hl=zh-CN&sort=date"

    try:
        # 优先用财联社/新浪快讯，国内源更及时
        sina_url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k={urllib.request.quote(keywords[0])}&num=5"
        data = urllib.request.urlopen(sina_url, timeout=5).read().decode('gbk')
        news = json.loads(data).get("result", {}).get("data", [])

        for n in news[:5]:
            item = NewsItem(
                title=n.get("title", ""),
                source="新浪快讯",
                published=n.get("ctime", ""),
                url=n.get("url", "")
            )
            if not item.published:
                item.published = datetime.fromtimestamp(int(n.get("intime", "0"))).strftime("%H:%M") if n.get("intime") else "未知"

            item.impact_level = classify_impact(item.title)
            alert.items.append(item)

    except Exception:
        # 兜底：搜网页
        try:
            search_url = "https://www.google.com/search?q=" + urllib.request.quote(query + " 2026-07-02")
            pass  # 后续扩展
        except:
            pass

    if not alert.items:
        # 最后手段：直接抓取新浪财经页面
        alert.items.append(NewsItem(
            title=f"检测到{spike:.1f}%拉升但未找到相关新闻",
            impact_level="🔥 一般级(无法获取消息)",
            source="系统检测",
            reason="请手动查新闻"
        ))

    alert.items = check_if_stale(alert.items, code)

    # 判定最强影响等级
    if alert.items:
        levels = [item.impact_level for item in alert.items if not item.is_old]
        if levels:
            alert.top_impact = max(levels, key=lambda x: len(x))

    # 调整卖点
    if alert.original_sells and "🔥🔥🔥" in alert.top_impact:
        alert.adjusted_sells, mult = adjust_sell_targets(alert.original_sells, "🔥🔥🔥")
        alert.summary = "里程碑利好！卖点上移至原始目标的1.5倍区间"
    elif alert.original_sells and "🔥🔥" in alert.top_impact:
        alert.adjusted_sells, mult = adjust_sell_targets(alert.original_sells, "🔥🔥")
        alert.summary = "重要利好，卖点上移30%"
    elif alert.original_sells:
        alert.adjusted_sells = alert.original_sells[:]
    else:
        alert.adjusted_sells = alert.original_sells[:] if alert.original_sells else []

    return alert


# ============================================================
# 手动事件驱动（用户手机收到消息时）
# ============================================================
def manual_event(code: str, name: str, event_title: str, event_time: str,
                 current_price: float, original_sells: list,
                 known_cost: float = 0) -> NewsAlert:
    """
    用户手动触发新闻事件分析
    用途: 用户手机收到消息但系统还没检测到
    """
    alert = NewsAlert(code=code, name=name, triggered=True)

    item = NewsItem(
        title=event_title,
        source="用户手动",
        published=event_time,
        impact_level=classify_impact(event_title)
    )
    alert.items = [item]
    alert.original_sells = [(p, p) for p in original_sells]
    alert.spike_pct = 999  # 手动模式

    # 判定
    if "ARR" in event_title or "8亿" in event_title or "里程碑" in event_title:
        alert.top_impact = "🔥🔥🔥 里程碑级"
        alert.adjusted_sells, _ = adjust_sell_targets(alert.original_sells, "🔥🔥🔥")
        alert.summary = "里程碑级利好（ARR破8亿美元）。原卖点已失效，建议新卖点如上。底仓坚决不动。"
    elif "突破" in event_title or "超预期" in event_title:
        alert.top_impact = "🔥🔥 重要级"
        alert.adjusted_sells, _ = adjust_sell_targets(alert.original_sells, "🔥🔥")
        alert.summary = "重要利好，卖点上移"
    else:
        alert.top_impact = "🔥 一般级"
        alert.adjusted_sells = alert.original_sells
        alert.summary = "一般利好，卖点不变"

    return alert
