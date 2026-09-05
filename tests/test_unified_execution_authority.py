import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "coordination" / "GOVERNANCE" / "unified_execution_validation.py"
spec = importlib.util.spec_from_file_location("unified_execution_validation", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

MAIN_OLD = "a" * 40
MAIN_NEW = "b" * 40


def _adapter(project_id, execution_repo, aliases=()):
    alias_block = ""
    if aliases:
        alias_block = "authority_project_aliases:\n" + "".join(
            f'  - "{item}"\n' for item in aliases
        )
    return (
        f'schema_version: "1.2"\n'
        'adapter_schema: "PROJECT-EXECUTION-ADAPTER-v1"\n'
        f'project_id: "{project_id}"\n'
        'global_protocol_id: "UNIFIED-AGENT-EXECUTION-FABRIC-v1"\n'
        'inherits_global_invariants: true\n'
        'control_plane_repository: "vxz2datoubo/second-brain-coordination"\n'
        f'execution_repository: "{execution_repo}"\n'
        + alias_block
        + f'repositories:\n  - repo: "{execution_repo}"\n'
        'canonical_entrypoints:\n  - "ENTRY"\n'
        'authority:\n  source: "CANONICAL"\n'
        'allowed_execution_carriers:\n  - "WORKBUDDY_CLI_HEADLESS"\n'
        'default_model_profiles:\n  standard: "FAST_LOW_COST"\n'
        'collision_domains:\n  - "DOMAIN"\n'
        'tool_interfaces:\n  - id: "TOOL"\n'
        'hard_boundaries:\n  - "NO_SELF_REVIEW"\n  - "NO_SELF_MERGE"\n'
        'acceptance:\n  required:\n    - "CI"\n'
        'handoff:\n  rule: "EXPLICIT"\n'
    )


def _authority_files(lease_suffix="old"):
    refs = {
        "canonical_route": "coordination/ROUTES/TASK.yaml",
        "work_claim": "coordination/A/WORK-CLAIM.yaml",
        "task_lease": "coordination/A/TASK-LEASE.yaml",
        "executor_reservation": "coordination/A/EXECUTOR-RESERVATION.yaml",
        "prewrite_snapshot": "coordination/A/PREWRITE.yaml",
        "executable_batch": "coordination/A/BATCH.json",
    }
    active = (
        'task_id: "TASK-1"\nroute_epoch: 7\nstatus: "READY"\nexecution_allowed: true\n'
        'repository: "vxz2datoubo/second-brain-coordination"\n'
        f'canonical_route: "{refs["canonical_route"]}"\n'
        f'work_claim: "{refs["work_claim"]}"\n'
        f'task_lease: "{refs["task_lease"]}"\n'
        f'executor_reservation: "{refs["executor_reservation"]}"\n'
        f'prewrite_snapshot: "{refs["prewrite_snapshot"]}"\n'
        f'executable_batch: "{refs["executable_batch"]}"\n'
        'implementation_branch: "workbuddy/task-1"\n'
        'source_checkpoint:\n  exact_head: "'
        + ("c" * 40)
        + '"\n'
        'authorized_paths:\n  - "tests/workbuddy/**"\n  - "tools/workbuddy/**"\n'
        'hard_boundaries:\n  - "NO_SELF_MERGE"\n'
    )
    route = (
        'project: "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001"\n'
        'task_id: "TASK-1"\nroute_epoch: 7\nstatus: "READY"\nexecution_allowed: true\n'
        'write_ownership:\n  workbuddy_exclusive:\n'
        '    - "tests/workbuddy/**"\n    - "tools/workbuddy/**"\n'
    )
    lease = (
        'project: "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001"\n'
        'task_id: "TASK-1"\nroute_epoch: 7\nimplementation_branch: "workbuddy/task-1"\n'
        'lease_state: "ACTIVE"\nexecution_allowed: true\n'
        'exclusive_write_surface:\n  - "tests/workbuddy/**"\n  - "tools/workbuddy/**"\n'
        f'lease_nonce: "{lease_suffix}"\n'
    )
    return {
        mod.ACTIVE_TASK_INDEX_REF: active.encode(),
        refs["canonical_route"]: route.encode(),
        refs["work_claim"]: b'task_id: "TASK-1"\nroute_epoch: 7\n',
        refs["task_lease"]: lease.encode(),
        refs["executor_reservation"]: b'task_id: "TASK-1"\nroute_epoch: 7\n',
        refs["prewrite_snapshot"]: b'task_id: "TASK-1"\nroute_epoch: 7\n',
        refs["executable_batch"]: b'{"task_id":"TASK-1","route_epoch":7}',
        mod.PROJECT_ADAPTER_PATHS[0]: _adapter(
            "SECOND_BRAIN",
            "vxz2datoubo/second-brain-coordination",
            ("SECOND_BRAIN",),
        ).encode(),
        mod.PROJECT_ADAPTER_PATHS[1]: _adapter(
            "TRADING_SYSTEM",
            "vxz2datoubo/second-brain-coordination",
            ("TRADING_SYSTEM",),
        ).encode(),
        mod.PROJECT_ADAPTER_PATHS[2]: _adapter(
            "REALTIME_INTERACTIVE_FILM_GAME",
            "vxz2datoubo/second-brain-coordination",
            ("CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001",),
        ).encode(),
        mod.PROJECT_ADAPTER_PATHS[3]: _adapter(
            "AI_DIRECTOR", "vxz2datoubo/eustia-ai-film", ("AI_DIRECTOR",)
        ).encode(),
    }


def _verified_authority(main_sha=MAIN_OLD, lease_suffix="old"):
    files = _authority_files(lease_suffix)

    def read(path):
        return files[path]

    with patch.object(mod, "_open_trusted_main", return_value=(main_sha, read)):
        return mod.build_verified_canonical_authority(".")


def _dispatch(authority):
    current = authority.as_mapping()
    return {
        key: copy.deepcopy(current[key])
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


def _admission(authority, dispatch_obj, lease_id="lease-new", generation=2):
    result = copy.deepcopy(dispatch_obj)
    result.update(
        {
            "route_status": "READY",
            "execution_allowed": True,
            "writer_lease_id": lease_id,
            "writer_lease_generation": generation,
        }
    )
    return result


class CanonicalAuthorityTrustBoundaryTests(unittest.TestCase):
    def test_public_builder_issues_valid_authority(self):
        auth = _verified_authority()
        dispatch = _dispatch(auth)
        admission = _admission(auth, dispatch)
        mod.validate_dispatch(dispatch, auth)
        mod.validate_local_admission(admission, dispatch, auth)

    def test_fully_self_consistent_caller_fabricated_authority_is_rejected(self):
        auth = _verified_authority()
        fabricated = copy.deepcopy(dict(auth.as_mapping()))
        dispatch = _dispatch(auth)
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, fabricated)

    def test_substituted_path_and_grant_fail_closed(self):
        auth = _verified_authority()
        dispatch = _dispatch(auth)
        dispatch["authorized_paths"] = ["**"]
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, auth)
        dispatch = _dispatch(auth)
        dispatch["authority_grants"] = ["EXECUTE_TASK", "PLACE_ORDER"]
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, auth)

    def test_missing_route_status_fails_closed(self):
        auth = _verified_authority()
        dispatch = _dispatch(auth)
        admission = _admission(auth, dispatch)
        del admission["route_status"]
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_local_admission(admission, dispatch, auth)


