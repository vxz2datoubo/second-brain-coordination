from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

ASSESSMENT_SCHEMA = "ChangeReversibilityAssessment/v1"
CHECKPOINT_SCHEMA = "KnownGoodCheckpoint/v1"
REVERT_PLAN_SCHEMA = "GovernedRevertPlan/v1"

ROLLBACK_TRIGGER_PHRASE = "做个滚回记号"

SURFACE_KINDS = {
    "CODE_CONFIG_ONLY",
    "POLICY_BEHAVIOR",
    "STATEFUL_DATA",
    "EXTERNAL_SIDE_EFFECT",
    "MIXED",
}
BLAST_RADII = {"SMALL", "MEDIUM", "LARGE", "CRITICAL"}
ROLLBACK_MECHANISMS = {
    "NONE",
    "GIT_REVERT",
    "FEATURE_FLAG_OR_VERSION_SWITCH",
    "MIGRATION",
    "SNAPSHOT",
    "COMPENSATION",
}
REVERSIBILITY_CLASSES = {
    "REVERSIBLE_GIT_ONLY",
    "REVERSIBLE_BY_VERSION_SWITCH",
    "REVERSIBLE_WITH_MIGRATION",
    "REVERSIBLE_WITH_SNAPSHOT",
    "COMPENSATABLE_ONLY",
    "IRREVERSIBLE_OR_HIGH_RISK",
}
TRIGGER_SOURCES = {
    "USER_EXPLICIT_ROLLBACK_MARKER",
    "GPT_LARGE_CHANGE_JUDGMENT",
    "PRE_MATERIAL_CHANGE_POLICY",
    "MANUAL_OPERATION",
}
ASSESSMENT_RESULTS = {
    "PASS",
    "REQUIRES_ROLLBACK_MARKER",
    "BLOCKED_ROLLBACK_PLAN_INCOMPLETE",
    "USER_APPROVAL_REQUIRED",
}
AUTHORITY = {
    "creates_task": False,
    "creates_route": False,
    "creates_work_claim": False,
    "grants_execution": False,
    "grants_write": False,
    "grants_review_accept": False,
    "grants_merge": False,
    "grants_release": False,
    "grants_trading": False,
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReversibleChangeError(ValueError):
    pass


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReversibleChangeError(f"{name}:MAPPING_REQUIRED")
    return value


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReversibleChangeError(f"{name}:NONEMPTY_STRING_REQUIRED")
    return value.strip()


def _require_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ReversibleChangeError(f"{name}:BOOLEAN_REQUIRED")
    return value


def _require_enum(value: Any, name: str, allowed: set[str]) -> str:
    text = _require_str(value, name)
    if text not in allowed:
        raise ReversibleChangeError(f"{name}:UNSUPPORTED:{text}")
    return text


def _require_sha40(value: Any, name: str) -> str:
    text = _require_str(value, name)
    if not SHA40.fullmatch(text):
        raise ReversibleChangeError(f"{name}:SHA40_REQUIRED")
    return text


def _require_sha256(value: Any, name: str) -> str:
    text = _require_str(value, name)
    if not SHA256.fullmatch(text):
        raise ReversibleChangeError(f"{name}:SHA256_REQUIRED")
    return text


def _normalize_optional_checkpoint_ref(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return _require_sha256(value, "rollback_checkpoint_ref")


def trigger_from_user_text(text: str) -> str:
    if not isinstance(text, str):
        raise ReversibleChangeError("user_text:STRING_REQUIRED")
    if ROLLBACK_TRIGGER_PHRASE in text:
        return "USER_EXPLICIT_ROLLBACK_MARKER"
    return "NONE"


def _classification(
    *,
    surface_kind: str,
    persistent_state_mutation: bool,
    external_irreversible_side_effect: bool,
    rollback_mechanism: str,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if external_irreversible_side_effect:
        reasons.append("EXTERNAL_IRREVERSIBLE_SIDE_EFFECT")
        return "IRREVERSIBLE_OR_HIGH_RISK", reasons

    if surface_kind == "EXTERNAL_SIDE_EFFECT":
        if rollback_mechanism == "COMPENSATION":
            reasons.append("EXTERNAL_SIDE_EFFECT_REQUIRES_COMPENSATION")
            return "COMPENSATABLE_ONLY", reasons
        reasons.append("EXTERNAL_SIDE_EFFECT_WITHOUT_COMPENSATION")
        return "IRREVERSIBLE_OR_HIGH_RISK", reasons

    if persistent_state_mutation or surface_kind in {"STATEFUL_DATA", "MIXED"}:
        if rollback_mechanism == "SNAPSHOT":
            reasons.append("STATEFUL_CHANGE_BOUND_TO_SNAPSHOT")
            return "REVERSIBLE_WITH_SNAPSHOT", reasons
        if rollback_mechanism == "MIGRATION":
            reasons.append("STATEFUL_CHANGE_BOUND_TO_MIGRATION")
            return "REVERSIBLE_WITH_MIGRATION", reasons
        reasons.append("STATEFUL_CHANGE_CANNOT_USE_GIT_ONLY_RECOVERY")
        return "IRREVERSIBLE_OR_HIGH_RISK", reasons

    if surface_kind == "POLICY_BEHAVIOR" and rollback_mechanism == "FEATURE_FLAG_OR_VERSION_SWITCH":
        reasons.append("POLICY_EFFECT_RECOVERY_BY_VERSION_SWITCH")
        return "REVERSIBLE_BY_VERSION_SWITCH", reasons

    if rollback_mechanism in {"NONE", "GIT_REVERT", "FEATURE_FLAG_OR_VERSION_SWITCH"}:
        if rollback_mechanism == "FEATURE_FLAG_OR_VERSION_SWITCH":
            reasons.append("VERSION_SWITCH_AVAILABLE")
            return "REVERSIBLE_BY_VERSION_SWITCH", reasons
        reasons.append("CODE_CONFIG_RECOVERABLE_BY_GIT_HISTORY")
        return "REVERSIBLE_GIT_ONLY", reasons

    reasons.append("ROLLBACK_MECHANISM_SURFACE_MISMATCH")
    return "IRREVERSIBLE_OR_HIGH_RISK", reasons


def assess_change_intent(
    intent_value: Mapping[str, Any],
    checkpoint_value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    intent = _require_mapping(intent_value, "intent")
    change_id = _require_str(intent.get("change_id"), "change_id")
    surface_kind = _require_enum(intent.get("surface_kind"), "surface_kind", SURFACE_KINDS)
    blast_radius = _require_enum(intent.get("blast_radius"), "blast_radius", BLAST_RADII)
    explicit_marker = _require_bool(
        intent.get("explicit_rollback_marker_requested"),
        "explicit_rollback_marker_requested",
    )
    gpt_judged_large = _require_bool(
        intent.get("gpt_judged_large_change"),
        "gpt_judged_large_change",
    )
    persistent_state = _require_bool(
        intent.get("persistent_state_mutation"),
        "persistent_state_mutation",
    )
    external_irreversible = _require_bool(
        intent.get("external_irreversible_side_effect"),
        "external_irreversible_side_effect",
    )
    rollback_mechanism = _require_enum(
        intent.get("rollback_mechanism"),
        "rollback_mechanism",
        ROLLBACK_MECHANISMS,
    )
    checkpoint_ref = _normalize_optional_checkpoint_ref(intent.get("rollback_checkpoint_ref"))
    checkpoint_binding_verified = False
    if checkpoint_value is not None:
        checkpoint = validate_known_good_checkpoint(checkpoint_value)
        actual_ref = checkpoint["checkpoint_digest"]
        if checkpoint_ref is not None and checkpoint_ref != actual_ref:
            raise ReversibleChangeError("assessment:CHECKPOINT_BINDING_MISMATCH")
        checkpoint_ref = actual_ref
        checkpoint_binding_verified = True

    classification, reasons = _classification(
        surface_kind=surface_kind,
        persistent_state_mutation=persistent_state,
        external_irreversible_side_effect=external_irreversible,
        rollback_mechanism=rollback_mechanism,
    )

    marker_required = (
        explicit_marker
        or gpt_judged_large
        or blast_radius in {"LARGE", "CRITICAL"}
        or persistent_state
        or surface_kind in {"STATEFUL_DATA", "MIXED", "EXTERNAL_SIDE_EFFECT"}
    )
    marker_reasons: list[str] = []
    if explicit_marker:
        marker_reasons.append("USER_EXPLICIT_ROLLBACK_MARKER")
    if gpt_judged_large:
        marker_reasons.append("GPT_LARGE_CHANGE_JUDGMENT")
    if blast_radius in {"LARGE", "CRITICAL"}:
        marker_reasons.append(f"BLAST_RADIUS_{blast_radius}")
    if persistent_state or surface_kind in {"STATEFUL_DATA", "MIXED", "EXTERNAL_SIDE_EFFECT"}:
        marker_reasons.append("STATEFUL_OR_MIXED_CHANGE")

    if classification == "IRREVERSIBLE_OR_HIGH_RISK":
        if external_irreversible:
            result = "USER_APPROVAL_REQUIRED"
        else:
            result = "BLOCKED_ROLLBACK_PLAN_INCOMPLETE"
    elif marker_required and not checkpoint_binding_verified:
        result = "REQUIRES_ROLLBACK_MARKER"
    else:
        result = "PASS"

    normalized_input = {
        "change_id": change_id,
        "surface_kind": surface_kind,
        "blast_radius": blast_radius,
        "explicit_rollback_marker_requested": explicit_marker,
        "gpt_judged_large_change": gpt_judged_large,
        "persistent_state_mutation": persistent_state,
        "external_irreversible_side_effect": external_irreversible,
        "rollback_mechanism": rollback_mechanism,
        "rollback_checkpoint_ref": checkpoint_ref,
    }
    payload = {
        "schema_version": ASSESSMENT_SCHEMA,
        "change_id": change_id,
        "normalized_input": normalized_input,
        "reversibility_class": classification,
        "assessment_result": result,
        "rollback_marker_required": marker_required,
        "rollback_marker_reasons": marker_reasons,
        "rollback_checkpoint_binding_verified": checkpoint_binding_verified,
        "classification_reasons": reasons,
        "authority": dict(AUTHORITY),
    }
    payload["assessment_digest"] = _digest(payload)
    return payload


def validate_assessment(value: Mapping[str, Any]) -> dict[str, Any]:
    assessment = dict(_require_mapping(value, "assessment"))
    if assessment.get("schema_version") != ASSESSMENT_SCHEMA:
        raise ReversibleChangeError("assessment:SCHEMA_MISMATCH")
    digest = _require_sha256(assessment.get("assessment_digest"), "assessment_digest")
    body = dict(assessment)
    body.pop("assessment_digest", None)
    if _digest(body) != digest:
        raise ReversibleChangeError("assessment:DIGEST_MISMATCH")
    if assessment.get("authority") != AUTHORITY:
        raise ReversibleChangeError("assessment:AUTHORITY_BOUNDARY_MISMATCH")
    _require_enum(assessment.get("reversibility_class"), "reversibility_class", REVERSIBILITY_CLASSES)
    result = _require_enum(assessment.get("assessment_result"), "assessment_result", ASSESSMENT_RESULTS)
    marker_required = _require_bool(assessment.get("rollback_marker_required"), "rollback_marker_required")
    checkpoint_verified = _require_bool(
        assessment.get("rollback_checkpoint_binding_verified"),
        "rollback_checkpoint_binding_verified",
    )
    if marker_required and result == "PASS" and not checkpoint_verified:
        raise ReversibleChangeError("assessment:UNVERIFIED_CHECKPOINT_CANNOT_PASS")
    normalized = _require_mapping(assessment.get("normalized_input"), "normalized_input")
    _require_enum(normalized.get("blast_radius"), "blast_radius", BLAST_RADII)
    _normalize_optional_checkpoint_ref(normalized.get("rollback_checkpoint_ref"))
    return assessment


def _git(repo_root: Path, *args: str) -> str:
    try:
        output = subprocess.check_output(
            ["git", *args],
            cwd=repo_root,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReversibleChangeError(f"git:{' '.join(args)}:FAILED") from exc
    return output.strip()


def capture_known_good_checkpoint(
    repo_root: str | Path,
    *,
    repository: str,
    expected_head: str,
    trigger_source: str,
    reason: str,
    required_branch: str = "main",
    previous_checkpoint_digest: str | None = None,
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    root = Path(repo_root)
    repository_name = _require_str(repository, "repository")
    expected = _require_sha40(expected_head, "expected_head")
    trigger = _require_enum(trigger_source, "trigger_source", TRIGGER_SOURCES)
    reason_text = _require_str(reason, "reason")
    branch_required = _require_str(required_branch, "required_branch")
    if previous_checkpoint_digest is not None:
        previous_checkpoint_digest = _require_sha256(
            previous_checkpoint_digest,
            "previous_checkpoint_digest",
        )

    head = _git(root, "rev-parse", "HEAD")
    if head != expected:
        raise ReversibleChangeError("checkpoint:HEAD_DRIFT")

    tree = _git(root, "rev-parse", "HEAD^{tree}")
    _require_sha40(tree, "tree_sha")
    branch = _git(root, "symbolic-ref", "--short", "-q", "HEAD")
    if branch != branch_required:
        raise ReversibleChangeError("checkpoint:BRANCH_MISMATCH")

    dirty = _git(root, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise ReversibleChangeError("checkpoint:WORKTREE_DIRTY")

    refs: list[str] = []
    seen: set[str] = set()
    for ref in evidence_refs:
        item = _require_str(ref, "evidence_ref")
        if item not in seen:
            refs.append(item)
            seen.add(item)

    semantic = {
        "schema_version": CHECKPOINT_SCHEMA,
        "repository": repository_name,
        "source_ref": branch,
        "canonical_commit": head,
        "tree_sha": tree,
        "trigger_source": trigger,
        "reason": reason_text,
        "qualification_level": "DESIGNATED_RECOVERY_ANCHOR",
        "git_binding_verified": True,
        "previous_checkpoint_digest": previous_checkpoint_digest,
        "evidence_refs": refs,
        "evidence_semantics": "REFERENCES_ONLY_NOT_ACCEPTANCE_AUTHORITY",
        "authority": dict(AUTHORITY),
    }
    digest = _digest(semantic)
    result = dict(semantic)
    result["checkpoint_id"] = f"KGC-{digest[:16]}"
    result["checkpoint_digest"] = digest
    return result


def validate_known_good_checkpoint(value: Mapping[str, Any]) -> dict[str, Any]:
    checkpoint = dict(_require_mapping(value, "checkpoint"))
    if checkpoint.get("schema_version") != CHECKPOINT_SCHEMA:
        raise ReversibleChangeError("checkpoint:SCHEMA_MISMATCH")
    digest = _require_sha256(checkpoint.get("checkpoint_digest"), "checkpoint_digest")
    checkpoint_id = _require_str(checkpoint.get("checkpoint_id"), "checkpoint_id")
    body = dict(checkpoint)
    body.pop("checkpoint_id", None)
    body.pop("checkpoint_digest", None)
    if _digest(body) != digest:
        raise ReversibleChangeError("checkpoint:DIGEST_MISMATCH")
    if checkpoint_id != f"KGC-{digest[:16]}":
        raise ReversibleChangeError("checkpoint:ID_MISMATCH")
    _require_sha40(checkpoint.get("canonical_commit"), "canonical_commit")
    _require_sha40(checkpoint.get("tree_sha"), "tree_sha")
    _require_enum(checkpoint.get("trigger_source"), "trigger_source", TRIGGER_SOURCES)
    if checkpoint.get("qualification_level") != "DESIGNATED_RECOVERY_ANCHOR":
        raise ReversibleChangeError("checkpoint:QUALIFICATION_MISMATCH")
    if checkpoint.get("git_binding_verified") is not True:
        raise ReversibleChangeError("checkpoint:GIT_BINDING_REQUIRED")
    if checkpoint.get("evidence_semantics") != "REFERENCES_ONLY_NOT_ACCEPTANCE_AUTHORITY":
        raise ReversibleChangeError("checkpoint:EVIDENCE_SEMANTICS_MISMATCH")
    if checkpoint.get("authority") != AUTHORITY:
        raise ReversibleChangeError("checkpoint:AUTHORITY_BOUNDARY_MISMATCH")
    previous = checkpoint.get("previous_checkpoint_digest")
    if previous is not None:
        _require_sha256(previous, "previous_checkpoint_digest")
    return checkpoint


def build_governed_revert_plan(
    checkpoint_value: Mapping[str, Any],
    assessment_value: Mapping[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    checkpoint = validate_known_good_checkpoint(checkpoint_value)
    assessment = validate_assessment(assessment_value)
    reason_text = _require_str(reason, "reason")

    if assessment["assessment_result"] != "PASS":
        raise ReversibleChangeError("revert_plan:ASSESSMENT_NOT_PASS")
    checkpoint_ref = assessment["normalized_input"].get("rollback_checkpoint_ref")
    if checkpoint_ref != checkpoint["checkpoint_digest"]:
        raise ReversibleChangeError("revert_plan:CHECKPOINT_BINDING_MISMATCH")

    classification = assessment["reversibility_class"]
    if classification == "IRREVERSIBLE_OR_HIGH_RISK":
        raise ReversibleChangeError("revert_plan:IRREVERSIBLE_CHANGE")

    strategy_by_class = {
        "REVERSIBLE_GIT_ONLY": "FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT",
        "REVERSIBLE_BY_VERSION_SWITCH": "VERSION_SWITCH_OR_FEATURE_FLAG",
        "REVERSIBLE_WITH_MIGRATION": "FORWARD_REVERT_PLUS_DOWN_MIGRATION",
        "REVERSIBLE_WITH_SNAPSHOT": "FORWARD_REVERT_PLUS_SNAPSHOT_RESTORE",
        "COMPENSATABLE_ONLY": "COMPENSATING_ACTION_PLUS_FORWARD_REVERT",
    }
    strategy = strategy_by_class[classification]
    blast_radius = assessment["normalized_input"]["blast_radius"]
    independent_review_required = blast_radius in {"MEDIUM", "LARGE", "CRITICAL"}
    user_approval_required = classification == "COMPENSATABLE_ONLY" or blast_radius == "CRITICAL"

    plan = {
        "schema_version": REVERT_PLAN_SCHEMA,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "checkpoint_digest": checkpoint["checkpoint_digest"],
        "target_commit": checkpoint["canonical_commit"],
        "target_tree": checkpoint["tree_sha"],
        "change_id": assessment["change_id"],
        "assessment_digest": assessment["assessment_digest"],
        "reversibility_class": classification,
        "strategy": strategy,
        "reason": reason_text,
        "preserve_history": True,
        "destructive_history_rewrite": False,
        "exact_head_reverification_required": True,
        "independent_review_required": independent_review_required,
        "user_approval_required": user_approval_required,
        "authority": dict(AUTHORITY),
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def validate_governed_revert_plan(value: Mapping[str, Any]) -> dict[str, Any]:
    plan = dict(_require_mapping(value, "revert_plan"))
    if plan.get("schema_version") != REVERT_PLAN_SCHEMA:
        raise ReversibleChangeError("revert_plan:SCHEMA_MISMATCH")
    digest = _require_sha256(plan.get("plan_digest"), "plan_digest")
    body = dict(plan)
    body.pop("plan_digest", None)
    if _digest(body) != digest:
        raise ReversibleChangeError("revert_plan:DIGEST_MISMATCH")
    _require_sha40(plan.get("target_commit"), "target_commit")
    _require_sha40(plan.get("target_tree"), "target_tree")
    _require_sha256(plan.get("checkpoint_digest"), "checkpoint_digest")
    _require_sha256(plan.get("assessment_digest"), "assessment_digest")
    _require_enum(plan.get("reversibility_class"), "reversibility_class", REVERSIBILITY_CLASSES)
    if plan.get("preserve_history") is not True:
        raise ReversibleChangeError("revert_plan:HISTORY_PRESERVATION_REQUIRED")
    if plan.get("destructive_history_rewrite") is not False:
        raise ReversibleChangeError("revert_plan:DESTRUCTIVE_HISTORY_REWRITE_FORBIDDEN")
    if plan.get("exact_head_reverification_required") is not True:
        raise ReversibleChangeError("revert_plan:EXACT_HEAD_REVERIFICATION_REQUIRED")
    if plan.get("authority") != AUTHORITY:
        raise ReversibleChangeError("revert_plan:AUTHORITY_BOUNDARY_MISMATCH")
    return plan


def _load_json(path: str) -> Mapping[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return _require_mapping(value, path)


def _dump(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def _cli() -> int:
    parser = argparse.ArgumentParser(description="R159 reversible change foundation")
    sub = parser.add_subparsers(dest="command", required=True)

    assess_parser = sub.add_parser("assess")
    assess_parser.add_argument("--input", required=True)
    assess_parser.add_argument("--checkpoint")

    checkpoint_parser = sub.add_parser("checkpoint")
    checkpoint_parser.add_argument("--repo-root", required=True)
    checkpoint_parser.add_argument("--repository", required=True)
    checkpoint_parser.add_argument("--expected-head", required=True)
    checkpoint_parser.add_argument("--trigger-source", required=True, choices=sorted(TRIGGER_SOURCES))
    checkpoint_parser.add_argument("--reason", required=True)
    checkpoint_parser.add_argument("--required-branch", default="main")

    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("--checkpoint", required=True)
    plan_parser.add_argument("--assessment", required=True)
    plan_parser.add_argument("--reason", required=True)

    args = parser.parse_args()
    if args.command == "assess":
        checkpoint = _load_json(args.checkpoint) if args.checkpoint else None
        _dump(assess_change_intent(_load_json(args.input), checkpoint))
    elif args.command == "checkpoint":
        _dump(
            capture_known_good_checkpoint(
                args.repo_root,
                repository=args.repository,
                expected_head=args.expected_head,
                trigger_source=args.trigger_source,
                reason=args.reason,
                required_branch=args.required_branch,
            )
        )
    elif args.command == "plan":
        _dump(
            build_governed_revert_plan(
                _load_json(args.checkpoint),
                _load_json(args.assessment),
                reason=args.reason,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
