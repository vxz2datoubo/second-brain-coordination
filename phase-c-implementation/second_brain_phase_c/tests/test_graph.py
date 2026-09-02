"""Tests for Graph Evolution Manager: relations, conflict sets, lineage chains."""
import pytest
from second_brain_phase_c.models import (
    KnowledgeAtom, AtomType, AtomStatus, PrivacyClass, Scope,
    RelationType, ConflictType, ConflictResolutionStatus,
)
from second_brain_phase_c.graph import GraphEvolutionManager


class TestGraphEvolution:
    def test_create_relation(self, graph_manager, atom_store):
        a1 = KnowledgeAtom(canonical_statement="A", atom_type=AtomType.CONCEPT)
        a2 = KnowledgeAtom(canonical_statement="B", atom_type=AtomType.CONCEPT)
        atom_store[a1.atom_id] = a1
        atom_store[a2.atom_id] = a2
        rel = graph_manager.create_relation(a1.atom_id, a2.atom_id, RelationType.IS_A, confidence=0.9)
        assert rel.relation_type == RelationType.IS_A
        assert rel.relation_id in a1.relation_ids
        assert rel.relation_id in a2.relation_ids

    def test_duplicate_relation_returns_existing(self, graph_manager, atom_store):
        a1 = KnowledgeAtom(canonical_statement="A")
        a2 = KnowledgeAtom(canonical_statement="B")
        atom_store[a1.atom_id] = a1
        atom_store[a2.atom_id] = a2
        rel1 = graph_manager.create_relation(a1.atom_id, a2.atom_id, RelationType.IS_A)
        rel2 = graph_manager.create_relation(a1.atom_id, a2.atom_id, RelationType.IS_A)
        assert rel1.relation_id == rel2.relation_id

    def test_create_conflict_set(self, graph_manager, atom_store):
        a1 = KnowledgeAtom(canonical_statement="X是对的")
        a2 = KnowledgeAtom(canonical_statement="X是错的")
        atom_store[a1.atom_id] = a1
        atom_store[a2.atom_id] = a2
        cs = graph_manager.create_conflict_set([a1.atom_id, a2.atom_id], ConflictType.FACTUAL, "Test conflict")
        assert atom_store[a1.atom_id].current_status == AtomStatus.CONFLICTED
        assert atom_store[a2.atom_id].current_status == AtomStatus.CONFLICTED
        assert atom_store[a1.atom_id].conflict_set_id == cs.conflict_set_id

    def test_resolve_conflict_set(self, graph_manager, atom_store):
        a1 = KnowledgeAtom(canonical_statement="X是对的")
        a2 = KnowledgeAtom(canonical_statement="X是错的")
        atom_store[a1.atom_id] = a1
        atom_store[a2.atom_id] = a2
        cs = graph_manager.create_conflict_set([a1.atom_id, a2.atom_id])
        graph_manager.resolve_conflict_set(cs.conflict_set_id, surviving_atom_id=a1.atom_id)
        assert atom_store[a1.atom_id].current_status == AtomStatus.ACTIVE
        assert atom_store[a2.atom_id].current_status == AtomStatus.SUPERSEDED
        assert cs.resolution_status == ConflictResolutionStatus.RESOLVED

    def test_supersession_lineage(self, graph_manager, atom_store):
        old = KnowledgeAtom(canonical_statement="旧版本", current_status=AtomStatus.ACTIVE)
        new = KnowledgeAtom(canonical_statement="新版本", current_status=AtomStatus.CANDIDATE)
        atom_store[old.atom_id] = old
        atom_store[new.atom_id] = new
        graph_manager.set_supersession(old.atom_id, new.atom_id)
        assert old.current_status == AtomStatus.SUPERSEDED
        assert old.lineage_head is False
        assert new.lineage_head is True
        assert new.atom_id in old.successor_atom_ids
        assert old.atom_id in new.predecessor_atom_ids

    def test_supersession_cycle_detection(self, graph_manager, atom_store):
        a = KnowledgeAtom(canonical_statement="A")
        b = KnowledgeAtom(canonical_statement="B")
        atom_store[a.atom_id] = a
        atom_store[b.atom_id] = b
        graph_manager.set_supersession(a.atom_id, b.atom_id)
        with pytest.raises(ValueError, match="cycle"):
            graph_manager.set_supersession(b.atom_id, a.atom_id)

    def test_lineage_chain(self, graph_manager, atom_store):
        v1 = KnowledgeAtom(canonical_statement="v1")
        v2 = KnowledgeAtom(canonical_statement="v2")
        v3 = KnowledgeAtom(canonical_statement="v3")
        atom_store[v1.atom_id] = v1
        atom_store[v2.atom_id] = v2
        atom_store[v3.atom_id] = v3
        graph_manager.set_supersession(v1.atom_id, v2.atom_id)
        graph_manager.set_supersession(v2.atom_id, v3.atom_id)
        chain = graph_manager.get_lineage_chain(v1.atom_id)
        assert len(chain) == 3
        assert chain[0] == v1.atom_id
        assert chain[-1] == v3.atom_id

    def test_get_current_head(self, graph_manager, atom_store):
        v1 = KnowledgeAtom(canonical_statement="v1")
        v2 = KnowledgeAtom(canonical_statement="v2")
        atom_store[v1.atom_id] = v1
        atom_store[v2.atom_id] = v2
        graph_manager.set_supersession(v1.atom_id, v2.atom_id)
        head = graph_manager.get_current_head(v1.atom_id)
        assert head.atom_id == v2.atom_id

    def test_consistency_checks_pass(self, graph_manager, atom_store):
        a1 = KnowledgeAtom(canonical_statement="A")
        a2 = KnowledgeAtom(canonical_statement="B")
        atom_store[a1.atom_id] = a1
        atom_store[a2.atom_id] = a2
        graph_manager.create_relation(a1.atom_id, a2.atom_id, RelationType.IS_A)
        results = graph_manager.run_all_consistency_checks()
        assert results["all_passed"] is True

    def test_revoke_relation(self, graph_manager, atom_store):
        from second_brain_phase_c.models import RelationStatus
        a1 = KnowledgeAtom(canonical_statement="A")
        a2 = KnowledgeAtom(canonical_statement="B")
        atom_store[a1.atom_id] = a1
        atom_store[a2.atom_id] = a2
        rel = graph_manager.create_relation(a1.atom_id, a2.atom_id, RelationType.IS_A)
        graph_manager.revoke_relation(rel.relation_id)
        assert rel.status == RelationStatus.REVOKED
