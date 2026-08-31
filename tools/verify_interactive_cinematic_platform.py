"""Deterministically verify the interactive-cinematic GitHub control plane.

This verifier intentionally checks only repository-resident architecture data.
It opens no credentials, performs no provider/network request, and never reads
local private-media or customer-runtime directories.  It is an executor-side
reproducibility guard, not an independent product or security acceptance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROGRAM_RELATIVE = Path("coordination/PROGRAMS/INTERACTIVE-CINEMATIC-PLATFORM-0001")
EXPECTED_SCHEMA = "InteractiveCinematicPlatformControlPlane/v1"
EXPECTED_PROGRAM_ID = "INTERACTIVE-CINEMATIC-PLATFORM-0001"
EXPECTED_PREFIXES = {
    "codex/interactive-cinematic-",
    "gpt/interactive-cinematic-",
    "workbuddy/interactive-cinematic-",
}
REQUIRED_CONTRACTS = {
    "ScriptPackage/v1",
    "PlayerCampaign/v1",
    "ChoiceIntent/v1",
    "NarrativeProposal/v1",
    "NarrativeState/v1",
    "QuestState/v1",
    "RewardState/v1",
    "RelationshipState/v1",
    "EvidenceItem/v1",
    "DramaticBeatSelection/v1",
    "AvatarIdentity/v1",
    "AvatarRevision/v1",
    "CharacterBible/v1",
    "CharacterAppearanceAnchor/v1",
    "AssetApproval/v1",
    "AppearanceContinuityRecord/v1",
    "DirectorBrief/v2",
    "ShotBundle/v1",
    "CinematicSegment/v1",
    "MediaJob/v1",
    "MediaResult/v1",
    "MediaQualityReport/v1",
    "ManualIntake/v1",
    "DouyinCommentIngest/v1",
    "DouyinImageCapabilityGate/v1",
    "CreativeKnowledgeCandidate/v1",
    "CorrectionProposal/v1",
    "HumanReviewDecision/v1",
    "ReusableSkillCandidate/v1",
}
MARKERS_BY_FILE = {
    "PROGRAM.yaml": ("program_id: INTERACTIVE-CINEMATIC-PLATFORM-0001", "no_external_or_paid_model_calls: true"),
    "ARCHITECTURE.md": ("ChoiceIntent/v1", "DouyinImageCapabilityGate/v1", "Eustia 不是默认输入"),
    "PRODUCT-UNDERSTANDING-MAP.yaml": ("schema: ProductUnderstandingMap/v1", "layer: explicit_known", "layer: opaque_unknown"),
    "SCRIPT-AND-DIRECTOR-CONTRACTS.md": ("ScriptPackage/v1", "DirectorBrief/v2", "MediaQualityReport/v1"),
    "RESEARCH-AND-VALIDATION-BACKLOG.md": ("Foreseeing Meaningful Choices", "MiniMax H3", "DouyinImageCapabilityGate/v1"),
    "MODULE-OWNERSHIP.yaml": ("schema: InteractiveCinematicPlatformOwnership/v1", "self_review_or_acceptance"),
    "STATUS.yaml": ("schema: InteractiveCinematicPlatformStatus/v1", "in_progress_slice:"),
    "RUNBOOK.md": ("python tools/verify_interactive_cinematic_platform.py", "不读取凭证"),
    "AI_HANDOFF.yaml": ("schema: AIHandoff/v1", "source_agent: CODEX", "reviewer: GPT_INDEPENDENT_REVIEWER"),
    "EVIDENCE/A0-ARCHITECTURE-BASELINE.md": ("agent_id", "EXECUTOR_VERIFIED_ONLY"),
}


class VerificationError(ValueError):
    """Raised when the committed control plane is incomplete or contradictory."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"invalid manifest: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise VerificationError("manifest root must be an object")
    return payload


def _require_string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise VerificationError(f"manifest {key} must be a non-empty list of strings")
    return value


def validate(root: Path) -> dict[str, Any]:
    """Validate A0's repository-only contracts and return a compact receipt."""

    program_root = root / PROGRAM_RELATIVE
    manifest_path = program_root / "CONTROL-PLANE-MANIFEST.json"
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != EXPECTED_SCHEMA:
        raise VerificationError("unexpected control-plane schema")
    if manifest.get("program_id") != EXPECTED_PROGRAM_ID:
        raise VerificationError("unexpected program id")
    if manifest.get("source_of_truth") != "GitHub repository and this control directory":
        raise VerificationError("source_of_truth must designate the committed control directory")

    required_files = _require_string_list(manifest, "required_files")
    for relative in required_files:
        path = program_root / relative
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise VerificationError(f"required control-plane file missing or empty: {relative}")

    prefixes = _require_string_list(manifest, "branch_prefixes")
    if len(prefixes) != len(set(prefixes)) or set(prefixes) != EXPECTED_PREFIXES:
        raise VerificationError("branch prefixes must be the three exact collaboration prefixes")

    contracts = _require_string_list(manifest, "contract_schemas")
    if len(contracts) != len(set(contracts)):
        raise VerificationError("contract catalog contains a duplicate schema")
    missing_contracts = sorted(REQUIRED_CONTRACTS.difference(contracts))
    if missing_contracts:
        raise VerificationError("contract catalog missing: " + ", ".join(missing_contracts))

    forbidden = _require_string_list(manifest, "github_forbidden")
    for required_boundary in ("real user photos or biometric features", "tokens, cookies, credentials, or secret-manager exports"):
        if required_boundary not in forbidden:
            raise VerificationError(f"github_forbidden lacks required privacy boundary: {required_boundary}")

    for relative, markers in MARKERS_BY_FILE.items():
        text = (program_root / relative).read_text(encoding="utf-8")
        absent = [marker for marker in markers if marker not in text]
        if absent:
            raise VerificationError(f"{relative} is missing required markers: {', '.join(absent)}")

    status_text = (program_root / "STATUS.yaml").read_text(encoding="utf-8")
    if "in_progress_slice: null" not in status_text and "in_progress_slice:\n" not in status_text:
        raise VerificationError("STATUS.yaml must explicitly declare its single in-progress slice or null")
    handoff_text = (program_root / "AI_HANDOFF.yaml").read_text(encoding="utf-8")
    if "executor_status: EXECUTOR_VERIFIED_ONLY" not in handoff_text:
        raise VerificationError("AI_HANDOFF.yaml must not claim independent acceptance for executor work")

    return {
        "status": "pass",
        "schema": EXPECTED_SCHEMA,
        "program_id": EXPECTED_PROGRAM_ID,
        "program_root": PROGRAM_RELATIVE.as_posix(),
        "required_file_count": len(required_files),
        "contract_count": len(contracts),
        "branch_prefix_count": len(prefixes),
        "external_calls_performed": False,
        "private_data_read": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root to validate; defaults to this repository",
    )
    args = parser.parse_args(argv)
    try:
        receipt = validate(args.root.resolve())
    except VerificationError as error:
        print(json.dumps({"status": "fail", "error": str(error)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
