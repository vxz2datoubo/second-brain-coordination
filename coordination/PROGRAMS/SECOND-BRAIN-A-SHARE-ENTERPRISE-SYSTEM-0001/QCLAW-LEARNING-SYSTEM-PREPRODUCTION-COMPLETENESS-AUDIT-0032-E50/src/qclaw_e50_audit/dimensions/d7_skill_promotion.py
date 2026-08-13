"""D7 audit: skill learning + promotion anti-forgery (E50 R3).

R3 mandatory (GPT review 4922729153, finding E50-R2-B03):
- E66 knowledge-promotion approval anti-forgery belongs under D9, NOT D7.
- D7 must audit a REAL canonical skill-learning/promotion subsystem:
  candidate -> experimental -> formal transitions bound to independent test
  receipts + rollback. If absent, report PARTIAL/BLOCKED/NOT_IMPLEMENTED.

Truthful findings (authoritative tree):
- coordination/SKILLS/*.yaml is a governance registry with an explicit
  maturity_state_machine (DISCOVERED -> ... -> CANDIDATE_SKILL_REGISTERED ->
  RESEARCH_VALIDATED -> CONTRACTED -> IMPLEMENTED -> A_SHARE_BACKTESTED ->
  SHADOW_VALIDATED -> VALIDATED_RESEARCH_CAPABILITY) and per-skill
  maturity/status labels. It declares lifecycle STAGES but is a DATA
  registry, not an executable promotion runtime.
- PHASE-1/tests/contract_validation.py is the only executable lifecycle
  gate: it validates a shared envelope's `status` against
  {candidate, approved, rejected, superseded, quarantined, experimental,
  active} and enforces candidate-cannot-write-authority + human_approval_ref
  for irreversible change. This is a promotion SAFETY GATE, not a full
  candidate->experimental->formal transition engine with independent test
  receipts.

Conclusion: there is NO executable skill-learning/promotion runtime that
binds candidate->experimental->formal transitions to independent test
receipts + rollback. The subsystem is PARTIAL (registry + safety gate only).
"""
from __future__ import annotations

import re
from .. import authoritative as access
from ..evidence_matrix import (
    DimensionVerdict, Evidence,
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
    VERDICT_NOT_AVAILABLE,
)

