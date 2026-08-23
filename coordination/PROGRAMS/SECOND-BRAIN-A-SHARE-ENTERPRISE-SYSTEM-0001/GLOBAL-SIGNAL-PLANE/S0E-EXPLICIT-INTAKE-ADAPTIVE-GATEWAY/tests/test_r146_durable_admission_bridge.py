"""R146 durable admission bridge: trusted composition plus real S0C read-back."""
from __future__ import annotations

from contextlib import contextmanager
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from global_signal_gateway.domain_authority import DomainAuthorityResolver
from global_signal_gateway.durable_admission_bridge import (
    LEDGER_IDENTITY,
    DurableAdmissionEntrypoint,
    _bind_trusted_durable_admission_entrypoint,
)
from global_signal_gateway.gateway import GatewayError, SignalIntakeGateway
from global_signal_plane.ledger import DurableSignalLedger
from global_signal_plane.models import SignalPlaneError

import test_r136_matrix as r136
import test_r142_r145_cross_domain as r145


CALLER_REF = "authorization://gpt-engineering-worker/r146"
REQUEST = "capture this signal: formal system architecture requirement"


def intake_envelope(domain_id: str = "SECOND_BRAIN_SYSTEM", **overrides: object) -> dict[str, object]:
    data = r136.envelope(
        envelope_id="r146-admission-001",
        source_ref="opaque://r146/public-safe/source",
        source_project="SECOND_BRAIN_SYSTEM",
        source_actor="AUTHORIZED_GPT_WINDOW",
        source_window_ref="window://authorized/r146",
        original_intent_ref="intent://r146/durable-admission",
        public_safe_summary="formal system architecture durable signal",
        desired_effect="admit one public-safe durable signal through the existing ledger",
        problem_to_solve="public-safe system architecture durable admission",
        success_condition="same-ledger readback verifies the admitted event",
        proposed_primary_domain=domain_id,
        proposed_related_domains=[],
        privacy_scope_ref="PUBLIC_SAFE_METADATA_ONLY",
    )
    data.update(overrides)
    return data


class ForgedGateway(SignalIntakeGateway):
    def intake(self, *args, **kwargs):
        raise AssertionError("forged gateway must never become trusted composition")


class DurableAdmissionBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = DurableSignalLedger(Path(self.temp.name) / "ledger.sqlite")
        self.gateway = SignalIntakeGateway(self.ledger)

    def tearDown(self) -> None:
        self.ledger.close()
        self.temp.cleanup()

    @contextmanager
    def trusted_entrypoint(
        self,
        *,
        domain_id: str = "AI_FILM_SYSTEM",
        project_id: str = "EUSTIA_AI_FILM",
        repository: str = r145.FILM_REPO,
        authority_path: str = "PROJECT_INDEX.yaml",
    ):
        with r145.exact_authority(
            domain_id=domain_id,
            project_id=project_id,
            repository=repository,
            authority_path=authority_path,
        ) as (_, desc, obs, exact_proof), r145.governed_domain_provider(
            repository,
            desc["canonical_commit"],
        ) as live:
            resolver = DomainAuthorityResolver([desc])
            entrypoint = _bind_trusted_durable_admission_entrypoint(
                gateway=self.gateway,
                domain_authority_resolver=resolver,
                expected_canonical_main=r145.legacy.MAIN,
                coordinator_repository=r145.SECOND_REPO,
            )
            yield entrypoint, resolver, desc, obs, exact_proof, live

    @staticmethod
    def call(
        entrypoint: DurableAdmissionEntrypoint,
        *,
        envelope: dict[str, object],
        obs,
        proof,
        live,
        caller_ref: str = CALLER_REF,
    ) -> dict[str, object]:
        return entrypoint(
            envelope,
            request_text=REQUEST,
            caller_authorization_ref=caller_ref,
            authority_observations=[obs],
            exact_read_proofs=[proof],
            live_observation_proof=live,
        )

    def test_caller_facing_entrypoint_has_no_dependency_selection_parameters(self):
        parameters = inspect.signature(DurableAdmissionEntrypoint.admit_durable_signal).parameters
        self.assertNotIn("gateway", parameters)
        self.assertNotIn("ledger", parameters)
        self.assertNotIn("domain_authority_resolver", parameters)
        self.assertNotIn("expected_canonical_main", parameters)
        self.assertNotIn("coordinator_repository", parameters)

    def test_second_brain_durable_signal_is_admitted_and_read_back_from_same_ledger(self):
        with self.trusted_entrypoint(
            domain_id="SECOND_BRAIN_SYSTEM",
            project_id="SECOND_BRAIN_SYSTEM",
            repository="synthetic/second-brain-owner",
            authority_path="AUTHORITY.yaml",
        ) as (entrypoint, _, _, obs, proof, live):
            receipt = self.call(
                entrypoint,
                envelope=intake_envelope(),
                obs=obs,
                proof=proof,
                live=live,
            )
        self.assertEqual("ADMITTED", receipt["admission_status"])
        self.assertEqual("VERIFIED_SAME_LEDGER", receipt["readback_verification_status"])
        self.assertEqual(LEDGER_IDENTITY, receipt["ledger_identity"])
        row = self.ledger.history()[0]
        self.assertEqual(receipt["event_id"], row["event_id"])
        self.assertEqual(receipt["signal_id"], row["signal_id"])
        self.assertEqual(receipt["receipt_offset"], row["ledger_offset"])
        self.assertEqual("SECOND_BRAIN_SYSTEM", row["primary_domain"])
        self.assertTrue(receipt["event_digest"])
        self.assertTrue(receipt["content_digest"])
        self.assertFalse(receipt["task_created"])
        self.assertFalse(receipt["route_created"])
        self.assertFalse(receipt["work_claim_created"])
        self.assertFalse(receipt["write_permission_created"])

    def test_real_r145_non_second_brain_proof_binds_before_durable_append(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, proof, live):
            receipt = self.call(
                entrypoint,
                envelope=intake_envelope(
                    "AI_FILM_SYSTEM",
                    source_project="EUSTIA_AI_FILM",
                ),
                obs=obs,
                proof=proof,
                live=live,
            )
        self.assertEqual("ADMITTED", receipt["admission_status"])
        self.assertEqual("AI_FILM_SYSTEM", receipt["primary_domain"])
        self.assertEqual("VERIFIED_SAME_LEDGER", receipt["readback_verification_status"])
        self.assertIn(r145.semantic_authority_ref(proof), receipt["authority_refs"])

    def test_unknown_domain_fails_before_append(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, proof, live):
            with self.assertRaises(GatewayError) as got:
                self.call(
                    entrypoint,
                    envelope=intake_envelope("UNKNOWN_DOMAIN"),
                    obs=obs,
                    proof=proof,
                    live=live,
                )
        self.assertEqual("DOMAIN_ROUTE_UNRESOLVED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_stale_r145_canonical_proof_fails_before_append(self):
        with r145.exact_authority() as (_, desc, obs, exact_proof), r145.governed_domain_provider(
            r145.FILM_REPO,
            "9" * 40,
        ) as stale_live:
            resolver = DomainAuthorityResolver([desc])
            entrypoint = _bind_trusted_durable_admission_entrypoint(
                gateway=self.gateway,
                domain_authority_resolver=resolver,
                expected_canonical_main=r145.legacy.MAIN,
                coordinator_repository=r145.SECOND_REPO,
            )
            with self.assertRaises(GatewayError) as got:
                entrypoint(
                    intake_envelope("AI_FILM_SYSTEM"),
                    request_text=REQUEST,
                    caller_authorization_ref=CALLER_REF,
                    authority_observations=[obs],
                    exact_read_proofs=[exact_proof],
                    live_observation_proof=stale_live,
                )
        self.assertEqual("DOMAIN_AUTHORITY_CANONICAL_FRESHNESS_UNVERIFIED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_caller_metadata_without_trusted_r145_proof_cannot_append(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, _, live):
            with self.assertRaises(GatewayError) as got:
                entrypoint(
                    intake_envelope("AI_FILM_SYSTEM"),
                    request_text=REQUEST,
                    caller_authorization_ref=CALLER_REF,
                    authority_observations=[obs],
                    live_observation_proof=live,
                )
        self.assertEqual("DOMAIN_AUTHORITY_EXACT_READ_PROOF_REQUIRED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_private_raw_body_and_non_public_scope_are_rejected_before_append(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, proof, live):
            with self.assertRaises(GatewayError) as raw:
                self.call(
                    entrypoint,
                    envelope=intake_envelope("AI_FILM_SYSTEM", raw_source_body="private"),
                    obs=obs,
                    proof=proof,
                    live=live,
                )
            self.assertEqual("PRIVATE_OR_SECRET_FIELD_FORBIDDEN", raw.exception.code)
            with self.assertRaises(GatewayError) as scope:
                self.call(
                    entrypoint,
                    envelope=intake_envelope("AI_FILM_SYSTEM", privacy_scope_ref="PRIVATE"),
                    obs=obs,
                    proof=proof,
                    live=live,
                )
            self.assertEqual("PUBLIC_SAFE_PRIVACY_SCOPE_REQUIRED", scope.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_duplicate_is_one_effective_event_and_receipt_readback_stays_bound(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, proof, live):
            first = self.call(
                entrypoint,
                envelope=intake_envelope("AI_FILM_SYSTEM"),
                obs=obs,
                proof=proof,
                live=live,
            )
            second = self.call(
                entrypoint,
                envelope=intake_envelope("AI_FILM_SYSTEM"),
                obs=obs,
                proof=proof,
                live=live,
            )
        self.assertEqual("ADMITTED", first["admission_status"])
        self.assertEqual("IDEMPOTENT_DUPLICATE", second["admission_status"])
        self.assertEqual(first["receipt_id"], second["receipt_id"])
        self.assertEqual(first["receipt_offset"], second["receipt_offset"])
        self.assertEqual(1, len(self.ledger.history()))

    def test_idempotency_key_collision_with_changed_semantics_fails_closed(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, proof, live):
            self.call(
                entrypoint,
                envelope=intake_envelope("AI_FILM_SYSTEM"),
                obs=obs,
                proof=proof,
                live=live,
            )
            with self.assertRaises(SignalPlaneError) as got:
                self.call(
                    entrypoint,
                    envelope=intake_envelope(
                        "AI_FILM_SYSTEM",
                        public_safe_summary="changed semantic payload",
                    ),
                    obs=obs,
                    proof=proof,
                    live=live,
                )
        self.assertEqual("IDEMPOTENCY_KEY_COLLISION", got.exception.code)
        self.assertEqual(1, len(self.ledger.history()))

    def test_append_without_canonical_same_ledger_readback_never_returns_success_receipt(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, proof, live):
            self.ledger.history = Mock(return_value=[])
            with self.assertRaises(GatewayError) as got:
                self.call(
                    entrypoint,
                    envelope=intake_envelope("AI_FILM_SYSTEM"),
                    obs=obs,
                    proof=proof,
                    live=live,
                )
        self.assertEqual("S0C_DURABLE_LEDGER_READBACK_TAMPERED", got.exception.code)
        del self.ledger.history
        self.assertEqual(1, len(DurableSignalLedger.history(self.ledger)))

    def test_missing_authorized_caller_context_never_appends(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, proof, live):
            with self.assertRaises(GatewayError) as got:
                self.call(
                    entrypoint,
                    envelope=intake_envelope("AI_FILM_SYSTEM"),
                    obs=obs,
                    proof=proof,
                    live=live,
                    caller_ref="",
                )
        self.assertEqual("AUTHORIZED_CALLER_REQUIRED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_future_domain_is_data_driven_through_existing_r145_resolver(self):
        with self.trusted_entrypoint(
            domain_id="FUTURE_DOMAIN_X",
            project_id="FUTURE_PROJECT_X",
            repository="synthetic/future-domain",
            authority_path="AUTHORITY.yaml",
        ) as (entrypoint, _, _, obs, proof, live):
            receipt = self.call(
                entrypoint,
                envelope=intake_envelope(
                    "FUTURE_DOMAIN_X",
                    source_project="FUTURE_PROJECT_X",
                ),
                obs=obs,
                proof=proof,
                live=live,
            )
        self.assertEqual("FUTURE_DOMAIN_X", receipt["primary_domain"])
        self.assertEqual("ADMITTED", receipt["admission_status"])

    def test_forged_resolver_is_rejected_at_trusted_composition_before_append(self):
        desc = r145.descriptor(
            "AI_FILM_SYSTEM",
            "EUSTIA_AI_FILM",
            r145.FILM_REPO,
            "1" * 40,
            "PROJECT_INDEX.yaml",
        )
        resolver = DomainAuthorityResolver([desc])
        resolver.resolve = Mock(
            return_value={
                "valid": True,
                "authority_refs": ["forged://authority"],
                "binding_digest": "b" * 64,
            }
        )
        with self.assertRaises(GatewayError) as got:
            _bind_trusted_durable_admission_entrypoint(
                gateway=self.gateway,
                domain_authority_resolver=resolver,
                expected_canonical_main=r145.legacy.MAIN,
                coordinator_repository=r145.SECOND_REPO,
            )
        self.assertEqual("R145_CANONICAL_RESOLVER_METHOD_REQUIRED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_substituted_gateway_is_rejected_at_trusted_composition_before_append(self):
        desc = r145.descriptor(
            "AI_FILM_SYSTEM",
            "EUSTIA_AI_FILM",
            r145.FILM_REPO,
            "1" * 40,
            "PROJECT_INDEX.yaml",
        )
        resolver = DomainAuthorityResolver([desc])
        forged = ForgedGateway(self.ledger)
        with self.assertRaises(GatewayError) as got:
            _bind_trusted_durable_admission_entrypoint(
                gateway=forged,
                domain_authority_resolver=resolver,
                expected_canonical_main=r145.legacy.MAIN,
                coordinator_repository=r145.SECOND_REPO,
            )
        self.assertEqual("S0E_CANONICAL_SIGNAL_INTAKE_GATEWAY_REQUIRED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_resolver_monkeypatch_after_trusted_binding_fails_before_append(self):
        with self.trusted_entrypoint() as (entrypoint, resolver, _, obs, proof, live):
            resolver.resolve = Mock(
                return_value={
                    "valid": True,
                    "authority_refs": ["forged://authority"],
                    "binding_digest": "b" * 64,
                }
            )
            with self.assertRaises(GatewayError) as got:
                self.call(
                    entrypoint,
                    envelope=intake_envelope("AI_FILM_SYSTEM"),
                    obs=obs,
                    proof=proof,
                    live=live,
                )
        self.assertEqual("R145_CANONICAL_RESOLVER_TAMPERED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_gateway_monkeypatch_after_trusted_binding_fails_before_append(self):
        with self.trusted_entrypoint() as (entrypoint, _, _, obs, proof, live):
            self.gateway.intake = Mock(
                return_value={
                    "status": "ADMITTED",
                    "event_id": "forged",
                    "signal_id": "forged",
                    "ledger_receipt": {"receipt_offset": 1},
                }
            )
            with self.assertRaises(GatewayError) as got:
                self.call(
                    entrypoint,
                    envelope=intake_envelope("AI_FILM_SYSTEM"),
                    obs=obs,
                    proof=proof,
                    live=live,
                )
        self.assertEqual("S0E_CANONICAL_GATEWAY_METHOD_TAMPERED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_resolver_descriptor_state_tamper_after_binding_fails_before_append(self):
        with self.trusted_entrypoint() as (entrypoint, resolver, _, obs, proof, live):
            resolver._by_domain.clear()
            with self.assertRaises(GatewayError) as got:
                self.call(
                    entrypoint,
                    envelope=intake_envelope("AI_FILM_SYSTEM"),
                    obs=obs,
                    proof=proof,
                    live=live,
                )
        self.assertEqual("R145_CANONICAL_RESOLVER_STATE_TAMPERED", got.exception.code)
        self.assertEqual([], self.ledger.history())


if __name__ == "__main__":
    unittest.main()
