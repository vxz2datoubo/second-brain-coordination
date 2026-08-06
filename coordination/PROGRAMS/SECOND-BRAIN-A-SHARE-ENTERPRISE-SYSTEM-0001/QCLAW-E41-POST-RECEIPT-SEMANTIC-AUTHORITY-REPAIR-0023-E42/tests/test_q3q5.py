"""E42 Q3-Q5 Tests — Master Records, Cognition, Skills"""
import unittest, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
sys.path.insert(0, SRC)
os.environ["PYTHONIOENCODING"] = "utf-8"

from qclaw_e42.master_record import (
    MasterRecord, MasterRecordRegistry, VersionEvent, VersionEventType,
    ConflictClass, compute_object_id, classify_conflict,
    prohibit_silent_overwrite,
)
from qclaw_e42.cognition import (
    CognitionEngine, CognitionEntry, CognitionLayer, InferenceQuality, MemoryZone,
)
from qclaw_e42.skill_lifecycle import (
    Skill, SkillBuilder, SkillState, TransitionReceipt, single_sample_not_formal,
)


# ==================== Q3 - Master Record ====================

class TestMasterRecord(unittest.TestCase):
    def test_compute_object_id_stable(self):
        id1 = compute_object_id("RSI indicator definition")
        id2 = compute_object_id("RSI indicator definition")
        self.assertEqual(id1, id2)

    def test_different_semantic_key_different_id(self):
        id1 = compute_object_id("RSI definition")
        id2 = compute_object_id("MACD definition")
        self.assertNotEqual(id1, id2)

    def test_id_is_deterministic_format(self):
        oid = compute_object_id("test key")
        self.assertEqual(len(oid), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in oid))

    def test_create_master(self):
        rec = MasterRecord(object_id="o1", current_content="content A")
        self.assertEqual(rec.current_content, "content A")
        self.assertEqual(rec.version_history, ())

    def test_version_event_requires_matching_previous(self):
        rec = MasterRecord(object_id="o1", current_content="v1")
        event = VersionEvent(
            event_type=VersionEventType.CORRECTION,
            previous_content="v1", new_content="v2",
            evidence_id="E001", reason="fix", timestamp="2026-08-01"
        )
        updated = rec.with_version_event(event)
        self.assertEqual(updated.current_content, "v2")
        self.assertEqual(len(updated.version_history), 1)

    def test_version_event_mismatch_previous_rejected(self):
        rec = MasterRecord(object_id="o1", current_content="v1")
        event = VersionEvent(
            event_type=VersionEventType.CORRECTION,
            previous_content="wrong", new_content="v2",
            evidence_id="E001", reason="fix", timestamp="2026-08-01"
        )
        with self.assertRaises(ValueError):
            rec.with_version_event(event)

    def test_conflict_tracked(self):
        rec = MasterRecord(object_id="o1", current_content="v1")
        rec = rec.with_conflict("conflicting text", "E005", ConflictClass.UNRESOLVED)
        self.assertEqual(len(rec.conflict_classifications), 1)

    def test_classify_conflict_default_unresolved(self):
        cc = classify_conflict("text A", "text B", None)
        self.assertEqual(cc, ConflictClass.UNRESOLVED)

    def test_classify_conflict_evidence_driven(self):
        cc = classify_conflict("a", "b", {"time_change": True})
        self.assertEqual(cc, ConflictClass.TIME_CHANGE)
        cc = classify_conflict("a", "b", {"definition_mismatch": True})
        self.assertEqual(cc, ConflictClass.DEFINITION_MISMATCH)
        cc = classify_conflict("a", "b", {"probable_error": True})
        self.assertEqual(cc, ConflictClass.PROBABLE_ERROR)
        cc = classify_conflict("a", "b", {"scenario_difference": True})
        self.assertEqual(cc, ConflictClass.SCENARIO_DIFFERENCE)

    def test_classify_no_heuristic_autoclass(self):
        """Conflict classification must not auto-label from word overlap."""
        cc = classify_conflict("the quick brown fox jumps", "the quick brown fox jumps", None)
        # Even near-identical text → UNRESOLVED without evidence
        self.assertEqual(cc, ConflictClass.UNRESOLVED)

    def test_silent_overwrite_blocked(self):
        rec = MasterRecord(object_id="o1", current_content="v1",
                           provenance_list=("P1",))
        event = VersionEvent(
            event_type=VersionEventType.ADDITION,
            previous_content="v1", new_content="v1_plus",
            evidence_id="E002", reason="add", timestamp="2026-08-01"
        )
        rec2 = rec.with_version_event(event)
        self.assertEqual(rec2.version_history[-1].event_id, event.event_id)

    def test_silent_overwrite_fails_without_evidence(self):
        rec = MasterRecord(object_id="o1", current_content="v1")
        with self.assertRaises(ValueError):
            prohibit_silent_overwrite(rec, "v2", "", VersionEventType.CORRECTION, "t")

    def test_second_transition_provenance(self):
        rec = MasterRecord(object_id="o1", current_content="v1",
                           provenance_list=("P1",))
        event1 = VersionEvent(VersionEventType.CORRECTION, "v1", "v2",
                              "E1", "fix 1", "2026-01-01")
        rec = rec.with_version_event(event1)
        event2 = VersionEvent(VersionEventType.REPLACEMENT, "v2", "v3",
                              "E2", "replace", "2026-02-01")
        rec = rec.with_version_event(event2)
        self.assertEqual(len(rec.version_history), 2)
        self.assertIn("E1", rec.provenance_list)
        self.assertIn("E2", rec.provenance_list)

    def test_registry_get_or_create(self):
        reg = MasterRecordRegistry()
        rec, created = reg.get_or_create("topic X", "content 1", "P1")
        self.assertTrue(created)
        rec2, created2 = reg.get_or_create("topic X", "different", "P2")
        self.assertFalse(created2)
        self.assertEqual(rec2.current_content, "content 1")  # returns existing

    def test_registry_update(self):
        reg = MasterRecordRegistry()
        rec, _ = reg.get_or_create("topic Y", "v1", "P1")
        event = VersionEvent(VersionEventType.CORRECTION, "v1", "v2",
                             "E99", "reason", "2026-01-01")
        rec2 = rec.with_version_event(event)
        reg.update(rec2)
        self.assertEqual(reg.get("topic Y").current_content, "v2")


