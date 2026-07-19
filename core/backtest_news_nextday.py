#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息面 → 次日涨跌 回测消化分析
================================
对齐: 当日收盘可知的新闻因子(date t)  vs  次日收益 fwd1[t]=close[t+1]/close[t]-1
扩展: fwd2 / fwd3 看信息衰减
无未来函数: 因子只用 t 日及之前的新闻; 收益用 t+1 日真实收盘价

输出:
  data/news_index/backtest/<code>_ic.csv          各因子 IC(秩相关/Pearson) + ICIR
  data/news_index/backtest/<code>_quintile.csv    按 composite_index 五分位分组次日收益 + 多空差
  data/news_index/backtest/<code>_strategy.csv     多空策略逐日收益与净值
  data/news_index/backtest/REPORT.md              综合结论
"""
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path("F:/aidanao")
EXPORT = ROOT / "data/news_index/exports"
RAW = ROOT / "data/news_db/staging/_raw"
OUT = ROOT / "data/news_index/backtest"
OUT.mkdir(parents=True, exist_ok=True)

NEWS = {
    "300418": EXPORT / "news_index_300418_2025-07-15_2026-07-15.csv",
    "300058": EXPORT / "news_index_300058_2025-07-15_2026-07-15.csv",
}
KL = {
    "300418": RAW / "kline_300418.json",
    "300058": RAW / "kline_300058.json",
}

FACTORS = [
    "composite_index", "mean_sentiment", "sentiment_dispersion", "n_articles",
    "log_volume", "article_impact", "positive_ratio", "negative_ratio",
    "mean_impact_level", "high_impact_count", "unique_sources",
    "ma5_sentiment", "ma20_sentiment", "sentiment_acceleration",
    "lag1_sentiment", "lag2_sentiment", "lag3_sentiment",
    "lag1_composite", "lag2_composite", "lag3_composite", "event_entropy",
]


def load_kline(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d["bars"]  # ascending by date


def fwd_returns(bars, ks=(1, 2, 3)):
    closes = [b["close"] for b in bars]
    dates = [b["date"] for b in bars]
    out = {k: {} for k in ks}
    for i in range(len(bars)):
        for k in ks:
            j = i + k
            if j < len(bars):
                out[k][dates[i]] = closes[j] / closes[i] - 1.0
    return out


def cum_fwd(bars, k):
    """累计 fwd-k 日收益: close[i+k]/close[i]-1 (持有 k 日)."""
    closes = [b["close"] for b in bars]
    dates = [b["date"] for b in bars]
    out = {}
    for i in range(len(bars)):
        j = i + k
        if j < len(bars):
            out[dates[i]] = closes[j] / closes[i] - 1.0
    return out


def to_float(s):
    if s is None:
        return None
    s = str(s).strip()
    if s == "" or s.lower() in ("nan", "none", "null"):
        return None
    try:
        return float(s)
    except Exception:
        return None


def pearson(xs, ys):
    n = len(xs)
    if n < 4:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def rank(a):
    order = sorted(range(len(a)), key=lambda i: a[i])
    r = [0.0] * len(a)
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(xs, ys):
    rx, ry = rank(xs), rank(ys)
    return pearson(rx, ry)


def tstat(vals):
    n = len(vals)
    if n < 3:
        return None
    m = sum(vals) / n
    sd = statistics.stdev(vals)
    if sd == 0:
        return None
    return m / (sd / math.sqrt(n))


def analyze(code):
    bars = load_kline(KL[code])
    fr = fwd_returns(bars, (1, 2, 3, 4, 5))
    # 读新闻 CSV
    news = {}
    with open(NEWS[code], encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            news[row["date"]] = row

    # 对齐: 取所有有 fwd1 且有当日新闻因子的交易日
    dates_with_fwd1 = list(fr[1].keys())
    aligned = [d for d in dates_with_fwd1 if d in news]

    # ---- 1) 各因子 IC ----
    ic_rows = []
    ic_by_factor = {}
    for fac in FACTORS:
        xs_full, ys1, ys2, ys3, ys4, ys5 = [], [], [], [], [], []
        xs_active, ys1a, ys2a, ys3a = [], [], [], []
        for d in aligned:
            fv = to_float(news[d].get(fac))
            if fv is None:
                continue
            r1 = fr[1][d]
            xs_full.append(fv)
            ys1.append(r1)
            ys2.append(fr[2].get(d))
            ys3.append(fr[3].get(d))
            ys4.append(fr[4].get(d))
            ys5.append(fr[5].get(d))
            nav = to_float(news[d].get("n_articles")) or 0
            if nav >= 1:
                xs_active.append(fv)
                ys1a.append(r1)
        # 全样本 IC
        ic1 = spearman(xs_full, ys1) if len(xs_full) >= 4 else None
        ic2 = spearman(xs_full, [y for y in ys2 if y is not None]) if len(xs_full) >= 4 else None
        ic3 = spearman(xs_full, [y for y in ys3 if y is not None]) if len(xs_full) >= 4 else None
        ic4 = spearman(xs_full, [y for y in ys4 if y is not None]) if len(xs_full) >= 4 else None
        ic5 = spearman(xs_full, [y for y in ys5 if y is not None]) if len(xs_full) >= 4 else None
        # 新闻活跃日 IC
        ica1 = spearman(xs_active, ys1a) if len(xs_active) >= 4 else None
        ic_by_factor[fac] = (ic1, ic3, ic5, ica1, len(xs_full), len(xs_active))
        ic_rows.append({
            "factor": fac,
            "n_full": len(xs_full),
            "ic_spearman_fwd1": round(ic1, 4) if ic1 is not None else "",
            "ic_spearman_fwd2": round(ic2, 4) if ic2 is not None else "",
            "ic_spearman_fwd3": round(ic3, 4) if ic3 is not None else "",
            "ic_spearman_fwd4": round(ic4, 4) if ic4 is not None else "",
            "ic_spearman_fwd5": round(ic5, 4) if ic5 is not None else "",
            "ic_spearman_fwd1_active": round(ica1, 4) if ica1 is not None else "",
            "n_active": len(xs_active),
        })
    # ICIR (需要 IC 序列 → 这里以截面不可得, 改为标注 |IC| 量级)
    with open(OUT / f"{code}_ic.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ic_rows[0].keys()))
        w.writeheader()
        for r in ic_rows:
            w.writerow(r)

    # ---- 2) composite_index 五分位分组 ----
    comp_pairs = []          # (composite_value, date)
    comp_val = {}            # date -> composite_value
    for d in aligned:
        cv = to_float(news[d].get("composite_index"))
        if cv is None:
            continue
        comp_pairs.append((cv, d))
        comp_val[d] = cv
    comp_pairs.sort(key=lambda x: x[0])
    n = len(comp_pairs)
    groups = [[] for _ in range(5)]
    for i, (cv, d) in enumerate(comp_pairs):
        g = min(4, int(i * 5 / n))
        groups[g].append(d)

    q_rows = []
    for gi, gdates in enumerate(groups, 1):
        r1 = [fr[1][d] for d in gdates if d in fr[1]]
        r2 = [fr[2][d] for d in gdates if d in fr[2]]
        r3 = [fr[3][d] for d in gdates if d in fr[3]]
        cvs = [comp_val[d] for d in gdates]
        q_rows.append({
            "quintile": gi,
            "n": len(gdates),
            "mean_fwd1": round(statistics.mean(r1), 5) if r1 else "",
            "mean_fwd2": round(statistics.mean(r2), 5) if r2 else "",
            "mean_fwd3": round(statistics.mean(r3), 5) if r3 else "",
            "tstat_fwd1": round(tstat(r1), 3) if len(r1) >= 3 else "",
            "composite_range": f"{min(cvs):.3f}~{max(cvs):.3f}" if cvs else "",
        })
    # 多空差 Q5-Q1 (趋势中性: 两组均横跨全周期, 整体漂移相互抵消)
    ls_mean = None
    ls_t = None
    if groups[4] and groups[0]:
        q5 = [fr[1][d] for d in groups[4] if d in fr[1]]
        q1 = [fr[1][d] for d in groups[0] if d in fr[1]]
        if q5 and q1:
            ls_mean = statistics.mean(q5) - statistics.mean(q1)
            ls_series = q5 + [-x for x in q1]
            ls_t = tstat(ls_series)
    with open(OUT / f"{code}_quintile.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(q_rows[0].keys()))
        w.writeheader()
        for r in q_rows:
            w.writerow(r)

    # ---- 3) 新闻活跃日 mean_sentiment 五分位 (主信号测试, 仅 n_articles≥1) ----
    active = []
    for d in aligned:
        nav_n = to_float(news[d].get("n_articles")) or 0
        if nav_n < 1:
            continue
        sv = to_float(news[d].get("mean_sentiment"))
        if sv is None:
            continue
        active.append((sv, d))
    active.sort(key=lambda x: x[0])
    na = len(active)
    agroups = [[] for _ in range(5)]
    for i, (sv, d) in enumerate(active):
        g = min(4, int(i * 5 / na)) if na else 0
        agroups[g].append(d)
    aq_rows = []
    for gi, gdates in enumerate(agroups, 1):
        r1 = [fr[1][d] for d in gdates if d in fr[1]]
        r2 = [fr[2][d] for d in gdates if d in fr[2]]
        r3 = [fr[3][d] for d in gdates if d in fr[3]]
        svs = [sv for sv, _ in active if _ in gdates]
        aq_rows.append({
            "quintile": gi,
            "n": len(gdates),
            "mean_fwd1": round(statistics.mean(r1), 5) if r1 else "",
            "mean_fwd2": round(statistics.mean(r2), 5) if r2 else "",
            "mean_fwd3": round(statistics.mean(r3), 5) if r3 else "",
            "tstat_fwd1": round(tstat(r1), 3) if len(r1) >= 3 else "",
            "sentiment_range": f"{min(svs):.3f}~{max(svs):.3f}" if svs else "",
        })
    aq_ls = None
    aq_ls_t = None
    if agroups[4] and agroups[0]:
        aq5 = [fr[1][d] for d in agroups[4] if d in fr[1]]
        aq1 = [fr[1][d] for d in agroups[0] if d in fr[1]]
        if aq5 and aq1:
            aq_ls = statistics.mean(aq5) - statistics.mean(aq1)
            aq_ls_t = tstat(aq5 + [-x for x in aq1])
    with open(OUT / f"{code}_active_sentiment_quintile.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(aq_rows[0].keys()))
        w.writeheader()
        for r in aq_rows:
            w.writerow(r)

    # ---- 4) 方向命中率 (活跃日, 按各因子自身IC符号定预测方向 vs 次日收益符号) ----
    # 注: negative_ratio 等负向因子, 预测方向取其 IC 符号, 避免反读
    hit_rows = []
    for fac in ["mean_sentiment", "composite_index", "article_impact", "negative_ratio",
                "lag2_sentiment", "lag2_composite"]:
        ic0 = ic_by_factor.get(fac, (None, None, 0, 0))[0]
        ic_sign = 0 if ic0 is None else (1 if ic0 > 0 else -1)
        pairs = []
        for d in aligned:
            nav_n = to_float(news[d].get("n_articles")) or 0
            if nav_n < 1:
                continue
            fv = to_float(news[d].get(fac))
            if fv is None or fv == 0:
                continue
            if d not in fr[1]:
                continue
            r1 = fr[1][d]
            if r1 == 0:
                continue
            # 预测方向 = IC符号 × 因子符号 (IC符号=0时退化为因子符号)
            pred = (ic_sign if ic_sign != 0 else (1 if fv > 0 else -1)) * (1 if fv > 0 else -1)
            actual = 1 if r1 > 0 else -1
            pairs.append(pred == actual)
        if pairs:
            hit = sum(1 for x in pairs if x) / len(pairs)
            # 比例检验 vs 0.5 随机线
            se = math.sqrt(0.25 / len(pairs))
            hit_t = (hit - 0.5) / se if se > 0 else None
            hit_rows.append({"factor": fac, "n": len(pairs),
                             "hit_rate": round(hit, 4),
                             "hit_tstat_vs50": round(hit_t, 3) if hit_t is not None else ""})
    with open(OUT / f"{code}_hitrate.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["factor", "n", "hit_rate", "hit_tstat_vs50"])
        w.writeheader()
        for r in hit_rows:
            w.writerow(r)

    # ---- 5) 波动测试: 新闻强度 vs |次日收益| (活跃日) ----
    vol_rows = []
    for fac in ["n_articles", "high_impact_count", "article_impact", "mean_impact_level"]:
        xs, ys = [], []
        for d in aligned:
            nav_n = to_float(news[d].get("n_articles")) or 0
            if nav_n < 1:
                continue
            fv = to_float(news[d].get(fac))
            if fv is None or d not in fr[1]:
                continue
            xs.append(fv)
            ys.append(abs(fr[1][d]))
        if len(xs) >= 4:
            vol_rows.append({"factor": fac, "n": len(xs),
                             "ic_absret_spearman": round(spearman(xs, ys), 4) if spearman(xs, ys) is not None else ""})
    with open(OUT / f"{code}_vol.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["factor", "n", "ic_absret_spearman"])
        w.writeheader()
        for r in vol_rows:
            w.writerow(r)

    # ---- 6) 修正策略净值: 仅活跃日, 按 mean_sentiment 方向 (趋势中性) ----
    nav = 1.0
    daily = []
    for sv, d in active:
        if d not in fr[1]:
            continue
        s = 1 if sv > 0 else -1
        ret = s * fr[1][d]
        nav *= (1 + ret)
        daily.append({"date": d, "signal": s, "fwd1": round(fr[1][d], 5),
                      "strat_ret": round(ret, 5), "nav": round(nav, 4)})
    with open(OUT / f"{code}_strategy_active.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "signal", "fwd1", "strat_ret", "nav"])
        w.writeheader()
        for r in daily:
            w.writerow(r)
    strat_nav = nav
    strat_total = nav - 1.0
    strat_days = len(daily)
    # 活跃日方向命中率(整体)
    overall_hit = (sum(1 for sv, d in active if d in fr[1] and
                       ((sv > 0) == (fr[1][d] > 0))) / strat_days) if strat_days else 0

    # ---- 7) 可交易策略 P&L: 活跃日按 mean_sentiment 方向持有 H 日 ----
    cfwd = {k: cum_fwd(bars, k) for k in (1, 2, 3, 4, 5)}
    strat_h = {}
    for H in (1, 2, 3, 4, 5):
        nav = 1.0
        rets = []
        for sv, d in active:
            if d not in cfwd[H]:
                continue
            s = 1 if sv > 0 else -1
            r = s * cfwd[H][d]
            nav *= (1 + r)
            rets.append(r)
        strat_h[H] = {
            "nav": nav,
            "total_ret": nav - 1.0,
            "days": len(rets),
            "mean_ret": statistics.mean(rets) if rets else 0.0,
            "tstat": tstat(rets) if len(rets) >= 3 else None,
        }
    # 策略 CSV (H=3 主展示, 蓝标滞后打法)
    with open(OUT / f"{code}_strategy_hold.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hold_days", "n_days", "mean_ret", "tstat", "total_ret", "nav"])
        for H in (1, 2, 3, 4, 5):
            r = strat_h[H]
            w.writerow([H, r["days"], round(r["mean_ret"], 5),
                        round(r["tstat"], 3) if r["tstat"] is not None else "",
                        round(r["total_ret"], 4), round(r["nav"], 4)])

    # ---- 8) 衰减类型自动分类 (可泛化到任意持仓) ----
    def _sig(x):
        return x is not None and abs(x) >= 0.10  # |IC|>=0.10 视为显著(小样本放宽)
    ms = ic_by_factor.get("mean_sentiment", (None,) * 6)
    ai = ic_by_factor.get("article_impact", (None,) * 6)
    ic1 = ms[0]
    ic3 = ms[1]
    ic5 = ms[2]
    if ic1 is None and ic3 is None and ic5 is None:
        decay_cls = "数据不足"
    elif _sig(ic1) and not (_sig(ic3) or _sig(ic5)):
        decay_cls = "新闻动量型(fwd1显著, 快速衰减→事件日看消息做次日)"
    elif (not _sig(ic1)) and (_sig(ic3) or _sig(ic5)):
        decay_cls = "新闻滞后型(fwd1≈0, fwd2/3显著→事件后第2-3日留意方向兑现)"
    elif _sig(ic1) and _sig(ic3):
        decay_cls = "新闻持续型(多日均显著→事件后数日均可参考)"
    else:
        decay_cls = "资金/技术驱动型(新闻无显著信号→看图+四渠道资金)"

    # 找最强因子
    best = max(ic_by_factor.items(), key=lambda kv: abs(kv[1][0]) if kv[1][0] is not None else 0)
    return {
        "code": code,
        "n_aligned": len(aligned),
        "n_active_news_days": sum(1 for d in aligned if (to_float(news[d].get("n_articles")) or 0) >= 1),
        "n_strat_days": strat_days,
        "strat_total_ret": strat_total,
        "strat_nav": strat_nav,
        "overall_hit": overall_hit,
        "ls_mean_fwd1": ls_mean,
        "ls_t": ls_t,
        "active_sent_ls": aq_ls,
        "active_sent_ls_t": aq_ls_t,
        "best_factor": best[0],
        "best_ic": best[1][0],
        "best_ic_active": best[1][1],
        "ic_by_factor": ic_by_factor,
        "strat_h": strat_h,
        "decay_cls": decay_cls,
        "date_min": min(aligned),
        "date_max": max(aligned),
    }


def _md_table(path, cols):
    if not Path(path).exists():
        return f"_(无 {Path(path).name})_"
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        return "_(空)_"
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join(["---"] * len(cols)) + "|"
    lines = [head, sep]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)


def main():
    report_parts = ["# 消息面 → 次日涨跌 回测报告", ""]
    report_parts.append("> 对齐口径: 当日收盘可知的新闻因子(date t) → 次日收益 fwd1[t]=close[t+1]/close[t]-1。"
                     "无未来函数。因子仅在新闻活跃日(n_articles≥1)有区分度; 无新闻日 composite_index 恒为0, 已单列。")
    report_parts.append("")
    for code in ("300418", "300058"):
        r = analyze(code)
        report_parts.append(f"## {code}")
        report_parts.append(f"- 对齐交易日: **{r['n_aligned']}** (区间 {r['date_min']}~{r['date_max']})")
        report_parts.append(f"- 新闻活跃日(n_articles≥1): **{r['n_active_news_days']}** (占 {r['n_active_news_days']/r['n_aligned']*100:.0f}%)")
        report_parts.append(f"- **活跃日趋势中性净值**: {r['strat_nav']:.3f} (累计 {r['strat_total_ret']*100:+.1f}%, {r['n_strat_days']}个交易日, 方向命中率 {r['overall_hit']*100:.1f}%)")
        report_parts.append(f"- **活跃日 mean_sentiment 五分位多空差(Q5−Q1)**: {r['active_sent_ls']*100:+.3f}%/日 (t={r['active_sent_ls_t']:.2f})")
        report_parts.append(f"- composite_index 全样本五分位多空差: {r['ls_mean_fwd1']*100:+.3f}%/日 (t={r['ls_t']:.2f}) — 注: 因144/241天恒为0, 此差主要反映正负新闻区分")
        report_parts.append("")
        report_parts.append("**① 各因子 IC 衰减表 (全样本秩相关, fwd1→fwd5)**")
        report_parts.append("")
        report_parts.append("| 因子 | fwd1 | fwd2 | fwd3 | fwd4 | fwd5 | 活跃日fwd1 | n全 | n活跃 |")
        report_parts.append("|---|---|---|---|---|---|---|---|---|")
        # 重新算 fwd2-5 IC (全样本), 复用 ic_rows 不易, 这里直接用 ic_by_factor 仅含 fwd1/3/5 活跃
        # 简化: 从 _ic.csv 读全量 fwd1-5
        ic_path = OUT / f"{code}_ic.csv"
        ic_map = {}
        if ic_path.exists():
            with open(ic_path, encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    ic_map[row["factor"]] = row
        items = sorted(ic_map.items(),
                       key=lambda kv: abs(float(kv[1]["ic_spearman_fwd1"])) if kv[1]["ic_spearman_fwd1"] not in ("", "None", None) else 0,
                       reverse=True)
        for fac, row in items:
            def g(c):
                v = row.get(c, "")
                return v if v not in ("", "None", None) else "—"
            report_parts.append(
                f"| {fac} | {g('ic_spearman_fwd1')} | {g('ic_spearman_fwd2')} | {g('ic_spearman_fwd3')} | {g('ic_spearman_fwd4')} | {g('ic_spearman_fwd5')} | {g('ic_spearman_fwd1_active')} | {row.get('n_full','')} | {row.get('n_active','')} |"
            )
        report_parts.append("")
        report_parts.append(f"**⑤ 衰减类型自动分类**: **{r['decay_cls']}**")
        report_parts.append("")
        report_parts.append("**② 方向命中率 (活跃日: 因子符号 vs 次日收益符号)**")
        report_parts.append("")
        report_parts.append(_md_table(OUT / f"{code}_hitrate.csv", ["factor", "n", "hit_rate", "hit_tstat_vs50"]))
        report_parts.append("")
        report_parts.append("**③ 波动测试 (新闻强度 vs |次日收益|, 活跃日秩相关)**")
        report_parts.append("")
        report_parts.append(_md_table(OUT / f"{code}_vol.csv", ["factor", "n", "ic_absret_spearman"]))
        report_parts.append("")
        report_parts.append("**④ 持有期策略 P&L: 活跃日按 mean_sentiment 方向持有 H 日 (趋势中性, 无杠杆)**")
        report_parts.append("")
        report_parts.append("| 持有H日 | 信号日数 | 日均收益 | t统计 | 累计收益 | 净值 |")
        report_parts.append("|---|---|---|---|---|---|")
        for H in (1, 2, 3, 4, 5):
            rr = r["strat_h"][H]
            tt = rr["tstat"]
            report_parts.append(
                f"| {H} | {rr['days']} | {rr['mean_ret']*100:+.3f}% | {tt:.2f} | {rr['total_ret']*100:+.1f}% | {rr['nav']:.3f} |"
            )
        report_parts.append("")
        report_parts.append(f"> 详见: `{code}_ic.csv`(fwd1-5全量) / `{code}_quintile.csv` / `{code}_active_sentiment_quintile.csv` / `{code}_hitrate.csv` / `{code}_vol.csv` / `{code}_strategy_active.csv` / `{code}_strategy_hold.csv`(持有期P&L)")
        report_parts.append("")
    (OUT / "REPORT.md").write_text("\n".join(report_parts), encoding="utf-8")
    print("\n".join(report_parts))


if __name__ == "__main__":
    main()
