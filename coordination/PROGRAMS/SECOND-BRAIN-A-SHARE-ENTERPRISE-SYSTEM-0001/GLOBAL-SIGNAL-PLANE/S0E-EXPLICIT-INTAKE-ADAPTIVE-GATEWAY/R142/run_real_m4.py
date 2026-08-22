from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping

import yaml

R142_ROOT = Path(__file__).resolve().parent
S0E_ROOT = R142_ROOT.parent
GLOBAL_SIGNAL_ROOT = S0E_ROOT.parent
sys.path[:0] = [str(S0E_ROOT / "src"), str(GLOBAL_SIGNAL_ROOT / "S0-SYNTHETIC" / "src")]

from global_signal_gateway.gateway import exact_git_read_proofs, validate_live_observation_proof  # noqa: E402
from global_signal_gateway.live_observation_provider import (  # noqa: E402
    ACTIVE_TASK_PATH, CONTROL_PATHS, CONTRACT_REVISION, DOMAIN_REPOSITORY, TARGET_REPOSITORY,
    DomainFreshnessTarget, LiveObservationProvider, LiveObservationRequest,
)
from global_signal_gateway.retrospective_evidence import (  # noqa: E402
    build_candidate_evidence, compare_post_hoc_oracle, expand_source_fragment_refs,
    verify_fact_catalog,
)
from global_signal_gateway.retrospective_intake import (  # noqa: E402
    REQUIRED_NEW_EXACT_PATHS, REQUIRED_SCAN_SURFACES, RetrospectiveSignalIntakeBridge,
    governed_snapshot_refs, reconcile_package, validate_import_package,
)
from global_signal_plane.ledger import DurableSignalLedger  # noqa: E402


def fail(code: str) -> None:
    raise SystemExit(code)


def read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"R142_M4_YAML_NOT_MAPPING:{path.name}")
    return value


def _exact_ref(proof: Any) -> str:
    return (
        f"git://{proof.repository}@{proof.commit}/{proof.path}"
        f"#blob={proof.blob_sha};sha256={proof.content_sha256}"
    )


def _policy_valid(plan: Mapping[str, Any]) -> bool:
    policy = plan.get("evidence_derivation_policy")
    if not isinstance(policy, Mapping):
        return False
    return bool(
        policy.get("expected_oracle_authoritative") is False
        and policy.get("expected_oracle_used_for_fact_selection") is False
        and policy.get("expected_oracle_used_for_evidence_slot_selection") is False
        and policy.get("oracle_mismatch_is_failure") is False
    )


def _current_observation_task(canonical_worktree: Path) -> tuple[str, int]:
    """Bind R137 observation to the exact current canonical task pointer.

    The R142 package is historical evidence.  The R137 provider, however,
    verifies current control-plane identity.  Reusing the stale R142 task id as
    if it were still active makes a fresh current observation impossible once a
    successor task exists.  Read the same exact-main ACTIVE_TASK_PATH that the
    provider itself validates, then let the provider independently bind its
    canonical route.
    """
    active = read_yaml(canonical_worktree / ACTIVE_TASK_PATH)
    task_id = active.get("task_id")
    route_epoch = active.get("route_epoch")
    canonical_route = active.get("canonical_route")
    if not isinstance(task_id, str) or not task_id or not isinstance(route_epoch, int):
        fail("R142_M4_CURRENT_TASK_BINDING_INVALID")
    if not isinstance(canonical_route, str) or not canonical_route.startswith("coordination/ROUTES/") or not canonical_route.endswith(".yaml"):
        fail("R142_M4_CURRENT_ROUTE_POINTER_INVALID")
    return task_id, route_epoch


