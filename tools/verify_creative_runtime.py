"""Offline, exact-head reproducibility verifier for the creative runtime.

This is intentionally a verifier rather than a release/merge tool. It runs no
network clients, reads no credentials, and changes only a temporary workspace.
It provides a compact JSON receipt that an independent reviewer can reproduce
from a frozen commit without relying on executor chat history.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)


def _git_head() -> str:
    result = _run(["git", "rev-parse", "HEAD"])
    if result.returncode != 0:
        raise RuntimeError("Cannot resolve git HEAD: " + result.stderr.strip())
    return result.stdout.strip()


def _load_cli() -> Any:
    path = ROOT / "apps" / "cli" / "creativectl.py"
    spec = importlib.util.spec_from_file_location("creative_runtime_verifier_cli", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load creativectl")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _demo(cli: Any) -> dict[str, Any]:
    """Run a deterministic route crossing all new runtime integration points."""

    from creative_runtime.local_intake import LocalIntakePolicy, LocalIntakeProjection, local_intake_gate_report
    from creative_runtime.ledger import LedgerViolation
    from tools.build_replay_capsule_package import build_package as build_replay_capsule_package
    from tools.verify_replay_capsule_package import verify_package as verify_replay_capsule_package

    with tempfile.TemporaryDirectory(prefix="creative-runtime-verify-") as directory:
        workspace = Path(directory)
        coverage = cli.run(["coverage", "--scenario", "three_scene"])
        night_coverage = cli.run(["coverage", "--scenario", "night_signal"])
        harbor_coverage = cli.run(["coverage", "--scenario", "harbor_protocol"])
        director_coverage = cli.run(["director-coverage", "--scenario", "three_scene"])
        night_director_coverage = cli.run(["director-coverage", "--scenario", "night_signal"])
        harbor_director_coverage = cli.run(["director-coverage", "--scenario", "harbor_protocol"])
        director_review = cli.run(["director-review", "--scenario", "three_scene"])
        night_director_review = cli.run(["director-review", "--scenario", "night_signal"])
        harbor_director_review = cli.run(["director-review", "--scenario", "harbor_protocol"])
        cli.run(["--workspace", str(workspace), "init", "--scenario", "three_scene"])
        cli.run(["--workspace", str(workspace), "choose", "listen"])
        cli.run(["--workspace", str(workspace), "choose", "approach"])
        cli.run(["--workspace", str(workspace), "choose", "listen"])
        timeline = cli.run(["--workspace", str(workspace), "timeline"])
        director = cli.run(["--workspace", str(workspace), "director"])
        frame = cli.run(["--workspace", str(workspace), "frame"])
        experience = cli.run(["--workspace", str(workspace), "experience"])
        sequence = cli.run(["--workspace", str(workspace), "sequence"])
        replay_capsule = cli.run(["--workspace", str(workspace), "replay-capsule"])
        replay_capsule_package = build_replay_capsule_package(workspace / "verified-replay-package", workspace)
        replay_capsule_package_verification = verify_replay_capsule_package(
            workspace / "verified-replay-package", require_clean_worktree=False
        )
        catalogue = cli.run(["catalog", "--scenario", "night_signal"])
        harbor_catalogue = cli.run(["catalog", "--scenario", "harbor_protocol"])
        script_catalog = cli.run(["script-catalog"])
        director_v2 = cli.run(
            [
                "--workspace", str(workspace), "director-v2",
                "--script-id", "synthetic-three-scene",
                "--script-revision", "SyntheticThreeScene/v1",
                "--style-profile-id", "cinematic_live_action",
            ]
        )
        drama_workspace = workspace / "drama-manager"
        cli.run(["--workspace", str(drama_workspace), "init", "--script-id", "synthetic-harbor-protocol"])
        drama_proposal = cli.run(["--workspace", str(drama_workspace), "propose", "listen"])
        cli.run(["--workspace", str(drama_workspace), "choose", "listen"])
        drama_campaign = cli.run(["--workspace", str(drama_workspace), "campaign"])
        drama_coverage = cli.run(["drama-coverage", "--scenario", "harbor_protocol"])
        understanding = cli.run(["--workspace", str(workspace), "understanding"])
        derived = cli.run(
            [
                "--workspace",
                str(workspace),
                "knowledge",
                "derive",
                "A documented handoff can preserve an earned witness lead.",
            ]
        )
        generation = cli.run(["--workspace", str(workspace), "generate-offline"])
        generation_verification = cli.run(
            ["--workspace", str(workspace), "verify-generation", generation["receipt"]["receipt_id"]]
        )
        feedback = cli.run(
            [
                "--workspace",
                str(workspace),
                "feedback",
                generation["receipt"]["receipt_id"],
                "4",
                "The verified offline route keeps the established spatial axis clear.",
            ]
        )
        migration = cli.run(["--workspace", str(workspace), "migrate"])
        v2_binding = cli.run(["--workspace", str(workspace), "verify-v2"])
        session_receipt = cli.run(["--workspace", str(workspace), "session-receipt"])
        audit = cli.run(["--workspace", str(workspace), "audit"])
        slot_workspace = workspace / "named-slot"
        slot_prefix = ["--workspace", str(slot_workspace), "--slot", "route_b"]
        cli.run([*slot_prefix, "init", "--scenario", "three_scene"])
        cli.run([*slot_prefix, "choose", "listen"])
        cli.run([*slot_prefix, "choose", "approach"])
        cli.run([*slot_prefix, "choose", "listen"])
        slot_generation = cli.run([*slot_prefix, "generate-offline"])
        slot_feedback = cli.run(
            [*slot_prefix, "feedback", slot_generation["receipt"]["receipt_id"], "5", "The named route keeps its evidence isolated."]
        )
        slot_migration = cli.run([*slot_prefix, "migrate"])
        slot_v2_binding = cli.run([*slot_prefix, "verify-v2"])
        slot_audit = cli.run([*slot_prefix, "audit"])
        realtime_workspace = workspace / "realtime-guard"
        realtime_prefix = ["--workspace", str(realtime_workspace), "--slot", "live_route"]
        cli.run([*realtime_prefix, "init", "--scenario", "night_signal"])
        realtime_frame = cli.run([*realtime_prefix, "frame"])
        realtime_command = "cmd_0123456789abcdef0123"
        realtime_first = cli.run(
            [
                *realtime_prefix,
                "choose",
                "listen",
                "--expected-frame-id",
                realtime_frame["frame_id"],
                "--command-id",
                realtime_command,
            ]
        )
        realtime_retry = cli.run(
            [
                *realtime_prefix,
                "choose",
                "listen",
                "--expected-frame-id",
                realtime_frame["frame_id"],
                "--command-id",
                realtime_command,
            ]
        )
        try:
            cli.run([*realtime_prefix, "choose", "listen", "--expected-frame-id", realtime_frame["frame_id"]])
        except LedgerViolation:
            stale_frame_rejected = True
        else:
            stale_frame_rejected = False
        realtime_timeline = cli.run([*realtime_prefix, "timeline"])
        local_intake = local_intake_gate_report(
            LocalIntakeProjection(
                request_id="req_0123456789abcdef0123",
                customer_reference="cust_0123456789abcdef",
                consent_revision="consent-v1",
                input_hash="a" * 64,
                received_at="2030-01-01T00:00:00Z",
                retention_deadline="2030-01-31T00:00:00Z",
                content_rating="non_explicit",
                cost_limit_minor=0,
                provider_confirmation=False,
            ),
            observed_at="2030-01-02T00:00:00Z",
            policy=LocalIntakePolicy(
                policy_id="policy_0123456789abcdef",
                approved_consent_revisions=("consent-v1",),
                maximum_retention_seconds=31 * 24 * 60 * 60,
                maximum_cost_limit_minor=0,
            ),
        )
        return {
            "scenario": "three_scene",
            "route_coverage_status": coverage["status"],
            "route_coverage_count": coverage["route_count"],
            "route_coverage_transition_count": len(coverage["covered_transition_ids"]),
            "night_signal_coverage_status": night_coverage["status"],
            "night_signal_route_count": night_coverage["route_count"],
            "night_signal_transition_count": len(night_coverage["covered_transition_ids"]),
            "harbor_protocol_coverage_status": harbor_coverage["status"],
            "harbor_protocol_route_count": harbor_coverage["route_count"],
            "harbor_protocol_transition_count": len(harbor_coverage["covered_transition_ids"]),
            "director_coverage_status": director_coverage["status"],
            "director_coverage_state_count": director_coverage["state_count"],
            "night_signal_director_coverage_status": night_director_coverage["status"],
            "night_signal_director_coverage_state_count": night_director_coverage["state_count"],
            "harbor_protocol_director_coverage_status": harbor_director_coverage["status"],
            "harbor_protocol_director_coverage_state_count": harbor_director_coverage["state_count"],
            "director_review_status": director_review["status"],
            "director_review_card_count": director_review["card_count"],
            "night_signal_director_review_status": night_director_review["status"],
            "night_signal_director_review_card_count": night_director_review["card_count"],
            "harbor_protocol_director_review_status": harbor_director_review["status"],
            "harbor_protocol_director_review_card_count": harbor_director_review["card_count"],
            "timeline_status": timeline["status"],
            "timeline_hash": timeline["timeline_hash"],
            "timeline_entry_count": len(timeline["entries"]),
            "final_state": timeline["entries"][-1]["state"],
            "director_status": director["status"],
            "director_can_generate": director["quality_report"]["can_generate"],
            "frame_status": frame["status"],
            "frame_choice_count": len(frame["legal_choices"]),
            "frame_slot": frame["slot_id"],
            "frame_director_timeline_hash": frame["director"]["source_timeline_hash"],
            "experience_status": experience["status"],
            "experience_frame_count": len(experience["frames"]),
            "experience_timeline_hash": experience["timeline_hash"],
            "sequence_status": sequence["status"],
            "sequence_step_count": len(sequence["steps"]),
            "sequence_total_duration_seconds": sequence["total_duration_seconds"],
            "sequence_timeline_hash": sequence["timeline_hash"],
            "sequence_cut_relations": [step["cut_contract"]["axis_relation"] for step in sequence["steps"]],
            "replay_capsule_status": replay_capsule["status"],
            "replay_capsule_id": replay_capsule["capsule_id"],
            "replay_capsule_timeline_hash": replay_capsule["timeline_hash"],
            "replay_capsule_event_count": replay_capsule["source"]["event_count"],
            "replay_capsule_contains_caller_free_text": replay_capsule["boundary"]["contains_caller_free_text"],
            "replay_capsule_package_status": replay_capsule_package["status"],
            "replay_capsule_package_capsule_id": replay_capsule_package_verification["capsule_id"],
            "replay_capsule_package_timeline_hash": replay_capsule_package_verification["timeline_hash"],
            "replay_capsule_package_member_count": replay_capsule_package_verification["package_member_count"],
            "catalog_status": catalogue["status"],
            "catalog_transition_count": len(catalogue["covered_transition_ids"]),
            "harbor_catalog_status": harbor_catalogue["status"],
            "harbor_catalog_transition_count": len(harbor_catalogue["covered_transition_ids"]),
            "script_catalog_status": script_catalog["status"],
            "script_catalog_count": script_catalog["script_count"],
            "script_style_profile_count": len(script_catalog["style_profiles"]),
            "director_v2_status": director_v2["status"],
            "director_v2_schema": director_v2["brief"]["schema"],
            "director_v2_can_generate": director_v2["quality_report"]["can_generate"],
            "drama_proposal_status": drama_proposal["status"],
            "drama_proposal_schema": drama_proposal["proposal"]["schema"],
            "drama_selection_schema": drama_proposal["selection"]["schema"],
            "drama_campaign_status": drama_campaign["status"],
            "drama_campaign_opposition_status": drama_campaign["antagonist_states"][0]["status"],
            "drama_coverage_status": drama_coverage["status"],
            "drama_coverage_percent": drama_coverage["coverage_percent"],
            "understanding_status": understanding["status"],
            "drift_statuses": [item["status"] for item in understanding["drift_assessments"]],
            "knowledge_status": derived["status"],
            "knowledge_candidate_status": derived["verified_timeline_candidate"]["candidate"]["status"],
            "generation_status": generation["status"],
            "generation_verification_status": generation_verification["status"],
            "generation_simulated": generation["receipt"]["result"]["simulated"],
            "generation_timeline_hash": generation["receipt"]["source"]["timeline_hash"],
            "feedback_status": feedback["status"],
            "feedback_rating": feedback["feedback"]["rating"],
            "feedback_candidate_status": feedback["knowledge_candidate"]["status"],
            "feedback_canonical_write": feedback["canonical_write"],
            "migration_status": migration["status"],
            "v2_source_binding_status": v2_binding["status"],
            "v2_source_binding_timeline_hash": v2_binding["timeline_hash"],
            "session_receipt_status": session_receipt["status"],
            "session_receipt_contains_events": session_receipt["contains_event_records"],
            "session_receipt_contains_customer_material": session_receipt["contains_customer_material"],
            "audit_status": audit["status"],
            "audit_generation_receipt_count": len(audit["evidence"]["verified_offline_generation_receipts"]),
            "audit_feedback_count": len(audit["evidence"]["verified_feedback"]),
            "named_slot_id": slot_audit["story"]["slot_id"],
            "named_slot_generation_slot": slot_generation["receipt"]["source"]["slot_id"],
            "named_slot_feedback_slot": slot_feedback["feedback"]["slot_id"],
            "named_slot_migration_slot": slot_migration["slot_id"],
            "named_slot_v2_slot": slot_v2_binding["slot_id"],
            "named_slot_audit_generation_count": len(slot_audit["evidence"]["verified_offline_generation_receipts"]),
            "named_slot_audit_feedback_count": len(slot_audit["evidence"]["verified_feedback"]),
            "realtime_first_command_status": realtime_first["status"],
            "realtime_retry_status": realtime_retry["status"],
            "realtime_retry_frame_matches": realtime_retry["current_frame_id"] == realtime_first["current_frame_id"],
            "realtime_stale_frame_rejected": stale_frame_rejected,
            "realtime_event_count": len(realtime_timeline["entries"]),
            "local_intake_projection_status": local_intake["status"],
            "local_intake_external_authorized": local_intake["external_provider_authorized"],
            "local_intake_vault_accessed": local_intake["customer_vault_accessed"],
        }


def verify(
    expected_head: str | None = None,
    *,
    run_test_suite: bool = True,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    actual_head = _git_head()
    if expected_head is not None and actual_head != expected_head:
        raise RuntimeError(f"Exact-head mismatch: expected {expected_head}, actual {actual_head}")
    if require_clean_worktree:
        status = _run(["git", "status", "--porcelain"])
        if status.returncode != 0:
            raise RuntimeError("Cannot determine git worktree status: " + status.stderr.strip())
        if status.stdout.strip():
            raise RuntimeError("Verification requires a clean worktree; use a fresh clone or commit/checkpoint first")
    if run_test_suite:
        tests = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_creative*.py"])
        if tests.returncode != 0:
            raise RuntimeError("Creative test suite failed:\n" + tests.stdout + tests.stderr)
    diff = _run(["git", "diff", "--check"])
    if diff.returncode != 0:
        raise RuntimeError("git diff --check failed:\n" + diff.stdout + diff.stderr)
    demonstration = _demo(_load_cli())
    expected_demo = {
        "timeline_status": "timeline_verified",
        "route_coverage_status": "route_coverage_verified",
        "route_coverage_count": 6,
        "route_coverage_transition_count": 8,
        "night_signal_coverage_status": "route_coverage_verified",
        "night_signal_route_count": 12,
        "night_signal_transition_count": 14,
        "harbor_protocol_coverage_status": "route_coverage_verified",
        "harbor_protocol_route_count": 14,
        "harbor_protocol_transition_count": 12,
        "director_coverage_status": "director_coverage_verified",
        "director_coverage_state_count": 12,
        "night_signal_director_coverage_status": "director_coverage_verified",
        "night_signal_director_coverage_state_count": 24,
        "harbor_protocol_director_coverage_status": "director_coverage_verified",
        "harbor_protocol_director_coverage_state_count": 24,
        "director_review_status": "director_review_board_verified",
        "director_review_card_count": 12,
        "night_signal_director_review_status": "director_review_board_verified",
        "night_signal_director_review_card_count": 24,
        "harbor_protocol_director_review_status": "director_review_board_verified",
        "harbor_protocol_director_review_card_count": 24,
        "timeline_entry_count": 4,
        "director_status": "director_verified",
        "director_can_generate": True,
        "frame_status": "interactive_frame_verified",
        "frame_choice_count": 1,
        "frame_slot": "default",
        "experience_status": "experience_manifest_verified",
        "experience_frame_count": 4,
        "sequence_status": "sequence_plan_verified",
        "sequence_step_count": 4,
        "sequence_total_duration_seconds": 52,
        "sequence_cut_relations": ["initial_space_established", "same_scene_axis_held", "new_scene_axis_reestablished", "same_scene_axis_held"],
        "catalog_status": "scenario_catalog_verified",
        "catalog_transition_count": 14,
        "harbor_catalog_status": "scenario_catalog_verified",
        "harbor_catalog_transition_count": 12,
        "script_catalog_status": "synthetic_registry_verified",
        "script_catalog_count": 4,
        "script_style_profile_count": 4,
        "director_v2_status": "director_v2_verified",
        "director_v2_schema": "DirectorBrief/v2",
        "director_v2_can_generate": True,
        "drama_proposal_status": "proposal_verified",
        "drama_proposal_schema": "NarrativeProposal/v1",
        "drama_selection_schema": "DramaticBeatSelection/v1",
        "drama_campaign_status": "campaign_progression_verified",
        "drama_campaign_opposition_status": "pressuring",
        "drama_coverage_status": "primary_choice_consequences_verified",
        "drama_coverage_percent": 100,
        "understanding_status": "understanding_mapped",
        "drift_statuses": ["pass", "pass", "pass", "pass"],
        "knowledge_status": "pending_human_review",
        "knowledge_candidate_status": "pending_human_review",
        "generation_status": "offline_generation_recorded",
        "generation_verification_status": "offline_generation_verified",
        "generation_simulated": True,
        "feedback_status": "feedback_recorded",
        "feedback_rating": 4,
        "feedback_candidate_status": "pending_human_review",
        "feedback_canonical_write": False,
        "migration_status": "migrated",
        "v2_source_binding_status": "v2_source_verified",
        "session_receipt_status": "session_source_verified",
        "session_receipt_contains_events": False,
        "session_receipt_contains_customer_material": False,
        "audit_status": "workspace_audit_verified",
        "audit_generation_receipt_count": 1,
        "audit_feedback_count": 1,
        "named_slot_id": "route_b",
        "named_slot_generation_slot": "route_b",
        "named_slot_feedback_slot": "route_b",
        "named_slot_migration_slot": "route_b",
        "named_slot_v2_slot": "route_b",
        "named_slot_audit_generation_count": 1,
        "named_slot_audit_feedback_count": 1,
        "realtime_first_command_status": "chosen",
        "realtime_retry_status": "command_already_applied",
        "realtime_retry_frame_matches": True,
        "realtime_stale_frame_rejected": True,
        "realtime_event_count": 2,
        "local_intake_projection_status": "local_intake_projection_valid",
        "local_intake_external_authorized": False,
        "local_intake_vault_accessed": False,
    }
    for key, expected in expected_demo.items():
        if demonstration[key] != expected:
            raise RuntimeError(f"Demonstration mismatch for {key}: {demonstration[key]!r} != {expected!r}")
    if demonstration["v2_source_binding_timeline_hash"] != demonstration["timeline_hash"]:
        raise RuntimeError("v2 source binding does not match the verified timeline hash")
    if demonstration["generation_timeline_hash"] != demonstration["timeline_hash"]:
        raise RuntimeError("offline generation receipt does not match the verified timeline hash")
    if demonstration["frame_director_timeline_hash"] != demonstration["timeline_hash"]:
        raise RuntimeError("interactive frame director evidence does not match the verified timeline hash")
    if demonstration["experience_timeline_hash"] != demonstration["timeline_hash"]:
        raise RuntimeError("interactive experience is not bound to the verified timeline hash")
    if demonstration["sequence_timeline_hash"] != demonstration["timeline_hash"]:
        raise RuntimeError("interactive sequence is not bound to the verified timeline hash")
    return {
        "schema": "CreativeRuntimeVerificationReceipt/v1",
        "head_sha": actual_head,
        "unit_test_command": f"{sys.executable} -m unittest discover -s tests -p test_creative*.py",
        "unit_test_status": "pass" if run_test_suite else "skipped_for_verifier_self_test",
        "worktree_status": "clean_required_and_clean" if require_clean_worktree else "not_checked_for_verifier_self_test",
        "diff_check_status": "pass",
        "demonstration": demonstration,
        "authority_note": "Executor reproducibility evidence only; independent acceptance requires a separate reviewer.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify the offline creative runtime at an exact git head.")
    parser.add_argument("--expected-head", help="Require this exact commit SHA before running checks.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify(args.expected_head), ensure_ascii=False, sort_keys=True, indent=2))
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "message": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
