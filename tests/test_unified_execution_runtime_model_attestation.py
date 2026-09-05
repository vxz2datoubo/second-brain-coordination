import dataclasses
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "coordination" / "GOVERNANCE" / "unified_execution_trust_gate.py"
spec = importlib.util.spec_from_file_location("unified_execution_runtime_attestation_test", MODULE_PATH)
gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)
base = gate.base

MAIN = "a" * 40


def identity(task_id="TASK-STD"):
    return {
        "control_plane_repository": base.TRUSTED_CONTROL_PLANE_REPOSITORY,
        "execution_repository": "vxz2datoubo/second-brain-coordination",
        "project_id": "SECOND_BRAIN",
        "task_id": task_id,
        "route_epoch": 185,
        "exact_base_sha": "b" * 40,
        "implementation_branch": "codex/standard-task",
        "collision_domain": "WRITESET_SHA256:test",
    }


def authority():
    return base.VerifiedCanonicalAuthority(
        base._freeze({**identity(), "canonical_main_sha": MAIN}),
        base._ISSUER,
    )


def attestation(task_id="TASK-STD", *, receipt="sha256:runtime"):
    return gate.VerifiedRuntimeModelClassificationAttestation(
        base._freeze(
            {
                **identity(task_id),
                "canonical_main_sha": MAIN,
                "attestation_ref": "coordination/A/RUNTIME-MODEL.yaml",
                "attestation_status": "ATTESTED",
                "resolved_model_display_name": "runtime-model",
                "model_resolution_status": "RESOLVED",
                "runtime_compute_class": "STANDARD",
                "runtime_invocation_mode": "CODEX_CLI",
                "classifier_provenance": "RUNTIME_DISCOVERY:test",
                "dispatch_compute_lane_receipt_digest": "sha256:lane",
                "compute_authorization_ref": "coordination/A/COMPUTE.yaml",
                "compute_authorization_receipt_digest": "sha256:compute",
                "runtime_model_attestation_receipt_digest": receipt,
            }
        ),
        gate._RUNTIME_MODEL_ATTESTATION_ISSUER,
    )


def dispatch_and_admission():
    dispatch = {
        **identity(),
        "carrier": "CODEX_STANDARD_ESCALATION",
        "compute_class": "STANDARD",
        "resolved_model_display_name": "runtime-model",
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


class RuntimeModelAttestationAttackTests(unittest.TestCase):
    def test_cross_task_runtime_attestation_replay_fails_closed(self):
        dispatch, admission = dispatch_and_admission()
        with self.assertRaises(base.ExecutionContractError):
            gate._validate_runtime_model_binding(
                attestation("OTHER-TASK"), admission, dispatch, authority()
            )

    def test_attestation_receipt_substitution_fails_closed(self):
        dispatch, admission = dispatch_and_admission()
        dispatch["runtime_model_attestation_receipt_digest"] = "sha256:other"
        admission["runtime_model_attestation_receipt_digest"] = "sha256:other"
        with self.assertRaises(base.ExecutionContractError):
            gate._validate_runtime_model_binding(
                attestation(), admission, dispatch, authority()
            )

    def test_compute_authorization_rebinding_fails_closed(self):
        dispatch, admission = dispatch_and_admission()
        dispatch["compute_authorization_receipt_digest"] = "sha256:other-compute"
        with self.assertRaises(base.ExecutionContractError):
            gate._validate_runtime_model_binding(
                attestation(), admission, dispatch, authority()
            )

    def test_duplicate_runtime_compute_class_keys_fail_closed(self):
        document = b'''control_plane_repository: "vxz2datoubo/second-brain-coordination"\nexecution_repository: "vxz2datoubo/second-brain-coordination"\nproject_id: "SECOND_BRAIN"\ntask_id: "TASK-STD"\nroute_epoch: 185\nexact_base_sha: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\nimplementation_branch: "codex/standard-task"\ncollision_domain: "WRITESET_SHA256:test"\nattestation_status: "ATTESTED"\nresolved_model_display_name: "runtime-model"\nmodel_resolution_status: "RESOLVED"\nruntime_compute_class: "STANDARD"\nruntime_compute_class: "FRONTIER"\nruntime_invocation_mode: "CODEX_CLI"\nclassifier_provenance: "RUNTIME_DISCOVERY:test"\ndispatch_compute_lane_receipt_digest: "sha256:lane"\ncompute_authorization_ref: "coordination/A/COMPUTE.yaml"\ncompute_authorization_receipt_digest: "sha256:compute"\n'''

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
