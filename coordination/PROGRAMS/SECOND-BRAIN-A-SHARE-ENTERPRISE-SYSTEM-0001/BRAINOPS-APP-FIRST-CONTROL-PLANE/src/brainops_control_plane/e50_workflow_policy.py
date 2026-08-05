"""Static policy validation for E50's exact-head synthetic workflow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import argparse
import json
import sys


class E50WorkflowPolicyCode(str, Enum):
    READY = "READY"
    UNREADABLE = "UNREADABLE"
    MISSING_EXACT_HEAD = "MISSING_EXACT_HEAD"
    MISSING_REQUIRED_STEP = "MISSING_REQUIRED_STEP"
    MISSING_EXTERNAL_EVIDENCE_DIR = "MISSING_EXTERNAL_EVIDENCE_DIR"
    SELF_CERTIFYING_FINAL_RELEASE = "SELF_CERTIFYING_FINAL_RELEASE"


@dataclass(frozen=True)
class E50WorkflowPolicyResult:
    code: E50WorkflowPolicyCode
    findings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.code is E50WorkflowPolicyCode.READY


_EXACT_HEAD = "github.event.pull_request.head.sha || github.sha"
_EXACT_CHECKOUT_REF = "ref: ${{ github.event.pull_request.head.sha || github.sha }}"
_REQUIRED = (
    "brainops_control_plane.ci_identity",
    "brainops_control_plane.e50_workflow_policy",
    "brainops_control_plane.e50_mutation_harness",
    'python-version: ["3.11", "3.13"]',
    'python -m unittest discover -s tests -p "test_*.py" -q',
    "python -m unittest tests.test_e50_release_closure tests.test_e50_clean_clone_reproduction tests.test_e50_workflow_policy -q",
)
_EXTERNAL_DIR = "E50_EVIDENCE_DIR=$RUNNER_TEMP/e50-"
_OUTPUTS = (
    '"$E50_EVIDENCE_DIR/full-regression.txt"',
    '"$E50_EVIDENCE_DIR/e50-focused-tests.txt"',
    '"$E50_EVIDENCE_DIR/e50-mutation-evidence.json"',
)


def validate_e50_workflow(path: Path) -> E50WorkflowPolicyResult:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return E50WorkflowPolicyResult(E50WorkflowPolicyCode.UNREADABLE, ("workflow_unreadable",))
    if _EXACT_HEAD not in text or _EXACT_CHECKOUT_REF not in text:
        return E50WorkflowPolicyResult(
            E50WorkflowPolicyCode.MISSING_EXACT_HEAD,
            (_EXACT_HEAD, _EXACT_CHECKOUT_REF),
        )
    missing = tuple(item for item in _REQUIRED if item not in text)
    if missing:
        return E50WorkflowPolicyResult(E50WorkflowPolicyCode.MISSING_REQUIRED_STEP, missing)
    missing_outputs = tuple(item for item in (_EXTERNAL_DIR, *_OUTPUTS) if item not in text)
    if missing_outputs:
        return E50WorkflowPolicyResult(
            E50WorkflowPolicyCode.MISSING_EXTERNAL_EVIDENCE_DIR, missing_outputs
        )
    if "READY_FOR_INDEPENDENT_REVIEW" in text:
        return E50WorkflowPolicyResult(
            E50WorkflowPolicyCode.SELF_CERTIFYING_FINAL_RELEASE,
            ("workflow_may_not_self_certify_final_release",),
        )
    return E50WorkflowPolicyResult(E50WorkflowPolicyCode.READY)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    arguments = parser.parse_args(argv)
    result = validate_e50_workflow(Path(arguments.workflow))
    print(json.dumps({"code": result.code.value, "findings": list(result.findings)}, sort_keys=True))
    return 0 if result.ready else 1


if __name__ == "__main__":
    sys.exit(main())