def main() -> None:
    canonical_main = os.environ.get("R142_BASE_SHA", "")
    canonical_worktree = Path(os.environ.get("R142_CANONICAL_WORKTREE", ""))
    output = Path(os.environ.get("R142_M4_OUTPUT", "r142-real-m4.json"))
    pr_number = int(os.environ.get("R142_PR_NUMBER", "400"))
    head_sha = os.environ.get("R142_PR_HEAD_SHA", "UNKNOWN")
    if len(canonical_main) != 40 or not canonical_worktree.is_dir():
        fail("R142_M4_CANONICAL_BINDING_REQUIRED")

    source_package = read_yaml(R142_ROOT / "REAL-RETROSPECTIVE-PACKAGE.yaml")
    historical_package_main = source_package.get("expected_canonical_main")
    if not isinstance(historical_package_main, str) or len(historical_package_main) != 40:
        fail("R142_M4_HISTORICAL_PACKAGE_BINDING_INVALID")
    # The reconstructed package records the main that was current when its
    # historical source was reconstructed. R145 must reconcile that same
    # historical intent against the fresh canonical main, not freeze current
    # truth to the historical reconstruction commit.
    raw_package = expand_source_fragment_refs(source_package)
    raw_package["expected_canonical_main"] = canonical_main
    package = validate_import_package(raw_package)
    if package["candidate_errors"]:
        fail(f"R142_M4_PACKAGE_INVALID:{package['candidate_errors']}")

    plan = read_yaml(R142_ROOT / "REAL-RETROSPECTIVE-EVIDENCE-PLAN.yaml")
    if plan.get("schema_version") != "R142RealRetrospectiveEvidencePlan/v2":
        fail("R142_M4_EVIDENCE_PLAN_V2_REQUIRED")
    historical_plan_main = plan.get("canonical_main")
    if not isinstance(historical_plan_main, str) or len(historical_plan_main) != 40:
        fail("R142_M4_HISTORICAL_PLAN_BINDING_INVALID")
    if not _policy_valid(plan):
        fail("R142_M4_ORACLE_INDEPENDENCE_POLICY_REQUIRED")

    current_observation_task, current_observation_epoch = _current_observation_task(canonical_worktree)

    candidates = {item["candidate_id"]: item for item in package["candidates"]}
    bindings = plan.get("candidate_fact_bindings")
    catalog = plan.get("fact_catalog")
    paths = plan.get("paths")
    if not isinstance(bindings, Mapping) or set(bindings) != set(candidates):
        fail("R142_M4_CANDIDATE_FACT_BINDING_MISMATCH")
    if not isinstance(catalog, Mapping) or not isinstance(paths, Mapping):
        fail("R142_M4_FACT_PLAN_INVALID")

    used_aliases = {
        str(check["alias"])
        for spec in catalog.values() if isinstance(spec, Mapping)
        for check in spec.get("checks", []) if isinstance(check, Mapping) and "alias" in check
    }
    required_paths = set(REQUIRED_NEW_EXACT_PATHS)
    for alias in used_aliases:
        if alias not in paths:
            fail(f"R142_M4_FACT_ALIAS_UNKNOWN:{alias}")
        required_paths.add(str(paths[alias]))

    exacts = exact_git_read_proofs(
        canonical_worktree,
        repository=TARGET_REPOSITORY,
        commit=canonical_main,
        paths=tuple(sorted(required_paths)),
        execution_id=f"r142-real-m4:{head_sha}",
    )
    exact_by_path = {proof.path: proof for proof in exacts}
    exact_ref_by_alias = {
        alias: _exact_ref(exact_by_path[str(paths[alias])])
        for alias in used_aliases
    }
    text_by_alias = {
        alias: (canonical_worktree / str(paths[alias])).read_text(encoding="utf-8")
        for alias in used_aliases
    }
    fact_results = verify_fact_catalog(plan, text_by_alias, exact_ref_by_alias)

    request = LiveObservationRequest(
        request_id=f"r142-real-m4-{head_sha[:16]}",
        provider_contract_revision=CONTRACT_REVISION,
        target_repository=TARGET_REPOSITORY,
        target_branch="main",
        pull_request_number=pr_number,
        expected_task_id=current_observation_task,
        expected_route_epoch=current_observation_epoch,
        required_control_plane_paths=CONTROL_PATHS,
        required_domain_freshness_targets=(DomainFreshnessTarget(DOMAIN_REPOSITORY),),
        required_review_scope="ALL_RAW_REVIEWS",
        requested_max_age_seconds=240,
        requested_at=datetime.now(timezone.utc).isoformat(),
    )
    live_bundle, live_proof = LiveObservationProvider().observe(request)
    if not validate_live_observation_proof(live_proof):
        fail("R142_M4_LIVE_PROVIDER_PROOF_INVALID")
    if (
        live_proof.current_main_sha != canonical_main
        or live_proof.head_sha != head_sha
        or live_proof.pr_number != pr_number
    ):
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
            provider_ref = live_proof.provider_attribution_ref
            s0c_ref = str(binding["s0c_projection_ref"])
            gateway_path = str(paths["GATEWAY"])
            gateway_ref = _exact_ref(exact_by_path[gateway_path])

            candidate_evidence: dict[str, Any] = {}
            derivations: dict[str, Any] = {}
            for candidate_id, candidate_binding in bindings.items():
                evidence, derivation = build_candidate_evidence(
                    candidate_binding,
                    fact_results,
                    provider_ref=provider_ref,
                    capability_ref=gateway_ref,
                    domain_current_ref=live_proof.domain_freshness_ref,
                )
                candidate_evidence[str(candidate_id)] = evidence
                derivations[str(candidate_id)] = derivation

            required_ref_by_path = {proof.path: _exact_ref(proof) for proof in exacts}
            coverage = {
                "current_signals": {"status": "SCANNED", "evidence_refs": [s0c_ref]},
                "historical_signals": {"status": "SCANNED", "evidence_refs": [s0c_ref]},
                "current_tasks": {"status": "SCANNED", "evidence_refs": [
                    required_ref_by_path["coordination/ACTIVE-CODEX-TASK.yaml"]
                ]},
                "current_missions": {"status": "SCANNED", "evidence_refs": [
                    required_ref_by_path["coordination/ACTIVE-PROGRAM-LANES.yaml"],
                    required_ref_by_path["coordination/PROGRAM-CONTROL-TOWER.md"],
                ]},
                "issues_pr_reviews": {"status": "SCANNED", "evidence_refs": [provider_ref]},
                "r136_r141_capabilities": {"status": "SCANNED", "evidence_refs": [
                    gateway_ref,
                    required_ref_by_path["coordination/PROGRAM-CONTROL-TOWER.md"],
                ]},
                "domain_canonical": {"status": "SCANNED", "evidence_refs": [
                    live_proof.domain_freshness_ref, provider_ref
                ]},
                "dependencies_conflicts_supersession": {"status": "SCANNED", "evidence_refs": [
                    required_ref_by_path["coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"],
                    required_ref_by_path["coordination/ACTIVE-PROGRAM-LANES.yaml"],
                ]},
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
                raw_package,
                snapshot,
                expected_canonical_main=canonical_main,
                live_observation_proof=live_proof,
                exact_read_proofs=exacts,
                ledger=ledger,
            )
            actual = {
                item["candidate_id"]: item["disposition"]
                for item in reconciliation["results"]
            }
            counts = dict(sorted(Counter(actual.values()).items()))
            oracle_report = compare_post_hoc_oracle(
                actual, plan.get("post_hoc_oracle", {})
            )

            bridge = RetrospectiveSignalIntakeBridge(
                ledger,
                live_observation_proof=live_proof,
                exact_read_proofs=exacts,
            )
            result = bridge.process(
                raw_package, snapshot, expected_canonical_main=canonical_main
            )
            receipts = result["receipts"]
            true_new_ids = sorted(
                item["candidate_id"]
                for item in receipts
                if item["disposition"] == "NEW_DURABLE_SIGNAL"
            )
            persisted = [
                item for item in receipts if item["write_status"] == "PERSISTED"
            ]
            if len(persisted) != len(true_new_ids):
                fail("R142_M4_NEW_PERSISTENCE_COUNT_MISMATCH")
            if not true_new_ids and ledger.history():
                fail("R142_M4_ZERO_NEW_MUST_NOT_WRITE")
            if any(
                item["disposition"] == "NEEDS_REVALIDATION"
                and item["write_status"] != "NOT_PERSISTED"
                for item in receipts
            ):
                fail("R142_M4_REVALIDATION_PERSISTED")

            replay_ok = ledger.observe_replay()
            projection = ledger.current_projection()
            if not replay_ok or projection is None:
                fail("R142_M4_S0C_REPLAY_UNPROVEN")

            report = {
                "schema_version": "R142RealM4Evidence/v2",
                "executor_role": "GPT_ENGINEERING_WORKER",
                "model_id": "GPT-5.6 Sol",
                "harness_tool_provenance": (
                    "GitHub Actions + R137 public GitHub live observation provider + "
                    "exact_git_read_proofs + temporary existing S0C DurableSignalLedger"
                ),
                "historical_source_status": (
                    "HISTORICAL_HANDOFF_SOURCE_AVAILABLE / "
                    "SOURCE_FRAGMENT_PROVENANCE_REEXTRACTED"
                ),
                "historical_source_ref": source_package["package_metadata"]["source_artifact_ref"],
                "source_fragment_ref_semantics": source_package["package_metadata"].get(
                    "source_fragment_ref_semantics"
                ),
                "historical_package_canonical_main": historical_package_main,
                "historical_plan_canonical_main": historical_plan_main,
                "fresh_current_main_rebind": True,
                "current_observation_task_id": current_observation_task,
                "current_observation_route_epoch": current_observation_epoch,
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
                "fact_results": fact_results,
                "candidate_derivations": derivations,
                "post_hoc_oracle_comparison": oracle_report,
                "current_disposition_counts": counts,
                "current_dispositions": {key: actual[key] for key in sorted(actual)},
                "current_new_durable_signal_ids": true_new_ids,
                "needs_revalidation_ids": sorted(
                    key for key, value in actual.items()
                    if value == "NEEDS_REVALIDATION"
                ),
                "durable_admission": (
                    "COMPLETED" if true_new_ids
                    else "NOT_APPLICABLE_NO_CURRENT_NEW"
                ),
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
                "signal_is_not_task": (
                    not result["automatic_task_created"]
                    and not result["automatic_work_claim_created"]
                ),
                "second_signal_truth_created": result["second_signal_truth_created"],
                "domain_or_w3_written": result["domain_or_w3_written"],
                "raw_private_body_committed": False,
                "f03_self_fulfilling_evidence_removed": True,
                "f04_source_fragment_provenance_corrected": True,
            }
            output.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(json.dumps({
                "R142_REAL_M4": "PASS",
                "candidate_count": len(candidates),
                "disposition_counts": counts,
                "current_new_ids": true_new_ids,
                "needs_revalidation_ids": report["needs_revalidation_ids"],
                "oracle_matches": {
                    "candidate_count": oracle_report["candidate_count_matches_legacy"],
                    "disposition_counts": oracle_report["disposition_counts_match_legacy"],
                },
                "durable_admission": report["durable_admission"],
                "s0c_replay_ok": replay_ok,
                "s0c_projection_checksum": projection.get("checksum"),
                "provider_ref": provider_ref,
            }, sort_keys=True))
        finally:
            ledger.close()


if __name__ == "__main__":
    main()
