import hashlib
import inspect
import json
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path


TASK_ID = "TDX-L2-INDEPENDENT-FORENSIC-RUN-0005"
ROOT = Path(r"F:\aidanao")
RESULTS = ROOT / "coordination" / "RESULTS" / "TDX-L2-INDEPENDENT-FORENSIC-RUN-0005"
EVIDENCE = ROOT / "coordination" / "EVIDENCE" / "TDX-L2-INDEPENDENT-FORENSIC-0005"
TQ_USER = Path(r"F:\tongdaxin\PYPlugins\user")
TQ_FILE = TQ_USER / "tqcenter.py"
DLL_FILE = Path(r"F:\tongdaxin\PYPlugins\TPythClient.dll")
CALL_LEDGER = RESULTS / "CALL-LEDGER.jsonl"

FORBIDDEN_KEYWORDS = ("order", "cancel", "asset", "position", "account", "broker")
ALLOWED_CALLS = {"initialize", "get_market_snapshot", "get_market_data", "close"}


def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="milliseconds")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def append_ledger(method, result, allowed=True, notes=None):
    record = {
        "task_id": TASK_ID,
        "time": now_iso(),
        "phase": "M3A",
        "method": method,
        "allowed": bool(allowed),
        "forbidden_function": any(k in method.lower() for k in FORBIDDEN_KEYWORDS),
        "tongdaxin_write": False,
        "result": result,
    }
    if notes:
        record["notes"] = notes
    with open(CALL_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def safe_jsonable(obj):
    try:
        json.dumps(obj, ensure_ascii=False, default=str)
        return obj
    except Exception:
        return repr(obj)


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(TQ_USER))

    static_lines = []
    static_lines.append("# TDXQUANT-STATIC-SURFACE\n")
    static_lines.append(f"- generated_at: `{now_iso()}`")
    static_lines.append(f"- python: `{sys.executable}`")
    static_lines.append(f"- tqcenter.py: `{TQ_FILE}`")
    static_lines.append(f"- tqcenter_sha256: `{sha256(TQ_FILE)}`")
    static_lines.append(f"- TPythClient.dll: `{DLL_FILE}`")
    static_lines.append(f"- TPythClient_sha256: `{sha256(DLL_FILE)}`")

    init_result = {"ok": False}
    snapshot_result = None
    tick_result = None
    close_result = None
    legacy_aliases = {}

    try:
        import tqcenter
        from tqcenter import tq

        methods = []
        for name, obj in inspect.getmembers(tq):
            if name.startswith("_"):
                continue
            if callable(obj):
                try:
                    sig = str(inspect.signature(obj))
                except Exception:
                    sig = "(signature_unavailable)"
                methods.append({"name": name, "signature": sig})

        static_lines.append("\n## Public callable surface\n")
        for item in methods:
            marker = ""
            if any(k in item["name"].lower() for k in FORBIDDEN_KEYWORDS):
                marker = " FORBIDDEN_BY_RUN_POLICY"
            static_lines.append(f"- `{item['name']}{item['signature']}`{marker}")

        legacy_aliases = {
            "get_full_tick": hasattr(tq, "get_full_tick"),
            "get_report_data": hasattr(tq, "get_report_data"),
        }
        static_lines.append("\n## Legacy alias check\n")
        for key, value in legacy_aliases.items():
            static_lines.append(f"- `{key}`: `{value}`")

        method = "initialize"
        if method not in ALLOWED_CALLS:
            raise RuntimeError(f"blocked non-whitelisted call: {method}")
        tq.initialize(__file__)
        init_result = {"ok": True, "run_id": getattr(tq, "run_id", None), "run_mode": getattr(tq, "run_mode", None)}
        append_ledger(method, init_result)

        method = "get_market_snapshot"
        if method not in ALLOWED_CALLS:
            raise RuntimeError(f"blocked non-whitelisted call: {method}")
        snapshot_result = tq.get_market_snapshot("300418.SZ")
        append_ledger(method, {"symbol": "300418.SZ", "type": type(snapshot_result).__name__, "keys": list(snapshot_result.keys()) if isinstance(snapshot_result, dict) else None})

        method = "get_market_data"
        if method not in ALLOWED_CALLS:
            raise RuntimeError(f"blocked non-whitelisted call: {method}")
        try:
            tick_result = tq.get_market_data(
                field_list=[],
                stock_list=["300418.SZ"],
                period="tick",
                start_time="",
                end_time="",
                count=1,
                dividend_type="none",
                fill_data=False,
            )
            append_ledger(method, {"symbol": "300418.SZ", "period": "tick", "type": type(tick_result).__name__, "result_preview": safe_jsonable(tick_result)})
        except Exception as exc:
            tick_result = {"exception_type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(limit=3)}
            append_ledger(method, {"symbol": "300418.SZ", "period": "tick", "exception_type": type(exc).__name__, "message": str(exc)})

    except Exception as exc:
        init_result = {"ok": False, "exception_type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(limit=5)}
    finally:
        try:
            if "tq" in locals():
                method = "close"
                if method in ALLOWED_CALLS:
                    tq.close()
                    close_result = {"ok": True}
                    append_ledger(method, close_result)
        except Exception as exc:
            close_result = {"ok": False, "exception_type": type(exc).__name__, "message": str(exc)}
            append_ledger("close", close_result, allowed=True)

    (RESULTS / "TDXQUANT-SNAPSHOT-RAW.json").write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "generated_at": now_iso(),
                "symbol": "300418.SZ",
                "initialize": init_result,
                "legacy_aliases": legacy_aliases,
                "snapshot": safe_jsonable(snapshot_result),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    write_text(
        RESULTS / "TDXQUANT-TICK-TEST.md",
        "# TDXQUANT-TICK-TEST\n\n"
        f"- generated_at: `{now_iso()}`\n"
        "- method: `get_market_data(period='tick')`\n"
        "- symbol: `300418.SZ`\n"
        f"- result:\n\n```json\n{json.dumps(safe_jsonable(tick_result), ensure_ascii=False, indent=2, default=str)}\n```\n\n"
        "Capability note: this file only records whether the wrapper returned repeatable per-record tick data. "
        "A snapshot, callback, NowVol, aggregate amount, or method name is not sufficient for `TICK_VERIFIED`.\n",
    )

    write_text(RESULTS / "TDXQUANT-STATIC-SURFACE.md", "\n".join(static_lines) + "\n")


if __name__ == "__main__":
    main()
