import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'coordination' / 'GOVERNANCE' / 'unified_execution_validation.py'
spec = importlib.util.spec_from_file_location('unified_execution_validation', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
MAIN_OLD = 'a' * 40
MAIN_NEW = 'b' * 40
BASE = 'c' * 40

def _thaw(value):
    if isinstance(value, dict) or hasattr(value, 'items'):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(item) for item in value]
    return value

def _adapter(project_id, execution_repo, aliases=()):
    alias_block = ''
    if aliases:
        alias_block = 'authority_project_aliases:\n' + ''.join((f'  - "{item}"\n' for item in aliases))
    return f'project_id: "{project_id}"\nglobal_protocol_id: "UNIFIED-AGENT-EXECUTION-FABRIC-v1"\ninherits_global_invariants: true\ncontrol_plane_repository: "vxz2datoubo/second-brain-coordination"\nexecution_repository: "{execution_repo}"\n' + alias_block + 'repositories:\n  - repo: "x"\ncanonical_entrypoints:\n  - "ENTRY"\nauthority:\n  source: "CANONICAL"\nallowed_execution_carriers:\n  - "WORKBUDDY_CLI_HEADLESS"\ndefault_model_profiles:\n  standard: "FAST_LOW_COST"\ncollision_domains:\n  - "DOMAIN"\ntool_interfaces:\n  - id: "TOOL"\nhard_boundaries:\n  - "NO_SELF_REVIEW"\n  - "NO_SELF_MERGE"\nacceptance:\n  required:\n    - "CI"\nhandoff:\n  rule: "EXPLICIT"\n'

