import json
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path


TASK_ID = "TDX-L2-INDEPENDENT-FORENSIC-RUN-0005"
ROOT = Path(r"F:\aidanao")
RESULTS = ROOT / "coordination" / "RESULTS" / "TDX-L2-INDEPENDENT-FORENSIC-RUN-0005"
TQ_USER = Path(r"F:\tongdaxin\PYPlugins\user")
CALL_LEDGER = RESULTS / "CALL-LEDGER.jsonl"
FORMULA_RESULTS = RESULTS / "FORMULA-L2-RESULTS.jsonl"

FORBIDDEN_KEYWORDS = ("order", "cancel", "asset", "position", "account", "broker")
SYMBOL = "300418.SZ"

FORMULAS = [
    {"formula_name": "L2_AMO", "formula_arg": "", "expected": "L2 amount aggregate candidate"},
    {"formula_name": "总委买量", "formula_arg": "", "expected": "aggregate bid order amount candidate"},
    {"formula_name": "总委卖量", "formula_arg": "", "expected": "aggregate ask order amount candidate"},
    {"formula_name": "总撤买量", "formula_arg": "", "expected": "aggregate bid cancellation amount candidate"},
    {"formula_name": "总撤卖量", "formula_arg": "", "expected": "aggregate ask cancellation amount candidate"},
    {"formula_name": "L2成交笔数", "formula_arg": "", "expected": "L2 trade-count aggregate candidate"},
    {"formula_name": "L2委托笔数", "formula_arg": "", "expected": "L2 order-count aggregate candidate"},
    {"formula_name": "集合竞价", "formula_arg": "", "expected": "call-auction formula-name candidate"},
]


def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="milliseconds")


def append_jsonl(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def append_ledger(method, result):
    append_jsonl(
        CALL_LEDGER,
        {
            "task_id": TASK_ID,
            "time": now_iso(),
            "phase": "M4",
            "method": method,
            "allowed": True,
            "forbidden_function": any(k in method.lower() for k in FORBIDDEN_KEYWORDS),
            "tongdaxin_write": False,
            "result": result,
        },
    )


def classify_formula_result(result):
    if result is None:
        return "NOT_AVAILABLE"
    if isinstance(result, dict):
        text = json.dumps(result, ensure_ascii=False, default=str)
        if result.get("ErrorId") not in (None, "0", 0):
            return "NOT_AVAILABLE"
        if "Error" in result or "error" in result:
            return "NOT_AVAILABLE"
        if any(key in text for key in ("时间", "Time", "Date", "Open", "Close")):
            return "TIME_SERIES"
        return "UNKNOWN"
    if isinstance(result, list):
        return "TIME_SERIES" if len(result) > 1 else "UNKNOWN"
    return "UNKNOWN"


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(TQ_USER))
    import tqcenter
    from tqcenter import tq

    try:
        tq.initialize(__file__)
        append_ledger("initialize", {"ok": True, "run_id": getattr(tq, "run_id", None)})
        for formula in FORMULAS:
            start = time.time()
            record = {
                "task_id": TASK_ID,
                "phase": "M4",
                "generated_at": now_iso(),
                "symbol_context": SYMBOL,
                "method": "formula_zb",
                **formula,
            }
            try:
                result = tq.formula_zb(formula_name=formula["formula_name"], formula_arg=formula["formula_arg"])
                record["duration_ms"] = int((time.time() - start) * 1000)
                record["result_type"] = type(result).__name__
                record["result"] = result
                record["classification"] = classify_formula_result(result)
                append_ledger("formula_zb", {"formula_name": formula["formula_name"], "classification": record["classification"], "duration_ms": record["duration_ms"]})
            except Exception as exc:
                record["duration_ms"] = int((time.time() - start) * 1000)
                record["exception_type"] = type(exc).__name__
                record["message"] = str(exc)
                record["traceback"] = traceback.format_exc(limit=3)
                record["classification"] = "NOT_AVAILABLE"
                append_ledger("formula_zb", {"formula_name": formula["formula_name"], "exception_type": type(exc).__name__, "message": str(exc), "duration_ms": record["duration_ms"]})
            append_jsonl(FORMULA_RESULTS, record)
    finally:
        try:
            tq.close()
            append_ledger("close", {"ok": True})
        except Exception as exc:
            append_ledger("close", {"ok": False, "exception_type": type(exc).__name__, "message": str(exc)})


if __name__ == "__main__":
    main()
