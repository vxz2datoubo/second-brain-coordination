"""Regression overlay for executable compute-lane admission.

The pre-remediation authority tests are executed first, then their dispatch helper is upgraded
so every existing trust-boundary story also exercises the required compute-lane fields.
"""
from pathlib import Path as _BootstrapPath

_base_path = _BootstrapPath(__file__).with_name("test_unified_execution_authority_base.py")
exec(compile(_base_path.read_text(encoding="utf-8"), str(_base_path), "exec"), globals(), globals())
del _base_path, _BootstrapPath

_base_dispatch = _dispatch


def _dispatch(
    authority,
    *,
    executor="WORKBUDDY_ENGINEERING_EXECUTOR",
    carrier="WORKBUDDY_CLI_HEADLESS",
    compute_class="STANDARD",
    model_profile="DEEP_ENGINEERING",
    resolved_model_display_name="Deepseek-V4-Pro",
):
    result = _base_dispatch(authority)
    result.update(
        {
            "executor": executor,
            "carrier": carrier,
            "compute_class": compute_class,
            "model_profile": model_profile,
            "resolved_model_display_name": resolved_model_display_name,
            "model_resolution_status": "RESOLVED",
        }
    )
    result["compute_lane_receipt_digest"] = mod.compute_lane_receipt_digest(result)
    return result


def _verified_compute_authorization(
    authority,
    *,
    carrier="CODEX_STANDARD_ESCALATION",
    owner_frontier_authorized=True,
    frontier_value_gate_status="PASS",
    frontier_gate_condition="ARCHITECTURE_LEVERAGE",
):
    current = authority.as_mapping()
    ref = "coordination/A/COMPUTE-LANE-AUTHORIZATION.yaml"
    if carrier == "CODEX_STANDARD_ESCALATION":
        executor = "CODEX_STANDARD_ENGINEER"
        compute_class = "STANDARD"
        profile = "CODEX_STANDARD_ENGINEERING"
        evidence = 'standard_value_case_status: "PASS"\n'
    else:
        executor = "CODEX_FRONTIER_ARCHITECT"
        compute_class = "FRONTIER"
        profile = "FRONTIER_ARCHITECTURE"
        owner = "true" if owner_frontier_authorized else "false"
        evidence = (
            f'frontier_value_gate_status: "{frontier_value_gate_status}"\n'
            f'owner_frontier_authorized: {owner}\n'
            f'frontier_gate_condition: "{frontier_gate_condition}"\n'
            'bounded_question_set_digest: "sha256:questions"\n'
            'fallback_if_frontier_unavailable: "RETURN_TO_GPT_PLUS_WORKBUDDY_OR_CODEX_STANDARD"\n'
        )
    document = (
        f'control_plane_repository: "{current["control_plane_repository"]}"\n'
        f'execution_repository: "{current["execution_repository"]}"\n'
        f'project_id: "{current["project_id"]}"\n'
        f'task_id: "{current["task_id"]}"\n'
        f'route_epoch: {current["route_epoch"]}\n'
        f'exact_base_sha: "{current["exact_base_sha"]}"\n'
        f'implementation_branch: "{current["implementation_branch"]}"\n'
        f'collision_domain: "{current["collision_domain"]}"\n'
        'authorization_status: "AUTHORIZED"\n'
        f'executor: "{executor}"\n'
        f'carrier: "{carrier}"\n'
        f'compute_class: "{compute_class}"\n'
        f'model_profile: "{profile}"\n'
        + evidence
    ).encode()

    def read(path):
        if path == ref:
            return document
        raise KeyError(path)

    with patch.object(mod, "_open_trusted_main", return_value=(current["canonical_main_sha"], read)):
        return mod.build_verified_compute_lane_authorization(".", ref)


