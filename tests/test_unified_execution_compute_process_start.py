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


class FreshComputeLaneProcessStartTests(unittest.TestCase):
    def test_codex_process_start_fails_without_canonical_compute_authorization(self):
        fresh = _authority()
        dispatch = {"carrier": "CODEX_STANDARD_ESCALATION"}
        with patch.object(gate, "validate_canonical_authority", return_value=fresh):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_process_start(".", {}, dispatch, fresh)

    def test_codex_process_start_substitutes_fresh_compute_authorization(self):
        fresh_authority = _authority()
        claimed_compute = _compute("claimed")
        fresh_compute = _compute("fresh")
        dispatch = {"carrier": "CODEX_STANDARD_ESCALATION"}
        admission = {"admission": "candidate"}
        ref = "coordination/A/COMPUTE.yaml"

        with patch.object(
            gate, "validate_canonical_authority", return_value=fresh_authority
        ), patch.object(
            gate, "validate_compute_lane_authorization", return_value=fresh_compute
        ) as compute_validate, patch.object(
            base, "validate_local_admission"
        ) as admission_validate:
            returned = gate.validate_process_start(
                ".",
                admission,
                dispatch,
                fresh_authority,
                ref,
                claimed_compute,
            )

        self.assertIs(returned, fresh_authority)
        compute_validate.assert_called_once_with(".", ref, claimed_compute)
        admission_validate.assert_called_once_with(
            admission, dispatch, fresh_authority, fresh_compute
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


if __name__ == "__main__":
    unittest.main()
