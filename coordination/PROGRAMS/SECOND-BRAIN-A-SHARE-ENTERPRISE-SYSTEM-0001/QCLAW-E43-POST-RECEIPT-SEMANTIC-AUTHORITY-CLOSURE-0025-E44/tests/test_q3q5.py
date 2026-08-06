"""E44 Q3-Q5 Tests — Master records, Cognition, Skills"""
import unittest, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)

from qclaw_e44.capability import CapabilityVerifier, EvidenceOrigin
from qclaw_e44.authority import EvidenceRegistry, EvidenceFactory
from qclaw_e44.master_record import (
    MasterRegistry, MasterRecord, VersionEvent, ConflictEntry,
    ConflictClass, EventType, MasterError,
)
from qclaw_e44.cognition import (
    CognitionEngine, CognitionEntry, CognitionState, MemoryZone,
)
from qclaw_e44.skill_lifecycle import (
    SkillFactory, SkillState, SkillPromotionGate, TransitionReceipt, Skill,
)


# ── Q3: Master Records ────────────────────────────────────────
class TestMasterRecord(unittest.TestCase):
    def setUp(self):
        self.reg = MasterRegistry(b"e44_master_key_xxxxxxxxxxxxxxx32")

    def test_create_record(self):
        mr = self.reg.create("content X", ("ev_001",))
        self.assertEqual(mr.current_content, "content X")
        self.assertEqual(mr.version_count, 1)
        self.assertTrue(mr.verify(self.reg))

    def test_semantic_identity_separate_from_content(self):
        mr1 = self.reg.create("content A", ("ev_a",))
        # Same semantic identity (same normalized content) → rejected
        with self.assertRaises(MasterError):
            self.reg.create("content A", ("ev_a2",))
        # Different content, different identity
        mr2 = self.reg.create("different content", ("ev_b",))
        self.assertNotEqual(mr1.semantic_identity, mr2.semantic_identity)

    def test_version_transition(self):
        mr = self.reg.create("v1 data", ("ev_1",))
        mr2 = self.reg.apply_version(mr.record_id, EventType.CORRECTION,
            "v2 corrected", ("ev_2",), "fixing data")
        self.assertEqual(mr2.current_content, "v2 corrected")
        self.assertEqual(mr2.version_count, 2)

    def test_conflict_registration(self):
        a = self.reg.create("alpha", ("ev_1",))
        b = self.reg.create("beta", ("ev_2",))
        ce = self.reg.register_conflict(a.record_id, b.record_id,
            ConflictClass.PROBABLE_ERROR, ("ev_3",), "conflicting values")
        self.assertTrue(ce.unresolved)
        self.assertEqual(self.reg.conflict_count, 1)

    def test_conflict_requires_registered_records(self):
        with self.assertRaises(MasterError):
            self.reg.register_conflict("fake_a", "fake_b",
                ConflictClass.UNRESOLVED, (), "bad")

    def test_classify_conflict_from_evidence_layers(self):
        cc = self.reg.classify_conflict("a", "b", "source_fact", "source_fact")
        self.assertEqual(cc, ConflictClass.PROBABLE_ERROR)
        cc2 = self.reg.classify_conflict("a", "b", "source_fact", "hypothesis")
        self.assertEqual(cc2, ConflictClass.DEFINITION_MISMATCH)

    def test_records_immutable_fields(self):
        mr = self.reg.create("test", ("ev_1",))
        with self.assertRaises((AttributeError,)):
            mr.current_content = "hacked"