def _authority_files(lease_suffix='old'):
    refs = {'canonical_route': 'coordination/ROUTES/TASK.yaml', 'work_claim': 'coordination/A/WORK-CLAIM.yaml', 'task_lease': 'coordination/A/TASK-LEASE.yaml', 'executor_reservation': 'coordination/A/EXECUTOR-RESERVATION.yaml', 'prewrite_snapshot': 'coordination/A/PREWRITE.yaml', 'executable_batch': 'coordination/A/BATCH.json'}
    paths = ['tests/workbuddy/**', 'tools/workbuddy/**']
    list_yaml = '\n'.join((f'  - "{p}"' for p in paths))
    active = f'''task_id: "TASK-1"\nroute_epoch: 7\nstatus: "READY"\nexecution_allowed: true\nrepository: "vxz2datoubo/second-brain-coordination"\ncanonical_route: "{refs['canonical_route']}"\nwork_claim: "{refs['work_claim']}"\ntask_lease: "{refs['task_lease']}"\nexecutor_reservation: "{refs['executor_reservation']}"\nprewrite_snapshot: "{refs['prewrite_snapshot']}"\nexecutable_batch: "{refs['executable_batch']}"\nimplementation_branch: "workbuddy/task-1"\nsource_checkpoint:\n  exact_head: "{BASE}"\nauthorized_paths:\n{list_yaml}\nhard_boundaries:\n  - "NO_SELF_MERGE"\n'''
    route = f'''repository: "vxz2datoubo/second-brain-coordination"\nproject: "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001"\ntask_id: "TASK-1"\nroute_epoch: 7\nstatus: "READY"\nexecution_allowed: true\nsource_checkpoint:\n  exact_head: "{BASE}"\nexecution:\n  implementation_branch: "workbuddy/task-1"\n  executable_batch: "{refs['executable_batch']}"\nwrite_ownership:\n  workbuddy_exclusive:\n    - "tests/workbuddy/**"\n    - "tools/workbuddy/**"\nbindings:\n  work_claim: "{refs['work_claim']}"\n  task_lease: "{refs['task_lease']}"\n  executor_reservation: "{refs['executor_reservation']}"\n  prewrite_snapshot: "{refs['prewrite_snapshot']}"\n  active_task: "{mod.ACTIVE_TASK_INDEX_REF}"\n'''
    claim = f'schema: "TaskLeaseClaim/v1"\nrepository: "vxz2datoubo/second-brain-coordination"\ntask_id: "TASK-1"\nroute_epoch: 7\nbranch: "workbuddy/task-1"\nstatus_observed: "READY"\nexecution_allowed_observed: true\nclaim_state: "ACTIVE"\nreviewed_or_base_head: "{BASE}"\nbranch_parent_required: "{BASE}"\nauthorized_paths:\n{list_yaml}\nhard_boundaries:\n  - "NO_SELF_MERGE"\n'
    lease = f'''schema: "TaskLease/v1"\nproject: "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001"\nrepository: "vxz2datoubo/second-brain-coordination"\ntask_id: "TASK-1"\nroute_epoch: 7\nimplementation_branch: "workbuddy/task-1"\nlease_state: "ACTIVE"\nexecution_allowed: true\nsubstantive_write_allowed: true\nsource_checkpoint: "{BASE}"\nexclusive_write_surface:\n{list_yaml}\nfreshness:\n  route: "{refs['canonical_route']}"\n  work_claim: "{refs['work_claim']}"\n  executor_reservation: "{refs['executor_reservation']}"\n  prewrite_snapshot: "{refs['prewrite_snapshot']}"\n  executable_batch: "{refs['executable_batch']}"\n  active_task: "{mod.ACTIVE_TASK_INDEX_REF}"\nlease_nonce: "{lease_suffix}"\n'''
    reservation = f'schema: "ExecutorReservation/v1"\nproject: "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001"\nrepository: "vxz2datoubo/second-brain-coordination"\ntask_id: "TASK-1"\nroute_epoch: 7\nreservation_state: "ACTIVE"\nimplementation_branch: "workbuddy/task-1"\nreservation_scope:\n{list_yaml}\nreservation_effect:\n  execution_identity_reserved: true\n  substantive_write_authorized_now: true\n'
    prewrite = f'''schema: "WorkBuddyPrewriteReconciliationSnapshot/v1"\nproject: "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001"\nrepository: "vxz2datoubo/second-brain-coordination"\ntask_id: "TASK-1"\nroute_epoch: 7\nsource_checkpoint:\n  immutable_checkpoint_exact_head: "{BASE}"\ncurrent_codex_route:\n  route_epoch: 7\n  status: "READY"\n  execution_allowed: true\nordered_batch:\n  executable_ref: "{refs['executable_batch']}"\nactivation_gate:\n  snapshot_precedes_workbuddy_branch: true\n  execution_allowed_now: false\n  requires_post_branch_fresh_readback: true\n  activation_commit_required: true\n'''
    batch = {'schema': 'CreativeExecutorWorkBatch/v1', 'project_id': 'CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001', 'authority': 'CANONICAL_BOUND_BATCH_EXECUTABLE', 'source_checkpoint': {'exact_head': BASE}, 'route_authority': {'execution_allowed': True, 'task_id': 'TASK-1', 'route_epoch': 7, 'route_ref': refs['canonical_route'], 'claim_ref': refs['work_claim'], 'lease_ref': refs['task_lease'], 'snapshot_ref': refs['prewrite_snapshot']}, 'items': [{'item_id': 'S1', 'write_paths': ['tests/workbuddy/unit/**']}, {'item_id': 'S2', 'write_paths': ['tools/workbuddy/unit/**']}]}
    return {mod.ACTIVE_TASK_INDEX_REF: active.encode(), refs['canonical_route']: route.encode(), refs['work_claim']: claim.encode(), refs['task_lease']: lease.encode(), refs['executor_reservation']: reservation.encode(), refs['prewrite_snapshot']: prewrite.encode(), refs['executable_batch']: json.dumps(batch).encode(), mod.PROJECT_ADAPTER_PATHS[0]: _adapter('SECOND_BRAIN', 'vxz2datoubo/second-brain-coordination', ('SECOND_BRAIN',)).encode(), mod.PROJECT_ADAPTER_PATHS[1]: _adapter('TRADING_SYSTEM', 'vxz2datoubo/second-brain-coordination', ('TRADING_SYSTEM',)).encode(), mod.PROJECT_ADAPTER_PATHS[2]: _adapter('REALTIME_INTERACTIVE_FILM_GAME', 'vxz2datoubo/second-brain-coordination', ('CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001',)).encode(), mod.PROJECT_ADAPTER_PATHS[3]: _adapter('AI_DIRECTOR', 'vxz2datoubo/eustia-ai-film', ('AI_DIRECTOR',)).encode()}

