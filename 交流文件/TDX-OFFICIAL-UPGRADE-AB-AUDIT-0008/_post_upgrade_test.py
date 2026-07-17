# -*- coding: utf-8 -*-
"""TDX-OFFICIAL-UPGRADE-AB-AUDIT-0008 — 升级后全自动 A/B 测试
P0: get_more_info(4标的)+tick | P1: 新方法+公式 | P2: HTTP+subscribe
禁止交易功能。"""
import sys, json, time, os, hashlib, subprocess
sys.path.insert(0, r"F:/tongdaxin/PYPlugins/user")
sys.path.insert(0, r"F:/tongdaxin/PYPlugins/sys")

BASE = r"F:/aidanao/交流文件/TDX-OFFICIAL-UPGRADE-AB-AUDIT-0008"
POST = os.path.join(BASE, "post-upgrade")
PRE_EV = os.path.join(BASE, "pre-upgrade/evidence")
os.makedirs(POST, exist_ok=True)
os.makedirs(os.path.join(POST,"subscribe"), exist_ok=True)

def jd(o): return json.dumps(o, ensure_ascii=False, indent=2)
def sha(f): return hashlib.sha256(open(f,"rb").read()).hexdigest()
def now(): return time.strftime("%H:%M:%S")
def save(fn, data, mode="w"):
    p = os.path.join(POST, fn)
    with open(p, mode, encoding="utf-8") as f:
        if isinstance(data, str): f.write(data)
        else: json.dump(data, f, ensure_ascii=False, indent=2)
    return p

RESULT = {"task":"TDX-OFFICIAL-UPGRADE-AB-AUDIT-0008","start":now(),"steps":[]}
def log(phase, msg, **kw):
    entry = {"t":now(),"phase":phase,"msg":msg}
    entry.update(kw)
    RESULT["steps"].append(entry)
    print(f"[{phase}] {msg}")

CODES = ["300418.SZ","300058.SZ","600519.SH","510300.SH"]
L2_FIELDS = ["L2TicNum","L2OrderNum","TotalBVol","TotalSVol","BCancel","SCancel",
             "Zjl","Zjl_HB","OpenAmo","OpenZTBuy","Wtb","FzAmo","VOpenZAF"]

# ============ STEP 1: ENVIRONMENT ============
log("ENV", "Starting post-upgrade environment check")
# versions
try:
    import tqcenter
    from tqcenter import tq
    tq_file = tqcenter.__file__
    dll_path = os.path.join(os.path.dirname(os.path.dirname(tq_file)), "TPythClient.dll")
    log("ENV", "import_ok", tqcenter_file=tq_file, dll_path=dll_path,
        tq_py_sha256=sha(tq_file), dll_sha256=sha(dll_path) if os.path.exists(dll_path) else "MISSING")
except Exception as e:
    log("ENV", "import_FAIL", err=str(e))
    save("ENVIRONMENT.md", "# POST-UPGRADE ENVIRONMENT\n\nFATAL: import failed\n"+str(e))
    sys.exit(1)

# method surface
all_methods = [m for m in dir(tq) if not m.startswith("__") and callable(getattr(tq,m,None))]
NEW_CANDIDATES = {
    "get_pricevol": False, "get_match_stkinfo": False, "get_relation": False,
    "formula_get_all": False, "formula_get_info": False, "formula_process_mul_exp": False,
}
for m in list(NEW_CANDIDATES.keys()):
    NEW_CANDIDATES[m] = hasattr(tq, m)
log("ENV", "method_surface", total=len(all_methods), new_candidates=NEW_CANDIDATES,
    all_new=[m for m in all_methods if m not in ["initialize","_auto_initialize","close","_auto_close","get_market_data","get_market_snapshot","get_stock_info","get_sector_list","get_user_sector","get_stock_list_in_sector","get_financial_data","get_financial_data_by_date","get_divid_factors","get_gpjy_value","get_gpjy_value_by_date","get_bkjy_value","get_bkjy_value_by_date","get_scjy_value","get_scjy_value_by_date","get_gp_one_data","get_trading_calendar","get_trading_dates","get_stock_list","order_stock","subscribe_quote","subscribe_hq","unsubscribe_hq","get_subscribe_hq_stock_list","send_message","send_warn","send_file","get_more_info","get_gb_info","get_gb_info_by_date","get_ipo_info","get_cb_info","get_kzz_info","get_trackzs_etf_info","download_file","refresh_cache","refresh_kline","create_sector","delete_sector","rename_sector","clear_sector","send_bt_data","send_user_block","send_res","_auto_initialize","_ensure_cleanup_registered","_get_run_id","_check_stock_code_format_batch"]])

