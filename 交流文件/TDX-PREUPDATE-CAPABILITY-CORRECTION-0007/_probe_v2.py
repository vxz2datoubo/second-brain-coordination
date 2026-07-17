# -*- coding: utf-8 -*-
"""TDX v1.0.4 运行时强制探针 — 先 tq.initialize(__file__) 再调 get_more_info"""
import sys, json, time, os, hashlib
sys.path.insert(0, r"F:/tongdaxin/PYPlugins/user")
sys.path.insert(0, r"F:/tongdaxin/PYPlugins/sys")

OUT = r"F:/aidanao/交流文件/TDX-PREUPDATE-CAPABILITY-CORRECTION-0007/probes"
os.makedirs(OUT, exist_ok=True)
RESULT = {"steps": [], "__file__": __file__, "python": sys.executable, "python_ver": sys.version}

def p(*args): RESULT["steps"].append({"t": round(time.time()-t0,3), "data": args})

t0 = time.time()
p("START")
try:
    import tqcenter
    from tqcenter import tq
    p("import_ok", tqcenter.__file__)

    # === Step 1: 检查方法存在性 ===
    methods = ["get_more_info","get_pricevol","formula_get_all","formula_get_info",
               "get_match_stkinfo","get_relation","get_gb_info","get_ipo_info",
               "download_file","get_trackzs_etf_info","send_message","send_warn"]
    for m in methods:
        exists = hasattr(tq, m)
        p("hasattr", m, exists)

    # === Step 2: 正确初始化 ===
    tq.initialize(__file__)
    p("initialize", "ok", f"run_id={tq.run_id}", f"initialized={tq._initialized}")

    # === Step 3: get_more_info 全量测试 ===
    codes = ["300418.SZ","300058.SZ","600519.SH","510300.SH"]
    for code in codes:
        try:
            t1 = time.time()
            data = tq.get_more_info(code)
            dt = round(time.time()-t1, 3)
            if isinstance(data, dict):
                keys = sorted(data.keys())
                # 定向请求L2字段
                l2_fields = ["L2TicNum","L2OrderNum","TotalBVol","TotalSVol","BCancel","SCancel",
                             "Zjl","Zjl_HB","OpenAmo","OpenZTBuy","Wtb","FzAmo","VOpenZAF"]
                l2_exist = {f: (f in data) for f in l2_fields}
                l2_vals = {f: data.get(f, "KEY_MISSING") for f in l2_fields}
                # save full raw
                fn = os.path.join(OUT, f"more_info_{code.replace('.','_')}.json")
                with open(fn,"w",encoding="utf-8") as f:
                    json.dump(data,f,ensure_ascii=False,indent=2)
                p("get_more_info", code, "ok", f"keys={len(keys)}", f"t={dt}s",
                  {"l2_exist":l2_exist, "l2_vals":l2_vals, "total_keys":keys[:30]})
            else:
                p("get_more_info", code, "empty_or_wrong_type", str(type(data)))
        except Exception as e:
            p("get_more_info", code, "FAIL", f"{type(e).__name__}: {e}")

    # === Step 4: get_market_data tick 验证 ===
    try:
        tick_ret = tq.get_market_data(stock_list=["300418.SZ"], period='tick', count=10)
        p("get_market_data_tick", "returned", str(type(tick_ret)), str(tick_ret)[:200])
    except Exception as e:
        p("get_market_data_tick", "FAIL", f"{type(e).__name__}: {e}")

    # === Step 5: close ===
    tq.close()
    p("close", "ok")

except Exception as e:
    import traceback
    p("FATAL", f"{type(e).__name__}: {e}", traceback.format_exc()[:1000])

RESULT["total_time"] = round(time.time()-t0, 3)
with open(os.path.join(OUT,"probe_result.json"),"w",encoding="utf-8") as f:
    json.dump(RESULT,f,ensure_ascii=False,indent=2)
print(json.dumps(RESULT,ensure_ascii=False,indent=2))
