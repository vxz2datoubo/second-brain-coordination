from __future__ import annotations

from hashlib import sha256
import json
import unittest

from e60_mutation_support import run_legacy_bootstrap_injection
from e60_runtime import ProviderEvidenceAggregate, runtime_identity_digest
from e60_runtime.execution import WholeTaskResourceLease


_N = int(
    "4860328296384066339081332229486435989775165605120886380697317341049670319131444432990037230279525616568637811580412731556012931985943462985444097595156577"
)
_D = int(
    "2957712637386351736198509116626913654030748350755011529898689445591695556213965829029713465252272845685574198755116825575907114152172592731323687075189929"
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def _provider_evidence() -> ProviderEvidenceAggregate:
    return ProviderEvidenceAggregate.from_mapping({
        "schema_version": "1.0", "task_id": "E60-test", "provider_run_id": "123",
        "tested_head": "1" * 40, "tested_parent": "2" * 40, "tested_tree": "3" * 40,
        "jobs": [
            {"python_minor": "3.11", "job_id": "457", "artifact_id": "790", "artifact_content_sha256": "e" * 64},
            {"python_minor": "3.13", "job_id": "456", "artifact_id": "789", "artifact_content_sha256": "d" * 64},
        ],
    })


def _payload() -> dict[str, object]:
    provider_evidence = _provider_evidence()
    value: dict[str, object] = {
        "authority_id": "synthetic-authority-1", "source_digest": "a" * 64,
        "runtime_identity_digest": runtime_identity_digest(), "tested_head": "1" * 40,
        "tested_parent": "2" * 40, "tested_tree": "3" * 40,
        "receipt_head": "4" * 40, "receipt_parent": "1" * 40,
        "receipt_tree": "5" * 40, "provider_evidence_aggregate_digest": provider_evidence.digest,
        "reviewer_acceptance_ref": "GITHUB_COMMIT:abcdef",
        "lifecycle": "ACCEPTED_EXTERNAL", "domain": "SYNTHETIC_EXTERNAL_ATTESTATION_ONLY",
        "key_id": "E60-SYNTHETIC-TEST-ONLY-RSA-RAW-SHA256-V1",
    }
    digest = int.from_bytes(sha256(_canonical(value)).digest(), "big")
    value["signature_hex"] = format(pow(digest, _D, _N), "x")
    return value


class LegacyBootstrapMutationTests(unittest.TestCase):
    def test_injected_legacy_harness_changes_runtime_identity_and_fails_closed(self) -> None:
        safe_sample = lambda: {
            "cpu_percent": 5.0, "available_ram_gib": 16.0, "foreground_contention": False,
            "user_reported_stutter": False, "unexpected_process_growth": False,
        }
        with WholeTaskResourceLease(task_id="E60-legacy-bootstrap-mutation", sample_provider=safe_sample) as lease:
            outcome = run_legacy_bootstrap_injection(
                lease,
                attestation_payload=_payload(),
                provider_evidence_payload=_provider_evidence().mapping(),
            )
        self.assertEqual(outcome.mutation_id, "E60-MUT-LEGACY-BOOTSTRAP-INJECTION-001")
        self.assertEqual(outcome.expected_rejection, "EXTERNAL_ATTESTATION_RUNTIME_IDENTITY_MISMATCH")
        self.assertEqual(outcome.observed_rejection, "EXTERNAL_ATTESTATION_RUNTIME_IDENTITY_MISMATCH")
        self.assertEqual(outcome.receipt.exit_code, 0)
        self.assertEqual(outcome.receipt.report["orphan_count"], 0)
        self.assertEqual(outcome.receipt.report["unrelated_terminated"], 0)


if __name__ == "__main__":
    unittest.main()