def _verified_authority(main_sha=MAIN_OLD, lease_suffix='old', mutate=None):
    files = _authority_files(lease_suffix)
    if mutate:
        mutate(files)

    def read(path):
        return files[path]
    with patch.object(mod, '_open_trusted_main', return_value=(main_sha, read)):
        return mod.build_verified_canonical_authority('.')

def _dispatch(authority):
    current = authority.as_mapping()
    return {key: _thaw(current[key]) for key in (*mod.COMMON_IDENTITY_FIELDS, 'canonical_main_sha', 'authority_chain_receipt_digest', 'authority_refs', 'authority_digests', 'authorized_paths', 'authority_grants', 'authority_denials', 'writer_lease_identity')}

def _admission(authority, dispatch_obj):
    result = copy.deepcopy(dispatch_obj)
    result.update({'route_status': 'READY', 'execution_allowed': True, 'writer_lease_identity': authority.as_mapping()['writer_lease_identity']})
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
        fabricated = _thaw(auth.as_mapping())
        dispatch = _dispatch(auth)
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, fabricated)

    def test_substituted_path_and_grant_fail_closed(self):
        auth = _verified_authority()
        dispatch = _dispatch(auth)
        dispatch['authorized_paths'] = ['**']
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, auth)
        dispatch = _dispatch(auth)
        dispatch['authority_grants'] = ['EXECUTE_TASK', 'PLACE_ORDER']
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, auth)

    def test_missing_route_status_fails_closed(self):
        auth = _verified_authority()
        dispatch = _dispatch(auth)
        admission = _admission(auth, dispatch)
        del admission['route_status']
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_local_admission(admission, dispatch, auth)

    def test_arbitrary_new_writer_lease_identity_fails_closed(self):
        auth = _verified_authority()
        dispatch = _dispatch(auth)
        admission = _admission(auth, dispatch)
        admission['writer_lease_identity'] = 'sha256:caller-made'
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_local_admission(admission, dispatch, auth)