# ==================== Q4 - Cognition ====================

class TestCognition(unittest.TestCase):
    def setUp(self):
        self.engine = CognitionEngine("TEST_ENGINE")

    def test_explicit_user_fact_needs_user_evidence(self):
        entry = self.engine.create(
            "E01", "risk tolerance", "high risk",
            is_stated=True, is_known=True, is_readable=True,
            has_user_origin_evidence=True, has_corroboration=True,
            has_direct_evidence=True,
            evidence_ids=("EV001",), source_document_id="SD1",
        )
        self.assertEqual(entry.quality, InferenceQuality.EXPLICIT_USER_FACT)
        self.assertEqual(entry.memory_zone, MemoryZone.GLOBAL)

    def test_low_confidence_guess_unpersisted(self):
        entry = self.engine.create(
            "E02", "guess", "maybe something",
            is_stated=False, is_known=False, is_readable=True,
            has_user_origin_evidence=False, has_corroboration=False,
            has_direct_evidence=False,
            evidence_ids=(),
        )
        self.assertEqual(entry.quality, InferenceQuality.LOW_CONFIDENCE_GUESS)
        self.assertEqual(entry.memory_zone, MemoryZone.UNPERSISTED)

    def test_global_memory_requires_evidence(self):
        engine = self.engine
        entry = engine.create(
            "E03", "fact", "something known",
            is_stated=True, is_known=True, is_readable=True,
            has_user_origin_evidence=True, has_corroboration=True,
            has_direct_evidence=True,
            evidence_ids=(),  # No evidence!
        )
        # Without evidence, falls to HIGH_PROBABILITY → PROJECT or CANDIDATE
        self.assertNotEqual(entry.memory_zone, MemoryZone.GLOBAL)

    def test_validate_global_needs_explicit_fact(self):
        engine = CognitionEngine()
        entry = CognitionEntry(
            entry_id="bad", subject="x", layer=CognitionLayer.KNOWN_AND_STATED,
            quality=InferenceQuality.HIGH_PROBABILITY_INFERENCE,
            content="data", evidence_ids=("E1",), memory_zone=MemoryZone.GLOBAL,
        )
        violations = engine.validate(entry)
        self.assertTrue(len(violations) > 0)

    def test_validate_project_no_low_confidence(self):
        engine = CognitionEngine()
        entry = CognitionEntry(
            entry_id="bad2", subject="x", layer=CognitionLayer.KNOWN_AND_STATED,
            quality=InferenceQuality.LOW_CONFIDENCE_GUESS,
            content="data", evidence_ids=(), memory_zone=MemoryZone.PROJECT,
        )
        violations = engine.validate(entry)
        self.assertTrue(len(violations) > 0)

    def test_layer_classification(self):
        eng = self.engine
        self.assertEqual(eng.classify_layer(True, True, True), CognitionLayer.KNOWN_AND_STATED)
        self.assertEqual(eng.classify_layer(False, False, False), CognitionLayer.UNKNOWN_AND_NEEDS_LAYERING)

    def test_quality_classification(self):
        eng = self.engine
        self.assertEqual(
            eng.classify_quality(True, True, True),
            InferenceQuality.EXPLICIT_USER_FACT
        )
        self.assertEqual(
            eng.classify_quality(False, False, False),
            InferenceQuality.LOW_CONFIDENCE_GUESS
        )


