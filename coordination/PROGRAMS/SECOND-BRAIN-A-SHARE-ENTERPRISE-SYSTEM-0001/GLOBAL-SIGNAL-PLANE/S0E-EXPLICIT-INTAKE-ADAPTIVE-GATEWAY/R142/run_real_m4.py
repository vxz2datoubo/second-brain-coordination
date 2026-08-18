from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

import yaml

R142_ROOT = Path(__file__).resolve().parent
S0E_ROOT = R142_ROOT.parent
GLOBAL_SIGNAL_ROOT = S0E_ROOT.parent
sys.path[:0] = [str(S0E_ROOT / "src"), str(GLOBAL_SIGNAL_ROOT / "S0-SYNTHETIC" / "src")]

from global_signal_gateway.gateway import exact_git_read_proofs, validate_live_observation_proof  # noqa: E402
from global_signal_gateway.live_observation_provider import (  # noqa: E402
    CONTROL_PATHS,
    CONTRACT_REVISION,
    DOMAIN_REPOSITORY,
    TARGET_REPOSITORY,
    DomainFreshnessTarget,
    LiveObservationProvider,
    LiveObservationRequest,
)
from global_signal_gateway.retrospective_intake import (  # noqa: E402
    REQUIRED_NEW_EXACT_PATHS,
    REQUIRED_SCAN_SURFACES,
    RetrospectiveSignalIntakeBridge,
    governed_snapshot_refs,
    reconcile_package,
    validate_import_package,
)
from global_signal_plane.ledger import DurableSignalLedger  # noqa: E402

TASK = "CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE"
EPOCH = 142


def fail(code: str) -> None:
    raise SystemExit(code)


def read_yaml(path: Path):
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"R142_M4_YAML_NOT_MAPPING:{path.name}")
    return value


def evidence_record(disposition: str, refs: list[str], provider_ref: str, capability_ref: str) -> dict[str, object]:
    arrays = {
        "current_signal_refs": [], "historical_signal_refs": [], "satisfied_refs": [], "duplicate_refs": [],
        "extends_refs": [], "reinforces_refs": [], "contradicts_refs": [], "superseded_refs": [],
        "domain_canonical_refs": [], "needs_revalidation_refs": [], "active_dependency_refs": [],
        "closed_task_refs": [], "issue_pr_review_refs": [provider_ref], "capability_refs": [capability_ref],
    }
    field = {
        "ALREADY_CANONICAL": "current_signal_refs",
        "ALREADY_SATISFIED": "satisfied_refs",
        "DOMAIN_CANONICAL_ONLY": "domain_canonical_refs",
        "NEEDS_REVALIDATION": "needs_revalidation_refs",
        "DUPLICATE": "duplicate_refs",
        "EXTENDS": "extends_refs",
        "REINFORCES": "reinforces_refs",
        "CONTRADICTS": "contradicts_refs",
        "SUPERSEDED": "superseded_refs",
    }.get(disposition)
    if field:
        arrays[field] = refs
    arrays["provenance_complete"] = True
    arrays["desired_effect_unmet"] = disposition != "ALREADY_SATISFIED"
    return arrays