class FullAuthorityChainSemanticTests(unittest.TestCase):

    def assert_mutation_rejected(self, mutate):
        with self.assertRaises(mod.ExecutionContractError):
            _verified_authority(mutate=mutate)

    def test_foreign_task_claim_rejected(self):

        def mutate(files):
            p = 'coordination/A/WORK-CLAIM.yaml'
            files[p] = files[p].replace(b'TASK-1', b'TASK-X', 1)
        self.assert_mutation_rejected(mutate)

    def test_foreign_epoch_claim_rejected(self):

        def mutate(files):
            p = 'coordination/A/WORK-CLAIM.yaml'
            files[p] = files[p].replace(b'route_epoch: 7', b'route_epoch: 8')
        self.assert_mutation_rejected(mutate)

    def test_inactive_claim_rejected(self):

        def mutate(files):
            p = 'coordination/A/WORK-CLAIM.yaml'
            files[p] = files[p].replace(b'claim_state: "ACTIVE"', b'claim_state: "RELEASED"')
        self.assert_mutation_rejected(mutate)

    def test_inactive_reservation_rejected(self):

        def mutate(files):
            p = 'coordination/A/EXECUTOR-RESERVATION.yaml'
            files[p] = files[p].replace(b'reservation_state: "ACTIVE"', b'reservation_state: "RELEASED"')
        self.assert_mutation_rejected(mutate)

    def test_narrowed_claim_scope_rejected(self):

        def mutate(files):
            p = 'coordination/A/WORK-CLAIM.yaml'
            files[p] = files[p].replace(b'  - "tools/workbuddy/**"\n', b'', 1)
        self.assert_mutation_rejected(mutate)

    def test_narrowed_reservation_scope_rejected(self):

        def mutate(files):
            p = 'coordination/A/EXECUTOR-RESERVATION.yaml'
            files[p] = files[p].replace(b'  - "tools/workbuddy/**"\n', b'', 1)
        self.assert_mutation_rejected(mutate)

    def test_mismatched_prewrite_checkpoint_rejected(self):

        def mutate(files):
            p = 'coordination/A/PREWRITE.yaml'
            files[p] = files[p].replace(BASE.encode(), b'd' * 40)
        self.assert_mutation_rejected(mutate)

    def test_batch_route_authority_mismatch_rejected(self):

        def mutate(files):
            p = 'coordination/A/BATCH.json'
            data = json.loads(files[p])
            data['route_authority']['route_epoch'] = 8
            files[p] = json.dumps(data).encode()
        self.assert_mutation_rejected(mutate)

    def test_batch_write_path_outside_authority_rejected(self):

        def mutate(files):
            p = 'coordination/A/BATCH.json'
            data = json.loads(files[p])
            data['items'][0]['write_paths'] = ['creative_runtime/**']
            files[p] = json.dumps(data).encode()
        self.assert_mutation_rejected(mutate)

class CarrierReleaseTrustBoundaryTests(unittest.TestCase):

    def _verified_release(self, old_auth, main_sha=MAIN_NEW):
        old = old_auth.as_mapping()
        release_ref = 'coordination/RELEASES/TASK-1.yaml'
        release = f'''control_plane_repository: "{old['control_plane_repository']}"\nexecution_repository: "{old['execution_repository']}"\nproject_id: "{old['project_id']}"\ntask_id: "{old['task_id']}"\nroute_epoch: {old['route_epoch']}\nexact_base_sha: "{old['exact_base_sha']}"\nimplementation_branch: "{old['implementation_branch']}"\ncollision_domain: "{old['collision_domain']}"\nwriter_lease_ref: "{old['authority_refs']['task_lease_ref']}"\nreleased_lease_digest: "{old['authority_digests']['task_lease_ref']}"\nwriter_lease_identity: "{old['writer_lease_identity']}"\nrelease_status: "RELEASED"\n'''.encode()

        def read(path):
            if path == release_ref:
                return release
            raise KeyError(path)
        with patch.object(mod, '_open_trusted_main', return_value=(main_sha, read)):
            return mod.build_verified_release_witness('.', release_ref)

    def test_valid_handoff_uses_verified_release_and_canonical_new_writer_identity(self):
        old_auth = _verified_authority(MAIN_OLD, 'old')
        new_auth = _verified_authority(MAIN_NEW, 'new')
        old_dispatch = _dispatch(old_auth)
        new_dispatch = _dispatch(new_auth)
        new_admission = _admission(new_auth, new_dispatch)
        witness = self._verified_release(old_auth)
        old = old_auth.as_mapping()
        handoff = {**{key: old[key] for key in mod.COMMON_IDENTITY_FIELDS}, 'from_carrier': 'WORKBUDDY_CLI_HEADLESS', 'to_carrier': 'WORKBUDDY_DESKTOP_INTERACTIVE', 'checkpoint_head_sha': 'd' * 40, 'old_writer_lease_identity': old['writer_lease_identity'], 'new_writer_admission_required': True}
        mod.validate_carrier_handoff(handoff, old_dispatch, old_auth, witness, new_dispatch, new_admission, new_auth)

    def test_fabricated_release_witness_is_rejected(self):
        old_auth = _verified_authority(MAIN_OLD, 'old')
        new_auth = _verified_authority(MAIN_NEW, 'new')
        old_dispatch = _dispatch(old_auth)
        new_dispatch = _dispatch(new_auth)
        new_admission = _admission(new_auth, new_dispatch)
        old = old_auth.as_mapping()
        handoff = {**{key: old[key] for key in mod.COMMON_IDENTITY_FIELDS}, 'from_carrier': 'WORKBUDDY_CLI_HEADLESS', 'to_carrier': 'WORKBUDDY_DESKTOP_INTERACTIVE', 'checkpoint_head_sha': 'd' * 40, 'old_writer_lease_identity': old['writer_lease_identity'], 'new_writer_admission_required': True}
        fabricated = {**{key: old[key] for key in mod.COMMON_IDENTITY_FIELDS}, 'writer_lease_ref': old['authority_refs']['task_lease_ref'], 'released_lease_digest': old['authority_digests']['task_lease_ref'], 'writer_lease_identity': old['writer_lease_identity'], 'release_status': 'RELEASED', 'canonical_main_sha': MAIN_NEW, 'release_receipt_digest': 'sha256:caller-made'}
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_carrier_handoff(handoff, old_dispatch, old_auth, fabricated, new_dispatch, new_admission, new_auth)

    def test_changed_new_lease_rejects_caller_claimed_writer_identity(self):
        old_auth = _verified_authority(MAIN_OLD, 'old')
        new_auth = _verified_authority(MAIN_NEW, 'new')
        old_dispatch = _dispatch(old_auth)
        new_dispatch = _dispatch(new_auth)
        new_admission = _admission(new_auth, new_dispatch)
        new_admission['writer_lease_identity'] = old_auth.as_mapping()['writer_lease_identity']
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_local_admission(new_admission, new_dispatch, new_auth)