access.setup_import_path()


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _load_phase1_contract_validation():
    """Import the authoritative PHASE-1 contract_validation module by path.

    It is a test-module (not a package), so import it by spec with a stable
    module name to avoid polluting sys.modules."""
    import importlib.util
    path = access.REPO_ROOT / "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-1/tests/contract_validation.py"
    spec = importlib.util.spec_from_file_location("_e50_p1_contract_validation", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def _read_skills_yaml():
    skills_dir = access.REPO_ROOT / "coordination/SKILLS"
    out = []
    if not skills_dir.is_dir():
        return out
    for p in sorted(skills_dir.glob("*.yaml")):
        try:
            out.append(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
    return out


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    # 1. Skill registry declares an explicit maturity state machine
    yamls = _read_skills_yaml()
    has_state_machine = any(
        "maturity_state_machine" in y and "CANDIDATE_SKILL_REGISTERED" in y
        for y in yamls
    )
    evidence.append(_check(
        "d7.skill_registry_maturity_state_machine",
        "Skill registry declares an explicit maturity/lifecycle state machine",
        has_state_machine,
        detail=f"skill yaml files read={len(yamls)}",
    ))

    # 2. Executable lifecycle gate enforces status whitelist
    p1 = _load_phase1_contract_validation()
    status_whitelist_enforced = False
    status_whitelist_detail = ""
    try:
        p1.validate_shared({
            "object_id": "obj.test.1", "schema_version": "1.0.0",
            "producer": "audit", "run_id": "r", "trace_id": "t",
            "status": "not-a-real-status", "created_at": "2026-01-01T00:00:00Z",
            "lineage": [{"x": 1}],
        })
    except p1.ContractViolation as e:
        status_whitelist_enforced = "lifecycle" in str(e)
        status_whitelist_detail = str(e)
    evidence.append(_check(
        "d7.lifecycle_status_whitelist_enforced",
        "Executable lifecycle gate enforces a status whitelist",
        status_whitelist_enforced,
        detail=status_whitelist_detail,
    ))

    # 3. Candidate cannot write authority (promotion anti-forgery)
    candidate_write_blocked = False
    candidate_write_detail = ""
    try:
        p1.validate_approval({
            "object_id": "obj.test.2", "schema_version": "1.0.0",
            "producer": "audit", "run_id": "r", "trace_id": "t",
            "status": "candidate", "created_at": "2026-01-01T00:00:00Z",
            "lineage": [{"x": 1}],
            "no_trade_gate": True, "rollback_pointer": "ptr",
            "authority_write": True,
        })
    except p1.ContractViolation as e:
        candidate_write_blocked = "candidate" in str(e)
        candidate_write_detail = str(e)
    evidence.append(_check(
        "d7.candidate_cannot_write_authority",
        "Executable gate blocks candidate from writing authority",
        candidate_write_blocked,
        detail=candidate_write_detail,
    ))

    # 4. Irreversible change requires human approval ref
    irreversible_requires_approval = False
    irreversible_detail = ""
    try:
        p1.validate_approval({
            "object_id": "obj.test.3", "schema_version": "1.0.0",
            "producer": "audit", "run_id": "r", "trace_id": "t",
            "status": "approved", "created_at": "2026-01-01T00:00:00Z",
            "lineage": [{"x": 1}],
            "no_trade_gate": True, "rollback_pointer": "ptr",
            "change_class": "irreversible", "human_approval_ref": None,
        })
    except p1.ContractViolation as e:
        irreversible_requires_approval = "human_approval_ref" in str(e)
        irreversible_detail = str(e)
    evidence.append(_check(
        "d7.irreversible_change_requires_human_approval",
        "Executable gate requires human_approval_ref for irreversible change",
        irreversible_requires_approval,
        detail=irreversible_detail,
    ))

    # 5. Full candidate->experimental->formal transition engine with
    #    independent test receipts + rollback EXISTS?
    #    (Honest: it does not. Only registry + safety gate.)
    evidence.append(_check(
        "d7.full_promotion_runtime_present",
        "Executable candidate->experimental->formal runtime with independent "
        "test receipts + rollback exists on canonical main",
        False,
        detail=("NOT_IMPLEMENTED: no executable promotion runtime found; only "
                "coordination/SKILLS registry (maturity state machine as data) "
                "and PHASE-1 contract_validation.py safety gate."),
    ))

    passed = sum(1 for e in evidence if e.passed)
    total = len(evidence)
    verdict = VERDICT_PARTIAL if passed >= 4 else VERDICT_FAIL

    return DimensionVerdict(
        dimension="D7",
        title="Skill learning + promotion anti-forgery",
        verdict=verdict,
        rationale=(f"{passed}/{total} skill-promotion gates passed. The canonical "
                   "subsystem is a registry + a lifecycle safety gate, but there is "
                   "NO executable candidate->experimental->formal runtime binding "
                   "transitions to independent test receipts + rollback."),
        evidence=evidence,
        critical=True,
        notes=("R3 correction (B03): E66 evidence is moved to D9. D7 audits the "
               "REAL skill subsystem: coordination/SKILLS/*.yaml declares a "
               "maturity_state_machine (DISCOVERED->...->VALIDATED_RESEARCH_"
               "CAPABILITY) as governance data; PHASE-1 contract_validation.py "
               "is an executable lifecycle gate that (a) whitelists status, "
               "(b) blocks candidate authority writes, (c) requires "
               "human_approval_ref for irreversible change. However there is NO "
               "runtime that binds candidate->experimental->formal transitions to "
               "independent test receipts + rollback. Honest verdict: PARTIAL."),
    )