class CarrierReleaseTrustBoundaryTests(unittest.TestCase):
    def _verified_release(self, old_auth, main_sha=MAIN_NEW):
        old = old_auth.as_mapping()
        release_ref = "coordination/RELEASES/TASK-1.yaml"
        release = (
            f'control_plane_repository: "{old["control_plane_repository"]}"\n'
            f'execution_repository: "{old["execution_repository"]}"\n'
            f'project_id: "{old["project_id"]}"\n'
            f'task_id: "{old["task_id"]}"\n'
            f'route_epoch: {old["route_epoch"]}\n'
            f'exact_base_sha: "{old["exact_base_sha"]}"\n'
            f'implementation_branch: "{old["implementation_branch"]}"\n'
            f'collision_domain: "{old["collision_domain"]}"\n'
            f'writer_lease_ref: "{old["authority_refs"]["task_lease_ref"]}"\n'
            f'released_lease_digest: "{old["authority_digests"]["task_lease_ref"]}"\n'
            'writer_lease_id: "lease-old"\nwriter_lease_generation: 4\n'
            'release_status: "RELEASED"\n'
        ).encode()

        def read(path):
            if path == release_ref:
                return release
            raise KeyError(path)

        with patch.object(mod, "_open_trusted_main", return_value=(main_sha, read)):
            return mod.build_verified_release_witness(".", release_ref)

    def test_valid_handoff_uses_verified_release_and_validates_new_admission(self):
        old_auth = _verified_authority(MAIN_OLD, "old")
        new_auth = _verified_authority(MAIN_NEW, "new")
        old_dispatch = _dispatch(old_auth)
        new_dispatch = _dispatch(new_auth)
        new_admission = _admission(new_auth, new_dispatch, "lease-new", 5)
        witness = self._verified_release(old_auth)
        old = old_auth.as_mapping()
        handoff = {
            **{key: old[key] for key in mod.COMMON_IDENTITY_FIELDS},
            "from_carrier": "WORKBUDDY_CLI_HEADLESS",
            "to_carrier": "WORKBUDDY_DESKTOP_INTERACTIVE",
            "checkpoint_head_sha": "d" * 40,
            "old_writer_lease_id": "lease-old",
            "old_writer_lease_generation": 4,
            "new_writer_admission_required": True,
        }
        mod.validate_carrier_handoff(
            handoff,
            old_dispatch,
            old_auth,
            witness,
            new_dispatch,
            new_admission,
            new_auth,
        )

    def test_fabricated_release_witness_is_rejected_even_if_fields_match(self):
        old_auth = _verified_authority(MAIN_OLD, "old")
        new_auth = _verified_authority(MAIN_NEW, "new")
        old_dispatch = _dispatch(old_auth)
        new_dispatch = _dispatch(new_auth)
        new_admission = _admission(new_auth, new_dispatch, "lease-new", 5)
        old = old_auth.as_mapping()
        handoff = {
            **{key: old[key] for key in mod.COMMON_IDENTITY_FIELDS},
            "from_carrier": "WORKBUDDY_CLI_HEADLESS",
            "to_carrier": "WORKBUDDY_DESKTOP_INTERACTIVE",
            "checkpoint_head_sha": "d" * 40,
            "old_writer_lease_id": "lease-old",
            "old_writer_lease_generation": 4,
            "new_writer_admission_required": True,
        }
        fabricated = {
            **{key: old[key] for key in mod.COMMON_IDENTITY_FIELDS},
            "writer_lease_ref": old["authority_refs"]["task_lease_ref"],
            "released_lease_digest": old["authority_digests"]["task_lease_ref"],
            "writer_lease_id": "lease-old",
            "writer_lease_generation": 4,
            "release_status": "RELEASED",
            "canonical_main_sha": MAIN_NEW,
            "release_receipt_digest": "sha256:caller-made",
        }
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_carrier_handoff(
                handoff,
                old_dispatch,
                old_auth,
                fabricated,
                new_dispatch,
                new_admission,
                new_auth,
            )


