"""R147 automatic ingress regressions, including independent-process durability."""
from __future__ import annotations

from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve()
R147 = HERE.parents[1]
PLANE = R147.parent
S0E = PLANE / "S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY"
S0C = PLANE / "S0-SYNTHETIC"
sys.path[:0] = [
    str(R147 / "src"),
    str(S0E / "src"),
    str(S0C / "src"),
    str(S0E / "tests"),
]

import test_r142_r145_cross_domain as r145  # noqa: E402
from global_signal_gateway.domain_authority import DomainAuthorityResolver  # noqa: E402
from global_signal_gateway.gateway import GatewayError  # noqa: E402
from r147_ingress import (  # noqa: E402
    REQUEST_SCHEMA,
    AutomaticSignalTowerIngress,
    GitReplayTransport,
    TrustedAuthorityMaterial,
    derive_envelope,
    validate_transport_request,
)


def request(
    *,
    attempt_id: str,
    summary: str = "Make ChatGPT Signal Tower capture automatic and durable.",
    domain: str = "AI_FILM_SYSTEM",
    source_project: str = "EUSTIA_AI_FILM",
    capture_identity: str | None = None,
    command: str = "把这个录入信号塔",
    **extra,
):
    value = {
        "schema_version": REQUEST_SCHEMA,
        "attempt_id": attempt_id,
        "capture_command": command,
        "source_project": source_project,
        "public_safe_summary": summary,
        "desired_effect": "Automatically preserve this public-safe requirement in the canonical Signal Tower.",
        "problem_to_solve": "Remove manual envelope and durable-ingress boilerplate from ChatGPT capture.",
        "success_condition": "A fresh invocation reads back the same effective S0C Signal.",
        "proposed_primary_domain": domain,
    }
    if capture_identity is not None:
        value["capture_identity"] = capture_identity
    value.update(extra)
    return value


class AuthorityHarness:
    def __init__(
        self,
        *,
        domain_id: str = "AI_FILM_SYSTEM",
        project_id: str = "EUSTIA_AI_FILM",
        repository: str = r145.FILM_REPO,
        authority_path: str = "PROJECT_INDEX.yaml",
    ):
        self.domain_id = domain_id
        self.project_id = project_id
        self.repository = repository
        self.authority_path = authority_path
        self.stack = ExitStack()
        self.material = None

    def __enter__(self):
        _, desc, obs, proof = self.stack.enter_context(
            r145.exact_authority(
                domain_id=self.domain_id,
                project_id=self.project_id,
                repository=self.repository,
                authority_path=self.authority_path,
            )
        )
        live = self.stack.enter_context(
            r145.governed_domain_provider(self.repository, desc["canonical_commit"])
        )
        self.material = TrustedAuthorityMaterial(
            resolver=DomainAuthorityResolver([desc]),
            observations=(obs,),
            exact_read_proofs=(proof,),
            live_observation_proof=live,
            expected_canonical_main=r145.legacy.MAIN,
            coordinator_repository=r145.SECOND_REPO,
        )
        return self

    def __exit__(self, *exc):
        return self.stack.__exit__(*exc)

    def __call__(self, request_value):
        del request_value
        assert self.material is not None
        return self.material


