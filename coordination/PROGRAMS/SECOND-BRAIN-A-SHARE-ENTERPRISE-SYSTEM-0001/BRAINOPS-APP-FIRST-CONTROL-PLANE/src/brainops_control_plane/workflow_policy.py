"""Executable policy checks for the E48 workflow text.

The validator proves policy structure only.  It does not claim that GitHub ran
an unpushed or locally mutated workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import argparse
import json
import sys


class WorkflowPolicyCode(str, Enum):
    READY = "READY"
    UNREADABLE = "UNREADABLE"
    MISSING_EXACT_HEAD = "MISSING_EXACT_HEAD"
    MISSING_REQUIRED_STEP = "MISSING_REQUIRED_STEP"


@dataclass(frozen=True)
class WorkflowPolicyResult:
    code: WorkflowPolicyCode
    findings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.code is WorkflowPolicyCode.READY


_EXACT_HEAD = "github.event.pull_request.head.sha || github.sha"
_EXACT_CHECKOUT_REF = "ref: ${{ github.event.pull_request.head.sha || github.sha }}"
_REQUIRED_STEPS = (
    "brainops_control_plane.ci_identity",
    "brainops_control_plane.release_gate",
    "brainops_control_plane.mutation_harness",
    "python-version: [\"3.11\", \"3.13\"]",
)


def validate_e48_workflow(path: Path) -> WorkflowPolicyResult:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return WorkflowPolicyResult(WorkflowPolicyCode.UNREADABLE, ("workflow_unreadable",))
    if _EXACT_HEAD not in text or _EXACT_CHECKOUT_REF not in text:
        return WorkflowPolicyResult(
            WorkflowPolicyCode.MISSING_EXACT_HEAD,
            (_EXACT_HEAD, _EXACT_CHECKOUT_REF),
        )
    missing = tuple(step for step in _REQUIRED_STEPS if step not in text)
    if missing:
        return WorkflowPolicyResult(WorkflowPolicyCode.MISSING_REQUIRED_STEP, missing)
    return WorkflowPolicyResult(WorkflowPolicyCode.READY)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    arguments = parser.parse_args(argv)
    result = validate_e48_workflow(Path(arguments.workflow))
    print(json.dumps({"code": result.code.value, "findings": list(result.findings)}, sort_keys=True))
    return 0 if result.ready else 1


if __name__ == "__main__":
    sys.exit(main())
