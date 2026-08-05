"""Fail-closed product validator for the one positive authority contract.

This module only inspects repository text.  It grants no authority and accepts
no caller-provided lifecycle evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import argparse
import json
import re
import sys


class AuthoritySurfaceCode(str, Enum):
    READY = "READY"
    INVALID_ROOT = "INVALID_ROOT"
    MISSING_MANDATORY_CHAIN = "MISSING_MANDATORY_CHAIN"
    PARALLEL_POSITIVE_AUTHORITY = "PARALLEL_POSITIVE_AUTHORITY"
    CALLER_MINTABLE_LIFECYCLE = "CALLER_MINTABLE_LIFECYCLE"
    ACTUAL_CLAIM_MUTATION_MISSING = "ACTUAL_CLAIM_MUTATION_MISSING"
    MIRROR_CLAIM_MUTATION = "MIRROR_CLAIM_MUTATION"
    REQUEST_BINDING_MISSING = "REQUEST_BINDING_MISSING"


@dataclass(frozen=True)
class AuthoritySurfaceResult:
    code: AuthoritySurfaceCode
    violations: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.code is AuthoritySurfaceCode.READY

    def document(self) -> dict[str, object]:
        return {"code": self.code.value, "violations": list(self.violations)}


_MANDATORY = (
    "src/brainops_control_plane/durable_authority.py",
    "src/brainops_control_plane/execution_lease.py",
)
_FORBIDDEN_FILES = ("recoverable_lifecycle.py",)
_FORBIDDEN_CLASS_SYMBOLS = (
    "RecoverableLifecycleAuthority",
    "LifecycleBinding",
    "TerminalEvidence",
)
_MANDATORY_ACTUAL_CLAIM_CALLS = (
    "self._claim_authority.attach_invocation_with_effect_permit(",
    "self._claim_authority.finalize_with_attested_terminal(",
)
_FORBIDDEN_MIRROR_CLAIM_SYMBOLS = ("ClaimSideRecord", "_mirror_claim", "mirror_claim")
_REQUIRED_REQUEST_BINDINGS = (
    '"claim_id": claim.claim_id',
    '"target": target.value',
    '"decision_digest": decision_digest',
)


def _capability_request_block(lease_text: str) -> str | None:
    """Return only the request-digest construction, never a file-wide match."""

    start = lease_text.find("        request_digest = canonical_hash(\n")
    if start < 0:
        return None
    end = lease_text.find("        try:\n            journal", start)
    return lease_text[start:end] if end >= 0 else None


def validate_single_positive_authority(program_root: Path) -> AuthoritySurfaceResult:
    """Validate the real package layout rather than a parallel state model."""

    if not program_root.is_dir():
        return AuthoritySurfaceResult(AuthoritySurfaceCode.INVALID_ROOT, ("program_root_missing",))
    missing = tuple(path for path in _MANDATORY if not (program_root / path).is_file())
    if missing:
        return AuthoritySurfaceResult(AuthoritySurfaceCode.MISSING_MANDATORY_CHAIN, missing)

    package = program_root / "src" / "brainops_control_plane"
    violations: list[str] = []
    for file_name in _FORBIDDEN_FILES:
        if (package / file_name).exists():
            violations.append(f"forbidden_positive_file:{file_name}")
    for source in sorted(package.glob("*.py")):
        if source.name == Path(__file__).name:
            continue
        text = source.read_text(encoding="utf-8")
        for symbol in _FORBIDDEN_CLASS_SYMBOLS:
            pattern = rf"^class\s+{re.escape(symbol)}\s*(?:\(|:)"
            if re.search(pattern, text, flags=re.MULTILINE):
                violations.append(f"forbidden_positive_symbol:{source.name}:{symbol}")
    if violations:
        code = (
            AuthoritySurfaceCode.CALLER_MINTABLE_LIFECYCLE
            if any("LifecycleBinding" in item for item in violations)
            else AuthoritySurfaceCode.PARALLEL_POSITIVE_AUTHORITY
        )
        return AuthoritySurfaceResult(code, tuple(violations))
    lease_text = (package / "execution_lease.py").read_text(encoding="utf-8")
    missing_calls = tuple(
        value for value in _MANDATORY_ACTUAL_CLAIM_CALLS if value not in lease_text
    )
    if missing_calls:
        return AuthoritySurfaceResult(
            AuthoritySurfaceCode.ACTUAL_CLAIM_MUTATION_MISSING,
            missing_calls,
        )
    mirror_symbols = tuple(
        value for value in _FORBIDDEN_MIRROR_CLAIM_SYMBOLS if value in lease_text
    )
    if mirror_symbols:
        return AuthoritySurfaceResult(
            AuthoritySurfaceCode.MIRROR_CLAIM_MUTATION,
            mirror_symbols,
        )
    request_block = _capability_request_block(lease_text)
    missing_request_bindings = (
        ("capability_request_digest_block",)
        if request_block is None
        else tuple(value for value in _REQUIRED_REQUEST_BINDINGS if value not in request_block)
    )
    if missing_request_bindings:
        return AuthoritySurfaceResult(
            AuthoritySurfaceCode.REQUEST_BINDING_MISSING,
            missing_request_bindings,
        )
    return AuthoritySurfaceResult(AuthoritySurfaceCode.READY)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-root", required=True)
    arguments = parser.parse_args(argv)
    result = validate_single_positive_authority(Path(arguments.program_root))
    print(json.dumps(result.document(), ensure_ascii=True, sort_keys=True))
    return 0 if result.ready else 1


if __name__ == "__main__":
    sys.exit(main())