def _codex_dispatch(authority, compute_authorization, *, frontier=False):
    authorized = compute_authorization.as_mapping()
    dispatch = _dispatch(
        authority,
        executor=authorized["executor"],
        carrier=authorized["carrier"],
        compute_class=authorized["compute_class"],
        model_profile=authorized["model_profile"],
        resolved_model_display_name="GPT-6 Astra" if frontier else "GPT-5.6",
    )
    dispatch["compute_authorization_ref"] = authorized["authorization_ref"]
    dispatch["compute_authorization_receipt_digest"] = authorized["compute_authorization_receipt_digest"]
    dispatch["compute_lane_receipt_digest"] = mod.compute_lane_receipt_digest(dispatch)
    return dispatch


class ComputeLaneTrustBoundaryTests(unittest.TestCase):
    def test_codex_standard_is_first_class_global_carrier(self):
        self.assertIn("CODEX_STANDARD_ESCALATION", mod.GLOBAL_CARRIERS)

    def test_compute_lane_field_omission_fails_closed(self):
        auth = _verified_authority()
        dispatch = _dispatch(auth)
        del dispatch["carrier"]
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, auth)

    def test_unresolved_model_fails_closed(self):
        auth = _verified_authority()
        dispatch = _dispatch(auth)
        dispatch["model_resolution_status"] = "UNKNOWN"
        dispatch["compute_lane_receipt_digest"] = mod.compute_lane_receipt_digest(dispatch)
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, auth)

    def test_valid_codex_standard_dispatch_requires_verified_authorization(self):
        auth = _verified_authority()
        compute_auth = _verified_compute_authorization(auth)
        dispatch = _codex_dispatch(auth, compute_auth)
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, auth)
        mod.validate_dispatch(dispatch, auth, compute_auth)
        admission = _admission(auth, dispatch)
        mod.validate_local_admission(admission, dispatch, auth, compute_auth)

    def test_standard_to_frontier_mutation_cannot_reuse_same_writer_and_standard_authorization(self):
        auth = _verified_authority()
        standard_auth = _verified_compute_authorization(auth)
        dispatch = _codex_dispatch(auth, standard_auth)
        dispatch.update(
            {
                "executor": "CODEX_FRONTIER_ARCHITECT",
                "carrier": "CODEX_FRONTIER_ESCALATION",
                "compute_class": "FRONTIER",
                "model_profile": "FRONTIER_ARCHITECTURE",
                "resolved_model_display_name": "GPT-6 Astra",
            }
        )
        dispatch["compute_lane_receipt_digest"] = mod.compute_lane_receipt_digest(dispatch)
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_dispatch(dispatch, auth, standard_auth)

    def test_frontier_dispatch_requires_value_gate_and_owner_authorization(self):
        auth = _verified_authority()
        with self.assertRaises(mod.ExecutionContractError):
            _verified_compute_authorization(
                auth,
                carrier="CODEX_FRONTIER_ESCALATION",
                owner_frontier_authorized=False,
            )
        with self.assertRaises(mod.ExecutionContractError):
            _verified_compute_authorization(
                auth,
                carrier="CODEX_FRONTIER_ESCALATION",
                frontier_value_gate_status="DENY",
            )
        frontier_auth = _verified_compute_authorization(auth, carrier="CODEX_FRONTIER_ESCALATION")
        dispatch = _codex_dispatch(auth, frontier_auth, frontier=True)
        mod.validate_dispatch(dispatch, auth, frontier_auth)

    def test_local_admission_detects_model_or_lane_mutation(self):
        auth = _verified_authority()
        compute_auth = _verified_compute_authorization(auth)
        dispatch = _codex_dispatch(auth, compute_auth)
        admission = _admission(auth, dispatch)
        admission["resolved_model_display_name"] = "GPT-6 Astra"
        with self.assertRaises(mod.ExecutionContractError):
            mod.validate_local_admission(admission, dispatch, auth, compute_auth)

    def test_all_project_adapters_admit_standard_without_widening_trading_order_authority(self):
        for path in mod.PROJECT_ADAPTER_PATHS:
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn('  - "CODEX_STANDARD_ESCALATION"', text)
        trading = (ROOT / "coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml").read_text(encoding="utf-8")
        self.assertIn('order_authority: "SEPARATE_EXPLICIT_OWNER_GATE"', trading)
        self.assertIn("place_order_allowed: false", trading)


if __name__ == "__main__":
    unittest.main()
