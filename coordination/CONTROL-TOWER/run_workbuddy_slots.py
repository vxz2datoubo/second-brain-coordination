from __future__ import annotations

import argparse
import json
from pathlib import Path

from workbuddy_slot_selection import select_workbuddy_slot, selection_witness
from workbuddy_slots import load_workbuddy_slots, validate_workbuddy_slots


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical WorkBuddy multi-slot registry and resolve a bounded target.")
    parser.add_argument("--repo-root", default="../..")
    parser.add_argument("--resolve-execution-target", action="store_true")
    parser.add_argument("--select-slot", default=None)
    parser.add_argument("--select-task", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    report = validate_workbuddy_slots(repo_root)
    exit_code = 0 if report["structural_check"] == "PASS" else 2

    selection_requested = bool(args.resolve_execution_target or args.select_slot is not None or args.select_task is not None)
    if selection_requested:
        if report["structural_check"] != "PASS":
            report["selection"] = {
                "status": "BLOCKED",
                "code": "WORKBUDDY_SLOT_SELECTION_REQUIRES_STRUCTURAL_PASS",
                "requested_worker_slot_id": args.select_slot,
                "requested_task_id": args.select_task,
                "selected_worker_slot_id": None,
                "selected_task_id": None,
                "candidate_worker_slot_ids": [],
                "execution_authority_granted": False,
                "runtime_exclusivity_proven": False,
                "detail": "Slot target resolution is unavailable because governed registry validation failed.",
            }
            exit_code = 3
        else:
            selection = select_workbuddy_slot(
                load_workbuddy_slots(repo_root),
                requested_worker_slot_id=args.select_slot,
                requested_task_id=args.select_task,
            )
            report["selection"] = selection_witness(selection)
            if selection.status != "SELECTED":
                exit_code = 3

    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