class AdapterSemanticTests(unittest.TestCase):

    def global_policy(self):
        return {'protocol_id': 'UNIFIED-AGENT-EXECUTION-FABRIC-v1', 'allowed_execution_carriers': sorted(mod.GLOBAL_CARRIERS), 'non_weakenable_invariants': sorted(mod.NON_WEAKENABLE_INVARIANTS)}

    def test_actual_four_project_adapter_documents_are_semantically_validated(self):
        for path in mod.PROJECT_ADAPTER_PATHS:
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding='utf-8')
                parsed = mod.parse_and_validate_project_adapter(text, self.global_policy())
                self.assertTrue(parsed['canonical_entrypoints'])
                self.assertTrue(parsed['tool_interfaces'])
                self.assertTrue(parsed['hard_boundaries'])

    def test_trading_order_authority_cannot_be_reworded_to_permissive_value(self):
        path = ROOT / 'coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml'
        text = path.read_text(encoding='utf-8')
        mutated = text.replace('order_authority: "SEPARATE_EXPLICIT_OWNER_GATE"', 'order_authority: "GENERIC_ENGINEERING_ROUTE"')
        with self.assertRaises(mod.ExecutionContractError):
            mod.parse_and_validate_project_adapter(mutated, self.global_policy())

    def test_trading_place_order_boolean_cannot_widen(self):
        path = ROOT / 'coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml'
        text = path.read_text(encoding='utf-8')
        mutated = text.replace('place_order_allowed: false', 'place_order_allowed: true')
        with self.assertRaises(mod.ExecutionContractError):
            mod.parse_and_validate_project_adapter(mutated, self.global_policy())

    def test_project_hard_boundary_removal_is_rejected(self):
        path = ROOT / 'coordination/EXECUTION/PROJECT-ADAPTERS/AI-DIRECTOR.yaml'
        text = path.read_text(encoding='utf-8')
        mutated = text.replace('  - "NO_SECOND_DIRECTOR_AUTHORITY"\n', '')
        with self.assertRaises(mod.ExecutionContractError):
            mod.parse_and_validate_project_adapter(mutated, self.global_policy())
if __name__ == '__main__':
    unittest.main()
