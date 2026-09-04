from __future__ import annotations

import argparse
import json
from pathlib import Path

from workbuddy_slot_selection import select_workbuddy_slot, selection_witness
from workbuddy_slots import normalize_workbuddy_slot, validate_workbuddy_slots


def resolve_selection_from_validated_report(
    report: dict,
    *,
    requested_worker_slot_id: str | None = None,
    requested_task_id: str | None = None,
) -> tuple[dict, int]:
    """Resolve only from the exact slot snapshot already emitted by validation.

    The registry is deliberately not reloaded here.  A later registry mutation
    therefore cannot be combined with a structural PASS from an earlier state.
    Selection remains identity-only and grants no execution/runtime authority.
    """

    if report.get("structural_check") != "PASS":
        return {
            "status": "BLOCKED",
            "code": "WORKBUDDY_SLOT_SELECTION_REQUIRES_STRUCTURAL_PASS",
            "requested_worker_slot_id": requested_worker_slot_id,
            "requested_task_id": requested_task_id,
            "selected_worker_slot_id": None,
            "selected_task_id": None,
            "candidate_worker_slot_ids": [],
            "execution_authority_granted": False,
            "runtime_exclusivity_proven": False,
            "detail": "Slot target resolution is unavailable because governed registry validation failed.",
        }, 3

    raw_slots = report.get("slots")
    if not isinstance(raw_slots, list) or not all(isinstance(item, dict) for item in raw_slots):
        return {
            "status": "BLOCKED",
            "code": "VALIDATED_WORKBUDDY_SLOT_SNAPSHOT_MALFORMED",
            "requested_worker_slot_id": requested_worker_slot_id,
            "requested_task_id": requested_task_id,
            "selected_worker_slot_id": None,
            "selected_task_id": None,
            "candidate_worker_slot_ids": [],
            "execution_authority_granted": False,
            "runtime_exclusivity_proven": False,
            "detail": "The validation report does not contain a usable exact slot snapshot.",
        }, 3

    validated_slots = [normalize_workbuddy_slot(item) for item in raw_slots]
    selection = select_workbuddy_slot(
        validated_slots,
        requested_worker_slot_id=requested_worker_slot_id,
        requested_task_id=requested_task_id,
    )
    return selection_witness(selection), (0 if selection.status == "SELECTED" else 3)


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
        selection, selection_exit = resolve_selection_from_validated_report(
            report,
            requested_worker_slot_id=args.select_slot,
            requested_task_id=args.select_task,
        )
        report["selection"] = selection
        exit_code = selection_exit if selection_exit else exit_code

    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
