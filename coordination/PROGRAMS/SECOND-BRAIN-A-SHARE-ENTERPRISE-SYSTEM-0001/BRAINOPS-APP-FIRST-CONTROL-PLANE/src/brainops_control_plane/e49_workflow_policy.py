"""Static policy validation for the E49 exact-head workflow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import argparse
import json
import sys


class E49WorkflowPolicyCode(str, Enum):
    READY = "READY"
    UNREADABLE = "UNREADABLE"
    MISSING_EXACT_HEAD = "MISSING_EXACT_HEAD"
    MISSING_REQUIRED_STEP = "MISSING_REQUIRED_STEP"
    MISSING_EXTERNAL_EVIDENCE_DIR = "MISSING_EXTERNAL_EVIDENCE_DIR"
    SELF_CERTIFYING_FINAL_RELEASE = "SELF_CERTIFYING_FINAL_RELEASE"


@dataclass(frozen=True)
class E49WorkflowPolicyResult:
    code: E49WorkflowPolicyCode
    findings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.code is E49WorkflowPolicyCode.READY


_EXACT_HEAD = "github.event.pull_request.head.sha || github.sha"
_EXACT_CHECKOUT_REF = "ref: ${{ github.event.pull_request.head.sha || github.sha }}"
_REQUIRED = (
    "brainops_control_plane.ci_identity",
    "brainops_control_plane.e49_workflow_policy",
    "brainops_control_plane.release_verifier",
    "brainops_control_plane.e49_mutation_harness",
    "python-version: [\"3.11\", \"3.13\"]",
    "IN_JOB_POLICY_AND_CURRENT_JOB_OBSERVATION_ONLY",
    "--mode pre_review",
)
_EXTERNAL_DIR = "E49_EVIDENCE_DIR=$RUNNER_TEMP/e49-"
_OUTPUTS = (
    '"$E49_EVIDENCE_DIR/e49-provider-pre-evidence.json"',
    '"$E49_EVIDENCE_DIR/e49-pre-review.json"',
    '"$E49_EVIDENCE_DIR/e49-mutation-evidence.json"',
)


def validate_e49_workflow(path: Path) -> E49WorkflowPolicyResult:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return E49WorkflowPolicyResult(E49WorkflowPolicyCode.UNREADABLE, ("workflow_unreadable",))
    if _EXACT_HEAD not in text or _EXACT_CHECKOUT_REF not in text:
        return E49WorkflowPolicyResult(
            E49WorkflowPolicyCode.MISSING_EXACT_HEAD,
            (_EXACT_HEAD, _EXACT_CHECKOUT_REF),
        )
    missing = tuple(item for item in _REQUIRED if item not in text)
    if missing:
        return E49WorkflowPolicyResult(E49WorkflowPolicyCode.MISSING_REQUIRED_STEP, missing)
    missing_outputs = tuple(item for item in (_EXTERNAL_DIR, *_OUTPUTS) if item not in text)
    if missing_outputs:
        return E49WorkflowPolicyResult(
            E49WorkflowPolicyCode.MISSING_EXTERNAL_EVIDENCE_DIR, missing_outputs
        )
    if "READY_FOR_INDEPENDENT_REVIEW" in text:
        return E49WorkflowPolicyResult(
            E49WorkflowPolicyCode.SELF_CERTIFYING_FINAL_RELEASE,
            ("workflow_may_not_self_certify_final_release",),
        )
    return E49WorkflowPolicyResult(E49WorkflowPolicyCode.READY)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    arguments = parser.parse_args(argv)
    result = validate_e49_workflow(Path(arguments.workflow))
    print(json.dumps({"code": result.code.value, "findings": list(result.findings)}, sort_keys=True))
    return 0 if result.ready else 1


if __name__ == "__main__":
    sys.exit(main())
