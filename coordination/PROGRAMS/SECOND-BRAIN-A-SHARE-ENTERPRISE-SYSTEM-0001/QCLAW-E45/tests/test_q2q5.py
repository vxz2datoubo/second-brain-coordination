"""E45 Q2/Q3/Q4/Q5 — Authority, Master, Cognition, Skill from verifier-only capability"""
import unittest, hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from qclaw_e45.capability import (
    VerifiedEvidenceCapabilityView, make_test_capability,
    EvidenceOrigin, VerificationState, ConfidenceBand,
)
from qclaw_e45.authority import (
    EvidenceRecord, EvidenceBundle, Atom, AtomType,
    EvidenceRegistry, EvidenceFactory,
)
from qclaw_e45.master_record import (
    MasterRecord, VersionEvent, TransitionType, ConflictClass,
    MasterRegistry,
)
from qclaw_e45.cognition import (
    CognitionEntry, MemoryZone, CognitionEngine,
)
from qclaw_e45.skill_lifecycle import (
    Skill, SkillState, SkillFactory, TestReceipt,
)

SAMPLE = b"RSI(14) above 70 indicates overbought conditions for the stock."

_counter = 0
def _make_cap(text=None, origin=EvidenceOrigin.SOURCE_DOCUMENT, verified=True, sid=None):
    global _counter; _counter += 1
    t = text or f"RSI({_counter})"
    sid = sid or f"doc_{_counter}"
    return make_test_capability(sid, (0, len(t)), t, origin, SAMPLE, verified=verified)


# ===== Q2 Authority =====

class TestAuthority(unittest.TestCase):
    def setUp(self):
        self.reg = EvidenceRegistry()
        self.evf = EvidenceFactory(self.reg)

    def test_create_record_from_capability(self):
        cap = _make_cap("market momentum")
        rec = self.evf.create_record(cap)
        self.assertEqual(rec.origin, EvidenceOrigin.SOURCE_DOCUMENT)
        self.assertEqual(rec.verification_state, VerificationState.VERIFIED)

    def test_record_confidence_derived(self):
        cap = _make_cap("momentum", verified=True, origin=EvidenceOrigin.SOURCE_DOCUMENT)
        rec = self.evf.create_record(cap)
        self.assertEqual(rec.confidence, ConfidenceBand.HIGH)

    def test_bundle_empty_rejected(self):
        with self.assertRaises(ValueError):
            self.evf.create_bundle([])

    def test_create_bundle(self):
        r1 = self.evf.create_record(_make_cap("RSI", sid="src_a"))
        r2 = self.evf.create_record(_make_cap("MACD", sid="src_b"))
        bundle = self.evf.create_bundle([r1, r2])
        self.assertEqual(len(bundle.records), 2)

    def test_create_atom_from_bundle(self):
        rec = self.evf.create_record(_make_cap("concept_text", sid="src_c"))
        bundle = self.evf.create_bundle([rec])
        atom = self.evf.create_atom(bundle, atom_type=AtomType.CONCEPT)
        self.assertEqual(atom.atom_type, AtomType.CONCEPT)

    def test_atom_verify(self):
        rec = self.evf.create_record(_make_cap("verify_me", sid="src_v"))
        bundle = self.evf.create_bundle([rec])
        atom = self.evf.create_atom(bundle)
        self.assertTrue(self.evf.verify_atom(atom))

    def test_foreign_object_reverify_fails(self):
        rec = self.evf.create_record(_make_cap("foreign_test", sid="src_f"))
        bundle = self.evf.create_bundle([rec])
        atom = self.evf.create_atom(bundle)
        reg2 = EvidenceRegistry()
        evf2 = EvidenceFactory(reg2)
        self.assertFalse(evf2.verify_atom(atom))

    def test_hypothesis_confidence_low(self):
        cap = _make_cap("maybe pattern", origin=EvidenceOrigin.HYPOTHESIS, verified=False, sid="hyp1")
        rec = self.evf.create_record(cap)
        self.assertEqual(rec.confidence, ConfidenceBand.LOW)

    def test_bundle_id_different_per_call(self):
        rec = self.evf.create_record(_make_cap("id_test", sid="src_id"))
        b1 = self.evf.create_bundle([rec])
        b2 = self.evf.create_bundle([rec])
        self.assertNotEqual(b1.bundle_id, b2.bundle_id)


# ===== Q3 Master Record =====

