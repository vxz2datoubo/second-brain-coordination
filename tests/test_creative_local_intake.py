from __future__ import annotations

from dataclasses import replace
import unittest

from creative_runtime.local_intake import LocalIntakeProjection, LocalIntakeViolation, local_intake_gate_report, validate_local_intake


class CreativeLocalIntakeTests(unittest.TestCase):
    def projection(self) -> LocalIntakeProjection:
        return LocalIntakeProjection(
            request_id="req_0123456789abcdef0123",
            customer_reference="cust_0123456789abcdef",
            consent_revision="consent-v3",
            input_hash="a" * 64,
            received_at="2030-01-01T00:00:00Z",
            retention_deadline="2030-01-31T00:00:00Z",
            content_rating="non_explicit",
            cost_limit_minor=0,
            provider_confirmation=False,
        )

    def test_opaque_local_projection_is_valid_but_never_authorizes_external_work(self) -> None:
        report = local_intake_gate_report(
            self.projection(),
            observed_at="2030-01-02T00:00:00Z",
            maximum_cost_limit_minor=0,
        )
        self.assertEqual(report["status"], "local_intake_projection_valid")
        self.assertFalse(report["external_provider_authorized"])
        self.assertFalse(report["customer_vault_accessed"])
        self.assertFalse(report["canonical_knowledge_write"])

    def test_pii_like_reference_expiry_content_and_cost_fail_closed(self) -> None:
        base = self.projection()
        invalid = (
            replace(base, customer_reference="alice@example.com"),
            replace(base, customer_reference="cust_0123456789abcdef", consent_revision="yes"),
            replace(base, content_rating="explicit"),
            replace(base, cost_limit_minor=101),
            replace(base, retention_deadline="2030-01-01T00:00:00Z"),
        )
        for projection in invalid:
            with self.assertRaises(LocalIntakeViolation):
                validate_local_intake(projection, observed_at="2030-01-02T00:00:00Z", maximum_cost_limit_minor=100)
        with self.assertRaisesRegex(LocalIntakeViolation, "expired"):
            validate_local_intake(base, observed_at="2030-02-01T00:00:00Z", maximum_cost_limit_minor=0)


if __name__ == "__main__":
    unittest.main()