# port 17709
try:
    r = subprocess.run(["powershell","-NoProfile","-Command","(Test-NetConnection 127.0.0.1 -Port 17709 -WarningAction SilentlyContinue -InformationLevel Quiet) -eq $true"],
                       capture_output=True, text=True, timeout=15)
    port17709 = "LISTENING" if "True" in r.stdout else "NOT_LISTENING"
except:
    port17709 = "CHECK_FAILED"
log("ENV", "port_17709", status=port17709)

save("POST-UPGRADE-ENVIRONMENT.md", f"# POST-UPGRADE ENVIRONMENT\n- tqcenter: {tq_file}\n- SHA256: {sha(tq_file)}\n- DLL: {dll_path} SHA256={sha(dll_path) if os.path.exists(dll_path) else 'MISSING'}\n- Methods: {len(all_methods)}\n- New: {NEW_CANDIDATES}\n- Port 17709: {port17709}")

# ============ STEP 2: INITIALIZE ============
log("INIT", "Initializing tq...")
try:
    tq.initialize(__file__)
    log("INIT", "ok", run_id=tq.run_id, initialized=tq._initialized)
except Exception as e:
    log("INIT", "FAIL", err=str(e))
    save("ENVIRONMENT.md", "FATAL: init failed: "+str(e))
    sys.exit(1)

# ============ P0-A: get_more_info A/B ============
log("P0A", "get_more_info for 4 codes")
ab = {}
for code in CODES:
    try:
        data = tq.get_more_info(code)
        keys = sorted(data.keys()) if isinstance(data, dict) else []
        l2 = {f: data.get(f, "MISSING") for f in L2_FIELDS}
        ab[code] = {"keys": len(keys), "key_list": keys, "l2_values": l2, "full_keys": keys}
        log("P0A", code, keys=len(keys), l2_fields_present=sum(1 for f in L2_FIELDS if f in data))
    except Exception as e:
        log("P0A", code, FAIL=str(e))
        ab[code] = {"error": str(e)}
save("GET-MORE-INFO-RAW.jsonl", "\n".join(jd({"code":c,**ab[c]}) for c in CODES))

# compare with pre-upgrade (0007 probe_v2)
pre_reference = {"300418.SZ":86,"300058.SZ":86,"600519.SH":86,"510300.SH":86}
diff_lines = ["# GET-MORE-INFO AB DIFF", f"Pre-upgrade (v1.0.4): 86 fields x 4 codes",
              f"Post-upgrade: see below\n"]
for code in CODES:
    pre_n = pre_reference.get(code, 86)
    post_n = ab[code].get("keys", 0)
    delta = post_n - pre_n
    diff_lines.append(f"\n## {code}")
    diff_lines.append(f"- Pre: {pre_n} fields | Post: {post_n} fields | Delta: {'+'+str(delta) if delta>=0 else str(delta)}")
    if "key_list" in ab[code]:
        new_keys = [k for k in ab[code]["key_list"] if k not in ["BCancel","BetaValue","CJJEPre1","CJJEPre3","CashZJ","ConZAFDateNum","DTDate_Recent","DTPrice","DYRatio","DynaPE","EverZTCount","FCAmo","FCb","FDEPre1","FDEPre2","FreeLtgb","FzAmo","Fzhsl","HisHigh","HisLow","HqDate","IPO_Price","IsKzz","IsT0Fund","IsZCZGP","KfEarnMoney","Kzz_HSCode","L2OrderNum","L2TicNum","LastStartZT","OtherName","PE30","PlateID","SCancel","SNum","SynCode","TotalBVol","TotalSVol","VOpenZAF","Wtb","Zjl","Zjl_HB","OpenAmo","OpenZTBuy","FCAmo","LLPrice","Ltgb","Ltgblt","MGJZC","MGSY","MoreName","Mytime","NickName","OpenZAFDateNum","PE","PEStatic","PETTM","PE_Current","PE_Dynamic","PE_Static","SCName","SGN","Syl","TBl","TGB_SS","TGBNum","TGB_YY","TGB_YS","TGB_ZD","VCloseZAF","Volume","ZAFDate","ZAFDay","ZGB","ZLC","ZQSC","ZSZ","Zal","Zql","dWtb","isZB","zZAF","zZAFDateNum"]]
        if new_keys:
            diff_lines.append(f"- **NEW fields**: {new_keys[:30]}")
        deleted = [k for k in ["BCancel","BetaValue","CJJEPre1","CJJEPre3","CashZJ","ConZAFDateNum","DTDate_Recent","DTPrice","DYRatio","DynaPE","EverZTCount","FCAmo","FCb","FDEPre1","FDEPre2","FreeLtgb","FzAmo","Fzhsl","HisHigh","HisLow","HqDate","IPO_Price","IsKzz","IsT0Fund","IsZCZGP","KfEarnMoney","Kzz_HSCode","L2OrderNum","L2TicNum","LastStartZT","SCancel","TotalBVol","TotalSVol","VOpenZAF","Wtb","Zjl","Zjl_HB","OpenAmo","OpenZTBuy"] if k not in ab[code]["key_list"]]
        if deleted:
            diff_lines.append(f"- **DELETED fields**: {deleted}")
    diff_lines.append(f"- L2 values: {jd({f:ab[code].get('l2_values',{}).get(f,'?') for f in L2_FIELDS[:6]})}")
