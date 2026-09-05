"""Requirement-to-evidence completion auditing."""

from __future__ import annotations

from .canonical import seal_contract
from .contracts import (
    CompletionReceipt,
    CompletionStatus,
    ContractMeta,
    RequirementEvidence,
)


def audit_completion(
    meta: ContractMeta,
    *,
    requirements: tuple[str, ...],
    evidence: tuple[RequirementEvidence, ...],
    changed_files: tuple[str, ...] = (),
    tests: tuple[str, ...] = (),
    external_anchors: tuple[str, ...] = (),
    unknowns: tuple[str, ...] = (),
    findings: tuple[str, ...] = (),
    rollback: tuple[str, ...] = (),
) -> CompletionReceipt:
    if not requirements:
        raise ValueError("COMPLETION_REQUIREMENTS_REQUIRED")
    if len(set(requirements)) != len(requirements):
        raise ValueError("COMPLETION_REQUIREMENTS_DUPLICATE")
    evidence_by_id = {item.requirement_id: item for item in evidence}
    missing = tuple(item for item in requirements if item not in evidence_by_id)
    unproven = tuple(
        item
        for item in requirements
        if item in evidence_by_id and evidence_by_id[item].disposition != "PROVES"
    )
    extra = tuple(item for item in evidence_by_id if item not in requirements)
    audit_findings = list(findings)
    if missing:
        audit_findings.append("MISSING_REQUIREMENT_EVIDENCE:" + ",".join(missing))
    if unproven:
        audit_findings.append("UNPROVEN_REQUIREMENTS:" + ",".join(unproven))
    if extra:
        audit_findings.append("EXTRA_REQUIREMENT_EVIDENCE:" + ",".join(extra))

    if missing or unproven:
        status = CompletionStatus.PARTIAL
    elif unknowns or audit_findings:
        status = CompletionStatus.SUCCESS_WITH_FINDINGS
    else:
        status = CompletionStatus.SUCCESS_CLEAN

    receipt = CompletionReceipt(
        meta=meta,
        requirement_evidence=evidence,
        changed_files=changed_files,
        tests=tests,
        external_anchors=external_anchors,
        unknowns=unknowns,
        findings=tuple(audit_findings),
        rollback=rollback,
        completion_status=status,
    )
    return seal_contract(receipt)
