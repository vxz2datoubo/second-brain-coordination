"""Generate public-safe R136/R145 exact authority receipts from fresh AI Film reads."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [
    str(
        ROOT
        / "coordination"
        / "PROGRAMS"
        / "SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001"
        / "GLOBAL-SIGNAL-PLANE"
        / "S0-SYNTHETIC"
        / "src"
    ),
    str(Path(__file__).resolve().parent / "src"),
]

from global_signal_gateway.gateway import (  # noqa: E402
    AI_FILM_COMMIT,
    SystemAwarenessProjection,
    ai_film_directing_read_only_smoke,
    temporary_exact_clone,
    validate_live_observation_proof,
)
from global_signal_gateway.live_observation_provider import (  # noqa: E402
    ACTIVE_TASK_PATH,
    CONTROL_PATHS,
    CONTRACT_REVISION,
    DOMAIN_REPOSITORY,
    TARGET_REPOSITORY,
    DomainFreshnessTarget,
    LiveObservationProvider,
    LiveObservationRequest,
)
from global_signal_gateway.semantic_authority import (  # noqa: E402
    exact_semantic_authority_proof,
    semantic_authority_ref,
)
from global_signal_plane.ledger import DurableSignalLedger  # noqa: E402


R145_AUTHORITY_CONTRACT = (
    "coordination/TASK-BRIEFS/"
    "GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145.yaml"
)
AI_FILM_AUTHORITY_PATH = "PROJECT_INDEX.yaml"
AI_FILM_EXPECTED_IDENTITY = {
    "domain_id": "AI_FILM_SYSTEM",
    "project_id": "EUSTIA_AI_FILM",
    "authority_schema_version": "AI_FILM_PROJECT_INDEX/v1",
    "writeback_owner": "AI_FILM_SYSTEM",
    "observation_mode": "READ_ONLY",
}


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(code)
    return value


def _pull_request_event() -> Mapping[str, Any] | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    pr = event.get("pull_request") if isinstance(event, Mapping) else None
    return pr if isinstance(pr, Mapping) else None


def _current_task(repo_root: Path) -> tuple[str, int]:
    value = yaml.safe_load((repo_root / ACTIVE_TASK_PATH).read_text(encoding="utf-8"))
    active = _mapping(value, "CURRENT_TASK_INVALID")
    task_id, epoch = active.get("task_id"), active.get("route_epoch")
    if not isinstance(task_id, str) or not task_id or not isinstance(epoch, int):
        raise RuntimeError("CURRENT_TASK_INVALID")
    return task_id, epoch


def _r145_real_governed_authority(repo_root: Path, pr_number: int) -> dict[str, Any]:
    task_id, epoch = _current_task(repo_root)
    request = LiveObservationRequest(
        request_id=f"r145-real-ai-film-{pr_number}",
        provider_contract_revision=CONTRACT_REVISION,
        target_repository=TARGET_REPOSITORY,
        target_branch="main",
        pull_request_number=pr_number,
        expected_task_id=task_id,
        expected_route_epoch=epoch,
        required_control_plane_paths=CONTROL_PATHS,
        required_domain_freshness_targets=(
            DomainFreshnessTarget(
                DOMAIN_REPOSITORY,
                domain_id="AI_FILM_SYSTEM",
                authority_contract_path=R145_AUTHORITY_CONTRACT,
            ),
        ),
        required_review_scope="ALL_RAW_REVIEWS",
        requested_max_age_seconds=240,
        requested_at=datetime.now(timezone.utc).isoformat(),
    )
    bundle, live_proof = LiveObservationProvider().observe(request)
    if not validate_live_observation_proof(live_proof):
        raise RuntimeError("R145_REAL_LIVE_PROOF_INVALID")

    source_records = [
        record
        for record in bundle.exact_objects
        if record.repository == DOMAIN_REPOSITORY and record.path == AI_FILM_AUTHORITY_PATH
    ]
    if len(source_records) != 1:
        raise RuntimeError("R145_REAL_AUTHORITY_SOURCE_NOT_EXACTLY_ONE")
    source = source_records[0]

    with temporary_exact_clone(
        f"https://github.com/{DOMAIN_REPOSITORY}.git", source.commit_sha
    ) as source_root:
        semantic_proof = exact_semantic_authority_proof(
            source_root,
            repository=DOMAIN_REPOSITORY,
            commit=source.commit_sha,
            path=AI_FILM_AUTHORITY_PATH,
            execution_id=f"r145-real-ai-film:{source.commit_sha[:16]}",
            governed_source_proof=live_proof,
            expected_identity=AI_FILM_EXPECTED_IDENTITY,
        )

    semantic_ref = semantic_authority_ref(semantic_proof)
    if semantic_ref.startswith("git://"):
        raise RuntimeError("R145_REAL_SEMANTIC_REF_INVALID")
    return {
        "status": "PASS",
        "provider_id": live_proof.provider_id,
        "provider_attribution_ref": live_proof.provider_attribution_ref,
        "provider_evidence_digest": live_proof.evidence_digest,
        "repository": source.repository,
        "canonical_commit": source.commit_sha,
        "authority_path": source.path,
        "authority_blob_sha": source.blob_sha,
        "authority_content_sha256": source.content_sha256,
        "semantic_authority_ref": semantic_ref,
        "semantic_identity": dict(AI_FILM_EXPECTED_IDENTITY),
        "raw_source_body_persisted": False,
        "cross_repo_write_performed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ledger = DurableSignalLedger(":memory:")
    awareness = SystemAwarenessProjection.from_canonical(
        ROOT, ledger.rebuild_projection(), ()
    )
    with temporary_exact_clone(
        "https://github.com/vxz2datoubo/eustia-ai-film.git", AI_FILM_COMMIT
    ) as source_root:
        receipt = ai_film_directing_read_only_smoke(
            source_root,
            awareness=awareness,
            fixture={
                "symptoms": ["左右反了"],
                "spatial": True,
                "feedback": True,
                "formal_scene_pixels": True,
            },
        )

    pr = _pull_request_event()
    if pr is None:
        receipt["r145_real_governed_authority"] = {
            "status": "NOT_APPLICABLE_NON_PULL_REQUEST_EVENT"
        }
    else:
        number = pr.get("number")
        if not isinstance(number, int) or number <= 0:
            raise RuntimeError("PULL_REQUEST_NUMBER_INVALID")
        repo_root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
        receipt["r145_real_governed_authority"] = _r145_real_governed_authority(
            repo_root, number
        )

    receipt["bounded_cleanup"] = "PASS"
    receipt["evidence_scope"] = "PUBLIC_SAFE_METADATA_ONLY"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
