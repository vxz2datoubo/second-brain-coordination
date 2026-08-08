"""Independent E60 attack tests using fixed, non-signing synthetic vectors."""

from __future__ import annotations

from copy import deepcopy
import importlib
import unittest

from e60_runtime import (
    AttestationError,
    CanonicalVerifier,
    ExternalAttestation,
    ProviderEvidenceAggregate,
    SourceSpanGrant,
)
from e60_test_fixtures import (
    BASE_ATTESTATION,
    BASE_SOURCE_SPAN,
    PENDING_ATTESTATION,
    PROVIDER_MAPPING,
    RUNTIME_MISMATCH_ATTESTATION,
    TOPOLOGY_MISMATCH_ATTESTATION,
    TOPOLOGY_MISMATCH_PROVIDER_MAPPING,
)


def _provider_evidence(mapping: dict[str, object] | None = None) -> ProviderEvidenceAggregate:
    return ProviderEvidenceAggregate.from_mapping(deepcopy(PROVIDER_MAPPING if mapping is None else mapping))


class AttestationBoundaryTests(unittest.TestCase):
    def test_fixed_synthetic_fixture_accepts_only_its_exact_signed_capability(self) -> None:
        attestation = ExternalAttestation.from_mapping(deepcopy(BASE_ATTESTATION))
        grant = SourceSpanGrant.from_mapping(deepcopy(BASE_SOURCE_SPAN))
        verifier = CanonicalVerifier(attestation, _provider_evidence())
        self.assertTrue(verifier.verify_source_span(grant))
        self.assertTrue(verifier.verify_evidence({"source_span": grant, "proposition": {"subject": "a", "predicate": "b", "object": "c", "polarity": "positive"}}))

    def test_direct_legacy_private_harness_import_cannot_bootstrap(self) -> None:
        runtime = importlib.import_module("e60_runtime")
        self.assertFalse(hasattr(runtime, "_SyntheticAuthorityHarness"))
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("e60_runtime.authority_client")

    def test_tampered_attestation_fails_with_original_signature(self) -> None:
        payload = deepcopy(BASE_ATTESTATION)
        payload["receipt_head"] = "7" * 40
        with self.assertRaisesRegex(AttestationError, "SIGNATURE_INVALID"):
            ExternalAttestation.from_mapping(payload)

    def test_arbitrary_raw_bytes_cannot_be_promoted_to_source_span(self) -> None:
        verifier = CanonicalVerifier(ExternalAttestation.from_mapping(deepcopy(BASE_ATTESTATION)), _provider_evidence())
        self.assertFalse(verifier.verify_source_span(b"caller supplied source"))
        self.assertFalse(verifier.verify_evidence({"source_span": b"caller supplied source", "proposition": {}}))

    def test_tampered_source_digest_cannot_be_represented_as_a_signed_grant(self) -> None:
        candidate = deepcopy(BASE_SOURCE_SPAN)
        candidate["source_digest"] = "e" * 64
        with self.assertRaisesRegex(AttestationError, "SIGNATURE_INVALID"):
            SourceSpanGrant.from_mapping(candidate)

    def test_pending_attestation_cannot_claim_external_acceptance(self) -> None:
        payload = deepcopy(PENDING_ATTESTATION)
        payload["reviewer_acceptance_ref"] = "GITHUB_PR_COMMENT:123"
        with self.assertRaisesRegex(AttestationError, "PENDING_CONTRADICTION"):
            ExternalAttestation.from_mapping(payload)

    def test_pending_attestation_cannot_create_verifier(self) -> None:
        attestation = ExternalAttestation.from_mapping(deepcopy(PENDING_ATTESTATION))
        with self.assertRaisesRegex(AttestationError, "REQUIRES_ACCEPTED_ATTESTATION"):
            CanonicalVerifier(attestation, _provider_evidence())

    def test_synthetic_fixture_with_runtime_identity_mismatch_cannot_create_verifier(self) -> None:
        attestation = ExternalAttestation.from_mapping(deepcopy(RUNTIME_MISMATCH_ATTESTATION))
        with self.assertRaisesRegex(AttestationError, "RUNTIME_IDENTITY_MISMATCH"):
            CanonicalVerifier(attestation, _provider_evidence())

    def test_provider_matrix_digest_mismatch_cannot_create_verifier(self) -> None:
        attestation = ExternalAttestation.from_mapping(deepcopy(BASE_ATTESTATION))
        other_mapping = deepcopy(PROVIDER_MAPPING)
        other_mapping["jobs"][0]["artifact_content_sha256"] = "f" * 64
        with self.assertRaisesRegex(AttestationError, "PROVIDER_EVIDENCE_DIGEST_MISMATCH"):
            CanonicalVerifier(attestation, _provider_evidence(other_mapping))

    def test_provider_matrix_topology_mismatch_cannot_create_verifier(self) -> None:
        attestation = ExternalAttestation.from_mapping(deepcopy(TOPOLOGY_MISMATCH_ATTESTATION))
        with self.assertRaisesRegex(AttestationError, "PROVIDER_EVIDENCE_TOPOLOGY_MISMATCH"):
            CanonicalVerifier(attestation, _provider_evidence(TOPOLOGY_MISMATCH_PROVIDER_MAPPING))

    def test_external_lifecycle_rejects_non_comment_reference_before_signature_check(self) -> None:
        payload = deepcopy(BASE_ATTESTATION)
        payload["lifecycle"] = "ACCEPTED_EXTERNAL"
        payload["reviewer_acceptance_ref"] = "GITHUB_COMMIT:abcdef"
        with self.assertRaisesRegex(AttestationError, "ACCEPTANCE_REFERENCE_INVALID"):
            ExternalAttestation.from_mapping(payload)


if __name__ == "__main__":
    unittest.main()