class R147AutomaticIngressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = Path(self.temp.name) / "transport" / "admitted_events.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def ingress(self, materializer):
        return AutomaticSignalTowerIngress(
            transport=GitReplayTransport(self.journal),
            authority_materializer=materializer,
            caller_authorization_ref="authorization://test/r147-trusted-host",
            clock=lambda: "2026-08-24T02:00:00+00:00",
        )

    def test_compact_request_derives_full_durable_envelope_without_caller_trust_engines(self):
        checked = validate_transport_request({
            "schema_version": REQUEST_SCHEMA,
            "attempt_id": "derive-1",
            "capture_command": "把这个录入信号塔",
            "public_safe_summary": "A public-safe durable requirement.",
            "proposed_primary_domain": "AI_FILM_SYSTEM",
        })
        envelope = derive_envelope(checked, captured_at="2026-08-24T02:00:00+00:00")
        self.assertEqual("DURABLE_SIGNAL", envelope["persistence_class"])
        self.assertEqual("GOVERNED_MISSION", envelope["execution_class"])
        self.assertEqual("PUBLIC_SAFE_METADATA_ONLY", envelope["privacy_scope_ref"])
        self.assertEqual(["UNKNOWN"], envelope["risks"])
        self.assertTrue(envelope["envelope_id"].startswith("r147-"))
        for forbidden in ("gateway", "ledger", "resolver", "proof", "authority_observations"):
            self.assertNotIn(forbidden, checked)

    def test_ai_film_admission_and_duplicate_reuse_same_effective_s0c_signal(self):
        with AuthorityHarness() as authority:
            ingress = self.ingress(authority)
            first = ingress.process(request(attempt_id="ai-1"))
            second = ingress.process(request(attempt_id="ai-2"))
        self.assertEqual("ADMITTED", first["status"])
        self.assertEqual("IDEMPOTENT_DUPLICATE", second["status"])
        self.assertEqual(first["signal_id"], second["signal_id"])
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(first["receipt_offset"], second["receipt_offset"])
        self.assertEqual("VERIFIED_SAME_LEDGER", first["readback_verification_status"])
        self.assertEqual("VERIFIED_FRESH_S0C_REPLAY", second["fresh_replay_verification_status"])
        self.assertEqual(1, second["transport_replay_after"]["event_count"])
        self.assertEqual(
            first["transport_replay_after"]["history_digest"],
            second["transport_replay_after"]["history_digest"],
        )

    def test_colliding_capture_identity_with_changed_semantics_fails_closed(self):
        with AuthorityHarness() as authority:
            ingress = self.ingress(authority)
            first = ingress.process(request(attempt_id="collision-1", capture_identity="stable-message-77"))
            second = ingress.process(request(
                attempt_id="collision-2",
                capture_identity="stable-message-77",
                summary="Changed semantic content under the same explicit capture identity.",
            ))
        self.assertEqual("ADMITTED", first["status"])
        self.assertFalse(second["durable_success"])
        self.assertEqual("IDEMPOTENCY_KEY_COLLISION", second["code"])
        transport = GitReplayTransport(self.journal)
        ledger, replay = transport.replay(transport.load_events())
        try:
            self.assertEqual(1, replay["event_count"])
        finally:
            ledger.close()

    def test_unknown_domain_fails_before_any_durable_transport_append(self):
        def unresolved(_request):
            raise GatewayError("DOMAIN_ROUTE_UNRESOLVED", "/proposed_primary_domain")
        result = self.ingress(unresolved).process(request(
            attempt_id="unknown-1",
            domain="UNKNOWN_DOMAIN",
            source_project="UNKNOWN_PROJECT",
        ))
        self.assertFalse(result["durable_success"])
        self.assertEqual("DOMAIN_ROUTE_UNRESOLVED", result["code"])
        self.assertFalse(self.journal.exists())

    def test_explicit_no_capture_short_circuits_before_authority_or_append(self):
        calls = []
        def should_not_run(_request):
            calls.append(True)
            raise AssertionError("authority must not be materialized")
        result = self.ingress(should_not_run).process(
            request(attempt_id="no-capture", command="先别录入信号塔，只是讨论")
        )
        self.assertEqual("NOT_CAPTURED", result["status"])
        self.assertEqual([], calls)
        self.assertFalse(self.journal.exists())

    def test_caller_cannot_supply_authority_or_raw_private_body(self):
        for field in ("authority_observations", "exact_read_proofs", "gateway", "raw_source_body"):
            with self.subTest(field=field):
                result = self.ingress(lambda _: None).process(
                    request(attempt_id=f"forbidden-{field}", **{field: "forged"})
                )
                self.assertFalse(result["durable_success"])
                self.assertEqual("R147_CALLER_TRUST_OR_PRIVATE_FIELD_FORBIDDEN", result["code"])
        self.assertFalse(self.journal.exists())

    def test_second_brain_named_domain_routes_through_same_descriptor_driven_r145_r146_path(self):
        with AuthorityHarness(
            domain_id="SECOND_BRAIN_SYSTEM",
            project_id="SECOND_BRAIN_SYSTEM",
            repository="synthetic/second-brain-owner",
            authority_path="AUTHORITY.yaml",
        ) as authority:
            result = self.ingress(authority).process(request(
                attempt_id="second-brain-1",
                domain="SECOND_BRAIN_SYSTEM",
                source_project="SECOND_BRAIN_SYSTEM",
            ))
        self.assertEqual("ADMITTED", result["status"])
        self.assertEqual("SECOND_BRAIN_SYSTEM", result["primary_domain"])

    def test_future_descriptor_driven_domain_needs_no_ingress_code_switch(self):
        with AuthorityHarness(
            domain_id="FUTURE_DOMAIN_7",
            project_id="FUTURE_PROJECT_7",
            repository="synthetic/future-domain-7",
            authority_path="AUTHORITY.yaml",
        ) as authority:
            result = self.ingress(authority).process(request(
                attempt_id="future-1",
                domain="FUTURE_DOMAIN_7",
                source_project="FUTURE_PROJECT_7",
            ))
        self.assertEqual("ADMITTED", result["status"])
        self.assertEqual("FUTURE_DOMAIN_7", result["primary_domain"])
        self.assertFalse(result["task_created"])
        self.assertFalse(result["route_created"])
        self.assertFalse(result["work_claim_created"])
        self.assertFalse(result["write_permission_created"])

    def test_independent_python_processes_observe_prior_durable_state_and_idempotency(self):
        script = r'''from contextlib import ExitStack
import json, sys
from pathlib import Path
import test_r142_r145_cross_domain as r145
from global_signal_gateway.domain_authority import DomainAuthorityResolver
from r147_ingress import AutomaticSignalTowerIngress, GitReplayTransport, TrustedAuthorityMaterial, REQUEST_SCHEMA
journal, attempt = Path(sys.argv[1]), sys.argv[2]
request = {
    "schema_version": REQUEST_SCHEMA,
    "attempt_id": attempt,
    "capture_command": "把这个录入信号塔",
    "source_project": "EUSTIA_AI_FILM",
    "public_safe_summary": "Independent-process durable R147 capture.",
    "desired_effect": "Prove a later interpreter sees the prior effective S0C Signal.",
    "problem_to_solve": "Ephemeral single-process state is insufficient.",
    "success_condition": "The second interpreter returns IDEMPOTENT_DUPLICATE for the same Signal.",
    "proposed_primary_domain": "AI_FILM_SYSTEM",
}
with ExitStack() as stack:
    _, desc, obs, proof = stack.enter_context(r145.exact_authority())
    live = stack.enter_context(r145.governed_domain_provider(r145.FILM_REPO, desc["canonical_commit"]))
    material = TrustedAuthorityMaterial(
        resolver=DomainAuthorityResolver([desc]), observations=(obs,), exact_read_proofs=(proof,),
        live_observation_proof=live, expected_canonical_main=r145.legacy.MAIN,
        coordinator_repository=r145.SECOND_REPO,
    )
    ingress = AutomaticSignalTowerIngress(
        transport=GitReplayTransport(journal), authority_materializer=lambda _request: material,
        caller_authorization_ref="authorization://subprocess/r147",
    )
    print(json.dumps(ingress.process(request), sort_keys=True))
'''
        first = subprocess.run(
            [sys.executable, "-c", script, str(self.journal), "proc-1"],
            capture_output=True, text=True, check=True,
        )
        second = subprocess.run(
            [sys.executable, "-c", script, str(self.journal), "proc-2"],
            capture_output=True, text=True, check=True,
        )
        first_receipt = json.loads(first.stdout.strip().splitlines()[-1])
        second_receipt = json.loads(second.stdout.strip().splitlines()[-1])
        self.assertEqual("ADMITTED", first_receipt["status"])
        self.assertEqual("IDEMPOTENT_DUPLICATE", second_receipt["status"])
        self.assertEqual(first_receipt["signal_id"], second_receipt["signal_id"])
        self.assertEqual(first_receipt["receipt_offset"], second_receipt["receipt_offset"])
        self.assertEqual(1, second_receipt["transport_replay_before"]["event_count"])
        self.assertEqual(
            first_receipt["transport_replay_after"]["projection_checksum"],
            second_receipt["transport_replay_after"]["projection_checksum"],
        )


if __name__ == "__main__":
    unittest.main()