class AdapterSemanticTests(unittest.TestCase):
    def global_policy(self):
        return {
            "protocol_id": "UNIFIED-AGENT-EXECUTION-FABRIC-v1",
            "allowed_execution_carriers": sorted(mod.GLOBAL_CARRIERS),
            "non_weakenable_invariants": sorted(mod.NON_WEAKENABLE_INVARIANTS),
        }

    def test_actual_four_project_adapter_documents_are_semantically_validated(self):
        paths = (
            "coordination/EXECUTION/PROJECT-ADAPTERS/SECOND-BRAIN.yaml",
            "coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml",
            "coordination/EXECUTION/PROJECT-ADAPTERS/REALTIME-INTERACTIVE-FILM.yaml",
            "coordination/EXECUTION/PROJECT-ADAPTERS/AI-DIRECTOR.yaml",
        )
        for path in paths:
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                parsed = mod.parse_and_validate_project_adapter(text, self.global_policy())
                self.assertTrue(parsed["canonical_entrypoints"])
                self.assertTrue(parsed["tool_interfaces"])
                self.assertTrue(parsed["hard_boundaries"])

    def test_unsafe_adapter_authority_widening_is_rejected(self):
        text = (
            ROOT / "coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml"
        ).read_text(encoding="utf-8")
        mutated = text.replace("place_order_allowed: false", "place_order_allowed: true")
        with self.assertRaises(mod.ExecutionContractError):
            mod.parse_and_validate_project_adapter(mutated, self.global_policy())


if __name__ == "__main__":
    unittest.main()
