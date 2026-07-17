# -*- coding: utf-8 -*-
"""TdxQuant 最小运行时探针：仅 get_market_snapshot (报表/行情表数据)，禁止 order/subscribe。
保存完整原始返回到 0004/probe/。记录 TdxW PID 前后状态。"""
import sys, json, time, os, subprocess
sys.path.insert(0, r"F:/tongdaxin/PYPlugins/user")
sys.path.insert(0, r"F:/tongdaxin/PYPlugins/sys")
OUT = r"F:/aidanao/交流文件/WORKBUDDY-TDX-L2-STRONG-MODEL-REAUDIT-0004/probe"

def tdxw_alive():
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",
            "(Get-Process -Id 1628 -ErrorAction SilentlyContinue) -ne $null"],
            capture_output=True,text=True,timeout=10)
        return r.stdout.strip()=="True"
    except: return "check_failed"

result = {"steps":[],"tdxw_pid_before":tdxw_alive()}
t0 = time.time()
try:
    import tqcenter
    _doc = getattr(tqcenter,'__doc__',None) or ''
    result["steps"].append({"step":"import_tqcenter","ok":True,"t":round(time.time()-t0,2),
                            "version":_doc[:80]})
    from tqcenter import tq
    for code in ["300418.SZ","600519.SH"]:
        try:
            t1=time.time()
            snap = tq.get_market_snapshot(code)
            dt=round(time.time()-t1,2)
            with open(os.path.join(OUT,f"snapshot_{code.replace('.','_')}.json"),"w",encoding="utf-8") as f:
                if isinstance(snap,(dict,list)): json.dump(snap,f,ensure_ascii=False,indent=2)
                else: f.write(str(snap))
            keys = list(snap.keys()) if isinstance(snap,dict) else ("list_len_"+str(len(snap)) if isinstance(snap,list) else type(snap).__name__)
            result["steps"].append({"step":"get_market_snapshot","code":code,"ok":True,"t_sec":dt,
                                    "keys":keys[:60] if isinstance(keys,list) else keys})
        except Exception as e:
            result["steps"].append({"step":"get_market_snapshot","code":code,"ok":False,
                                    "err":f"{type(e).__name__}: {e}"})
    try:
        tq.close(); result["steps"].append({"step":"close","ok":True})
    except Exception as e:
        result["steps"].append({"step":"close","err":str(e)})
except Exception as e:
    import traceback
    result["steps"].append({"step":"import_tqcenter","ok":False,
                            "err":f"{type(e).__name__}: {e}","trace":traceback.format_exc()[:2000]})
result["total_time"]=round(time.time()-t0,2)
result["tdxw_pid_after"]=tdxw_alive()
with open(os.path.join(OUT,"probe_result.json"),"w",encoding="utf-8") as f:
    json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False,indent=2))
