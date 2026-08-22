from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

import e59_runtime  # noqa: E402
from e59_runtime import AuthorityAnchor, AuthorityError, CanonicalVerifier, Proposition  # noqa: E402
from e59_runtime.authority_client import _SyntheticAuthorityHarness  # noqa: E402


class CanonicalAuthorityBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # The semantic boundary suite is not a resource-pressure test. P0
        # exercises the real gate separately; pinning this fixture prevents a
        # busy desktop from turning an authority-contract regression into an
        # unrelated CPU-throttle result.
        cls._resource_patch = patch(
            "e59_runtime.process_tree.resource_snapshot",
            return_value={"available_ram_gib": 16.0, "cpu_percent": 5.0, "python_process_count": 1},
        )
        cls._resource_patch.start()
        try:
            cls.harness = _SyntheticAuthorityHarness().start()
        except BaseException:
            cls._resource_patch.stop()
            raise
        assert cls.harness.issuer is not None
        assert cls.harness.verifier is not None
        cls.issuer = cls.harness.issuer
        cls.verifier = cls.harness.verifier

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.harness.close()
        finally:
            cls._resource_patch.stop()

    @staticmethod
    def proposition(*, polarity: str = "AFFIRM", subject: str = "issuer-A", object_value: str = "fact-X") -> Proposition:
        return Proposition(subject, "reported", object_value, polarity, "public", "2026-Q3")

    def accepted_evidence(self, *, source_text: bytes = b"issuer-A reported fact-X") -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        source = self.issuer.admit_source(source_text)
        span = self.issuer.issue_span(source, 0, len(source_text))
        evidence = self.issuer.validate_evidence(source, span, self.proposition(), source_text.decode("utf-8"))
        return source, span, evidence

    def test_public_runtime_exports_no_bootstrap_or_issuer(self) -> None:
        self.assertFalse(hasattr(e59_runtime, "bootstrap_trusted_runtime"))
        self.assertFalse(hasattr(e59_runtime, "TrustedSemanticExecutor"))
        self.assertNotIn("_SemanticIssuer", e59_runtime.__all__)

    def test_direct_caller_constructor_cannot_create_a_canonical_verifier(self) -> None:
        descriptor = self.harness.descriptor
        anchor = self.harness.anchor
        assert descriptor is not None and anchor is not None
        with self.assertRaisesRegex(AuthorityError, "REQUIRES_AUTHORITY_FACTORY"):
            CanonicalVerifier(descriptor, anchor, "caller-token")

    def test_accepted_source_span_evidence_passes(self) -> None:
        _, _, evidence = self.accepted_evidence()
        self.assertTrue(self.verifier.verify_evidence(evidence))

    def test_caller_authored_evidence_object_fails_host_ledger_verification(self) -> None:
        _, _, evidence = self.accepted_evidence()
        forged = dict(evidence)
        forged["outcome"] = "PASS"
        forged["evidence_id"] = "caller-authored-evidence"
        self.assertFalse(self.verifier.verify_evidence(forged))

    def test_mutated_accepted_evidence_fails_host_ledger_verification(self) -> None:
        _, _, evidence = self.accepted_evidence()
        forged = dict(evidence)
        forged["source_digest"] = "0" * 64
        self.assertFalse(self.verifier.verify_evidence(forged))

    def test_source_span_binding_rejects_replaced_source_id(self) -> None:
        source, span, _ = self.accepted_evidence()
        forged_source = dict(source)
        forged_source["source_id"] = "caller-source"
        with self.assertRaisesRegex(AuthorityError, "SOURCE_SPAN_CAPABILITY"):
            self.issuer.validate_evidence(forged_source, span, self.proposition(), "issuer-A reported fact-X")

    def test_source_span_binding_rejects_changed_excerpt(self) -> None:
        source, span, _ = self.accepted_evidence()
        with self.assertRaisesRegex(AuthorityError, "EXCERPT_DOES_NOT_MATCH"):
            self.issuer.validate_evidence(source, span, self.proposition(), "caller replacement")

    def test_source_span_binding_rejects_invalid_utf8_boundary(self) -> None:
        raw = "人 A".encode("utf-8")
        source = self.issuer.admit_source(raw)
        with self.assertRaisesRegex(AuthorityError, "STRICT_UTF8"):
            self.issuer.issue_span(source, 1, len(raw))

    def test_relation_type_is_derived_as_contradiction(self) -> None:
        raw = b"issuer-A reported fact-X"
        left_source = self.issuer.admit_source(raw)
        left_span = self.issuer.issue_span(left_source, 0, len(raw))
        left = self.issuer.validate_evidence(left_source, left_span, self.proposition(polarity="AFFIRM"), raw.decode())
        right_source = self.issuer.admit_source(raw + b" independently")
        right_span = self.issuer.issue_span(right_source, 0, len(raw))
        right = self.issuer.validate_evidence(right_source, right_span, self.proposition(polarity="DENY"), raw.decode())
        relation = self.issuer.derive_relation(left, right)
        self.assertEqual(relation["relation_type"], "CONTRADICTS")
        self.assertTrue(self.verifier.verify_relation(relation))

    def test_caller_relation_label_cannot_override_ontology(self) -> None:
        raw = b"issuer-A reported fact-X"
        left_source = self.issuer.admit_source(raw)
        left_span = self.issuer.issue_span(left_source, 0, len(raw))
        left = self.issuer.validate_evidence(left_source, left_span, self.proposition(polarity="AFFIRM"), raw.decode())
        right_source = self.issuer.admit_source(raw + b" secondary")
        right_span = self.issuer.issue_span(right_source, 0, len(raw))
        right = self.issuer.validate_evidence(right_source, right_span, self.proposition(polarity="DENY"), raw.decode())
        with self.assertRaisesRegex(AuthorityError, "CALLER_RELATION_HINT"):
            self.issuer.derive_relation(left, right, relation_hint="CORROBORATES")

    def test_forged_relation_is_rejected_by_host_ledger(self) -> None:
        raw = b"issuer-A reported fact-X"
        left_source = self.issuer.admit_source(raw)
        left_span = self.issuer.issue_span(left_source, 0, len(raw))
        left = self.issuer.validate_evidence(left_source, left_span, self.proposition(), raw.decode())
        right_source = self.issuer.admit_source(raw + b" secondary")
        right_span = self.issuer.issue_span(right_source, 0, len(raw))
        right = self.issuer.validate_evidence(right_source, right_span, self.proposition(object_value="fact-Y"), raw.decode())
        relation = self.issuer.derive_relation(left, right)
        forged = dict(relation)
        forged["relation_type"] = "CONTRADICTS"
        self.assertFalse(self.verifier.verify_relation(forged))

    def test_descriptor_or_anchor_substitution_is_not_an_acceptance_path(self) -> None:
        descriptor = self.harness.descriptor
        anchor = self.harness.anchor
        assert descriptor is not None and anchor is not None
        fake_anchor = AuthorityAnchor("foreign-authority", anchor.descriptor_digest, anchor.protocol_version)
        with self.assertRaisesRegex(AuthorityError, "REQUIRES_AUTHORITY_FACTORY"):
            CanonicalVerifier(descriptor, fake_anchor, "caller-token")


class AuthorityLifecycleTests(unittest.TestCase):
    def test_test_authority_host_is_reaped_by_owned_tree(self) -> None:
        with patch("e59_runtime.process_tree.resource_snapshot", return_value={"available_ram_gib": 16.0, "cpu_percent": 5.0, "python_process_count": 1}):
            harness = _SyntheticAuthorityHarness().start()
            try:
                assert harness.verifier is not None
                self.assertTrue(harness.verifier._request("describe")["ok"])
            finally:
                harness.close()
        report = harness._tree.report()
        self.assertEqual(report["postflight_task_owned_process_count"], 0)
        self.assertEqual(report["orphan_count"], 0)

    def test_failed_authority_start_releases_its_gate(self) -> None:
        with patch("e59_runtime.process_tree.resource_snapshot", return_value={"available_ram_gib": 16.0, "cpu_percent": 5.0, "python_process_count": 1}):
            harness = _SyntheticAuthorityHarness()
            with patch.object(harness._tree, "spawn", side_effect=RuntimeError("spawn failure")):
                with self.assertRaisesRegex(RuntimeError, "spawn failure"):
                    harness.start()
            self.assertFalse(harness._gate._held)


if __name__ == "__main__":
    unittest.main(verbosity=2)
