"""Offline fail-closed checks before an E47 receipt-only commit.

The validator deliberately consumes evidence supplied by a caller.  It does
not call GitHub, an App, a CLI, or any authority service.  Its narrow job is to
prevent a local receipt from being prepared when exact-head CI or the required
lifecycle evidence is absent, mismatched, incomplete, or still placeholder
text.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath

from .models import ValidationError, require_identifier, require_sha1
from .recoverable_lifecycle import LifecycleStage


class PreReceiptCode(str, Enum):
    READY = "READY"
    TESTED_HEAD_CI_MISSING = "TESTED_HEAD_CI_MISSING"
    TESTED_HEAD_CI_MISMATCH = "TESTED_HEAD_CI_MISMATCH"
    RECEIPT_HEAD_CI_MISSING = "RECEIPT_HEAD_CI_MISSING"
    RECEIPT_HEAD_CI_MISMATCH = "RECEIPT_HEAD_CI_MISMATCH"
    PYTHON_MATRIX_INCOMPLETE = "PYTHON_MATRIX_INCOMPLETE"
    STAGE_COVERAGE_INCOMPLETE = "STAGE_COVERAGE_INCOMPLETE"
    PLACEHOLDER_PRESENT = "PLACEHOLDER_PRESENT"
    RECEIPT_TOPOLOGY_INVALID = "RECEIPT_TOPOLOGY_INVALID"
    RECEIPT_SCOPE_INVALID = "RECEIPT_SCOPE_INVALID"


_REQUIRED_PYTHONS = frozenset({"3.11", "3.13"})
_RUNTIME_SUFFIXES = frozenset({".py", ".yaml", ".yml", ".toml", ".json"})
_RECEIPT_PREFIX = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/E47/"


@dataclass(frozen=True)
class ExactHeadCiEvidence:
    workflow: str
    head_sha1: str
    python_versions: frozenset[str]
    conclusion: str
    run_reference: str

    def __post_init__(self) -> None:
        require_identifier(self.workflow, "CI workflow")
        require_sha1(self.head_sha1, "CI head SHA")
        require_identifier(self.conclusion, "CI conclusion")
        # GitHub Actions run IDs are commonly all digits.  Prefixing the
        # opaque reference preserves the existing stable-identifier grammar
        # without pretending a provider-issued numeric ID is a route name.
        require_identifier(f"ci.{self.run_reference}", "CI run reference")
        if not self.python_versions:
            raise ValidationError("CI python version set must be nonempty")

    @property
    def successful_exact_matrix(self) -> bool:
        return self.conclusion == "success" and _REQUIRED_PYTHONS.issubset(self.python_versions)


@dataclass(frozen=True)
class ReceiptTopology:
    tested_head_sha1: str
    receipt_parent_sha1: str
    receipt_head_sha1: str
    receipt_changed_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.tested_head_sha1, "tested head SHA"),
            (self.receipt_parent_sha1, "receipt parent SHA"),
            (self.receipt_head_sha1, "receipt head SHA"),
        ):
            require_sha1(value, label)
        if not self.receipt_changed_paths:
            raise ValidationError("receipt commit must be nonempty")
        for path in self.receipt_changed_paths:
            if not isinstance(path, str) or not path or path.startswith("/") or ".." in PurePosixPath(path).parts:
                raise ValidationError("receipt changed path invalid")

    @property
    def is_receipt_only(self) -> bool:
        if self.receipt_parent_sha1 != self.tested_head_sha1:
            return False
        for path in self.receipt_changed_paths:
            suffix = PurePosixPath(path).suffix.lower()
            if not path.startswith(_RECEIPT_PREFIX) or suffix in _RUNTIME_SUFFIXES:
                return False
        return True


@dataclass(frozen=True)
class PreReceiptValidationInput:
    tested_head_sha1: str
    tested_head_ci: ExactHeadCiEvidence | None
    receipt_topology: ReceiptTopology | None = None
    receipt_head_ci: ExactHeadCiEvidence | None = None
    completed_stages: frozenset[LifecycleStage] = frozenset()
    text_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_sha1(self.tested_head_sha1, "pre-receipt tested head SHA")
        for text in self.text_evidence:
            if not isinstance(text, str):
                raise ValidationError("pre-receipt text evidence must be string")


def _has_placeholder(text_evidence: tuple[str, ...]) -> bool:
    markers = ("TODO", "TBD", "<PLACEHOLDER>", "[PLACEHOLDER]", "UNKNOWN_SHA")
    return any(marker in text.upper() for text in text_evidence for marker in markers)


def validate_pre_receipt(value: PreReceiptValidationInput, *, require_receipt_head: bool = False) -> PreReceiptCode:
    """Fail closed until exact test/receipt evidence satisfies E47 topology."""

    tested_ci = value.tested_head_ci
    if tested_ci is None:
        return PreReceiptCode.TESTED_HEAD_CI_MISSING
    if tested_ci.head_sha1 != value.tested_head_sha1:
        return PreReceiptCode.TESTED_HEAD_CI_MISMATCH
    if not tested_ci.successful_exact_matrix:
        return PreReceiptCode.PYTHON_MATRIX_INCOMPLETE
    if set(value.completed_stages) != set(LifecycleStage):
        return PreReceiptCode.STAGE_COVERAGE_INCOMPLETE
    if _has_placeholder(value.text_evidence):
        return PreReceiptCode.PLACEHOLDER_PRESENT

    topology = value.receipt_topology
    if topology is None:
        return PreReceiptCode.READY if not require_receipt_head else PreReceiptCode.RECEIPT_HEAD_CI_MISSING
    if not topology.is_receipt_only:
        return PreReceiptCode.RECEIPT_TOPOLOGY_INVALID if topology.receipt_parent_sha1 != value.tested_head_sha1 else PreReceiptCode.RECEIPT_SCOPE_INVALID
    if not require_receipt_head:
        return PreReceiptCode.READY
    receipt_ci = value.receipt_head_ci
    if receipt_ci is None:
        return PreReceiptCode.RECEIPT_HEAD_CI_MISSING
    if receipt_ci.head_sha1 != topology.receipt_head_sha1:
        return PreReceiptCode.RECEIPT_HEAD_CI_MISMATCH
    if not receipt_ci.successful_exact_matrix:
        return PreReceiptCode.PYTHON_MATRIX_INCOMPLETE
    return PreReceiptCode.READY
