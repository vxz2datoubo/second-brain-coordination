import dataclasses
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "coordination" / "GOVERNANCE" / "unified_execution_trust_gate.py"
spec = importlib.util.spec_from_file_location("unified_execution_trust_gate_compute_test", MODULE_PATH)
gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)
base = gate.base

MAIN = "a" * 40


def _identity():
    return {
        "control_plane_repository": base.TRUSTED_CONTROL_PLANE_REPOSITORY,
        "execution_repository": "vxz2datoubo/second-brain-coordination",
        "project_id": "SECOND_BRAIN",
        "task_id": "TASK-STD",
        "route_epoch": 185,
        "exact_base_sha": "b" * 40,
        "implementation_branch": "codex/standard-task",
        "collision_domain": "WRITESET_SHA256:test",
    }


def _authority(marker="fresh"):
    return base.VerifiedCanonicalAuthority(
        base._freeze({**_identity(), "canonical_main_sha": MAIN, "marker": marker}),
        base._ISSUER,
    )


def _compute(marker="fresh", carrier="CODEX_STANDARD_ESCALATION"):
    if carrier == "CODEX_STANDARD_ESCALATION":
        executor = "CODEX_STANDARD_ENGINEER"
        compute_class = "STANDARD"
        profile = "CODEX_STANDARD_ENGINEERING"
    else:
        executor = "CODEX_FRONTIER_ARCHITECT"
        compute_class = "FRONTIER"
        profile = "FRONTIER_ARCHITECTURE"
    return base.VerifiedComputeLaneAuthorization(
        base._freeze(
            {
                **_identity(),
                "canonical_main_sha": MAIN,
                "authorization_ref": "coordination/A/COMPUTE.yaml",
                "authorization_status": "AUTHORIZED",
                "executor": executor,
                "carrier": carrier,
                "compute_class": compute_class,
                "model_profile": profile,
                "marker": marker,
            }
        ),
        base._ISSUER,
    )


def _runtime_attestation(
    *,
    model="GPT-runtime-model",
    runtime_compute_class="STANDARD",
    invocation_mode="CODEX_CLI",
    dispatch_digest="sha256:lane",
    receipt="sha256:runtime",
    marker="fresh",
):
    return gate.VerifiedRuntimeModelClassificationAttestation(
        base._freeze(
            {
                **_identity(),
                "canonical_main_sha": MAIN,
                "attestation_ref": "coordination/A/RUNTIME-MODEL.yaml",
                "attestation_status": "ATTESTED",
                "resolved_model_display_name": model,
                "model_resolution_status": "RESOLVED",
                "runtime_compute_class": runtime_compute_class,
                "runtime_invocation_mode": invocation_mode,
                "classifier_provenance": "RUNTIME_DISCOVERY:test",
                "dispatch_compute_lane_receipt_digest": dispatch_digest,
                "compute_authorization_ref": "coordination/A/COMPUTE.yaml",
                "compute_authorization_receipt_digest": "sha256:compute",
                "runtime_model_attestation_receipt_digest": receipt,
                "marker": marker,
            }
        ),
        gate._RUNTIME_MODEL_ATTESTATION_ISSUER,
    )


def _runtime_bound_dispatch_and_admission():
    dispatch = {
        **_identity(),
        "carrier": "CODEX_STANDARD_ESCALATION",
        "compute_class": "STANDARD",
        "resolved_model_display_name": "GPT-runtime-model",
        "model_resolution_status": "RESOLVED",
        "compute_lane_receipt_digest": "sha256:lane",
        "compute_authorization_ref": "coordination/A/COMPUTE.yaml",
        "compute_authorization_receipt_digest": "sha256:compute",
        "runtime_invocation_mode": "CODEX_CLI",
        "runtime_model_attestation_ref": "coordination/A/RUNTIME-MODEL.yaml",
        "runtime_model_attestation_receipt_digest": "sha256:runtime",
    }
    admission = {
        "runtime_invocation_mode": "CODEX_CLI",
        "runtime_model_attestation_ref": "coordination/A/RUNTIME-MODEL.yaml",
        "runtime_model_attestation_receipt_digest": "sha256:runtime",
    }
    return dispatch, admission


