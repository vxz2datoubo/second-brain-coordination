from __future__ import annotations

from copy import deepcopy
import unittest

from e60_mutation_support import run_legacy_bootstrap_injection
from e60_runtime import ProviderEvidenceAggregate
from e60_runtime.execution import WholeTaskResourceLease
from e60_test_fixtures import BASE_ATTESTATION, PROVIDER_MAPPING


class LegacyBootstrapMutationTests(unittest.TestCase):
    def test_injected_legacy_harness_changes_runtime_identity_and_fails_closed(self) -> None:
        safe_sample = lambda: {
            "cpu_percent": 5.0, "available_ram_gib": 16.0, "foreground_contention": False,
            "user_reported_stutter": False, "unexpected_process_growth": False,
        }
        provider_evidence = ProviderEvidenceAggregate.from_mapping(deepcopy(PROVIDER_MAPPING))
        with WholeTaskResourceLease(task_id="E60-legacy-bootstrap-mutation", sample_provider=safe_sample) as lease:
            outcome = run_legacy_bootstrap_injection(
                lease,
                attestation_payload=deepcopy(BASE_ATTESTATION),
                provider_evidence_payload=provider_evidence.mapping(),
            )
        self.assertEqual(outcome.mutation_id, "E60-MUT-LEGACY-BOOTSTRAP-INJECTION-001")
        self.assertEqual(outcome.expected_rejection, "EXTERNAL_ATTESTATION_RUNTIME_IDENTITY_MISMATCH")
        self.assertEqual(outcome.observed_rejection, "EXTERNAL_ATTESTATION_RUNTIME_IDENTITY_MISMATCH")
        self.assertEqual(outcome.receipt.exit_code, 0)
        self.assertEqual(outcome.receipt.report["orphan_count"], 0)
        self.assertEqual(outcome.receipt.report["unrelated_terminated"], 0)


if __name__ == "__main__":
    unittest.main()
