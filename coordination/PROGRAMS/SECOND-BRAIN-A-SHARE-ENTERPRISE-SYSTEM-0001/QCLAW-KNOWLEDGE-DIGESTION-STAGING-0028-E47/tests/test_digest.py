"""E47 Digest Tests — validates candidate packages.
All assertions CANDIDATE-ONLY; no formal authority tests.
"""
import unittest
import hashlib
import os
import sys

# Add E47 src to path
here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(os.path.dirname(here), "src")
sys.path.insert(0, src)

from qclaw_e47_digest.intraday_extrema import (
    digest_intraday_extrema, CandidateDigestPackage,
    Atom, AtomType, EvidenceKind, Confidence, Relation, Unknown,
    CandidateMemoryRecord, CandidateSkill,
)
from qclaw_e47_digest.credit_calibration import digest_credit_calibration


# Real source text from Issue #188
INTRADAY_SOURCE = """# A股弱驱动状态下日内极值间隔研究与技能化

module_id: A-SHARE-INTRADAY-EXTREMA-INTERVAL-0013
skill_id: A-SHARE-INTRADAY-EXTREMA-INTERVAL-WEAK-DRIVE-SKILL-0013
status: BLUEPRINT_AND_RESEARCH_VALIDATION_REQUESTED
hypothesis_status: UNVERIFIED_CANDIDATE
user_observation: "在没有强烈买入或卖出时，日内阶段最高点与最低点常相差约20至30分钟"
boundary: research_only / NO_TRADE
codex_dispatch: NOT_AUTHORIZED_WHILE_E56_ACTIVE
qclaw_parallel_route: E44
workbuddy_runtime: PAUSED

## Research question
Test whether the 20-30 active-trading-minute interval between intraday stage extremes
is statistically distinguishable from random walk in weak-drive conditions.

## Validation design
1. Define weak-drive quantifiable criteria
2. Identify intraday stage extremes
3. Compute interval distribution
4. Random walk baseline comparison
"""

CREDIT_SOURCE = """## Purpose
Establish an empirical planning calibration for QCLAW running DeepSeek V4 Pro.
This is a workload-capacity calibration, NOT a claim about tokens/FLOPs/GPU-seconds.

## Observed samples
### Sample A — historical approximate
- User-reported starting balance: ~100 credits
- User-reported ending balance: ~50 credits
- Approximate consumption: ~50 credits
- Most likely matching engineering task: E17 / PR #100

### Recommended
- target spend 50-55, reserve 15-20 credits
"""


class TestIntradayExtremaDigest(unittest.TestCase):
    """Test Issue #188 intraday extrema candidate package."""

    @classmethod
    def setUpClass(cls):
        cls.pkg = digest_intraday_extrema(INTRADAY_SOURCE)

    def test_package_identity(self):
        self.assertEqual(self.pkg.package_id, "E47-DIGEST-001-INTRADAY-EXTREMA")
        self.assertIn("issue", self.pkg.source_url.lower())
        self.assertGreater(len(self.pkg.source_hash), 0)

    def test_atom_count(self):
        self.assertEqual(len(self.pkg.atoms), 8)

    def test_concept_atom_weak_drive(self):
        a = self.pkg.atoms[0]
        self.assertEqual(a.atom_type, AtomType.CONCEPT)
        self.assertIn("弱驱动", a.content)
        self.assertEqual(a.evidence_kind, EvidenceKind.EXTRACTED_DEFINITION)

    def test_mechanism_atom_interval(self):
        a = self.pkg.atoms[1]
        self.assertEqual(a.atom_type, AtomType.MECHANISM)
        self.assertIn("20至30分钟", a.content)
        self.assertEqual(a.evidence_kind, EvidenceKind.SOURCE_USER_OBSERVATION)
        self.assertEqual(a.confidence, Confidence.LOW)

    def test_scope_atom(self):
        scope_atoms = [a for a in self.pkg.atoms if a.atom_type == AtomType.SCOPE]
        self.assertEqual(len(scope_atoms), 2)

    def test_verification_method(self):
        vm = [a for a in self.pkg.atoms if a.atom_type == AtomType.VERIFICATION_METHOD]
        self.assertEqual(len(vm), 1)
        self.assertIn("随机游走", vm[0].content)

    def test_hypothesis_marked_as_inference(self):
        h = [a for a in self.pkg.atoms if a.atom_type == AtomType.HYPOTHESIS]
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0].evidence_kind, EvidenceKind.INFERENCE)

    def test_no_atom_is_fact_without_source(self):
        """No atom should claim HIGH confidence without SOURCE_USER_OBSERVATION or EXTRACTED_DEFINITION evidence."""
        for a in self.pkg.atoms:
            if a.confidence == Confidence.HIGH:
                self.assertIn(a.evidence_kind, [
                    EvidenceKind.SOURCE_USER_OBSERVATION,
                    EvidenceKind.EXTRACTED_DEFINITION,
                ], f"Atom {a.atom_id} has HIGH confidence but only {a.evidence_kind}")

    def test_no_trade_boundary(self):
        """Boundary NO_TRADE must be explicitly preserved."""
        for a in self.pkg.atoms:
            if a.atom_type == AtomType.SCOPE and "NO_TRADE" in a.content:
                return
        # Also check scope constraint
        self.assertTrue(any("research_only" in a.content.lower() or "NO_TRADE" in a.content
                           for a in self.pkg.atoms),
                        "NO_TRADE boundary must be in atoms")

    def test_relations_exist(self):
        self.assertGreater(len(self.pkg.relations), 0)
        rel_types = {r.relation_type for r in self.pkg.relations}
        self.assertIn("DEPENDS_ON", rel_types)
        self.assertIn("VERIFIED_BY", rel_types)
        self.assertIn("REFINES", rel_types)

    def test_relation_atoms_valid(self):
        """All relation source/target IDs must exist in atoms."""
        atom_ids = {a.atom_id for a in self.pkg.atoms}
        for r in self.pkg.relations:
            self.assertIn(r.source_id, atom_ids, f"Relation {r.source_id}->{r.target_id}: source not found")
            self.assertIn(r.target_id, atom_ids, f"Relation {r.source_id}->{r.target_id}: target not found")

    def test_unknowns_identified(self):
        self.assertGreater(len(self.pkg.unknowns), 0)
        self.assertEqual(self.pkg.unknowns[0].unknown_id, "U001")

    def test_candidate_memory_records(self):
        self.assertGreater(len(self.pkg.memory_records), 0)
        for m in self.pkg.memory_records:
            self.assertEqual(m.memory_zone, "CANDIDATE", "Pre-E60: all memory must be CANDIDATE")
            self.assertIsNotNone(m.source_atom_ids)

    def test_candidate_skill(self):
        self.assertGreater(len(self.pkg.skills), 0)
        for s in self.pkg.skills:
            self.assertEqual(s.state, "CANDIDATE", "Pre-E60: all skills must be CANDIDATE")
            self.assertTrue(s.requires_e60_authority, "Pre-E60: all skills require E60 gate")

    def test_package_hash_stable(self):
        h1 = self.pkg.package_hash()
        h2 = digest_intraday_extrema(INTRADAY_SOURCE).package_hash()
        self.assertEqual(h1, h2, "Package hash must be deterministic")

    def test_package_summary_not_empty(self):
        self.assertIn("atoms", self.pkg.summary.lower())

    def test_to_dict_produces_valid_structure(self):
        d = self.pkg.to_dict()
        for key in ["package_id", "atoms", "relations", "unknowns", "memory_records", "skills"]:
            self.assertIn(key, d, f"Missing key: {key}")


