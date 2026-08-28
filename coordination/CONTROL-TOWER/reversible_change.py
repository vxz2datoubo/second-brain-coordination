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
_MARKER_PREFIX = "refs/tags/r159-known-good/"
_INTENT_FIELDS = {
    "change_id",
    "surface_kind",
    "blast_radius",
    "explicit_rollback_marker_requested",
    "gpt_judged_large_change",
    "persistent_state_mutation",
    "external_irreversible_side_effect",
    "rollback_mechanism",
    "rollback_checkpoint_ref",
}
_STRATEGY_BY_CLASS = {
    "REVERSIBLE_GIT_ONLY": "FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT",
    "REVERSIBLE_BY_VERSION_SWITCH": "VERSION_SWITCH_OR_FEATURE_FLAG",
    "REVERSIBLE_WITH_MIGRATION": "FORWARD_REVERT_PLUS_DOWN_MIGRATION",
    "REVERSIBLE_WITH_SNAPSHOT": "FORWARD_REVERT_PLUS_SNAPSHOT_RESTORE",
    "COMPENSATABLE_ONLY": "COMPENSATING_ACTION_PLUS_FORWARD_REVERT",
}


class ReversibleChangeError(ValueError):
    pass


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


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


def _git(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=repo_root,
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReversibleChangeError(f"git:{' '.join(args)}:FAILED") from exc


def _git_optional(repo_root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=repo_root,
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _marker_ref(checkpoint_digest: str) -> str:
    digest = _require_sha256(checkpoint_digest, "checkpoint_digest")
    return f"{_MARKER_PREFIX}{digest}"


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
    if external_irreversible_side_effect:
        return "IRREVERSIBLE_OR_HIGH_RISK", ["EXTERNAL_IRREVERSIBLE_SIDE_EFFECT"]

    if surface_kind == "EXTERNAL_SIDE_EFFECT":
        if rollback_mechanism == "COMPENSATION":
            return "COMPENSATABLE_ONLY", [
                "EXTERNAL_SIDE_EFFECT_REQUIRES_COMPENSATION"
            ]
        return "IRREVERSIBLE_OR_HIGH_RISK", [
            "EXTERNAL_SIDE_EFFECT_WITHOUT_COMPENSATION"
        ]

    if persistent_state_mutation or surface_kind in {"STATEFUL_DATA", "MIXED"}:
        if rollback_mechanism == "SNAPSHOT":
            return "REVERSIBLE_WITH_SNAPSHOT", ["STATEFUL_CHANGE_BOUND_TO_SNAPSHOT"]
        if rollback_mechanism == "MIGRATION":
            return "REVERSIBLE_WITH_MIGRATION", ["STATEFUL_CHANGE_BOUND_TO_MIGRATION"]
        return "IRREVERSIBLE_OR_HIGH_RISK", [
            "STATEFUL_CHANGE_CANNOT_USE_GIT_ONLY_RECOVERY"
        ]

    if (
        surface_kind == "POLICY_BEHAVIOR"
        and rollback_mechanism == "FEATURE_FLAG_OR_VERSION_SWITCH"
    ):
        return "REVERSIBLE_BY_VERSION_SWITCH", [
            "POLICY_EFFECT_RECOVERY_BY_VERSION_SWITCH"
        ]

    if rollback_mechanism in {
        "NONE",
        "GIT_REVERT",
        "FEATURE_FLAG_OR_VERSION_SWITCH",
    }:
        if rollback_mechanism == "FEATURE_FLAG_OR_VERSION_SWITCH":
            return "REVERSIBLE_BY_VERSION_SWITCH", ["VERSION_SWITCH_AVAILABLE"]
        return "REVERSIBLE_GIT_ONLY", ["CODE_CONFIG_RECOVERABLE_BY_GIT_HISTORY"]

    return "IRREVERSIBLE_OR_HIGH_RISK", ["ROLLBACK_MECHANISM_SURFACE_MISMATCH"]


def _normalize_intent(intent_value: Mapping[str, Any]) -> dict[str, Any]:
    intent = dict(_require_mapping(intent_value, "intent"))
    missing = sorted(_INTENT_FIELDS - set(intent))
    extra = sorted(set(intent) - _INTENT_FIELDS)
    if missing:
        raise ReversibleChangeError(f"intent:FIELD_MISSING:{missing[0]}")
    if extra:
        raise ReversibleChangeError(f"intent:FIELD_UNRECOGNIZED:{extra[0]}")

    return {
        "change_id": _require_str(intent.get("change_id"), "change_id"),
        "surface_kind": _require_enum(
            intent.get("surface_kind"), "surface_kind", SURFACE_KINDS
        ),
        "blast_radius": _require_enum(
            intent.get("blast_radius"), "blast_radius", BLAST_RADII
        ),
        "explicit_rollback_marker_requested": _require_bool(
            intent.get("explicit_rollback_marker_requested"),
            "explicit_rollback_marker_requested",
        ),
        "gpt_judged_large_change": _require_bool(
            intent.get("gpt_judged_large_change"),
            "gpt_judged_large_change",
        ),
        "persistent_state_mutation": _require_bool(
            intent.get("persistent_state_mutation"),
            "persistent_state_mutation",
        ),
        "external_irreversible_side_effect": _require_bool(
            intent.get("external_irreversible_side_effect"),
            "external_irreversible_side_effect",
        ),
        "rollback_mechanism": _require_enum(
            intent.get("rollback_mechanism"),
            "rollback_mechanism",
            ROLLBACK_MECHANISMS,
        ),
        "rollback_checkpoint_ref": _normalize_optional_checkpoint_ref(
            intent.get("rollback_checkpoint_ref")
        ),
    }


def _derive_assessment(
    normalized: Mapping[str, Any],
    checkpoint_binding_verified: bool,
) -> dict[str, Any]:
    classification, classification_reasons = _classification(
        surface_kind=str(normalized["surface_kind"]),
        persistent_state_mutation=bool(normalized["persistent_state_mutation"]),
        external_irreversible_side_effect=bool(
            normalized["external_irreversible_side_effect"]
        ),
        rollback_mechanism=str(normalized["rollback_mechanism"]),
    )

    marker_required = (
        bool(normalized["explicit_rollback_marker_requested"])
        or bool(normalized["gpt_judged_large_change"])
        or normalized["blast_radius"] in {"LARGE", "CRITICAL"}
        or bool(normalized["persistent_state_mutation"])
        or normalized["surface_kind"]
        in {"STATEFUL_DATA", "MIXED", "EXTERNAL_SIDE_EFFECT"}
    )

    marker_reasons: list[str] = []
    if normalized["explicit_rollback_marker_requested"]:
        marker_reasons.append("USER_EXPLICIT_ROLLBACK_MARKER")
    if normalized["gpt_judged_large_change"]:
        marker_reasons.append("GPT_LARGE_CHANGE_JUDGMENT")
    if normalized["blast_radius"] in {"LARGE", "CRITICAL"}:
        marker_reasons.append(f"BLAST_RADIUS_{normalized['blast_radius']}")
    if normalized["persistent_state_mutation"] or normalized["surface_kind"] in {
        "STATEFUL_DATA",
        "MIXED",
        "EXTERNAL_SIDE_EFFECT",
    }:
        marker_reasons.append("STATEFUL_OR_MIXED_CHANGE")

    if classification == "IRREVERSIBLE_OR_HIGH_RISK":
        if normalized["external_irreversible_side_effect"]:
            result = "USER_APPROVAL_REQUIRED"
        else:
            result = "BLOCKED_ROLLBACK_PLAN_INCOMPLETE"
    elif marker_required and not checkpoint_binding_verified:
        result = "REQUIRES_ROLLBACK_MARKER"
    else:
        result = "PASS"

    payload = {
        "schema_version": ASSESSMENT_SCHEMA,
        "change_id": normalized["change_id"],
        "normalized_input": dict(normalized),
        "reversibility_class": classification,
        "assessment_result": result,
        "rollback_marker_required": marker_required,
        "rollback_marker_reasons": marker_reasons,
        "rollback_checkpoint_binding_verified": checkpoint_binding_verified,
        "classification_reasons": classification_reasons,
        "authority": dict(AUTHORITY),
    }
    payload["assessment_digest"] = _digest(payload)
    return payload


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
    root = Path(repo_root).resolve()
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
    marker_ref = _marker_ref(digest)

    existing = _git_optional(root, "rev-parse", "--verify", "-q", marker_ref)
    if existing is None:
        _git(root, "update-ref", marker_ref, head, "0" * 40)
    elif existing != head:
        raise ReversibleChangeError("checkpoint:GIT_MARKER_COLLISION")

    if _git(root, "rev-parse", "--verify", marker_ref) != head:
        raise ReversibleChangeError("checkpoint:GIT_MARKER_CREATE_FAILED")

    result = dict(semantic)
    result["checkpoint_id"] = f"KGC-{digest[:16]}"
    result["checkpoint_digest"] = digest
    return result


def validate_known_good_checkpoint(
    value: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    checkpoint = dict(_require_mapping(value, "checkpoint"))
    if checkpoint.get("schema_version") != CHECKPOINT_SCHEMA:
        raise ReversibleChangeError("checkpoint:SCHEMA_MISMATCH")

    digest = _require_sha256(
        checkpoint.get("checkpoint_digest"), "checkpoint_digest"
    )
    checkpoint_id = _require_str(checkpoint.get("checkpoint_id"), "checkpoint_id")
    body = dict(checkpoint)
    body.pop("checkpoint_id", None)
    body.pop("checkpoint_digest", None)
    if _digest(body) != digest:
        raise ReversibleChangeError("checkpoint:DIGEST_MISMATCH")
    if checkpoint_id != f"KGC-{digest[:16]}":
        raise ReversibleChangeError("checkpoint:ID_MISMATCH")

    commit = _require_sha40(checkpoint.get("canonical_commit"), "canonical_commit")
    tree = _require_sha40(checkpoint.get("tree_sha"), "tree_sha")
    source_ref = _require_str(checkpoint.get("source_ref"), "source_ref")
    _require_enum(
        checkpoint.get("trigger_source"), "trigger_source", TRIGGER_SOURCES
    )
    _require_str(checkpoint.get("repository"), "repository")
    _require_str(checkpoint.get("reason"), "reason")

    if checkpoint.get("qualification_level") != "DESIGNATED_RECOVERY_ANCHOR":
        raise ReversibleChangeError("checkpoint:QUALIFICATION_MISMATCH")
    if checkpoint.get("git_binding_verified") is not True:
        raise ReversibleChangeError("checkpoint:GIT_BINDING_REQUIRED")
    if (
        checkpoint.get("evidence_semantics")
        != "REFERENCES_ONLY_NOT_ACCEPTANCE_AUTHORITY"
    ):
        raise ReversibleChangeError("checkpoint:EVIDENCE_SEMANTICS_MISMATCH")
    if checkpoint.get("authority") != AUTHORITY:
        raise ReversibleChangeError("checkpoint:AUTHORITY_BOUNDARY_MISMATCH")

    previous = checkpoint.get("previous_checkpoint_digest")
    if previous is not None:
        _require_sha256(previous, "previous_checkpoint_digest")

    marker_ref = _marker_ref(digest)
    marker_commit = _git_optional(
        root,
        "rev-parse",
        "--verify",
        "-q",
        f"{marker_ref}^{{commit}}",
    )
    if marker_commit != commit:
        raise ReversibleChangeError("checkpoint:TRUSTED_GIT_MARKER_REQUIRED")

    actual_tree = _git_optional(root, "rev-parse", f"{commit}^{{tree}}")
    if actual_tree != tree:
        raise ReversibleChangeError("checkpoint:TREE_BINDING_MISMATCH")

    branch_tip = _git_optional(
        root,
        "rev-parse",
        "--verify",
        f"refs/heads/{source_ref}",
    )
    if branch_tip is None:
        raise ReversibleChangeError("checkpoint:SOURCE_REF_MISSING")

    try:
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", commit, branch_tip],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReversibleChangeError(
            "checkpoint:SOURCE_REF_ANCESTRY_MISMATCH"
        ) from exc

    return checkpoint


def assess_change_intent(
    intent_value: Mapping[str, Any],
    checkpoint_value: Mapping[str, Any] | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    normalized = _normalize_intent(intent_value)
    checkpoint_verified = False

    if checkpoint_value is not None:
        if repo_root is None:
            raise ReversibleChangeError("assessment:CHECKPOINT_REPO_ROOT_REQUIRED")
        checkpoint = validate_known_good_checkpoint(
            checkpoint_value,
            repo_root=repo_root,
        )
        actual_ref = checkpoint["checkpoint_digest"]
        if (
            normalized["rollback_checkpoint_ref"] is not None
            and normalized["rollback_checkpoint_ref"] != actual_ref
        ):
            raise ReversibleChangeError("assessment:CHECKPOINT_BINDING_MISMATCH")
        normalized["rollback_checkpoint_ref"] = actual_ref
        checkpoint_verified = True

    return _derive_assessment(normalized, checkpoint_verified)


def validate_assessment(
    value: Mapping[str, Any],
    *,
    checkpoint_value: Mapping[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    assessment = dict(_require_mapping(value, "assessment"))
    if assessment.get("schema_version") != ASSESSMENT_SCHEMA:
        raise ReversibleChangeError("assessment:SCHEMA_MISMATCH")

    digest = _require_sha256(
        assessment.get("assessment_digest"), "assessment_digest"
    )
    body = dict(assessment)
    body.pop("assessment_digest", None)
    if _digest(body) != digest:
        raise ReversibleChangeError("assessment:DIGEST_MISMATCH")

    normalized = _normalize_intent(
        _require_mapping(assessment.get("normalized_input"), "normalized_input")
    )
    if checkpoint_value is None:
        expected = assess_change_intent(normalized)
    else:
        expected = assess_change_intent(
            normalized,
            checkpoint_value,
            repo_root=repo_root,
        )

    if assessment != expected:
        raise ReversibleChangeError("assessment:SEMANTIC_REDERIVATION_MISMATCH")
    return assessment


def _derive_revert_plan(
    checkpoint: Mapping[str, Any],
    assessment: Mapping[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    if assessment["assessment_result"] != "PASS":
        raise ReversibleChangeError("revert_plan:ASSESSMENT_NOT_PASS")

    if (
        assessment["normalized_input"].get("rollback_checkpoint_ref")
        != checkpoint["checkpoint_digest"]
    ):
        raise ReversibleChangeError("revert_plan:CHECKPOINT_BINDING_MISMATCH")

    classification = assessment["reversibility_class"]
    if classification == "IRREVERSIBLE_OR_HIGH_RISK":
        raise ReversibleChangeError("revert_plan:IRREVERSIBLE_CHANGE")
    if classification not in _STRATEGY_BY_CLASS:
        raise ReversibleChangeError("revert_plan:STRATEGY_UNAVAILABLE")

    blast_radius = assessment["normalized_input"]["blast_radius"]
    plan = {
        "schema_version": REVERT_PLAN_SCHEMA,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "checkpoint_digest": checkpoint["checkpoint_digest"],
        "target_commit": checkpoint["canonical_commit"],
        "target_tree": checkpoint["tree_sha"],
        "change_id": assessment["change_id"],
        "assessment_digest": assessment["assessment_digest"],
        "reversibility_class": classification,
        "strategy": _STRATEGY_BY_CLASS[classification],
        "reason": _require_str(reason, "reason"),
        "preserve_history": True,
        "destructive_history_rewrite": False,
        "exact_head_reverification_required": True,
        "independent_review_required": blast_radius
        in {"MEDIUM", "LARGE", "CRITICAL"},
        "user_approval_required": classification == "COMPENSATABLE_ONLY"
        or blast_radius == "CRITICAL",
        "authority": dict(AUTHORITY),
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def build_governed_revert_plan(
    checkpoint_value: Mapping[str, Any],
    assessment_value: Mapping[str, Any],
    *,
    reason: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    checkpoint = validate_known_good_checkpoint(
        checkpoint_value,
        repo_root=repo_root,
    )
    assessment = validate_assessment(
        assessment_value,
        checkpoint_value=checkpoint,
        repo_root=repo_root,
    )
    return _derive_revert_plan(checkpoint, assessment, reason=reason)


def validate_governed_revert_plan(
    value: Mapping[str, Any],
    *,
    checkpoint_value: Mapping[str, Any],
    assessment_value: Mapping[str, Any],
    repo_root: str | Path,
) -> dict[str, Any]:
    plan = dict(_require_mapping(value, "revert_plan"))
    if plan.get("schema_version") != REVERT_PLAN_SCHEMA:
        raise ReversibleChangeError("revert_plan:SCHEMA_MISMATCH")

    digest = _require_sha256(plan.get("plan_digest"), "plan_digest")
    body = dict(plan)
    body.pop("plan_digest", None)
    if _digest(body) != digest:
        raise ReversibleChangeError("revert_plan:DIGEST_MISMATCH")

    if plan.get("preserve_history") is not True:
        raise ReversibleChangeError("revert_plan:HISTORY_PRESERVATION_REQUIRED")
    if plan.get("destructive_history_rewrite") is not False:
        raise ReversibleChangeError(
            "revert_plan:DESTRUCTIVE_HISTORY_REWRITE_FORBIDDEN"
        )
    if plan.get("exact_head_reverification_required") is not True:
        raise ReversibleChangeError(
            "revert_plan:EXACT_HEAD_REVERIFICATION_REQUIRED"
        )
    if plan.get("authority") != AUTHORITY:
        raise ReversibleChangeError("revert_plan:AUTHORITY_BOUNDARY_MISMATCH")

    checkpoint = validate_known_good_checkpoint(
        checkpoint_value,
        repo_root=repo_root,
    )
    assessment = validate_assessment(
        assessment_value,
        checkpoint_value=checkpoint,
        repo_root=repo_root,
    )
    expected = _derive_revert_plan(
        checkpoint,
        assessment,
        reason=_require_str(plan.get("reason"), "reason"),
    )
    if plan != expected:
        raise ReversibleChangeError("revert_plan:SEMANTIC_REDERIVATION_MISMATCH")
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
    assess_parser.add_argument("--repo-root")

    checkpoint_parser = sub.add_parser("checkpoint")
    checkpoint_parser.add_argument("--repo-root", required=True)
    checkpoint_parser.add_argument("--repository", required=True)
    checkpoint_parser.add_argument("--expected-head", required=True)
    checkpoint_parser.add_argument(
        "--trigger-source",
        required=True,
        choices=sorted(TRIGGER_SOURCES),
    )
    checkpoint_parser.add_argument("--reason", required=True)
    checkpoint_parser.add_argument("--required-branch", default="main")

    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("--checkpoint", required=True)
    plan_parser.add_argument("--assessment", required=True)
    plan_parser.add_argument("--reason", required=True)
    plan_parser.add_argument("--repo-root", required=True)

    args = parser.parse_args()
    if args.command == "assess":
        checkpoint = _load_json(args.checkpoint) if args.checkpoint else None
        if checkpoint is not None and not args.repo_root:
            raise ReversibleChangeError("assessment:CHECKPOINT_REPO_ROOT_REQUIRED")
        _dump(
            assess_change_intent(
                _load_json(args.input),
                checkpoint,
                repo_root=args.repo_root,
            )
        )
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
                repo_root=args.repo_root,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