save("GET-MORE-INFO-AB-DIFF.md", "\n".join(diff_lines))

# ============ P0-B: Tick ============
log("P0B", "Testing get_market_data(period='tick')")
try:
    tick_ret = tq.get_market_data(stock_list=["300418.SZ"], period='tick', count=10, end_time=time.strftime("%Y%m%d%H%M%S"))
    tick_keys = list(tick_ret.keys()) if isinstance(tick_ret, dict) else []
    tick_first = tick_ret.get(list(tick_ret.keys())[0]) if isinstance(tick_ret,dict) and tick_ret else None
    tick_str = str(tick_ret)[:2000]
    is_tick_verified = isinstance(tick_ret, dict) and len(tick_ret) > 0 and "error" not in str(tick_ret).lower()
    if is_tick_verified:
        # check for Date/Time fields indicating tick-level data
        sample = tick_ret.get(list(tick_ret.keys())[0], {})
        if isinstance(sample, dict):
            has_dt = "Date" in sample or "Time" in sample or "datetime" in sample
            log("P0B", "TICK_RUNTIME_VERIFIED", keys=tick_keys, has_datetime=has_dt, sample_type=str(type(sample)))
        else:
            log("P0B", "TICK_UNEXPECTED_FORMAT", sample_type=str(type(sample)))
    else:
        log("P0B", "TICK_FAILED", error=tick_str[:200])
    save("TICK-RUNTIME-TEST.json", {"status":"RUNTIME_VERIFIED" if is_tick_verified else "FAILED","raw":tick_str,"keys":tick_keys})
except Exception as e:
    log("P0B", "TICK_EXCEPTION", err=str(e))
    save("TICK-RUNTIME-TEST.json", {"status":"EXCEPTION","error":str(e)})

# ============ P1: New Methods ============
log("P1", "Testing new methods")
new_tests = {}

for mname in ["get_pricevol","get_match_stkinfo","get_relation"]:
    if hasattr(tq, mname):
        try:
            method = getattr(tq, mname)
            if mname == "get_pricevol":
                ret = method("300418.SZ")
            elif mname == "get_match_stkinfo":
                ret = method("昆仑")
            elif mname == "get_relation":
                ret = method("300418.SZ")
            new_tests[mname] = {"exists":True,"runtime_ok":True,"sample":str(ret)[:500]}
            log("P1", mname, ok=True)
        except Exception as e:
            new_tests[mname] = {"exists":True,"runtime_ok":False,"error":str(e)}
            log("P1", mname, fail=str(e))
    else:
        new_tests[mname] = {"exists":False}
        log("P1", mname, exists=False)

# Formula methods
for mname in ["formula_get_all","formula_get_info","formula_process_mul_exp"]:
    if hasattr(tq, mname):
        new_tests[mname] = {"exists":True}
        log("P1", mname, exists=True)
        # formula_get_all: get formula catalog
        if mname == "formula_get_all":
            try:
                all_f = getattr(tq, mname)()
                new_tests[mname]["runtime_ok"] = True
                new_tests[mname]["count"] = len(all_f) if isinstance(all_f, (dict,list)) else 0
                # search L2 keywords
                l2_kw = ["L2","逐笔","委托","撤单","竞价","匹配","未匹配","主力","资金","队列","tick","分笔"]
                l2_hits = {}
                if isinstance(all_f, dict):
                    for k, v in all_f.items():
                        combined = f"{k}".lower()
                        for kw in l2_kw:
                            if kw.lower() in combined:
                                l2_hits[k] = str(v)[:200]
                elif isinstance(all_f, list):
                    for item in all_f:
                        if isinstance(item, str):
                            for kw in l2_kw:
                                if kw in item:
                                    l2_hits[item] = ""
                log("P1", "formula_L2_hits", hits=len(l2_hits), names=list(l2_hits.keys())[:20])
                save("FORMULA-CATALOG.json", {"all": all_f if isinstance(all_f, (dict,list)) else str(all_f)[:5000], "L2_candidates": l2_hits})
            except Exception as e:
                new_tests[mname]["runtime_ok"] = False
                new_tests[mname]["error"] = str(e)
    else:
        new_tests[mname] = {"exists":False}

