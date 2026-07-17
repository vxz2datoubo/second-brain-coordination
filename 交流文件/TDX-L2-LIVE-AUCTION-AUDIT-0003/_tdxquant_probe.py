import sys, json, traceback
sys.path.insert(0, r"F:/tongdaxin/PYPlugins/user")
sys.path.insert(0, r"F:/tongdaxin/PYPlugins/sys")
RESULT = {"step": [], "ok": False}
try:
    import tqcenter
    RESULT["step"].append("import_ok")
    # enumerate public callable on tq class
    from tqcenter import tq
    methods = [m for m in dir(tq) if not m.startswith("__")]
    RESULT["tq_public_methods"] = methods
    RESULT["step"].append("enum_ok")
    # read-only snapshot call (NO order/subscribe)
    try:
        snap = tq.get_market_snapshot(0, "300418")  # market=0 sz, code
        RESULT["snapshot_type"] = str(type(snap))
        RESULT["snapshot_head"] = str(snap)[:1500]
        RESULT["step"].append("snapshot_ok")
        RESULT["ok"] = True
    except Exception as e:
        RESULT["snapshot_error"] = f"{type(e).__name__}: {e}"
        RESULT["step"].append("snapshot_fail")
except Exception as e:
    RESULT["import_error"] = f"{type(e).__name__}: {e}"
    RESULT["trace"] = traceback.format_exc()[:2000]
print(json.dumps(RESULT, ensure_ascii=False))
