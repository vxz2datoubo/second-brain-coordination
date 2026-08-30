"""Run a bounded, deterministic multi-session rehearsal with synthetic data only.

This is an evidence rehearsal for future local operations.  It measures no
production throughput and reads no customer material; it exercises independent
slot lifecycle, frame-version preconditions, and idempotent command retries in
a temporary workspace that is deleted at process exit.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


MIN_SESSION_COUNT = 1
MAX_SESSION_COUNT = 16


def _load_cli() -> Any:
    path = ROOT / "apps" / "cli" / "creativectl.py"
    spec = importlib.util.spec_from_file_location("creative_runtime_operations_rehearsal_cli", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load creativectl for operation rehearsal")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rehearse_operations(session_count: int = 8) -> dict[str, Any]:
    """Exercise independent synthetic sessions with stable, bounded metrics."""

    if not isinstance(session_count, int) or not MIN_SESSION_COUNT <= session_count <= MAX_SESSION_COUNT:
        raise ValueError(f"session_count must be an integer {MIN_SESSION_COUNT}..{MAX_SESSION_COUNT}")
    cli = _load_cli()
    with tempfile.TemporaryDirectory(prefix="creative-runtime-operations-rehearsal-") as directory:
        workspace = Path(directory)
        sessions: list[dict[str, Any]] = []
        for index in range(session_count):
            slot = f"load_{index:02d}"
            prefix = ["--workspace", str(workspace), "--slot", slot]
            initialized = cli.run([*prefix, "init", "--scenario", "night_signal"])
            frame = cli.run([*prefix, "frame"])
            first_command = "cmd_" + format(index, "020x")
            first = cli.run([*prefix, "choose", "listen", "--expected-frame-id", frame["frame_id"], "--command-id", first_command])
            retry = cli.run([*prefix, "choose", "listen", "--expected-frame-id", frame["frame_id"], "--command-id", first_command])
            after_listen = cli.run([*prefix, "frame"])
            second_command = "cmd_" + format(session_count + index, "020x")
            second = cli.run([*prefix, "choose", "approach", "--expected-frame-id", after_listen["frame_id"], "--command-id", second_command])
            timeline = cli.run([*prefix, "timeline"])
            if first["status"] != "chosen" or retry["status"] != "command_already_applied" or second["status"] != "chosen":
                raise RuntimeError("Synthetic operation rehearsal command lifecycle is not deterministic")
            if retry["current_frame_id"] != first["current_frame_id"] or len(timeline["entries"]) != 3:
                raise RuntimeError("Synthetic operation rehearsal retry or ledger count diverged")
            sessions.append(
                {
                    "slot_id": slot,
                    "initialized_status": initialized["status"],
                    "first_command_status": first["status"],
                    "retry_status": retry["status"],
                    "second_command_status": second["status"],
                    "event_count": len(timeline["entries"]),
                    "timeline_hash": timeline["timeline_hash"],
                    "final_scene_id": timeline["entries"][-1]["state"]["scene_id"],
                }
            )
        operations = cli.run(["--workspace", str(workspace), "operations"])
        if not operations["mutation_safe"] or operations["metrics"]["verified_slot_count"] != session_count:
            raise RuntimeError("Synthetic operation rehearsal operations report is not clean")
        return {
            "schema": "CreativeRuntimeSyntheticOperationsRehearsal/v1",
            "status": "synthetic_operations_rehearsal_verified",
            "session_count": session_count,
            "per_session_event_count": 3,
            "total_event_count": session_count * 3,
            "idempotent_retry_count": session_count,
            "independent_slot_count": len({item["slot_id"] for item in sessions}),
            "all_final_scenes": sorted({item["final_scene_id"] for item in sessions}),
            "operations_metrics": dict(operations["metrics"]),
            "sessions": sessions,
            "boundary": {
                "synthetic_only": True,
                "customer_data_present": False,
                "external_provider_called": False,
                "concurrency_benchmark": False,
                "production_capacity_claim": False,
            },
            "authority_note": "Lifecycle evidence only. This is not a production load benchmark or authorization for customer intake.",
        }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run a bounded synthetic multi-session creative-runtime operations rehearsal.")
    parser.add_argument("--session-count", type=int, default=8, help="Synthetic session count, bounded to 1..16 (default: 8).")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(rehearse_operations(args.session_count), ensure_ascii=False, sort_keys=True, indent=2))
    except (RuntimeError, ValueError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
