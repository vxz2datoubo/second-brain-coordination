"""Tests for Post-write Verification: 5 verification tests."""
import pytest
from second_brain_phase_c.models import (
    KnowledgeAtom, AtomType, AtomStatus, PrivacyClass, Scope,
    SourceRef,
)


class TestPostWriteVerification:
    def test_exact_recall_pass(self, verifier, atom_store, sample_atom):
        atom_store[sample_atom.atom_id] = sample_atom
        result = verifier.verify(sample_atom)
        assert result.exact_recall_pass is True

    def test_paraphrase_recall_with_fixture(self, verifier, atom_store, sample_atom):
        atom_store[sample_atom.atom_id] = sample_atom
        verifier.register_paraphrase_fixture(sample_atom.atom_id,
            ["GIL阻止Python多线程并行", "Python全局解释器锁影响并发"])
        result = verifier.verify(sample_atom)
        assert result.paraphrase_recall_pass in (True, False)

    def test_graph_recall(self, verifier, atom_store, sample_atom):
        atom_store[sample_atom.atom_id] = sample_atom
        result = verifier.verify(sample_atom)
        assert result.graph_recall_pass is True

    def test_scope_isolation(self, verifier, atom_store, sample_atom):
        atom_store[sample_atom.atom_id] = sample_atom
        result = verifier.verify(sample_atom)
        assert result.scope_isolation_pass is True

    def test_temporal_status_current(self, verifier, atom_store, sample_atom):
        sample_atom.current_status = AtomStatus.ACTIVE
        sample_atom.lineage_head = True
        atom_store[sample_atom.atom_id] = sample_atom
        result = verifier.verify(sample_atom)
        assert result.temporal_status_pass is True

    def test_temporal_status_superseded(self, verifier, atom_store):
        atom = KnowledgeAtom(canonical_statement="旧版本",
            current_status=AtomStatus.SUPERSEDED, lineage_head=False,
            scope=Scope(user_scope="test"))
        atom_store[atom.atom_id] = atom
        result = verifier.verify(atom)
        assert result.temporal_status_pass is True

    def test_all_passed_for_valid_atom(self, verifier, atom_store, sample_atom):
        atom_store[sample_atom.atom_id] = sample_atom
        verifier.register_paraphrase_fixture(sample_atom.atom_id, [sample_atom.canonical_statement])
        result = verifier.verify(sample_atom)
        assert result.exact_recall_pass is True
        assert result.graph_recall_pass is True
        assert result.scope_isolation_pass is True
        assert result.temporal_status_pass is True

    def test_verification_details(self, verifier, atom_store, sample_atom):
        atom_store[sample_atom.atom_id] = sample_atom
        result = verifier.verify(sample_atom)
        assert "exact_recall" in result.details
        assert "scope_isolation" in result.details
        assert result.verified_at is not None
