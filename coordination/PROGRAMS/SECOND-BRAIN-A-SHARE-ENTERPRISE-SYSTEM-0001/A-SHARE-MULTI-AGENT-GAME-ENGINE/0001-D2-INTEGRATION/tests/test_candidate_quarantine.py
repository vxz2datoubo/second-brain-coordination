from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from candidate_quarantine import (  # noqa: E402
    CANONICAL_FAMILIES, CandidateEnvelope, ClaimEvidenceEnvelope, negotiate_schema,
    translate_ontology, validate_candidate, validate_claim_envelope,
)


def valid_candidate(**changes):
    envelope = CandidateEnvelope(
        source_schema_version="1.2", source_commit_lock="a" * 40, artifact_hashes=("b" * 64,),
        verifier_command="python verify_fixture.py", verifier_evidence_hashes=("c" * 64,), status="CANDIDATE",
        authority_write=False, source_capability="SYNTHETIC_RESEARCH_ONLY", source_family_label="retail",
        source_subtype_label="synthetic-retail", canonical_family_label="RETAIL", target_kind="CANDIDATE_CLAIM",
        identity_claimed=False, deterministic_status="EXECUTED_WITH_RECEIPT",
    )
    return replace(envelope, **changes)


class CandidateQuarantineTests(unittest.TestCase):
    def test_only_synthetic_candidate_can_pass(self):
        decision = validate_candidate(valid_candidate())
        self.assertTrue(decision.accepted)
        self.assertEqual("RETAIL", decision.translation.canonical_family)
        self.assertEqual(len(CANONICAL_FAMILIES), 4)

    def test_version_negotiation_fails_closed(self):
        self.assertFalse(negotiate_schema("2.0")[0])
        self.assertFalse(negotiate_schema("not-a-version")[0])

    def test_abbreviated_lock_and_missing_verification_are_rejected(self):
        decision = validate_candidate(valid_candidate(source_commit_lock="short", verifier_command="", verifier_evidence_hashes=()))
        self.assertFalse(decision.accepted)
        self.assertIn("ABBREVIATED_OR_INVALID_SOURCE_LOCK", decision.reason_codes)
        self.assertIn("MISSING_VERIFIER_COMMAND", decision.reason_codes)

    def test_hash_and_hardcoded_determinism_are_rejected(self):
        decision = validate_candidate(valid_candidate(artifact_hashes=("not-a-hash",), deterministic_status="HARDCODED_PASS"))
        self.assertFalse(decision.accepted)
        self.assertIn("MISSING_OR_INVALID_ARTIFACT_HASH", decision.reason_codes)
        self.assertIn("HARDCODED_DETERMINISM_STATUS_REJECTED", decision.reason_codes)

    def test_authority_identity_and_fact_promotion_are_rejected(self):
        decision = validate_candidate(valid_candidate(authority_write=True, identity_claimed=True, target_kind="FACT"))
        self.assertFalse(decision.accepted)
        self.assertIn("CANDIDATE_STATUS_OR_AUTHORITY_VIOLATION", decision.reason_codes)
        self.assertIn("IDENTITY_PROMOTION_REJECTED", decision.reason_codes)
        self.assertIn("CLAIM_TO_FACT_OR_RUNTIME_PROMOTION_REJECTED", decision.reason_codes)

    def test_unknown_and_deprecated_canonical_labels_are_rejected(self):
        unknown = validate_candidate(valid_candidate(canonical_family_label="UNKNOWN"))
        deprecated = validate_candidate(valid_candidate(canonical_family_label="LargeCapital"))
        self.assertFalse(unknown.accepted)
        self.assertFalse(deprecated.accepted)
        self.assertEqual("UNMAPPED_UNKNOWN", unknown.translation.canonical_family)
        self.assertEqual("DEPRECATED_LABEL_PRESENTED_AS_CANONICAL", deprecated.translation.rationale)

    def test_source_labels_are_preserved_separately(self):
        translation = translate_ontology("source-retail-label", "source-subtype", None)
        self.assertEqual("source-retail-label", translation.source_family_label)
        self.assertEqual("source-subtype", translation.source_subtype_label)
        self.assertEqual("UNMAPPED_UNKNOWN", translation.canonical_family)

    def test_claim_envelope_requires_expiry_and_candidate_only_promotion(self):
        claim = ClaimEvidenceEnvelope("fixture-1", "SYNTHETIC_FIXTURE", "synthetic-only", ("d" * 64,), (), ("unknown",), 101)
        self.assertTrue(validate_claim_envelope(claim, 100)[0])
        self.assertFalse(validate_claim_envelope(replace(claim, expires_at_ns=100), 100)[0])
        self.assertFalse(validate_claim_envelope(replace(claim, promotion="FACT"), 100)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