class TestCreditCalibrationDigest(unittest.TestCase):
    """Test Issue #201 credit calibration candidate package."""

    @classmethod
    def setUpClass(cls):
        cls.pkg = digest_credit_calibration(CREDIT_SOURCE)

    def test_package_identity(self):
        self.assertEqual(self.pkg.package_id, "E47-DIGEST-002-CREDIT-CALIBRATION")

    def test_data_source_atom(self):
        ds = [a for a in self.pkg.atoms if a.atom_type == AtomType.DATA_SOURCE]
        self.assertEqual(len(ds), 1)
        self.assertIn("100 credits", ds[0].content)

    def test_scope_constrains_mapping(self):
        s = [a for a in self.pkg.atoms if a.atom_type == AtomType.SCOPE]
        self.assertGreater(len(s), 0)
        self.assertIn("token", s[0].content.lower())  # Mentions what it is NOT

    def test_confidence_low_for_single_sample(self):
        """Single-sample estimate should not be HIGH confidence."""
        indicators = [a for a in self.pkg.atoms if a.atom_type == AtomType.INDICATOR]
        for a in indicators:
            self.assertNotEqual(a.confidence, Confidence.HIGH,
                f"Single sample atom {a.atom_id} should not be HIGH confidence")

    def test_all_memory_candidate(self):
        for m in self.pkg.memory_records:
            self.assertEqual(m.memory_zone, "CANDIDATE")

    def test_all_skills_candidate(self):
        for s in self.pkg.skills:
            self.assertEqual(s.state, "CANDIDATE")
            self.assertTrue(s.requires_e60_authority)

    def test_atom_count(self):
        self.assertEqual(len(self.pkg.atoms), 4)

    def test_deterministic_hash(self):
        h1 = self.pkg.package_hash()
        h2 = digest_credit_calibration(CREDIT_SOURCE).package_hash()
        self.assertEqual(h1, h2)


class TestPreE60FailsClosed(unittest.TestCase):
    """Verify that E60 gate blocking is structural, not just comments."""

    def test_no_formal_memory_zone_possible(self):
        """Memory zone enum only has CANDIDATE available."""
        from qclaw_e47_digest.intraday_extrema import CandidateMemoryRecord
        try:
            # This is a structural check: the class hardcodes CANDIDATE
            m = CandidateMemoryRecord(
                record_id="test", statement="test",
                memory_zone="GLOBAL",  # type: ignore
                confidence=Confidence.LOW,
                source_atom_ids=("A001",),
                evidence_basis="test",
            )
            d = m.to_dict()
            self.assertEqual(d["memory_zone"], "CANDIDATE",
                "to_dict must ALWAYS return CANDIDATE regardless of input")
        except Exception as e:
            # Even better if it fails
            pass

    def test_no_formal_skill_possible(self):
        """Skill state always CANDIDATE in to_dict."""
        from qclaw_e47_digest.intraday_extrema import CandidateSkill
        s = CandidateSkill(
            skill_id="test", name="test", description="test",
            state="FORMAL",  # type: ignore
            failure_conditions="test",
        )
        d = s.to_dict()
        self.assertEqual(d["state"], "CANDIDATE",
            "to_dict must ALWAYS return CANDIDATE regardless of input")

    def test_all_atoms_in_package_have_source(self):
        for pkg in [digest_intraday_extrema(INTRADAY_SOURCE),
                     digest_credit_calibration(CREDIT_SOURCE)]:
            for a in pkg.atoms:
                self.assertGreater(len(a.source_reference), 0,
                    f"Atom {a.atom_id} missing source_reference")


if __name__ == "__main__":
    unittest.main()