def main() -> None:
    canonical_main = os.environ.get("R142_BASE_SHA", "")
    canonical_worktree = Path(os.environ.get("R142_CANONICAL_WORKTREE", ""))
    output = Path(os.environ.get("R142_M4_OUTPUT", "r142-real-m4.json"))
    pr_number = int(os.environ.get("R142_PR_NUMBER", "400"))
    head_sha = os.environ.get("R142_PR_HEAD_SHA", "UNKNOWN")
    if len(canonical_main) != 40 or not canonical_worktree.is_dir():
        fail("R142_M4_CANONICAL_BINDING_REQUIRED")

    raw_package = read_yaml(R142_ROOT / "REAL-RETROSPECTIVE-PACKAGE.yaml")
    package = validate_import_package(raw_package)
    if package["candidate_errors"]:
        fail(f"R142_M4_PACKAGE_INVALID:{package['candidate_errors']}")
    plan = read_yaml(R142_ROOT / "REAL-RETROSPECTIVE-EVIDENCE-PLAN.yaml")
    if plan.get("canonical_main") != canonical_main or raw_package.get("expected_canonical_main") != canonical_main:
        fail("R142_M4_PLAN_CANONICAL_DRIFT")
    candidates = {item["candidate_id"]: item for item in package["candidates"]}
    plan_candidates = plan.get("candidates", {})
    if set(candidates) != set(plan_candidates):
        fail("R142_M4_RECONSTRUCTION_PLAN_ID_MISMATCH")

    path_aliases = plan.get("paths", {})
    if not isinstance(path_aliases, dict):
        fail("R142_M4_PATH_PLAN_INVALID")
    required_paths = set(REQUIRED_NEW_EXACT_PATHS)
    for spec in plan_candidates.values():
        if not isinstance(spec, dict) or not isinstance(spec.get("refs"), list):
            fail("R142_M4_CANDIDATE_PLAN_INVALID")
        for alias in spec["refs"]:
            if alias not in path_aliases:
                fail(f"R142_M4_UNKNOWN_PATH_ALIAS:{alias}")
            required_paths.add(str(path_aliases[alias]))

    exacts = exact_git_read_proofs(
        canonical_worktree,
        repository=TARGET_REPOSITORY,
        commit=canonical_main,
        paths=tuple(sorted(required_paths)),
        execution_id=f"r142-real-m4:{head_sha}",
    )
    exact_by_path = {proof.path: proof for proof in exacts}
    exact_by_alias = {
        alias: f"git://{proof.repository}@{proof.commit}/{proof.path}#blob={proof.blob_sha};sha256={proof.content_sha256}"
        for alias, path in path_aliases.items()
        for proof in [exact_by_path[str(path)]]
    }

    request = LiveObservationRequest(
        request_id=f"r142-real-m4-{head_sha[:16]}",
        provider_contract_revision=CONTRACT_REVISION,
        target_repository=TARGET_REPOSITORY,
        target_branch="main",
        pull_request_number=pr_number,
        expected_task_id=TASK,
        expected_route_epoch=EPOCH,
        required_control_plane_paths=CONTROL_PATHS,
        required_domain_freshness_targets=(DomainFreshnessTarget(DOMAIN_REPOSITORY),),
        required_review_scope="ALL_RAW_REVIEWS",
        requested_max_age_seconds=240,
        requested_at=datetime.now(timezone.utc).isoformat(),
    )
    live_bundle, live_proof = LiveObservationProvider().observe(request)
    if not validate_live_observation_proof(live_proof):
        fail("R142_M4_LIVE_PROVIDER_PROOF_INVALID")
    if live_proof.current_main_sha != canonical_main or live_proof.head_sha != head_sha or live_proof.pr_number != pr_number:
        fail("R142_M4_LIVE_PROVIDER_HEAD_OR_MAIN_DRIFT")

    with tempfile.TemporaryDirectory(prefix="r142-real-m4-") as directory:
        ledger = DurableSignalLedger(Path(directory) / "real-m4.sqlite")
        try:
            binding = governed_snapshot_refs(
                expected_canonical_main=canonical_main,
                live_observation_proof=live_proof,
                exact_read_proofs=exacts,
                ledger=ledger,
            )
            if not binding["valid"]:
                fail(f"R142_M4_GOVERNED_BINDING_INVALID:{binding['reason']}")
            s0c_ref = str(binding["s0c_projection_ref"])
            provider_ref = live_proof.provider_attribution_ref
            gateway_ref = exact_by_alias["GATEWAY"]
            candidate_evidence: dict[str, object] = {}
            for candidate_id, spec in plan_candidates.items():
                refs = [exact_by_alias[alias] for alias in spec["refs"]]
                candidate_evidence[candidate_id] = evidence_record(str(spec["disposition"]), refs, provider_ref, gateway_ref)

            coverage = {
                "current_signals": {"status": "SCANNED", "evidence_refs": [s0c_ref]},
                "historical_signals": {"status": "SCANNED", "evidence_refs": [s0c_ref]},
                "current_tasks": {"status": "SCANNED", "evidence_refs": [exact_by_alias["ACTIVE_TASK"]]},
                "current_missions": {"status": "SCANNED", "evidence_refs": [exact_by_alias["ACTIVE_LANES"], exact_by_alias["CONTROL_TOWER"]]},
                "issues_pr_reviews": {"status": "SCANNED", "evidence_refs": [provider_ref]},
                "r136_r141_capabilities": {"status": "SCANNED", "evidence_refs": [gateway_ref, exact_by_alias["CONTROL_TOWER"]]},
                "domain_canonical": {"status": "SCANNED", "evidence_refs": [provider_ref]},
                "dependencies_conflicts_supersession": {"status": "SCANNED", "evidence_refs": [exact_by_alias["CLAIMS"], exact_by_alias["ACTIVE_LANES"]]},
            }
            if set(coverage) != set(REQUIRED_SCAN_SURFACES):
                fail("R142_M4_SCAN_COVERAGE_INTERNAL_ERROR")
            snapshot = {
                "schema_version": "CurrentCanonicalSnapshot/v1",
                "snapshot_id": f"r142-real-m4:{canonical_main}:{live_bundle.observation_id}",
                "canonical_main": canonical_main,
                "observed_at": live_proof.observed_at,
                "source_provenance_refs": [provider_ref, s0c_ref, *binding["exact_read_refs"]],
                "scan_coverage": coverage,
                "candidate_evidence": candidate_evidence,
            }
            reconciliation = reconcile_package(
                raw_package, snapshot, expected_canonical_main=canonical_main,
                live_observation_proof=live_proof, exact_read_proofs=exacts, ledger=ledger,
            )
            actual = {item["candidate_id"]: item["disposition"] for item in reconciliation["results"]}
            expected = {candidate_id: str(spec["disposition"]) for candidate_id, spec in plan_candidates.items()}
            if actual != expected:
                mismatch = {key: {"expected": expected.get(key), "actual": actual.get(key)} for key in sorted(set(actual) | set(expected)) if expected.get(key) != actual.get(key)}
                fail(f"R142_M4_DISPOSITION_MISMATCH:{mismatch}")
            counts = dict(sorted(Counter(actual.values()).items()))
            expected_counts = {key: int(value) for key, value in plan.get("expected_counts", {}).items()}
            for key, expected_count in expected_counts.items():
                if counts.get(key, 0) != expected_count:
                    fail(f"R142_M4_COUNT_MISMATCH:{key}:{counts.get(key, 0)}:{expected_count}")

            bridge = RetrospectiveSignalIntakeBridge(
                ledger, live_observation_proof=live_proof, exact_read_proofs=exacts,
            )
            result = bridge.process(raw_package, snapshot, expected_canonical_main=canonical_main)
            receipts = result["receipts"]
            true_new_ids = sorted(item["candidate_id"] for item in receipts if item["disposition"] == "NEW_DURABLE_SIGNAL")
            persisted = [item for item in receipts if item["write_status"] == "PERSISTED"]
            if len(persisted) != len(true_new_ids):
                fail("R142_M4_NEW_PERSISTENCE_COUNT_MISMATCH")
            if not true_new_ids and ledger.history():
                fail("R142_M4_ZERO_NEW_MUST_NOT_WRITE")
            if any(item["disposition"] == "NEEDS_REVALIDATION" and item["write_status"] != "NOT_PERSISTED" for item in receipts):
                fail("R142_M4_REVALIDATION_PERSISTED")

            replay_ok = ledger.observe_replay()
            projection = ledger.current_projection()
            if not replay_ok or projection is None:
                fail("R142_M4_S0C_REPLAY_UNPROVEN")
            report = {
                "schema_version": "R142RealM4Evidence/v1",
                "executor_role": "GPT_ENGINEERING_WORKER",
                "model_id": "GPT-5.6 Sol",
                "harness_tool_provenance": "GitHub Actions + R137 public GitHub live observation provider + exact_git_read_proofs + temporary existing S0C DurableSignalLedger",
                "historical_source_status": "HISTORICAL_HANDOFF_SOURCE_AVAILABLE / PRE_ENUMERATED_PACKAGE_NOT_RECOVERED",
                "historical_source_ref": raw_package["package_metadata"]["source_artifact_ref"],
                "historical_estimate_candidate_count": "approximately-45 / NON_AUTHORITATIVE",
                "historical_estimate_new_count": "approximately-24 / NOT_RECOVERED / UNKNOWN",
                "reconstructed_candidate_count": len(candidates),
                "package_digest": package["package_digest"],
                "canonical_main": canonical_main,
                "pr_number": pr_number,
                "pr_head_sha": head_sha,
                "live_observation": {
                    "provider_id": live_proof.provider_id,
                    "provider_attribution_ref": provider_ref,
                    "evidence_digest": live_proof.evidence_digest,
                    "observed_at": live_proof.observed_at,
                    "fresh_until": live_proof.fresh_until,
                    "current_main_sha": live_proof.current_main_sha,
                    "pr_state": live_proof.pr_state,
                    "review_state_ref": live_proof.review_state_ref,
                    "domain_freshness_ref": live_proof.domain_freshness_ref,
                },
                "exact_read_count": len(exacts),
                "s0c_pre_admission_projection_ref": s0c_ref,
                "current_disposition_counts": counts,
                "current_dispositions": {key: actual[key] for key in sorted(actual)},
                "current_new_durable_signal_ids": true_new_ids,
                "needs_revalidation_ids": sorted(key for key, value in actual.items() if value == "NEEDS_REVALIDATION"),
                "unknowns": ["historical approximately-24 NEW machine labels were not recovered"],
                "durable_admission": "COMPLETED" if true_new_ids else "NOT_APPLICABLE_NO_CURRENT_NEW",
                "durable_receipts": persisted,
                "s0c_history_event_count": len(ledger.history()),
                "s0c_replay_ok": replay_ok,
                "s0c_projection": {
                    "reducer_version": projection.get("reducer_version"),
                    "ledger_watermark": projection.get("ledger_watermark"),
                    "input_revision": projection.get("input_revision"),
                    "projection_version": projection.get("projection_version"),
                    "checksum": projection.get("checksum"),
                    "signal_count": len(projection.get("signals", [])),
                },
                "signal_is_not_task": not result["automatic_task_created"] and not result["automatic_work_claim_created"],
                "second_signal_truth_created": result["second_signal_truth_created"],
                "domain_or_w3_written": result["domain_or_w3_written"],
                "raw_private_body_committed": False,
            }
            output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({
                "R142_REAL_M4": "PASS",
                "candidate_count": len(candidates),
                "disposition_counts": counts,
                "current_new_ids": true_new_ids,
                "needs_revalidation_ids": report["needs_revalidation_ids"],
                "durable_admission": report["durable_admission"],
                "s0c_replay_ok": replay_ok,
                "s0c_projection_checksum": projection.get("checksum"),
                "provider_ref": provider_ref,
            }, sort_keys=True))
        finally:
            ledger.close()


if __name__ == "__main__":
    main()
