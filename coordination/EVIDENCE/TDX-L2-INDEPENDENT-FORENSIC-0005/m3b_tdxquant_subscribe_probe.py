import hashlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path


TASK_ID = "TDX-L2-INDEPENDENT-FORENSIC-RUN-0005"
ROOT = Path(r"F:\aidanao")
RESULTS = ROOT / "coordination" / "RESULTS" / "TDX-L2-INDEPENDENT-FORENSIC-RUN-0005"
EVIDENCE = ROOT / "coordination" / "EVIDENCE" / "TDX-L2-INDEPENDENT-FORENSIC-0005"
TQ_USER = Path(r"F:\tongdaxin\PYPlugins\user")
CALL_LEDGER = RESULTS / "CALL-LEDGER.jsonl"
SUBSCRIBE_RAW = RESULTS / "TDXQUANT-SUBSCRIBE-RAW.jsonl"

FORBIDDEN_KEYWORDS = ("order", "cancel", "asset", "position", "account", "broker")
ALLOWED_CALLS = {"initialize", "subscribe_hq", "get_market_snapshot", "get_subscribe_hq_stock_list", "unsubscribe_hq", "close"}
SYMBOL = "300418.SZ"
RUN_SECONDS = 120


def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="milliseconds")


def append_jsonl(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def append_ledger(method, result, allowed=True, notes=None):
    record = {
        "task_id": TASK_ID,
        "time": now_iso(),
        "phase": "M3B",
        "method": method,
        "allowed": bool(allowed),
        "forbidden_function": any(k in method.lower() for k in FORBIDDEN_KEYWORDS),
        "tongdaxin_write": False,
        "result": result,
    }
    if notes:
        record["notes"] = notes
    append_jsonl(CALL_LEDGER, record)


def hash_text(text):
    if isinstance(text, bytes):
        data = text
    else:
        data = str(text).encode("utf-8", errors="replace")
    return hashlib.sha256(data).hexdigest()


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(TQ_USER))

    callback_state = {"seq": 0, "last_perf_ns": None, "first_perf_ns": None}
    summary = {
        "task_id": TASK_ID,
        "symbol": SYMBOL,
        "generated_at": now_iso(),
        "run_seconds": RUN_SECONDS,
        "initialize": None,
        "subscribe_result": None,
        "subscribe_list_result": None,
        "snapshot_samples": [],
        "callback_count": 0,
        "callback_interval_ms_min": None,
        "callback_interval_ms_max": None,
        "callback_interval_ms_avg": None,
        "error": None,
        "closed": False,
    }

    intervals = []

    def callback(payload):
        perf_ns = time.perf_counter_ns()
        now = now_iso()
        seq = callback_state["seq"] + 1
        callback_state["seq"] = seq
        if callback_state["first_perf_ns"] is None:
            callback_state["first_perf_ns"] = perf_ns
        if callback_state["last_perf_ns"] is not None:
            intervals.append((perf_ns - callback_state["last_perf_ns"]) / 1_000_000)
        callback_state["last_perf_ns"] = perf_ns

        record = {
            "task_id": TASK_ID,
            "phase": "M3B",
            "symbol": SYMBOL,
            "seq": seq,
            "receive_time": now,
            "perf_counter_ns": perf_ns,
            "payload_type": type(payload).__name__,
            "payload_sha256": hash_text(payload),
            "payload_raw": payload,
        }
        try:
            record["payload_json"] = json.loads(payload) if isinstance(payload, str) else None
        except Exception as exc:
            record["payload_json_error"] = f"{type(exc).__name__}: {exc}"
        append_jsonl(SUBSCRIBE_RAW, record)

    try:
        import tqcenter
        from tqcenter import tq

        method = "initialize"
        tq.initialize(__file__)
        summary["initialize"] = {"ok": True, "run_id": getattr(tq, "run_id", None), "run_mode": getattr(tq, "run_mode", None)}
        append_ledger(method, summary["initialize"])

        method = "subscribe_hq"
        result = tq.subscribe_hq([SYMBOL], callback=callback)
        summary["subscribe_result"] = result
        append_ledger(method, {"symbol": SYMBOL, "result_type": type(result).__name__, "result": result})

        method = "get_subscribe_hq_stock_list"
        try:
            sub_list = tq.get_subscribe_hq_stock_list()
        except Exception as exc:
            sub_list = {"exception_type": type(exc).__name__, "message": str(exc)}
        summary["subscribe_list_result"] = sub_list
        append_ledger(method, {"result": sub_list})

        start = time.monotonic()
        next_snapshot_at = 0
        while time.monotonic() - start < RUN_SECONDS:
            elapsed = time.monotonic() - start
            if elapsed >= next_snapshot_at:
                method = "get_market_snapshot"
                try:
                    snap = tq.get_market_snapshot(SYMBOL)
                    sample = {
                        "receive_time": now_iso(),
                        "elapsed_sec": round(elapsed, 3),
                        "keys": list(snap.keys()) if isinstance(snap, dict) else None,
                        "snapshot": snap,
                    }
                    summary["snapshot_samples"].append(sample)
                    append_ledger(method, {"symbol": SYMBOL, "elapsed_sec": round(elapsed, 3), "keys": sample["keys"]})
                except Exception as exc:
                    append_ledger(method, {"symbol": SYMBOL, "exception_type": type(exc).__name__, "message": str(exc)})
                next_snapshot_at += 30
            time.sleep(0.25)

    except Exception as exc:
        summary["error"] = {"exception_type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(limit=5)}
    finally:
        try:
            if "tq" in locals():
                method = "unsubscribe_hq"
                try:
                    result = tq.unsubscribe_hq([SYMBOL])
                    append_ledger(method, {"symbol": SYMBOL, "result_type": type(result).__name__, "result": result})
                except Exception as exc:
                    append_ledger(method, {"symbol": SYMBOL, "exception_type": type(exc).__name__, "message": str(exc)})
                method = "close"
                tq.close()
                summary["closed"] = True
                append_ledger(method, {"ok": True})
        except Exception as exc:
            append_ledger("close", {"ok": False, "exception_type": type(exc).__name__, "message": str(exc)})

    summary["callback_count"] = callback_state["seq"]
    if intervals:
        summary["callback_interval_ms_min"] = min(intervals)
        summary["callback_interval_ms_max"] = max(intervals)
        summary["callback_interval_ms_avg"] = sum(intervals) / len(intervals)
    append_jsonl(SUBSCRIBE_RAW, {"task_id": TASK_ID, "phase": "M3B_SUMMARY", **summary})


if __name__ == "__main__":
    main()
