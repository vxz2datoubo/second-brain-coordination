"""Standard WorkBuddy return package builder.

Rule (TASK-BRIEF.yaml): "Define a standard return package (branch, head sha,
tests, findings, unknowns, telemetry) that never carries credential values."

This is the ONLY sanctioned shape in which a bridge worker reports back. It is
deliberately small: it carries enough for a verifier/reviewer to adjudicate and
NOTHING that could leak a secret or smuggle an out-of-band instruction.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from .contracts import BridgeBoundaryError, ReturnPackage
from .redaction import assert_no_secrets, redact

_MAX_ITEMS = 200


def _clean(items: Iterable[str], *, where: str) -> tuple[str, ...]:
    """Validate then redact.

    Order matters: we REJECT a credential-bearing entry rather than laundering
    it. Silently redacting would let a compromised worker keep reporting while
    its leak went unnoticed; failing closed forces an investigation.
    """
    out: list[str] = []
    for raw in items:
        original = str(raw)
        # Reject BEFORE redaction — a live credential is an incident, not noise.
        assert_no_secrets(original, where=where)
        text = redact(original).strip()
        if not text:
            continue
        assert_no_secrets(text, where=where)
        if len(text) > 2000:
            raise BridgeBoundaryError(f"{where} entry exceeds 2000 characters")
        out.append(text)
        if len(out) > _MAX_ITEMS:
            raise BridgeBoundaryError(f"{where} exceeds {_MAX_ITEMS} entries")
    return tuple(out)


def build_return_package(
    *,
    task_id: str,
    route_epoch: int | None,
    branch: str,
    head_sha: str | None = None,
    tests: Iterable[str] = (),
    findings: Iterable[str] = (),
    unknowns: Iterable[str] = (),
    changed_files: Iterable[str] = (),
    telemetry: Mapping[str, object] | None = None,
) -> ReturnPackage:
    """Build a redacted return package.

    Fails closed if any field would persist a credential-looking value.
    """
    if not task_id or not str(task_id).strip():
        raise BridgeBoundaryError("return package requires a non-empty task_id")
    if head_sha is not None:
        head = str(head_sha).strip()
        if head and (len(head) < 7 or len(head) > 64):
            raise BridgeBoundaryError(f"head_sha {head!r} is not a plausible git sha")
    else:
        head = None

    clean_telemetry: dict[str, object] = {}
    for key, value in dict(telemetry or {}).items():
        safe_key = redact(str(key))
        if isinstance(value, (int, float, bool)) or value is None:
            clean_telemetry[safe_key] = value
        else:
            clean_telemetry[safe_key] = redact(str(value))
    # Telemetry is metadata: refuse anything credential-shaped.
    assert_no_secrets(
        " ".join(f"{k}={v}" for k, v in clean_telemetry.items()),
        where="return package telemetry",
    )

    return ReturnPackage(
        task_id=redact(str(task_id)),
        route_epoch=route_epoch,
        branch=redact(str(branch)),
        head_sha=head,
        tests=_clean(tests, where="return package tests"),
        findings=_clean(findings, where="return package findings"),
        unknowns=_clean(unknowns, where="return package unknowns"),
        changed_files=_clean(changed_files, where="return package changed_files"),
        telemetry=clean_telemetry,
        redacted=True,
    )
