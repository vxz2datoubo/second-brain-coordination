"""Run E59's bounded Windows descendant-tree canary and emit a safe receipt."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e59_runtime.process_tree import OwnedProcessTree, ResourceGate, ResourceViolation, descendant_root_program, resource_snapshot


def _run_case(gate: ResourceGate, name: str, *, root_exit_first: bool, cleanup: str) -> dict[str, object]:
    tree = OwnedProcessTree(f"E59-P0-{name}", gate=gate)
    if cleanup in {"exception", "ctrl_c"}:
        try:
            with tree:
                root = tree.spawn(descendant_root_program(grandchildren=2, root_exit_first=root_exit_first), purpose=name)
                tree.wait_for_descendants(root, minimum=2, timeout_seconds=3)
                if cleanup == "exception":
                    raise RuntimeError("E59_CONTROLLED_EXCEPTION")
                raise KeyboardInterrupt("E59_CONTROLLED_CTRL_C")
        except (RuntimeError, KeyboardInterrupt):
            report = tree.report()
            report["controlled_failure_observed"] = cleanup
            return report
    with tree:
        root = tree.spawn(descendant_root_program(grandchildren=2, root_exit_first=root_exit_first), purpose=name)
        tree.wait_for_descendants(root, minimum=2, timeout_seconds=3)
        if cleanup == "root_exit":
            tree.wait(root, timeout_seconds=3)
        elif cleanup == "timeout":
            try:
                tree.wait(root, timeout_seconds=0.01)
            except TimeoutError:
                pass
            except Exception as exc:
                if type(exc).__name__ != "TimeoutExpired":
                    raise
        tree.cleanup(cleanup)
        return tree.report()


def _mutex_contention_case() -> dict[str, object]:
    contender = ResourceGate("E59-P0-duplicate-daemon-contender")
    try:
        contender.acquire()
    except ResourceViolation as exc:
        return {"rejected": True, "reason": str(exc), "dual_agent_and_duplicate_daemon": True}
    finally:
        contender.release()
    raise RuntimeError("E59_MUTEX_CONTENTION_NOT_REJECTED")


def main() -> int:
    receipt: dict[str, object] = {
        "task_id": "CODEX-E59-P0-BOUNDED-DESCENDANT-CANARY",
        "status": "PASS",
        "cases": {},
        "historical_attribution": "HISTORICAL_ATTRIBUTION_UNRECOVERABLE",
        "current_prevention": "CURRENT_PREVENTION_EXPERIMENTALLY_VERIFIED_FOR_BOUNDED_CANARIES_ONLY",
    }
    try:
        receipt["preflight"] = resource_snapshot()
        with ResourceGate("E59-P0-shared", max_task_processes=4, max_shared_processes=8) as gate:
            receipt["cases"] = {
                "child_with_live_grandchildren": _run_case(gate, "live-grandchildren", root_exit_first=False, cleanup="normal"),
                "root_exits_first": _run_case(gate, "root-exits-first", root_exit_first=True, cleanup="root_exit"),
                "timeout_cleanup": _run_case(gate, "timeout", root_exit_first=False, cleanup="timeout"),
                "exception_cancellation_cleanup": _run_case(gate, "exception", root_exit_first=False, cleanup="exception"),
                "ctrl_c_cleanup": _run_case(gate, "ctrl-c", root_exit_first=False, cleanup="ctrl_c"),
                "repeated_launch_accumulation": {
                    "first": _run_case(gate, "repeat-first", root_exit_first=False, cleanup="normal"),
                    "second": _run_case(gate, "repeat-second", root_exit_first=False, cleanup="normal"),
                },
                "dual_agent_duplicate_daemon_contention": _mutex_contention_case(),
            }
    except BaseException as exc:  # receipt must preserve even unexpected canary failures
        receipt["status"] = "FAIL"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
        receipt["traceback"] = traceback.format_exc(limit=8)
    try:
        receipt["postflight"] = resource_snapshot()
    except BaseException as exc:
        receipt["status"] = "FAIL"
        receipt["postflight_error_type"] = type(exc).__name__
        receipt["postflight_error"] = str(exc)
    output = TASK_ROOT / "P0-BOUNDED-DESCENDANT-CANARY-RECEIPT.json"
    output.write_text(json.dumps(receipt, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