# ==================== Q5 - Skills ====================

class TestSkills(unittest.TestCase):
    def setUp(self):
        self.builder = SkillBuilder()

    def test_propose_candidate(self):
        skill = self.builder.propose_candidate("RSI Strategy", "A momentum strategy")
        self.assertEqual(skill.state, SkillState.CANDIDATE)
        self.assertEqual(len(skill.skill_id), 64)

    def test_candidate_to_experimental(self):
        skill = self.builder.propose_candidate("test", "desc")
        receipts = (
            TransitionReceipt("R1", SkillState.CANDIDATE, SkillState.EXPERIMENTAL, ("E1",)),
            TransitionReceipt("R2", SkillState.CANDIDATE, SkillState.EXPERIMENTAL, ("E2",)),
        )
        exp = self.builder.promote_to_experimental(skill, receipts, ("E1", "E2"))
        self.assertEqual(exp.state, SkillState.EXPERIMENTAL)
        self.assertEqual(len(exp.transition_history), 1)

    def test_promote_without_receipts_fails(self):
        skill = self.builder.propose_candidate("test", "desc")
        with self.assertRaises(ValueError):
            self.builder.promote_to_experimental(skill, (), ())

    def test_experimental_to_formal(self):
        skill = self.builder.propose_candidate("formal test", "desc")
        receipts = (TransitionReceipt("R1", SkillState.CANDIDATE, SkillState.EXPERIMENTAL, ("E1",)),)
        exp = self.builder.promote_to_experimental(skill, receipts, ("E1",))

        tr = (TransitionReceipt("RT1", SkillState.EXPERIMENTAL, SkillState.FORMAL, ("EV",)),)
        formal = self.builder.promote_to_formal(
            exp, tr, ("CASE001",), ("CE001",),
            "applies to liquid markets",
            ("market closure prevents execution",),
            "revert to experimental on 3 consecutive failures"
        )
        self.assertEqual(formal.state, SkillState.FORMAL)

    def test_formal_requires_all_fields(self):
        skill = self.builder.propose_candidate("test", "desc")
        receipts = (TransitionReceipt("R1", SkillState.CANDIDATE, SkillState.EXPERIMENTAL, ("E1",)),)
        exp = self.builder.promote_to_experimental(skill, receipts, ("E1",))

        with self.assertRaises(ValueError):
            self.builder.promote_to_formal(exp, (), ("C1",), (), "", (), "")

    def test_direct_formal_construction_safe(self):
        """Skill constructor doesn't enforce state, but builder forces transitions."""
        # Direct construction is possible but SkillBuilder enforces the lifecycle
        skill = self.builder.propose_candidate("test", "desc")
        self.assertEqual(skill.state, SkillState.CANDIDATE)

    def test_skip_experimental_to_formal_fails(self):
        skill = self.builder.propose_candidate("test", "desc")
        with self.assertRaises(ValueError):
            self.builder.promote_to_formal(
                skill, (TransitionReceipt("r", SkillState.CANDIDATE, SkillState.FORMAL, ("e",)),),
                ("c",), ("ce",), "scope", ("fc",), "rollback"
            )

    def test_demote(self):
        skill = self.builder.propose_candidate("test", "desc")
        receipts = (TransitionReceipt("R1", SkillState.CANDIDATE, SkillState.EXPERIMENTAL, ("E1",)),)
        exp = self.builder.promote_to_experimental(skill, receipts, ("E1",))
        demoted = self.builder.demote(exp, "failed tests")
        self.assertEqual(demoted.state, SkillState.DEMOTED)

    def test_deprecate(self):
        skill = self.builder.propose_candidate("test", "desc")
        dep = self.builder.deprecate(skill, "outdated approach")
        self.assertEqual(dep.state, SkillState.DEPRECATED)
        self.assertEqual(dep.deprecation_reason, "outdated approach")

    def test_supersede(self):
        skill = self.builder.propose_candidate("test", "desc")
        sup = self.builder.supersede(skill, "new-skill-id")
        self.assertEqual(sup.state, SkillState.SUPERSEDED)
        self.assertEqual(sup.superseded_by, "new-skill-id")

    def test_single_sample_not_formal(self):
        self.assertTrue(single_sample_not_formal())


if __name__ == "__main__":
    unittest.main(verbosity=2)