# ── Q4: Cognition ─────────────────────────────────────────────
class TestCognition(unittest.TestCase):
    def setUp(self):
        self.ev_registry = EvidenceRegistry()
        self.ev_factory = EvidenceFactory(self.ev_registry, b"e44_ev_key_xxxxxxxxxxxxxxxxx32")
        self.cv = CapabilityVerifier("E44-cog-issuer", "1.0")
        self.cog = CognitionEngine(self.ev_registry, b"e44_cog_key_xxxxxxxxxxxxxxxxx32")

    def _make_record(self, text: bytes):
        cap = self.cv.verify(text, f"src:0:{len(text)}", EvidenceOrigin.SOURCE_FACT)
        return self.ev_factory.create_record(cap)

    def test_user_explicit_produces_known_and_stated(self):
        rec = self._make_record(b"I know that my data is correct")
        entry = self.cog.analyze(rec.record_id)
        self.assertEqual(entry.state, CognitionState.KNOWN_AND_STATED)
        self.assertEqual(entry.stability_score, 1.0)

    def test_source_fact_produces_known_but_unstated(self):
        rec = self._make_record(b"Market data shows a 5% increase")
        entry = self.cog.analyze(rec.record_id)
        self.assertEqual(entry.state, CognitionState.KNOWN_BUT_UNSTATED)

    def test_hypothesis_produces_unknown_needs_layering(self):
        rec = self._make_record(b"It could be that patterns repeat")
        entry = self.cog.analyze(rec.record_id)
        self.assertEqual(entry.state, CognitionState.UNKNOWN_AND_NEEDS_LAYERING)

    def test_no_auto_global(self):
        """GLOBAL is not automatically given. USER_EXPLICIT → PROJECT."""
        rec = self._make_record(b"I know this well")
        entry = self.cog.analyze(rec.record_id)
        self.assertNotEqual(entry.memory_zone, MemoryZone.GLOBAL)

    def test_value_judgment_do_not_persist(self):
        rec = self._make_record(b"This is the best approach")
        entry = self.cog.analyze(rec.record_id)
        self.assertEqual(entry.memory_zone, MemoryZone.DO_NOT_PERSIST)

    def test_entry_verification(self):
        rec = self._make_record(b"Data here")
        entry = self.cog.analyze(rec.record_id)
        self.assertTrue(self.cog.verify(entry))

    def test_unregistered_record_rejected(self):
        with self.assertRaises(ValueError):
            self.cog.analyze("nonexistent_id")

    def test_buffer_fills(self):
        rec = self._make_record(b"entry one")
        self.cog.analyze(rec.record_id)
        self.assertEqual(self.cog.buffer_count, 1)


# ── Q5: Skills ────────────────────────────────────────────────
class TestSkillLifecycle(unittest.TestCase):
    def setUp(self):
        self.factory = SkillFactory(b"e44_skill_key_xxxxxxxxxxxxxxxxx32")

    def test_create_skill_starts_candidate(self):
        s = self.factory.create_skill("test", "desc")
        self.assertEqual(s.state, SkillState.CANDIDATE)
        self.assertTrue(self.factory.verify(s))

    def test_promote_candidate_to_experimental(self):
        s = self.factory.create_skill("promo", "test skill")
        r = TransitionReceipt(
            receipt_id="r1", from_state=SkillState.CANDIDATE,
            to_state=SkillState.EXPERIMENTAL,
            evidence_record_ids=("e1", "e2"), test_run_id="run1",
            case_count=3, counterexample_count=0,
            scope_definition="domain:test",
            failure_conditions=("f1", "f2"), rollback_defined=True,
            timestamp_ns=time.time_ns())
        s2 = self.factory.promote(s, SkillState.EXPERIMENTAL, r)
        self.assertEqual(s2.state, SkillState.EXPERIMENTAL)

    def test_insufficient_cases_rejected(self):
        s = self.factory.create_skill("weak", "not enough")
        r = TransitionReceipt(
            receipt_id="r2", from_state=SkillState.CANDIDATE,
            to_state=SkillState.EXPERIMENTAL,
            evidence_record_ids=("e1",), test_run_id="run_w",
            case_count=1, counterexample_count=0,
            scope_definition="test", failure_conditions=("f1",),
            rollback_defined=True, timestamp_ns=time.time_ns())
        with self.assertRaises(ValueError):
            self.factory.promote(s, SkillState.EXPERIMENTAL, r)

    def test_single_sample_not_formal(self):
        gate = SkillPromotionGate()
        r = TransitionReceipt(
            receipt_id="r3", from_state=SkillState.EXPERIMENTAL,
            to_state=SkillState.FORMAL,
            evidence_record_ids=("e1", "e2", "e3"), test_run_id="run3",
            case_count=1, counterexample_count=0,
            scope_definition="test", failure_conditions=("f1", "f2"),
            rollback_defined=True, timestamp_ns=time.time_ns())
        self.assertFalse(gate.can_promote_to_formal(r))

    def test_demote_skill(self):
        s = self.factory.create_skill("demoting", "test")
        s2 = self.factory.demote(s, "ev_demote")
        self.assertEqual(s2.state, SkillState.DEMOTED)

    def test_unregistered_skill_rejected(self):
        forged = Skill(
            skill_id="fake", name="fake", state=SkillState.FORMAL,
            description="fake", transitions=(), schema_version="44.0",
            issuer="fake", factory_signature=b"bad")
        self.assertFalse(self.factory.verify(forged))


if __name__ == "__main__":
    unittest.main(verbosity=2)