class TestMasterRecord(unittest.TestCase):
    def setUp(self):
        self.reg = EvidenceRegistry()
        self.evf = EvidenceFactory(self.reg)
        self.mr = MasterRegistry()
        self._sid = 0

    def _rec(self, text):
        self._sid += 1
        cap = make_test_capability(f"src_m{self._sid}", (0, len(text)), text,
                                   EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE, verified=True)
        return self.evf.create_record(cap)

    def test_create_master(self):
        rec = self._rec("RSI concept")
        bundle = self.evf.create_bundle([rec])
        master = self.mr.create_master(bundle, "obj1")
        self.assertEqual(master.object_id, "obj1")
        self.assertEqual(len(master.versions), 1)

    def test_master_identity_stable(self):
        rec = self._rec("stable id")
        bundle = self.evf.create_bundle([rec])
        self.mr.create_master(bundle, "obj_id_stable")
        m2 = self.mr.get_master("obj_id_stable")
        self.assertIsNotNone(m2)

    def test_add_version(self):
        rec1 = self._rec("initial")
        bundle1 = self.evf.create_bundle([rec1])
        master = self.mr.create_master(bundle1, "ver1")
        rec2 = self._rec("revised")
        bundle2 = self.evf.create_bundle([rec2])
        vt = self.mr.add_version(master, bundle2, TransitionType.CORRECTION, "tightened")
        self.assertEqual(vt.transition, TransitionType.CORRECTION)

    def test_version_history_length(self):
        rec1 = self._rec("v1 content")
        bundle1 = self.evf.create_bundle([rec1])
        master = self.mr.create_master(bundle1, "vchain")
        rec2 = self._rec("v2 content")
        bundle2 = self.evf.create_bundle([rec2])
        self.mr.add_version(master, bundle2, TransitionType.ADDITION, "added")
        self.assertEqual(len(master.versions), 2)

    def test_contradiction_unresolved_default(self):
        rec1 = self._rec("bullish signal")
        bundle1 = self.evf.create_bundle([rec1])
        master = self.mr.create_master(bundle1, "conf_obj")
        rec2 = self._rec("bearish signal")
        bundle2 = self.evf.create_bundle([rec2])
        conflict = self.mr.classify_conflict(master, bundle2)
        self.assertEqual(conflict, ConflictClass.UNRESOLVED)

    def test_transition_verified(self):
        rec = self._rec("transition test")
        bundle = self.evf.create_bundle([rec])
        master = self.mr.create_master(bundle, "trans1")
        valid = self.mr.verify_transition(master, bundle, TransitionType.REPLACEMENT, "replaced")
        self.assertTrue(valid)


# ===== Q4 Cognition =====

class TestCognition(unittest.TestCase):
    def setUp(self):
        self.reg = EvidenceRegistry()
        self.evf = EvidenceFactory(self.reg)
        self.ce = CognitionEngine(self.reg)
        self._sid = 0

    def _user_cap(self, text):
        self._sid += 1
        return make_test_capability(f"user_msg_{self._sid}", (0, len(text)), text,
                                   EvidenceOrigin.USER_EXPLICIT_MESSAGE,
                                   text.encode(), verified=True)

    def _doc_cap(self, text):
        self._sid += 1
        return make_test_capability(f"doc_{self._sid}", (0, len(text)), text,
                                   EvidenceOrigin.SOURCE_DOCUMENT, SAMPLE, verified=True)

    def test_user_origin_gets_global(self):
        cap = self._user_cap("I know RSI is overbought")
        rec = self.evf.create_record(cap)
        bundle = self.evf.create_bundle([rec])
        entry = self.ce.derive_entry(bundle)
        self.assertEqual(entry.memory_zone, MemoryZone.GLOBAL)

    def test_source_document_not_global(self):
        cap = self._doc_cap("trend following analysis")
        rec = self.evf.create_record(cap)
        bundle = self.evf.create_bundle([rec])
        entry = self.ce.derive_entry(bundle)
        self.assertNotEqual(entry.memory_zone, MemoryZone.GLOBAL)

    def test_author_claim_is_candidate(self):
        cap = make_test_capability("author_1", (0, 10), "claim text",
                                   EvidenceOrigin.AUTHOR_CLAIM, b"claim text", verified=False)
        rec = self.evf.create_record(cap)
        bundle = self.evf.create_bundle([rec])
        entry = self.ce.derive_entry(bundle)
        self.assertEqual(entry.memory_zone, MemoryZone.CANDIDATE)

    def test_generic_prose_not_global(self):
        cap = self._doc_cap("I believe stocks will rise tomorrow")
        rec = self.evf.create_record(cap)
        bundle = self.evf.create_bundle([rec])
        entry = self.ce.derive_entry(bundle)
        self.assertNotEqual(entry.memory_zone, MemoryZone.GLOBAL)


# ===== Q5 Skill Lifecycle =====

class TestSkillLifecycle(unittest.TestCase):
    def setUp(self):
        self.sf = SkillFactory()

    def test_create_skill_candidate(self):
        r = TestReceipt("r1", ["c1"], True, 0, "one case")
        s = self.sf.create_skill("s1", "test", r)
        self.assertEqual(s.state, SkillState.CANDIDATE)

    def test_promote_to_experimental(self):
        r = TestReceipt("r1", ["c1","c2"], True, 0, "2 cases")
        s = self.sf.create_skill("s2", "exp candidate", r)
        s = self.sf.promote(s, [r], SkillState.EXPERIMENTAL)
        self.assertEqual(s.state, SkillState.EXPERIMENTAL)

    def test_promote_to_formal(self):
        r1 = TestReceipt("r1", ["c1","c2","c3"], True, 0, "3 cases run1")
        s = self.sf.create_skill("s3", "formal candidate", r1)
        r2 = TestReceipt("r2", ["c4","c5"], True, 0, "2 more")
        s = self.sf.promote(s, [r1], SkillState.EXPERIMENTAL)
        s = self.sf.promote(s, [r1, r2], SkillState.FORMAL)
        self.assertEqual(s.state, SkillState.FORMAL)

    def test_direct_formal_blocked(self):
        r = TestReceipt("r1", ["c1"], True, 0, "one case")
        s = self.sf.create_skill("s4", "test", r)
        with self.assertRaises(ValueError):
            self.sf.promote(s, [r], SkillState.FORMAL)

    def test_demote_preserves_reason(self):
        r = TestReceipt("r1", ["c1","c2"], True, 0, "2 cases")
        s = self.sf.create_skill("s5", "test", r)
        s = self.sf.promote(s, [r], SkillState.EXPERIMENTAL)
        s = self.sf.demote(s, "counterexample found", r)
        self.assertEqual(s.state, SkillState.DEMOTED)
        self.assertIn("counterexample", s.demotion_reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