class FreshComputeLaneProcessStartTests(unittest.TestCase):
    def test_codex_process_start_fails_without_canonical_compute_authorization(self):
        fresh = _authority()
        dispatch = {"carrier": "CODEX_STANDARD_ESCALATION"}
        with patch.object(gate, "validate_canonical_authority", return_value=fresh):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_process_start(".", {}, dispatch, fresh)

    def test_codex_process_start_substitutes_fresh_compute_and_runtime_attestations(self):
        fresh_authority = _authority()
        claimed_compute = _compute("claimed")
        fresh_compute = _compute("fresh")
        claimed_runtime = _runtime_attestation(marker="claimed")
        fresh_runtime = _runtime_attestation(marker="fresh")
        dispatch, admission = _runtime_bound_dispatch_and_admission()
        ref = "coordination/A/COMPUTE.yaml"
        runtime_ref = "coordination/A/RUNTIME-MODEL.yaml"

        with patch.object(
            gate, "validate_canonical_authority", return_value=fresh_authority
        ), patch.object(
            gate, "validate_compute_lane_authorization", return_value=fresh_compute
        ) as compute_validate, patch.object(
            base, "validate_local_admission"
        ) as admission_validate, patch.object(
            gate, "validate_runtime_model_attestation", return_value=fresh_runtime
        ) as runtime_validate:
            returned = gate.validate_process_start(
                ".",
                admission,
                dispatch,
                fresh_authority,
                ref,
                claimed_compute,
                runtime_ref,
                claimed_runtime,
            )

        self.assertIs(returned, fresh_authority)
        self.assertGreaterEqual(compute_validate.call_count, 1)
        admission_validate.assert_called_once()
        runtime_validate.assert_called_once_with(".", runtime_ref, claimed_runtime)

    def test_codex_process_start_fails_closed_without_runtime_attestation(self):
        fresh = _authority()
        dispatch, admission = _runtime_bound_dispatch_and_admission()
        with patch.object(
            gate,
            "_pre_runtime_attestation_validate_process_start",
            return_value=fresh,
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_process_start(
                    ".",
                    admission,
                    dispatch,
                    fresh,
                    "coordination/A/COMPUTE.yaml",
                    _compute(),
                )

    def test_stale_or_mutated_compute_snapshot_is_rejected_by_fresh_comparison(self):
        fresh = _compute("fresh")
        claimed = dataclasses.replace(
            fresh,
            _payload=base._freeze({**dict(fresh.as_mapping()), "marker": "forged"}),
        )
        with patch.object(gate, "_fresh_compute_lane_authorization", return_value=fresh):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_compute_lane_authorization(
                    ".", "coordination/A/COMPUTE.yaml", claimed
                )

    def test_stale_or_mutated_runtime_attestation_is_rejected_by_fresh_comparison(self):
        fresh = _runtime_attestation(marker="fresh")
        claimed = dataclasses.replace(
            fresh,
            _payload=base._freeze({**dict(fresh.as_mapping()), "marker": "forged"}),
        )
        with patch.object(gate, "_fresh_runtime_model_attestation", return_value=fresh):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_runtime_model_attestation(
                    ".", "coordination/A/RUNTIME-MODEL.yaml", claimed
                )

    def test_caller_supplied_runtime_classification_mapping_is_not_authority(self):
        with self.assertRaises(base.ExecutionContractError):
            gate._runtime_model_attestation_mapping(
                {
                    "runtime_compute_class": "STANDARD",
                    "resolved_model_display_name": "forged",
                }
            )

    def test_standard_authorization_cannot_start_frontier_attested_runtime(self):
        fresh = _authority()
        dispatch, admission = _runtime_bound_dispatch_and_admission()
        frontier_runtime = _runtime_attestation(runtime_compute_class="FRONTIER")
        with patch.object(
            gate,
            "_pre_runtime_attestation_validate_process_start",
            return_value=fresh,
        ), patch.object(
            gate, "validate_runtime_model_attestation", return_value=frontier_runtime
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_process_start(
                    ".",
                    admission,
                    dispatch,
                    fresh,
                    "coordination/A/COMPUTE.yaml",
                    _compute(),
                    "coordination/A/RUNTIME-MODEL.yaml",
                    frontier_runtime,
                )

    def test_runtime_model_substitution_with_recomputed_dispatch_receipt_is_rejected(self):
        fresh = _authority()
        dispatch, admission = _runtime_bound_dispatch_and_admission()
        dispatch["resolved_model_display_name"] = "substituted-runtime-model"
        dispatch["compute_lane_receipt_digest"] = "sha256:recomputed"
        runtime = _runtime_attestation()
        with patch.object(
            gate,
            "_pre_runtime_attestation_validate_process_start",
            return_value=fresh,
        ), patch.object(
            gate, "validate_runtime_model_attestation", return_value=runtime
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_process_start(
                    ".",
                    admission,
                    dispatch,
                    fresh,
                    "coordination/A/COMPUTE.yaml",
                    _compute(),
                    "coordination/A/RUNTIME-MODEL.yaml",
                    runtime,
                )

    def test_invocation_mode_substitution_is_rejected(self):
        fresh = _authority()
        dispatch, admission = _runtime_bound_dispatch_and_admission()
        dispatch["runtime_invocation_mode"] = "SUBSTITUTED_MODE"
        admission["runtime_invocation_mode"] = "SUBSTITUTED_MODE"
        runtime = _runtime_attestation(invocation_mode="CODEX_CLI")
        with patch.object(
            gate,
            "_pre_runtime_attestation_validate_process_start",
            return_value=fresh,
        ), patch.object(
            gate, "validate_runtime_model_attestation", return_value=runtime
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_process_start(
                    ".",
                    admission,
                    dispatch,
                    fresh,
                    "coordination/A/COMPUTE.yaml",
                    _compute(),
                    "coordination/A/RUNTIME-MODEL.yaml",
                    runtime,
                )

    def test_non_codex_process_start_rejects_injected_codex_compute_authorization(self):
        fresh = _authority()
        dispatch = {"carrier": "WORKBUDDY_CLI_HEADLESS"}
        with patch.object(gate, "validate_canonical_authority", return_value=fresh):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_process_start(
                    ".",
                    {},
                    dispatch,
                    fresh,
                    "coordination/A/COMPUTE.yaml",
                    _compute(),
                )

    def test_secure_compute_builder_rejects_duplicate_protected_keys(self):
        document = b'''control_plane_repository: "vxz2datoubo/second-brain-coordination"\nexecution_repository: "vxz2datoubo/second-brain-coordination"\nproject_id: "SECOND_BRAIN"\ntask_id: "TASK-STD"\nroute_epoch: 185\nexact_base_sha: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\nimplementation_branch: "codex/standard-task"\ncollision_domain: "WRITESET_SHA256:test"\nauthorization_status: "AUTHORIZED"\nexecutor: "CODEX_STANDARD_ENGINEER"\ncarrier: "CODEX_STANDARD_ESCALATION"\ncarrier: "CODEX_FRONTIER_ESCALATION"\ncompute_class: "STANDARD"\nmodel_profile: "CODEX_STANDARD_ENGINEERING"\nstandard_value_case_status: "PASS"\n'''

        def read(path):
            self.assertEqual(path, "coordination/A/COMPUTE.yaml")
            return document

        with patch.object(gate, "_protected_open", return_value=(MAIN, read)):
            with self.assertRaises(base.ExecutionContractError):
                gate._secure_build_verified_compute_lane_authorization(
                    ".", "coordination/A/COMPUTE.yaml"
                )

    def test_secure_runtime_attestation_builder_rejects_unclassified_runtime(self):
        document = b'''control_plane_repository: "vxz2datoubo/second-brain-coordination"\nexecution_repository: "vxz2datoubo/second-brain-coordination"\nproject_id: "SECOND_BRAIN"\ntask_id: "TASK-STD"\nroute_epoch: 185\nexact_base_sha: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\nimplementation_branch: "codex/standard-task"\ncollision_domain: "WRITESET_SHA256:test"\nattestation_status: "ATTESTED"\nresolved_model_display_name: "runtime-model"\nmodel_resolution_status: "RESOLVED"\nruntime_compute_class: "UNKNOWN"\nruntime_invocation_mode: "CODEX_CLI"\nclassifier_provenance: "RUNTIME_DISCOVERY:test"\ndispatch_compute_lane_receipt_digest: "sha256:lane"\ncompute_authorization_ref: "coordination/A/COMPUTE.yaml"\ncompute_authorization_receipt_digest: "sha256:compute"\n'''

        def read(path):
            self.assertEqual(path, "coordination/A/RUNTIME-MODEL.yaml")
            return document

        with patch.object(gate, "_protected_open", return_value=(MAIN, read)):
            with self.assertRaises(base.ExecutionContractError):
                gate._secure_build_verified_runtime_model_attestation(
                    ".", "coordination/A/RUNTIME-MODEL.yaml"
                )


if __name__ == "__main__":
    unittest.main()
