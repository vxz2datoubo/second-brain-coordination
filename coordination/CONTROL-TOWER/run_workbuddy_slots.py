#!/usr/bin/env python3
"""Read-only CLI for WorkBuddy plural slot projection and explicit selection.

This command never starts WorkBuddy, never mutates the registry, and never converts a
logical selection into process authority. It exists so CI/operators can mechanically
observe legal multi-slot ambiguity and prove that explicit selection succeeds.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


slots = _load("workbuddy_slots", "workbuddy_slots.py")
selection = _load("workbuddy_slot_selection", "workbuddy_slot_selection.py")


def _emit(payload: Any) -> None:
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-path", default=".")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="List projected WorkBuddy slots")
    mode.add_argument("--legacy-projection", action="store_true")
    mode.add_argument(
        "--resolve-execution-target",
        action="store_true",
        help="Resolve one logical slot. This does not authorize process start.",
    )
    parser.add_argument("--task-id")
    parser.add_argument("--worker-slot-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        slot_set = slots.load_workbuddy_slot_set(args.repo_path)
        if args.list:
            _emit(slot_set.as_dict())
            return 0
        if args.legacy_projection:
            _emit(slots.compatibility_legacy_projection(slot_set))
            return 0

        result = selection.select_workbuddy_slot(
            slot_set.slots,
            task_id=args.task_id,
            worker_slot_id=args.worker_slot_id,
        )
        _emit(result.as_dict())
        if result.status == selection.SELECTED:
            return 0
        if result.status == selection.AMBIGUOUS:
            return 3  # expected-safe legal multi-slot ambiguity
        if result.status == selection.NO_ELIGIBLE:
            return 4
        return 5
    except (slots.WorkBuddySlotError, selection.SlotSelectionError) as exc:
        _emit(
            {
                "schema": "WORKBUDDY_SLOT_CLI_ERROR/v1",
                "status": "FAIL_CLOSED",
                "error": str(exc),
                "process_start_authorized": False,
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