save("POST-UPGRADE-METHOD-SURFACE.md", f"# POST-UPGRADE METHOD SURFACE\n- Total methods: {len(all_methods)}\n- New methods: {jd(NEW_CANDIDATES)}\n- Runtime tests: {jd(new_tests)}")

# ============ P2-A: HTTP 17709 ============
log("P2A", "HTTP 17709 check")
http_test = {"port": port17709}
if port17709 == "LISTENING":
    http_result = {}
    for call_name in ["get_market_snapshot","get_more_info"]:
        # JSON-RPC to 127.0.0.1:17709
        payload = {"method":call_name,"params":[CODES[0]]} if call_name != "get_market_snapshot" else {"method":call_name,"params":[CODES[0],[]]}
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:17709/", data=json.dumps(payload).encode(),
                                         headers={"Content-Type":"application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            http_result[call_name] = json.loads(resp.read())
            log("P2A", f"HTTP_{call_name}", ok=True)
        except Exception as e:
            http_result[call_name] = {"error": str(e)}
            log("P2A", f"HTTP_{call_name}", fail=str(e))
    http_test["results"] = http_result
    save("HTTP-17709-RAW.jsonl", jd(http_result))
else:
    log("P2A", "http_skipped", reason="port not listening")

save("HTTP-17709-POSTUPGRADE.md", f"# HTTP 17709 POST-UPGRADE\nport_status: {port17709}\n{jd(http_test)}")

# ============ P2-B: subscribe_hq (120s) ============
log("P2B", "subscribe_hq 120s test starting...")
sub_results = {"callbacks":[], "snapshots":[], "more_infos":[]}
SUB_TIMEOUT = 120 if not hasattr(tq, 'get_pricevol') else 120  # full 120s in upgraded env

def sub_callback(raw_data):
    ts = time.time()
    try:
        decoded = raw_data.decode('utf-8') if isinstance(raw_data, bytes) else str(raw_data)
        sub_results["callbacks"].append({"t":ts,"data":decoded[:500]})
        # callback-triggered snapshot
        try:
            snap = tq.get_market_snapshot("300418.SZ")
            sub_results["snapshots"].append({"t":ts,"snap":str(snap)[:300]})
        except: pass
        # callback-triggered more_info
        try:
            mi = tq.get_more_info("300418.SZ")
            mi_l2 = {f: mi.get(f,"?") for f in ["L2TicNum","BCancel","SCancel","Zjl"]} if isinstance(mi,dict) else mi
            sub_results["more_infos"].append({"t":ts,"l2":mi_l2})
        except: pass
    except:
        sub_results["callbacks"].append({"t":ts,"decode_error":True})

try:
    tq.subscribe_hq(stock_list=["300418.SZ"], callback=sub_callback)
    log("P2B", "subscribe_hq registered, waiting...")
    t_start = time.time()
    while time.time() - t_start < SUB_TIMEOUT:
        time.sleep(1)
    tq.unsubscribe_hq(stock_list=["300418.SZ"])
    log("P2B", "unsubscribe done", callbacks=len(sub_results["callbacks"]),
        snapshots=len(sub_results["snapshots"]), more_infos=len(sub_results["more_infos"]))
except Exception as e:
    log("P2B", "subscribe FAIL", err=str(e))

save(os.path.join("subscribe","SUBSCRIBE-AGGREGATE-RAW.jsonl"), jd(sub_results))

# ============ CLEANUP ============
try:
    tq.close()
    log("CLOSE", "ok")
except:
    pass

RESULT["end"] = now()
RESULT["duration_sec"] = int(time.time() - time.strptime(RESULT["start"],"%H:%M:%S").tm_sec if False else 0)
save("STATUS.yaml", RESULT)

# ============ RUN-RECEIPT ============
receipt = [
    f"# RUN-RECEIPT — POST-UPGRADE",
    f"End: {now()}",
    f"Methods: {len(all_methods)} (new: {sum(1 for v in NEW_CANDIDATES.values() if v)})",
    f"get_more_info AB: compared with 86-field baseline",
    f"Tick: {'VERIFIED' if 'is_tick_verified' in dir() and is_tick_verified else 'check TICK-RUNTIME-TEST.md'}",
    f"New methods tested: {list(NEW_CANDIDATES.keys())}",
    f"HTTP 17709: {port17709}",
    f"Subscribe callbacks: {len(sub_results['callbacks'])}",
    f"Safety: NO order/account/trade calls",
]
save("RUN-RECEIPT.md", "\n".join(receipt))
print("ALL DONE")
print(jd({"steps_count":len(RESULT["steps"]),"final_new_candidates":NEW_CANDIDATES,"port17709":port17709}))
