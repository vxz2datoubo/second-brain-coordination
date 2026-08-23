"""R146 durable admission bridge: real S0C read-back plus R145 authority gate."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from global_signal_gateway.domain_authority import DomainAuthorityResolver
from global_signal_gateway.durable_admission_bridge import (
    LEDGER_IDENTITY,
    DurableAdmissionBridge,
    admit_durable_signal,
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


def mock_bound_resolver(domain_id: str) -> DomainAuthorityResolver:
    desc = r145.descriptor(
        domain_id,
        f"PROJECT_{domain_id}",
        "synthetic/public-authority",
        "1" * 40,
        "AUTHORITY.yaml",
    )
    resolver = DomainAuthorityResolver([desc])
    resolver.resolve = Mock(
        return_value={
            "valid": True,
            "reason": "DOMAIN_CANONICAL_AUTHORITY_BOUND",
            "domain_id": domain_id,
            "project_id": desc["project_id"],
            "repository": desc["repository"],
            "canonical_commit": desc["canonical_commit"],
            "writeback_owner": domain_id,
            "authority_refs": ["provider://r145/test", "governed-semantic-authority://sha256=" + "a" * 64],
            "trusted_authority_refs": ["governed-semantic-authority://sha256=" + "a" * 64],
            "provider_attribution_ref": "provider://r145/test",
            "binding_digest": "b" * 64,
            "legacy_compatibility": False,
        }
    )
    return resolver


class TamperingLedger(DurableSignalLedger):
    tamper_readback = False

    def history(self):
        rows = super().history()
        if self.tamper_readback and rows:
            rows[-1] = dict(rows[-1])
            rows[-1]["signal_id"] = "signal:tampered-after-append"
        return rows


class TamperingGateway(SignalIntakeGateway):
    def intake(self, *args, **kwargs):
        result = super().intake(*args, **kwargs)
        self.ledger.tamper_readback = True
        return result


class DurableAdmissionBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = DurableSignalLedger(Path(self.temp.name) / "ledger.sqlite")
        self.gateway = SignalIntakeGateway(self.ledger)

    def tearDown(self) -> None:
        self.ledger.close()
        self.temp.cleanup()

    def bridge(self, domain_id: str = "SECOND_BRAIN_SYSTEM") -> DurableAdmissionBridge:
        return DurableAdmissionBridge(
            gateway=self.gateway,
            domain_authority_resolver=mock_bound_resolver(domain_id),
            expected_canonical_main="f" * 40,
            coordinator_repository=r145.SECOND_REPO,
        )

    def test_second_brain_durable_signal_is_admitted_and_read_back_from_same_ledger(self):
        receipt = admit_durable_signal(
            intake_envelope(),
            gateway=self.gateway,
            domain_authority_resolver=mock_bound_resolver("SECOND_BRAIN_SYSTEM"),
            expected_canonical_main="f" * 40,
            coordinator_repository=r145.SECOND_REPO,
            request_text=REQUEST,
            caller_authorization_ref=CALLER_REF,
            authority_observations=[],
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
        with r145.exact_authority() as (_, desc, obs, exact_proof), r145.governed_domain_provider(
            r145.FILM_REPO, desc["canonical_commit"]
        ) as live:
            resolver = DomainAuthorityResolver([desc])
            bridge = DurableAdmissionBridge(
                gateway=self.gateway,
                domain_authority_resolver=resolver,
                expected_canonical_main=r145.legacy.MAIN,
                coordinator_repository=r145.SECOND_REPO,
            )
            receipt = bridge.admit(
                intake_envelope("AI_FILM_SYSTEM", source_project="EUSTIA_AI_FILM"),
                request_text=REQUEST,
                caller_authorization_ref=CALLER_REF,
                authority_observations=[obs],
                exact_read_proofs=[exact_proof],
                live_observation_proof=live,
            ).public_dict()
        self.assertEqual("ADMITTED", receipt["admission_status"])
        self.assertEqual("AI_FILM_SYSTEM", receipt["primary_domain"])
        self.assertEqual("VERIFIED_SAME_LEDGER", receipt["readback_verification_status"])
        self.assertIn(r145.semantic_authority_ref(exact_proof), receipt["authority_refs"])

    def test_unknown_domain_fails_before_append(self):
        known = r145.descriptor("KNOWN_DOMAIN", "KNOWN_PROJECT", "synthetic/repo", "1" * 40, "AUTHORITY.yaml")
        bridge = DurableAdmissionBridge(
            gateway=self.gateway,
            domain_authority_resolver=DomainAuthorityResolver([known]),
            expected_canonical_main="f" * 40,
            coordinator_repository=r145.SECOND_REPO,
        )
        with self.assertRaises(GatewayError) as got:
            bridge.admit(
                intake_envelope("UNKNOWN_DOMAIN"),
                request_text=REQUEST,
                caller_authorization_ref=CALLER_REF,
                authority_observations=[],
            )
        self.assertEqual("DOMAIN_ROUTE_UNRESOLVED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_stale_r145_canonical_proof_fails_before_append(self):
        with r145.exact_authority() as (_, desc, obs, exact_proof), r145.governed_domain_provider(
            r145.FILM_REPO, "9" * 40
        ) as stale_live:
            bridge = DurableAdmissionBridge(
                gateway=self.gateway,
                domain_authority_resolver=DomainAuthorityResolver([desc]),
                expected_canonical_main=r145.legacy.MAIN,
                coordinator_repository=r145.SECOND_REPO,
            )
            with self.assertRaises(GatewayError) as got:
                bridge.admit(
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
        desc = r145.descriptor("AI_FILM_SYSTEM", "EUSTIA_AI_FILM", r145.FILM_REPO, "1" * 40, "PROJECT_INDEX.yaml")
        obs = r145.observation(desc)
        bridge = DurableAdmissionBridge(
            gateway=self.gateway,
            domain_authority_resolver=DomainAuthorityResolver([desc]),
            expected_canonical_main=r145.legacy.MAIN,
            coordinator_repository=r145.SECOND_REPO,
        )
        with self.assertRaises(GatewayError) as got:
            bridge.admit(
                intake_envelope("AI_FILM_SYSTEM"),
                request_text=REQUEST,
                caller_authorization_ref=CALLER_REF,
                authority_observations=[obs],
            )
        self.assertEqual("DOMAIN_AUTHORITY_EXACT_READ_PROOF_REQUIRED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_private_raw_body_and_non_public_scope_are_rejected_before_append(self):
        bridge = self.bridge()
        with self.assertRaises(GatewayError) as raw:
            bridge.admit(
                intake_envelope(raw_source_body="private"),
                request_text=REQUEST,
                caller_authorization_ref=CALLER_REF,
                authority_observations=[],
            )
        self.assertEqual("PRIVATE_OR_SECRET_FIELD_FORBIDDEN", raw.exception.code)
        with self.assertRaises(GatewayError) as scope:
            bridge.admit(
                intake_envelope(privacy_scope_ref="PRIVATE"),
                request_text=REQUEST,
                caller_authorization_ref=CALLER_REF,
                authority_observations=[],
            )
        self.assertEqual("PUBLIC_SAFE_PRIVACY_SCOPE_REQUIRED", scope.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_duplicate_is_one_effective_event_and_receipt_readback_stays_bound(self):
        bridge = self.bridge()
        first = bridge.admit(
            intake_envelope(), request_text=REQUEST, caller_authorization_ref=CALLER_REF, authority_observations=[]
        ).public_dict()
        second = bridge.admit(
            intake_envelope(), request_text=REQUEST, caller_authorization_ref=CALLER_REF, authority_observations=[]
        ).public_dict()
        self.assertEqual("ADMITTED", first["admission_status"])
        self.assertEqual("IDEMPOTENT_DUPLICATE", second["admission_status"])
        self.assertEqual(first["receipt_id"], second["receipt_id"])
        self.assertEqual(first["receipt_offset"], second["receipt_offset"])
        self.assertEqual(1, len(self.ledger.history()))

    def test_idempotency_key_collision_with_changed_semantics_fails_closed(self):
        bridge = self.bridge()
        bridge.admit(
            intake_envelope(), request_text=REQUEST, caller_authorization_ref=CALLER_REF, authority_observations=[]
        )
        with self.assertRaises(SignalPlaneError) as got:
            bridge.admit(
                intake_envelope(public_safe_summary="changed semantic payload"),
                request_text=REQUEST,
                caller_authorization_ref=CALLER_REF,
                authority_observations=[],
            )
        self.assertEqual("IDEMPOTENCY_KEY_COLLISION", got.exception.code)
        self.assertEqual(1, len(self.ledger.history()))

    def test_append_without_matching_same_ledger_readback_never_returns_success_receipt(self):
        self.ledger.close()
        tamper = TamperingLedger(Path(self.temp.name) / "tamper.sqlite")
        self.ledger = tamper
        self.gateway = TamperingGateway(tamper)
        bridge = self.bridge()
        with self.assertRaises(GatewayError) as got:
            bridge.admit(
                intake_envelope(), request_text=REQUEST, caller_authorization_ref=CALLER_REF, authority_observations=[]
            )
        self.assertEqual("DURABLE_ADMISSION_READBACK_MISMATCH", got.exception.code)
        tamper.tamper_readback = False
        self.assertEqual(1, len(tamper.history()))

    def test_missing_authorized_caller_context_never_appends(self):
        with self.assertRaises(GatewayError) as got:
            self.bridge().admit(
                intake_envelope(), request_text=REQUEST, caller_authorization_ref="", authority_observations=[]
            )
        self.assertEqual("AUTHORIZED_CALLER_REQUIRED", got.exception.code)
        self.assertEqual([], self.ledger.history())

    def test_future_domain_is_data_driven_through_existing_r145_resolver(self):
        with r145.exact_authority(
            domain_id="FUTURE_DOMAIN_X",
            project_id="FUTURE_PROJECT_X",
            repository="synthetic/future-domain",
            authority_path="AUTHORITY.yaml",
        ) as (_, desc, obs, exact_proof), r145.governed_domain_provider(
            "synthetic/future-domain", desc["canonical_commit"]
        ) as live:
            bridge = DurableAdmissionBridge(
                gateway=self.gateway,
                domain_authority_resolver=DomainAuthorityResolver([desc]),
                expected_canonical_main=r145.legacy.MAIN,
                coordinator_repository=r145.SECOND_REPO,
            )
            receipt = bridge.admit(
                intake_envelope("FUTURE_DOMAIN_X", source_project="FUTURE_PROJECT_X"),
                request_text=REQUEST,
                caller_authorization_ref=CALLER_REF,
                authority_observations=[obs],
                exact_read_proofs=[exact_proof],
                live_observation_proof=live,
            ).public_dict()
        self.assertEqual("FUTURE_DOMAIN_X", receipt["primary_domain"])
        self.assertEqual("ADMITTED", receipt["admission_status"])


if __name__ == "__main__":
    unittest.main()