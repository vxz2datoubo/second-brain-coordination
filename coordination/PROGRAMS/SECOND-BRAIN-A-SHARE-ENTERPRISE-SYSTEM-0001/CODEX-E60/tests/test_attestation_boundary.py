"""Independent E60 attack tests; signing material intentionally stays outside runtime."""

from __future__ import annotations

from hashlib import sha256
import importlib
import json
import unittest

from e60_runtime import AttestationError, CanonicalVerifier, ExternalAttestation, SourceSpanGrant


_N = int(
    "4860328296384066339081332229486435989775165605120886380697317341049670319131444432990037230279525616568637811580412731556012931985943462985444097595156577"
)
_D = int(
    "2957712637386351736198509116626913654030748350755011529898689445591695556213965829029713465252272845685574198755116825575907114152172592731323687075189929"
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def _sign(payload: dict[str, object]) -> str:
    digest = int.from_bytes(sha256(_canonical(payload)).digest(), "big")
    return format(pow(digest, _D, _N), "x")


def _attestation_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "authority_id": "synthetic-authority-1",
        "source_digest": "a" * 64,
        "runtime_identity_digest": "b" * 64,
        "tested_head": "1" * 40,
        "tested_parent": "2" * 40,
        "tested_tree": "3" * 40,
        "receipt_head": "4" * 40,
        "receipt_parent": "1" * 40,
        "receipt_tree": "5" * 40,
        "provider_run_id": "123",
        "provider_job_id": "456",
        "artifact_digest": "c" * 64,
        "reviewer_acceptance_ref": "GITHUB_COMMIT:abcdef",
        "lifecycle": "ACCEPTED_EXTERNAL",
        "domain": "SYNTHETIC_EXTERNAL_ATTESTATION_ONLY",
        "key_id": "E60-SYNTHETIC-TEST-ONLY-RSA-RAW-SHA256-V1",
    }
    payload.update(overrides)
    payload["signature_hex"] = _sign({key: value for key, value in payload.items() if key != "signature_hex"})
    return payload


class AttestationBoundaryTests(unittest.TestCase):
    def test_external_attestation_and_source_span_are_accepted(self) -> None:
        attestation = ExternalAttestation.from_mapping(_attestation_payload())
        unsigned = {
            "attestation_id": attestation.attestation_id,
            "source_digest": "a" * 64,
            "start_byte": 0,
            "end_byte": 5,
            "decoded_digest": "d" * 64,
            "domain": "SYNTHETIC_EXTERNAL_ATTESTATION_ONLY",
            "key_id": "E60-SYNTHETIC-TEST-ONLY-RSA-RAW-SHA256-V1",
        }
        grant = SourceSpanGrant.from_mapping({
            "attestation_id": unsigned["attestation_id"], "source_digest": unsigned["source_digest"],
            "start_byte": unsigned["start_byte"], "end_byte": unsigned["end_byte"],
            "decoded_digest": unsigned["decoded_digest"], "signature_hex": _sign(unsigned),
        })
        verifier = CanonicalVerifier(attestation)
        self.assertTrue(verifier.verify_source_span(grant))
        self.assertTrue(verifier.verify_evidence({"source_span": grant, "proposition": {"subject": "a", "predicate": "b", "object": "c", "polarity": "positive"}}))

    def test_direct_legacy_private_harness_import_cannot_bootstrap(self) -> None:
        runtime = importlib.import_module("e60_runtime")
        self.assertFalse(hasattr(runtime, "_SyntheticAuthorityHarness"))
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("e60_runtime.authority_client")

    def test_tampered_attestation_fails_even_with_original_signature(self) -> None:
        payload = _attestation_payload(receipt_head="6" * 40)
        payload["receipt_head"] = "7" * 40
        with self.assertRaisesRegex(AttestationError, "SIGNATURE_INVALID"):
            ExternalAttestation.from_mapping(payload)

    def test_arbitrary_raw_bytes_cannot_be_promoted_to_source_span(self) -> None:
        verifier = CanonicalVerifier(ExternalAttestation.from_mapping(_attestation_payload()))
        self.assertFalse(verifier.verify_source_span(b"caller supplied source"))
        self.assertFalse(verifier.verify_evidence({"source_span": b"caller supplied source", "proposition": {}}))

    def test_source_digest_substitution_is_rejected(self) -> None:
        attestation = ExternalAttestation.from_mapping(_attestation_payload())
        unsigned = {
            "attestation_id": attestation.attestation_id, "source_digest": "e" * 64,
            "start_byte": 0, "end_byte": 1, "decoded_digest": "d" * 64,
            "domain": "SYNTHETIC_EXTERNAL_ATTESTATION_ONLY", "key_id": "E60-SYNTHETIC-TEST-ONLY-RSA-RAW-SHA256-V1",
        }
        grant = SourceSpanGrant.from_mapping({
            "attestation_id": unsigned["attestation_id"], "source_digest": unsigned["source_digest"],
            "start_byte": 0, "end_byte": 1, "decoded_digest": unsigned["decoded_digest"], "signature_hex": _sign(unsigned),
        })
        self.assertFalse(CanonicalVerifier(attestation).verify_source_span(grant))

    def test_pending_attestation_cannot_claim_external_acceptance(self) -> None:
        payload = _attestation_payload(lifecycle="PENDING_EXTERNAL", reviewer_acceptance_ref="GITHUB_COMMIT:abcdef")
        with self.assertRaisesRegex(AttestationError, "PENDING_CONTRADICTION"):
            ExternalAttestation.from_mapping(payload)


if __name__ == "__main__":
    unittest.main()
