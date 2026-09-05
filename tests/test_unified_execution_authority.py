import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "coordination" / "GOVERNANCE" / "unified_execution_validation.py"
spec = importlib.util.spec_from_file_location("unified_execution_validation", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def canonical_authority():
    refs = {
        "active_task_index_ref": "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
        "canonical_route_ref": "coordination/ROUTES/WORKBUDDY-R175-ORDERED-BATCH.yaml",
        "work_claim_ref": "coordination/.../WORK-CLAIM.yaml",
        "task_lease_ref": "coordination/.../TASK-LEASE.yaml",
        "executor_reservation_ref": "coordination/.../EXECUTOR-RESERVATION.yaml",
        "prewrite_snapshot_ref": "coordination/.../PREWRITE-RECONCILIATION-SNAPSHOT.yaml",
        "executable_batch_ref": "coordination/.../EXECUTABLE-BATCH.json",
    }
    digests = {key: f"sha256:{key}:0123456789" for key in refs}
    return {
        "control_plane_repository": "vxz2datoubo/second-brain-coordination",
        "execution_repository": "vxz2datoubo/second-brain-coordination",
        "project_id": "REALTIME_INTERACTIVE_FILM_GAME",
        "task_id": "WORKBUDDY-R175-ORDERED-BATCH",
        "route_epoch": 175,
        "exact_base_sha": "740788a3847a402923bf2e89093d910eda0c89d0",
        "implementation_branch": "workbuddy/r175-ordered-batch-execution",
        "collision_domain": "INTERACTIVE_FILM_PROGRAM_ROUTE",
        "canonical_main_sha": "04124e233dc813cca4054851ef6a470b342d82fe",
        "authority_chain_receipt_digest": "sha256:authority-chain:0123456789abcdef",
        "authority_refs": refs,
        "authority_digests": digests,
        "route_status": "READY",
        "execution_allowed": True,
        "lease_released": False,
        "lease_replaced": False,
        "authority_replaced": False,
        "fresh_readback": True,
        "authorized_paths": ["tests/workbuddy/**", "tools/workbuddy/**"],
        "authority_grants": ["WRITE_AUTHORIZED_PATHS"],
        "authority_denials": ["NO_DIRECT_MAIN", "NO_SELF_MERGE"],
    }


def dispatch(authority):
    return {
        key: copy.deepcopy(authority[key])
        for key in (
            *mod.COMMON_IDENTITY_FIELDS,
            "canonical_main_sha",
            "authority_chain_receipt_digest",
            "authority_refs",
            "authority_digests",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
        )
    }


def admission(authority, dispatch_obj):
    result = copy.deepcopy(dispatch_obj)
    result.update(
        {
            "route_status": "READY",
            "execution_allowed": True,
            "writer_lease_id": "lease-new",
            "writer_lease_generation": 2,
            "admitted": True,
        }
    )
    return result


class AuthorityBindingTests(unittest.TestCase):
    def test_valid_dispatch_and_admission(self):
        auth = canonical_authority()
        d = dispatch(auth)
        a = admission(auth, d)
        mod.validate_dispatch(d, auth)
        mod.validate_local_admission(a, d, auth)

    def test_stale_or_released_lease_fails_closed(self):
        auth = canonical_authority()
        auth["lease_released"] = True
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch(auth), auth)

    def test_replaced_authority_document_fails_closed(self):
        auth = canonical_authority()
        d = dispatch(auth)
        auth["authority_digests"]["task_lease_ref"] = "sha256:moved:abcdef0123456789"
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(d, auth)

    def test_substituted_authorized_path_fails_closed(self):
        auth = canonical_authority()
        d = dispatch(auth)
        d["authorized_paths"] = ["**"]
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(d, auth)

    def test_substituted_grant_fails_closed(self):
        auth = canonical_authority()
        d = dispatch(auth)
        d["authority_grants"] = ["WRITE_AUTHORIZED_PATHS", "PLACE_ORDER"]
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(d, auth)

    def test_missing_route_status_fails_closed(self):
        auth = canonical_authority()
        d = dispatch(auth)
        a = admission(auth, d)
        del a["route_status"]
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_local_admission(a, d, auth)

    def test_moved_main_fails_closed(self):
        auth = canonical_authority()
        d = dispatch(auth)
        d["canonical_main_sha"] = "moved"
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(d, auth)


