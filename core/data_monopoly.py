"""
数据垄断引擎 v2 — 长期可迭代
基于 data/pull_manifest.json 配置, 自动拉取所有数据到本地
支持: 增量更新 / 失败重试 / 进度追踪 / 一键扩容
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.tushare_bridge import ts

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw', 'tushare')
MANIFEST = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'pull_manifest.json')
STATE_FILE = os.path.join(DATA_DIR, '_pull_state.json')
os.makedirs(DATA_DIR, exist_ok=True)

# ══════════════════════════════════════════
# 状态管理 — 知道什么拉了, 什么没拉
# ══════════════════════════════════════════
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"pulls": {}, "meta": {"started": datetime.now().isoformat()}}

def save_state(state):
    state["meta"]["updated"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def is_done(state, key):
    """检查某个拉取是否已完成"""
    return state["pulls"].get(key, {}).get("status") == "done"

def mark_done(state, key, count, size_bytes):
    state["pulls"][key] = {
        "status": "done",
        "count": count,
        "size_kb": size_bytes // 1024,
        "time": datetime.now().isoformat()
    }
    save_state(state)

def mark_failed(state, key, error):
    state["pulls"][key] = {"status": "failed", "error": str(error)[:200]}
    save_state(state)

# ══════════════════════════════════════════
# 通用拉取工具
# ══════════════════════════════════════════
def save_file(name, data):
    path = os.path.join(DATA_DIR, f'{name}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return path, len(json.dumps(data))

def pull_daily_range(getter, name, start, end, batch_days=90):
    """分批次拉日期范围, 合并去重。
    关键修正: 不再对"全失败→空[]"静默标done; 多数批次失败时抛异常,
    让调用方的 except 标记 failed(可见+可重试)。"""
    all_data = []
    current = datetime.strptime(start, '%Y%m%d')
    end_dt = datetime.strptime(end, '%Y%m%d')
    batches = 0
    fail_cnt = 0
    
    while current <= end_dt:
        batch_end = min(current + timedelta(days=batch_days), end_dt)
        s = current.strftime('%Y%m%d')
        e = batch_end.strftime('%Y%m%d')
        
        ok = False; batch = None
        for _attempt in range(2):  # 单批重试1次, 自愈瞬时超时
            try:
                batch = getter(s, e)
                ok = True
                break
            except Exception:
                if _attempt == 0:
                    time.sleep(1.0)
        batches += 1
        if ok:
            if batch:
                all_data.extend(batch)
            if batches % 20 == 0:
                print(f'  [{name}] {s[:6]}... 已拉{len(all_data)}条')
        else:
            fail_cnt += 1
            if fail_cnt <= 3 or fail_cnt % 20 == 0:
                print(f'  [{name}] {s}→{e} 失败')
        
        time.sleep(0.45)  # rate limit
        current = batch_end + timedelta(days=1)
    
    print(f'  [{name}] 完成 {batches}批 成功{len(all_data)}条 失败{fail_cnt}批')
    # 多数批次失败且零数据 → 视为拉取失败, 抛异常让调用方标 failed(不再静默空完成)
    if batches > 0 and fail_cnt > batches * 0.5 and len(all_data) == 0:
        raise RuntimeError(f"{name} 全部批次失败({fail_cnt}/{batches}), 代理可能限流/接口异常")
    return all_data

# ══════════════════════════════════════════
# STAGE 1: 股票级数据
# ══════════════════════════════════════════
def pull_stock_data(manifest, state):
    """拉取所有股票的历史数据"""
    stock_configs = manifest.get("stocks", {})
    
    for group_name, group in sorted(stock_configs.items(), key=lambda x: x[1].get("priority", 99)):
        stocks = group.get("list", [])
        apis = group.get("apis", [])
        note = group.get("note", "")
        
        if not stocks:
            continue
        
        print(f"\n{'='*50}")
        print(f"  📦 {group_name}: {len(stocks)}只票 — {note}")
        print(f"{'='*50}")
        
        for code in stocks:
            code_short = code.replace('.SZ','').replace('.SH','')
            
            for api in apis:
                key = f"stock_{code_short}_{api}"
                if is_done(state, key):
                    print(f'  ✓ {code_short} {api} (已拉)')
                    continue
                
                print(f'  ▼ {code_short} {api}...')
                try:
                    if api == "moneyflow":
                        getter = lambda start_date, end_date: ts.moneyflow(code, start_date, end_date)
                    elif api == "daily":
                        getter = lambda start_date, end_date: ts.daily(code, start_date, end_date)
                    elif api == "daily_basic":
                        getter = lambda start_date, end_date: ts.daily_basic(code, start_date, end_date)
                    elif api == "margin_detail":
                        getter = lambda start_date, end_date: ts.margin_detail(code, start_date, end_date)
                    elif api == "fina_indicator":
                        data = ts.fina_indicator(code)
                        path, size = save_file(f'{code_short}_{api}', data)
                        mark_done(state, key, len(data), size)
                        print(f'    ✅ {len(data)}条')
                        continue
                    elif api == "share_float":
                        data = ts.share_float(ts_code=code)
                        path, size = save_file(f'{code_short}_{api}', data)
                        mark_done(state, key, len(data), size)
                        print(f'    ✅ {len(data)}条')
                        continue
                    else:
                        print(f'    ⚠️ 未知API: {api}')
                        continue
                    
                    data = pull_daily_range(getter, f'{code_short}_{api}', '20100101', '20260711')
                    path, size = save_file(f'{code_short}_{api}', data)
                    mark_done(state, key, len(data), size)
                    
                except Exception as ex:
                    print(f'    ❌ {ex}')
                    mark_failed(state, key, ex)

# ══════════════════════════════════════════
# STAGE 2: 板块数据
# ══════════════════════════════════════════
def pull_sector_data(manifest, state):
    """拉取板块级数据 — 直接用 bridge 避免 lambda 参数问题"""
    sectors = manifest.get("sectors", {})
    
    from core.tushare_bridge import ts as tushare
    
    for name, cfg in sectors.items():
        key = f"sector_{name}"
        if is_done(state, key):
            print(f'✓ {name} (已拉)')
            continue
        
        print(f'\n  ▼ {name} — {cfg.get("note","")}')
        start = cfg.get("start", "20200101")
        batch_days = cfg.get("batch_months", 1) * 30
        
        # 直接调用 bridge API
        if name == "concept_flow":
            data = pull_daily_range(
                lambda s, e: tushare.moneyflow_cnt_ths(start_date=s, end_date=e),
                name, start, '20260711', batch_days)
        elif name == "industry_flow":
            data = pull_daily_range(
                lambda s, e: tushare.moneyflow_ind_ths(start_date=s, end_date=e),
                name, start, '20260711', batch_days)
        elif name == "limit_concept":
            data = pull_daily_range(
                lambda s, e: tushare.limit_cpt_list(start_date=s, end_date=e),
                name, start, '20260711', batch_days)
        else:
            continue
        
        path, size = save_file(name, data)
        mark_done(state, key, len(data), size)

# ══════════════════════════════════════════
# STAGE 3: 全市场数据
# ══════════════════════════════════════════
def _stage3_resume_path():
    return os.path.join(DATA_DIR, "_stage3_resume.json")

def load_resume():
    p = _stage3_resume_path()
    if os.path.exists(p):
        try:
            return json.load(open(p, "r", encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_resume(d):
    json.dump(d, open(_stage3_resume_path(), "w", encoding="utf-8"), ensure_ascii=False)

def pull_market_wide(manifest, state):
    """拉取全市场数据"""
    mw = manifest.get("market_wide", {})
    
    for name, cfg in mw.items():
        key = f"market_{name}"
        if is_done(state, key):
            print(f'✓ {name} (已拉)')
            continue
        
        api = cfg["api"]
        print(f'\n  ▼ {name} — {cfg.get("note","")}')
        
        if cfg.get("onetime"):
            if api == "stock_basic":
                data = ts.stock_basic()
            else:
                print(f'    ⚠️ 未知onetime API: {api}')
                continue
            path, size = save_file(name, data)
            mark_done(state, key, len(data), size)
            print(f'    ✅ {len(data)}条')
        else:
            getter_map = {
                "top_list": None,  # handled specially
                "limit_list": None,
            }
            if api == "top_list":
                # Day-by-day 健壮拉取: 超时重试 + 定期落盘 + 跳月保护 + 断点续拉(根治假活)
                resume = load_resume()
                rkey = "top_list"
                all_data = []
                fpath = os.path.join(DATA_DIR, name + ".json")
                if os.path.exists(fpath):
                    try:
                        all_data = json.load(open(fpath, "r", encoding="utf-8"))
                        print(f"    ↺ 续拉: 载入已有 {len(all_data)} 条", flush=True)
                    except Exception:
                        all_data = []
                fail_cnt = 0
                empty_streak = 0
                start_date = datetime(2020, 1, 1)
                rd = resume.get(rkey)
                d = (datetime.strptime(rd, "%Y%m%d") + timedelta(days=1)) if rd else start_date
                end = datetime(2026, 7, 11)
                last_dump = len(all_data)
                while d <= end:
                    ds = d.strftime('%Y%m%d')
                    items, ok = [], False
                    for _ in range(2):  # 超时/异常重试1次, 不傻等
                        try:
                            r = ts._call("top_list", {"trade_date": ds}, '')
                            items = r if r else []
                            ok = True
                            break
                        except Exception:
                            time.sleep(0.5)
                    if ok and items:
                        all_data.extend(items)
                        empty_streak = 0
                    elif ok:  # 正常空(周末/节假日), 不计入失败
                        empty_streak += 1
                    else:  # 请求异常才算失败
                        fail_cnt += 1
                        empty_streak += 1
                    if ok:
                        resume[rkey] = ds
                        save_resume(resume)
                    step = len(all_data) + fail_cnt
                    if d.day == 1 or step % 50 == 0:
                        print(f'    {ds} 累计{len(all_data)}条 失败{fail_cnt}天', flush=True)
                    if len(all_data) - last_dump >= 500:  # 防中断丢数据
                        save_file(name, all_data)
                        last_dump = len(all_data)
                        print(f'    💾 落盘 {len(all_data)}条 @ {ds}', flush=True)
                    if empty_streak > 100:  # 连续100天空 → 跳下月(异常/代理问题)
                        print(f'    ⚠️ 连续100天无数据 @ {ds}, 跳月', flush=True)
                        d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
                        empty_streak = 0
                        continue
                    d += timedelta(days=1)
                    time.sleep(0.35)
                total_days = (end - start_date).days + 1
                if fail_cnt > total_days * 0.5:
                    print(f'    ❌ 失败率过高({fail_cnt}/{total_days}), 不标记完成, 待代理恢复后重拉', flush=True)
                else:
                    save_file(name, all_data)
                    mark_done(state, key, len(all_data), 0)
                    print(f'    ✅ 总{len(all_data)}条 失败{fail_cnt}天')
            elif api == "limit_list":
                # 正确接口名是 limit_list_d (旧 limit_list 代理返回 40001 接口不存在)
                # 一次调用返回当天全部, 用每行最后字段 limit(U涨停/D跌停/Z炸板) 区分
                resume = load_resume()
                rkey = "limit_list"
                fup = os.path.join(DATA_DIR, "limit_up_all.json")
                fdn = os.path.join(DATA_DIR, "limit_down_all.json")
                fzb = os.path.join(DATA_DIR, "limit_zha_all.json")
                def _load_lst(fp):
                    try:
                        return json.load(open(fp, "r", encoding="utf-8")) if os.path.exists(fp) else []
                    except Exception:
                        return []
                all_up, all_dn, all_zb = _load_lst(fup), _load_lst(fdn), _load_lst(fzb)
                fail_cnt = 0
                empty_streak = 0
                start_date = datetime(2020, 1, 1)
                rd = resume.get(rkey)
                d = (datetime.strptime(rd, "%Y%m%d") + timedelta(days=1)) if rd else start_date
                end = datetime(2026, 7, 11)
                last_dump = len(all_up) + len(all_dn) + len(all_zb)
                while d <= end:
                    ds = d.strftime('%Y%m%d')
                    items, ok = [], False
                    for _ in range(2):
                        try:
                            r = ts._call("limit_list_d", {"trade_date": ds}, '')
                            items = r if r else []
                            ok = True
                            break
                        except Exception:
                            time.sleep(0.5)
                    if not ok:  # 请求异常才算失败
                        fail_cnt += 1
                        empty_streak += 1
                    elif items:
                        for row in items:
                            flag = row[-1] if row else None
                            if flag == 'U': all_up.append(row)
                            elif flag == 'D': all_dn.append(row)
                            elif flag == 'Z': all_zb.append(row)
                        empty_streak = 0
                        resume[rkey] = ds
                        save_resume(resume)
                    else:  # 正常空(周末/节假日)
                        empty_streak += 1
                        resume[rkey] = ds
                        save_resume(resume)
                    tot = len(all_up) + len(all_dn) + len(all_zb)
                    if d.day == 1:
                        print(f'    {ds} 涨{len(all_up)}炸{len(all_zb)}跌{len(all_dn)} 失败{fail_cnt}', flush=True)
                    if tot - last_dump >= 500:
                        save_file('limit_up_all', all_up)
                        save_file('limit_down_all', all_dn)
                        save_file('limit_zha_all', all_zb)
                        last_dump = tot
                        print(f'    💾 落盘 涨{len(all_up)}炸{len(all_zb)}跌{len(all_dn)} @ {ds}', flush=True)
                    if empty_streak > 100:
                        print(f'    ⚠️ 连续100天无数据 @ {ds}, 跳月', flush=True)
                        d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
                        empty_streak = 0
                        continue
                    d += timedelta(days=1)
                    time.sleep(0.35)
                total_days = (end - start_date).days + 1
                if fail_cnt > total_days * 0.5:
                    print(f'    ❌ 失败率过高({fail_cnt}/{total_days}), 不标记完成, 待代理恢复后重拉', flush=True)
                else:
                    save_file('limit_up_all', all_up)
                    save_file('limit_down_all', all_dn)
                    save_file('limit_zha_all', all_zb)
                    mark_done(state, key, len(all_up)+len(all_dn)+len(all_zb), 0)
                    print(f'    ✅ 涨停{len(all_up)}炸板{len(all_zb)}跌停{len(all_dn)} 失败{fail_cnt}天')

# ══════════════════════════════════════════
# STAGE 4: 概念映射 (最关键!)
# ══════════════════════════════════════════
def pull_concept_mappings(manifest, state):
    """构建 概念↔股票 双向映射"""
    mappings = manifest.get("mappings", {})
    
    for name, cfg in mappings.items():
        key = f"mapping_{name}"
        if is_done(state, key):
            print(f'✓ {name} (已拉)')
            continue
        
        if name == "concept_to_stocks":
            print(f'\n  ▼ 概念→成分股 映射...')
            # Load concept flow to get all codes
            flow_file = os.path.join(DATA_DIR, 'concept_flow.json')
            if not os.path.exists(flow_file):
                print('    ⚠️ 先拉 concept_flow 数据!')
                continue
            
            with open(flow_file, 'r', encoding='utf-8') as f:
                flow_data = json.load(f)
            
            concept_codes = sorted(set(r[1] for r in flow_data if len(r)>1))
            print(f'    {len(concept_codes)}个概念代码')
            
            concept_map = {}
            stock_map = {}
            done = 0
            fail_cnt = 0
            for code in concept_codes:
                try:
                    members = ts.ths_member(code)
                    if members:
                        stocks = [m[1] for m in members]
                        concept_map[code] = stocks
                        for s in stocks:
                            if s not in stock_map: stock_map[s] = []
                            stock_map[s].append(code)
                    done += 1
                    if done % 50 == 0:
                        print(f'    {done}/{len(concept_codes)} 失败{fail_cnt}')
                        save_file('concept_to_stocks', concept_map)
                        save_file('stock_to_concepts', stock_map)
                    time.sleep(0.3)
                except Exception as ex:
                    fail_cnt += 1
            
            save_file('concept_to_stocks', concept_map)
            save_file('stock_to_concepts', stock_map)
            mark_done(state, key, len(concept_map), 0)
            print(f'    ✅ {len(concept_map)}个概念→成分股 映射完成')
            
            # Print our holdings
            for code in ['300418.SZ', '300058.SZ']:
                concepts = stock_map.get(code, [])
                print(f'\n    {code}: {len(concepts)}个概念:')
                for c in concepts[:10]:
                    name_match = [r[2] for r in flow_data if r[1]==c]
                    nm = name_match[0] if name_match else '?'
                    print(f'      {c} → {nm}')
        
        elif name == "ths_hot":
            if cfg.get("daily_snapshot"):
                print(f'\n  ▼ 同花顺热榜快照...')
                hot_industry = ts.ths_hot(market="行业板块", is_new="Y")
                hot_concept = ts.ths_hot(market="概念板块", is_new="Y")
                save_file('ths_hot_industry', hot_industry)
                save_file('ths_hot_concept', hot_concept)
                mark_done(state, key, len(hot_industry)+len(hot_concept), 0)
                print(f'    ✅ 行业{len(hot_industry)} 概念{len(hot_concept)}')

# ══════════════════════════════════════════
# STAGE 5: 题材核心票扩容 (换仓无忧)
# ══════════════════════════════════════════
def expand_theme_stocks(manifest, state):
    """根据概念映射, 为每个核心题材拉TOP股票的moneyflow"""
    stock_map_file = os.path.join(DATA_DIR, 'stock_to_concepts.json')
    concept_map_file = os.path.join(DATA_DIR, 'concept_to_stocks.json')
    
    if not os.path.exists(concept_map_file):
        print('⚠️ 先跑 Stage 4 拉概念映射!')
        return
    
    flow_file = os.path.join(DATA_DIR, 'concept_flow.json')
    with open(flow_file, 'r', encoding='utf-8') as f:
        flow_data = json.load(f)
    with open(concept_map_file, 'r', encoding='utf-8') as f:
        concept_map = json.load(f)
    
    # 从 manifest 读取要扩容的主题
    theme_config = manifest.get("stocks", {}).get("theme_top20", {})
    themes = theme_config.get("themes", [])
    per_theme = theme_config.get("per_theme_stocks", 5)
    
    # 对每个主题, 找到概念代码
    all_stocks = set()
    concept_codes_map = {}  # name → code
    
    for r in flow_data:
        if len(r) > 2:
            concept_codes_map[r[2]] = r[1]
    
    for theme_name in themes:
        code = concept_codes_map.get(theme_name)
        if not code:
            print(f'  ⚠️ 找不到概念: {theme_name}')
            continue
        
        members = concept_map.get(code, [])
        print(f'  {theme_name}: {len(members)}只成分股 → 取TOP{per_theme}')
        all_stocks.update(members[:per_theme])
    
    print(f'\n  去重后: {len(all_stocks)}只需拉')
    
    # 拉每只股票的 moneyflow (只拉没有的)
    for code in sorted(all_stocks)[:50]:  # 首批50只
        code_short = code.replace('.SZ','').replace('.SH','')
        key = f"stock_{code_short}_moneyflow"
        if is_done(state, key):
            continue
        
        print(f'  ▼ {code_short} moneyflow...')
        try:
            data = pull_daily_range(
                lambda s, e: ts.moneyflow(code, s, e),
                f'{code_short}_mf', '20200101', '20260711'
            )
            path, size = save_file(f'{code_short}_moneyflow', data)
            mark_done(state, key, len(data), size)
        except Exception as ex:
            print(f'    ❌ {ex}')

# ══════════════════════════════════════════
# STAGE 6: 指数/大盘 (所有分析技能的地基)
# ══════════════════════════════════════════
def pull_index_data(manifest, state):
    """拉取核心指数日线 + daily_basic (PE/PB/市值/换手)"""
    idx_cfg = manifest.get("indices", {})
    indices = idx_cfg.get("list", ['000001.SH','000300.SH','399001.SZ','399006.SZ','000905.SH','000688.SH'])
    apis = idx_cfg.get("apis", ['daily','daily_basic'])
    print(f"\n{'='*50}\n  📊 指数/大盘: {len(indices)}只 × {apis}\n{'='*50}")
    for code in indices:
        code_short = code.replace('.SZ','').replace('.SH','')
        for api in apis:
            key = f"index_{code_short}_{api}"
            if is_done(state, key):
                print(f'  ✓ {code_short} {api} (已拉)')
                continue
            print(f'  ▼ {code} {api}...')
            try:
                if api == "daily":
                    getter = lambda s,e: ts._call("index_daily", {"ts_code":code,"start_date":s,"end_date":e})
                else:
                    getter = lambda s,e: ts._call("index_dailybasic", {"ts_code":code,"start_date":s,"end_date":e})
                data = pull_daily_range(getter, f'index_{code_short}_{api}', '20100101', '20260712')
                path, size = save_file(f'index_{code_short}_{api}', data)
                mark_done(state, key, len(data), size)
            except Exception as ex:
                print(f'    ❌ {ex}')
                mark_failed(state, key, ex)

# ══════════════════════════════════════════
# STAGE 7: 主题票补 daily + daily_basic (之前只拉了 moneyflow)
# ══════════════════════════════════════════
def expand_theme_basic(manifest, state):
    """从 state 找已有 moneyflow 的主题/其他票, 补 OHLCV + 估值"""
    theme_codes = set()
    for k in state["pulls"]:
        if k.startswith("stock_") and k.endswith("_moneyflow"):
            theme_codes.add(k[len("stock_"):-len("_moneyflow")])
    theme_codes -= {'300418','300058'}  # 核心票已全量
    print(f"\n{'='*50}\n  📦 主题票补 daily/daily_basic: {len(theme_codes)}只\n{'='*50}")
    for code in sorted(theme_codes):
        full = code + '.SH' if code.startswith('6') else code + '.SZ'
        kd = f"stock_{code}_daily"
        if not is_done(state, kd):
            try:
                data = pull_daily_range(lambda s,e: ts.daily(full, s, e), f'stock_{code}_daily', '20100101','20260712')
                _,size = save_file(f'stock_{code}_daily', data)
                mark_done(state, kd, len(data), size)
            except Exception as ex:
                mark_failed(state, kd, ex)
        kb = f"stock_{code}_daily_basic"
        if not is_done(state, kb):
            try:
                data = pull_daily_range(lambda s,e: ts.daily_basic(full, s, e), f'stock_{code}_daily_basic', '20100101','20260712')
                _,size = save_file(f'stock_{code}_daily_basic', data)
                mark_done(state, kb, len(data), size)
            except Exception as ex:
                mark_failed(state, kb, ex)

# ══════════════════════════════════════════
# STAGE 8: 北向资金持仓 (沪深港通)
# ══════════════════════════════════════════
def pull_north_holding(manifest, state):
    """北向持股 — 注: 本代理(gyzcloud)未开放 north_holding 接口, 探测后跳过"""
    # 探测代理是否支持 (硬化_call 会在 code!=0 时抛异常)
    try:
        ts._call("north_holding", {"ts_code":"300418.SZ","trade_date":"20260711"})
        avail = True
    except Exception as ex:
        avail = False
        print(f"\n{'='*50}\n  🌊 北向持仓: 跳过\n{'='*50}")
        print(f"  ⚠️ 代理(g yzcloud)未提供 north_holding 接口 ({ex}), Stage 8 跳过")
        print(f"  (北向数据需官方Tushare全量token或换源, 本次不拉)")
    if not avail:
        return
    codes = ['300418.SZ','300058.SZ']
    for k in state["pulls"]:
        if k.startswith("stock_") and k.endswith("_moneyflow"):
            cs = k[len("stock_"):-len("_moneyflow")]
            full = cs+'.SH' if cs.startswith('6') else cs+'.SZ'
            if full not in codes: codes.append(full)
    print(f"\n{'='*50}\n  🌊 北向持仓: {len(codes)}只\n{'='*50}")
    for code in codes:
        code_short = code.replace('.SZ','').replace('.SH','')
        key = f"north_{code_short}"
        if is_done(state, key):
            continue
        try:
            data = pull_daily_range(
                lambda s,e: ts._call("north_holding", {"ts_code":code,"start_date":s,"end_date":e}),
                f'north_{code_short}', '20170101', '20260712')
            _,size = save_file(f'north_{code_short}', data)
            mark_done(state, key, len(data), size)
        except Exception as ex:
            mark_failed(state, key, ex)

# ══════════════════════════════════════════
# STAGE 9: 核心持仓筹码 (股东户数 + cyq成本分布)
# ══════════════════════════════════════════
def pull_chip_data(manifest, state):
    """昆仑/蓝标 股东户数 + cyq_chips + cyq_perf"""
    for code in ['300418.SZ','300058.SZ']:
        code_short = code.replace('.SZ','').replace('.SH','')
        # 股东户数: 代理仅支持单日(end_date), 按月末采样拿历史序列
        kh = f"chip_{code_short}_holdernumber"
        if not is_done(state, kh):
            print(f'  ▼ {code_short} holdernumber (月末采样)...')
            try:
                samples = []
                d = datetime(2010,1,1); end = datetime(2026,7,12)
                while d <= end:
                    try:
                        rows = ts.stk_holdernumber(code, end_date=d.strftime('%Y%m%d'))
                        if rows: samples.extend(rows)
                    except Exception:
                        pass
                    d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
                    time.sleep(0.3)
                _,size = save_file(f"chip_{code_short}_holdernumber", samples)
                mark_done(state, kh, len(samples), size)
                print(f'    ✅ {len(samples)}条')
            except Exception as ex:
                mark_failed(state, kh, ex)
        # cyq 成本分布 (区间, 正常)
        for api,caller in [
            ('cyq_chips', lambda s,e: ts.cyq_chips(code, start_date=s, end_date=e)),
            ('cyq_perf', lambda s,e: ts.cyq_perf(code, start_date=s, end_date=e)),
        ]:
            key = f"chip_{code_short}_{api}"
            if is_done(state, key):
                continue
            print(f'  ▼ {code_short} {api}...')
            try:
                data = pull_daily_range(caller, f"chip_{code_short}_{api}", '20100101', '20260712')
                _,size = save_file(f"chip_{code_short}_{api}", data)
                mark_done(state, key, len(data), size)
            except Exception as ex:
                mark_failed(state, key, ex)

# ══════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════
def run(stage=None):
    manifest = json.load(open(MANIFEST, 'r', encoding='utf-8'))
    state = load_state()
    
    print("╔══════════════════════════════════════╗")
    print("║  数据垄断引擎 v2 — 长期可迭代       ║")
    print("╚══════════════════════════════════════╝")
    
    stages = {
        '1': ('持仓+主题票', lambda: pull_stock_data(manifest, state)),
        '2': ('板块资金流', lambda: pull_sector_data(manifest, state)),
        '3': ('全市场数据', lambda: pull_market_wide(manifest, state)),
        '4': ('概念映射', lambda: pull_concept_mappings(manifest, state)),
        '5': ('题材扩容', lambda: expand_theme_stocks(manifest, state)),
        '6': ('指数/大盘', lambda: pull_index_data(manifest, state)),
        '7': ('主题票补daily_basic', lambda: expand_theme_basic(manifest, state)),
        '8': ('北向资金持仓', lambda: pull_north_holding(manifest, state)),
        '9': ('核心持仓筹码', lambda: pull_chip_data(manifest, state)),
    }
    
    if stage and stage in stages:
        name, func = stages[stage]
        print(f"\n🚀 Stage {stage}: {name}")
        func()
    else:
        for s, (name, func) in stages.items():
            print(f"\n🚀 Stage {s}: {name}")
            try:
                func()
            except Exception as ex:
                print(f"  ❌ Stage {s} 失败: {ex}")
    
    # 最终统计
    total_size = sum(os.path.getsize(os.path.join(DATA_DIR, f)) 
                     for f in os.listdir(DATA_DIR) if f.endswith('.json') and not f.startswith('_'))
    state["meta"]["total_size_mb"] = total_size // 1024 // 1024
    state["meta"]["last_run"] = datetime.now().isoformat()
    save_state(state)
    
    print(f"\n🎉 {'全部' if not stage else 'Stage '+stage} 完成! 总数据: {total_size//1024//1024}MB")

if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else None
    run(stage)
