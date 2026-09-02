"""Tests for data models: serialization, deserialization, status checks."""
import pytest
from second_brain_phase_c.models import (
    KnowledgeAtom, KnowledgeEpisode, AtomType, AtomStatus,
    PrivacyClass, Scope, SourceRef, OrganizationalLayer,
    DistillationLayers, ParaCategory, _now_iso,
)


class TestKnowledgeAtom:
    def test_serialization_roundtrip(self, sample_atom):
        d = sample_atom.to_dict()
        restored = KnowledgeAtom.from_dict(d)
        assert restored.atom_id == sample_atom.atom_id
        assert restored.canonical_statement == sample_atom.canonical_statement
        assert restored.atom_type == sample_atom.atom_type
        assert restored.confidence == sample_atom.confidence
        assert restored.scope.user_scope == sample_atom.scope.user_scope

    def test_is_current_active(self):
        atom = KnowledgeAtom(current_status=AtomStatus.ACTIVE, lineage_head=True)
        assert atom.is_current() is True

    def test_is_not_current_superseded(self):
        atom = KnowledgeAtom(current_status=AtomStatus.SUPERSEDED, lineage_head=False)
        assert atom.is_current() is False

    def test_is_not_current_revoked(self):
        atom = KnowledgeAtom(current_status=AtomStatus.REVOKED, lineage_head=True)
        assert atom.is_current() is False

    def test_is_expired(self):
        atom = KnowledgeAtom(valid_to="2020-01-01T00:00:00+00:00")
        assert atom.is_expired() is True

    def test_not_expired_no_valid_to(self):
        atom = KnowledgeAtom(valid_to=None)
        assert atom.is_expired() is False

    def test_organizational_layer_preserved(self, sample_atom):
        d = sample_atom.to_dict()
        restored = KnowledgeAtom.from_dict(d)
        assert restored.organizational_layer is not None
        assert restored.organizational_layer.para_category == ParaCategory.RESOURCE

    def test_distillation_layers_preserved(self, sample_atom):
        d = sample_atom.to_dict()
        restored = KnowledgeAtom.from_dict(d)
        assert restored.distillation_layers is not None
        assert restored.distillation_layers.distillation_progress == 1

    def test_counterevidence_structured(self):
        from second_brain_phase_c.models import CounterEvidenceRef, EvidenceStrength, RelationType
        atom = KnowledgeAtom(counterevidence=[CounterEvidenceRef(
            atom_id="ce_001", evidence_strength=EvidenceStrength.STRONG,
            relation_type=RelationType.CONTRADICTS)])
        d = atom.to_dict()
        restored = KnowledgeAtom.from_dict(d)
        assert len(restored.counterevidence) == 1
        assert restored.counterevidence[0].evidence_strength == EvidenceStrength.STRONG


class TestKnowledgeEpisode:
    def test_serialization_roundtrip(self, sample_episode):
        d = sample_episode.to_dict()
        restored = KnowledgeEpisode.from_dict(d)
        assert restored.episode_id == sample_episode.episode_id
        assert restored.source_pointer == sample_episode.source_pointer
        assert restored.content_language == sample_episode.content_language

    def test_raw_content_storage_default(self):
        ep = KnowledgeEpisode()
        from second_brain_phase_c.models import RawContentStorage
        assert ep.raw_content_storage == RawContentStorage.INLINE


class TestScope:
    def test_matching_scopes(self):
        s1 = Scope(user_scope="u1", project_scope="p1", privacy_class=PrivacyClass.PUBLIC)
        s2 = Scope(user_scope="u1", project_scope="p1", privacy_class=PrivacyClass.PUBLIC)
        assert s1.matches(s2) is True

    def test_different_user_scopes(self):
        s1 = Scope(user_scope="u1")
        s2 = Scope(user_scope="u2")
        assert s1.matches(s2) is False

    def test_private_not_match_public(self):
        s1 = Scope(user_scope="u1", privacy_class=PrivacyClass.PRIVATE)
        s2 = Scope(user_scope="u1", privacy_class=PrivacyClass.PUBLIC)
        assert s1.matches(s2) is False