class CarrierHandoffTests(unittest.TestCase):
    def setUp(self):
        self.identity = {
            "control_plane_repository": "vxz2datoubo/second-brain-coordination",
            "execution_repository": "vxz2datoubo/eustia-ai-film",
            "project_id": "AI_DIRECTOR",
            "task_id": "DIRECTOR-TASK-1",
            "route_epoch": 7,
            "exact_base_sha": "a" * 40,
            "implementation_branch": "workbuddy/director-task-1",
            "collision_domain": "DIRECTOR_RUNTIME_COMPILERS",
        }
        self.handoff = {
            **self.identity,
            "from_carrier": "WORKBUDDY_CLI_HEADLESS",
            "to_carrier": "WORKBUDDY_DESKTOP_INTERACTIVE",
            "checkpoint_head_sha": "b" * 40,
            "old_writer_lease_id": "lease-old",
            "old_writer_lease_generation": 4,
            "old_writer_release_receipt_digest": "sha256:release:0123456789",
            "release_readback_canonical_main_sha": "c" * 40,
            "new_writer_admission_required": True,
        }
        self.witness = {
            **self.identity,
            "writer_lease_id": "lease-old",
            "writer_lease_generation": 4,
            "release_status": "RELEASED",
            "release_receipt_digest": "sha256:release:0123456789",
            "canonical_readback_verified": True,
            "canonical_main_sha": "c" * 40,
        }
        self.new_admission = {
            **self.identity,
            "admitted": True,
            "writer_lease_id": "lease-new",
            "writer_lease_generation": 5,
        }

    def test_valid_handoff(self):
        mod.validate_carrier_handoff(self.handoff, self.witness, self.new_admission)

    def test_cross_task_release_replay_fails(self):
        witness = copy.deepcopy(self.witness)
        witness["task_id"] = "OTHER"
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_carrier_handoff(self.handoff, witness, self.new_admission)

    def test_old_epoch_release_replay_fails(self):
        witness = copy.deepcopy(self.witness)
        witness["route_epoch"] = 6
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_carrier_handoff(self.handoff, witness, self.new_admission)

    def test_wrong_branch_or_collision_fails(self):
        witness = copy.deepcopy(self.witness)
        witness["collision_domain"] = "OTHER"
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_carrier_handoff(self.handoff, witness, self.new_admission)

    def test_caller_asserted_release_without_canonical_readback_fails(self):
        witness = copy.deepcopy(self.witness)
        witness["canonical_readback_verified"] = False
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_carrier_handoff(self.handoff, witness, self.new_admission)


class AdapterSemanticTests(unittest.TestCase):
    def global_policy(self):
        return {
            "protocol_id": "UNIFIED-AGENT-EXECUTION-FABRIC-v1",
            "allowed_execution_carriers": sorted(mod.GLOBAL_CARRIERS),
            "non_weakenable_invariants": sorted(mod.NON_WEAKENABLE_INVARIANTS),
        }

    def adapter(self):
        return {
            "project_id": "AI_DIRECTOR",
            "global_protocol_id": "UNIFIED-AGENT-EXECUTION-FABRIC-v1",
            "inherits_global_invariants": True,
            "control_plane_repository": "vxz2datoubo/second-brain-coordination",
            "execution_repository": "vxz2datoubo/eustia-ai-film",
            "allowed_execution_carriers": ["WORKBUDDY_CLI_HEADLESS"],
        }

    def test_valid_narrowing_adapter(self):
        mod.validate_project_adapter(self.adapter(), self.global_policy())

    def test_unknown_carrier_fails(self):
        adapter = self.adapter()
        adapter["allowed_execution_carriers"].append("UNBOUNDED_SHELL")
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_project_adapter(adapter, self.global_policy())

    def test_invariant_weakening_fails(self):
        adapter = self.adapter()
        adapter["global_invariant_overrides"] = {"no_self_review": False}
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_project_adapter(adapter, self.global_policy())

    def test_second_global_router_fails(self):
        adapter = self.adapter()
        adapter["global_router"] = "project-local-router"
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_project_adapter(adapter, self.global_policy())


if __name__ == "__main__":
    unittest.main()
