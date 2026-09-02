"""
Test fixtures for PHASE_C tests.
"""
import pytest
from typing import Dict, List

from second_brain_phase_c.models import (
    KnowledgeAtom, KnowledgeEpisode, AtomType, EpistemicRole,
    EvidenceQuality, FreshnessClass, AtomStatus, PrivacyClass,
    Scope, SourceRef, OrganizationalLayer, DistillationLayers,
    ParaCategory, _now_iso,
)
from second_brain_phase_c.audit import AuditLogStore
from second_brain_phase_c.graph import GraphEvolutionManager
from second_brain_phase_c.reconciliation import ReconciliationEngine
from second_brain_phase_c.verification import PostWriteVerifier
from second_brain_phase_c.migration import CompatibilityMigrator
from second_brain_phase_c.templates import MarkdownTemplateRenderer


@pytest.fixture
def atom_store():
    return {}


@pytest.fixture
def audit_store():
    return AuditLogStore()


@pytest.fixture
def graph_manager(atom_store):
    return GraphEvolutionManager(atom_store)


@pytest.fixture
def reconciliation_engine(atom_store, graph_manager, audit_store):
    return ReconciliationEngine(atom_store, graph_manager, audit_store)


@pytest.fixture
def verifier(atom_store):
    return PostWriteVerifier(atom_store)


@pytest.fixture
def migrator():
    return CompatibilityMigrator()


@pytest.fixture
def renderer():
    return MarkdownTemplateRenderer()


@pytest.fixture
def sample_atom():
    return KnowledgeAtom(
        canonical_statement="Python的GIL使得多线程无法真正并行执行CPU密集型任务",
        atom_type=AtomType.MECHANISM,
        entities=["Python", "GIL", "多线程", "CPU密集型"],
        topic_tags=["Python", "并发", "性能"],
        epistemic_role=EpistemicRole.SOURCE_FACT,
        source_refs=[SourceRef(episode_id="ep_test_001", span_locator="p1-3")],
        evidence_quality=EvidenceQuality.DIRECT,
        confidence=0.85,
        scope=Scope(user_scope="test_user", privacy_class=PrivacyClass.PUBLIC),
        freshness_class=FreshnessClass.STRUCTURAL,
        current_status=AtomStatus.ACTIVE,
        organizational_layer=OrganizationalLayer(para_category=ParaCategory.RESOURCE),
        distillation_layers=DistillationLayers(
            layer0_source_span_ref="ep_test_001:p1-3",
            layer1_full_note="Python GIL prevents true parallelism for CPU-bound tasks.",
            distillation_progress=1,
        ),
    )


@pytest.fixture
def sample_episode():
    return KnowledgeEpisode(
        source_type="ARTICLE",
        source_pointer="https://example.com/python-gil",
        source_content_hash="abc123",
        raw_content="Python's Global Interpreter Lock (GIL) is a mutex...",
        content_language="en",
        user_scope="test_user",
    )


@pytest.fixture
def populated_store(atom_store, sample_atom):
    atom_store[sample_atom.atom_id] = sample_atom
    atom2 = KnowledgeAtom(
        canonical_statement="使用multiprocessing可以绕过GIL实现真正的并行",
        atom_type=AtomType.METHOD,
        entities=["Python", "GIL", "multiprocessing", "并行"],
        topic_tags=["Python", "并发", "性能"],
        epistemic_role=EpistemicRole.SOURCE_FACT,
        source_refs=[SourceRef(episode_id="ep_test_002")],
        confidence=0.8,
        scope=Scope(user_scope="test_user", privacy_class=PrivacyClass.PUBLIC),
        current_status=AtomStatus.ACTIVE,
    )
    atom_store[atom2.atom_id] = atom2
    atom3 = KnowledgeAtom(
        canonical_statement="Python的GIL不影响多线程性能",
        atom_type=AtomType.FACT_CLAIM,
        entities=["Python", "GIL", "多线程"],
        topic_tags=["Python", "并发"],
        epistemic_role=EpistemicRole.SOURCE_CLAIM,
        source_refs=[SourceRef(episode_id="ep_test_003")],
        confidence=0.6,
        scope=Scope(user_scope="test_user", privacy_class=PrivacyClass.PUBLIC),
        current_status=AtomStatus.ACTIVE,
    )
    atom_store[atom3.atom_id] = atom3
    atom4 = KnowledgeAtom(
        canonical_statement="Python的GIL使得多线程无法真正并行执行CPU密集型任务",
        atom_type=AtomType.MECHANISM,
        entities=["Python", "GIL"],
        epistemic_role=EpistemicRole.SOURCE_FACT,
        source_refs=[SourceRef(episode_id="ep_test_004")],
        confidence=0.85,
        scope=Scope(user_scope="other_user", privacy_class=PrivacyClass.PUBLIC),
        current_status=AtomStatus.ACTIVE,
    )
    atom_store[atom4.atom_id] = atom4
    atom5 = KnowledgeAtom(
        canonical_statement="Python 3.9的GIL实现方式与之前相同",
        atom_type=AtomType.FACT_CLAIM,
        entities=["Python", "GIL", "Python3.9"],
        epistemic_role=EpistemicRole.SOURCE_FACT,
        source_refs=[SourceRef(episode_id="ep_test_005")],
        confidence=0.7,
        scope=Scope(user_scope="test_user", privacy_class=PrivacyClass.PUBLIC),
        current_status=AtomStatus.SUPERSEDED,
        lineage_head=False,
    )
    atom_store[atom5.atom_id] = atom5
    return atom_store


@pytest.fixture
def legacy_atom_data():
    return {
        "id": "legacy_001",
        "type": "mechanism",
        "statement": "测试机制：A导致B",
        "entities": ["A", "B"],
        "tags": ["测试"],
        "epistemic_role": "fact",
        "confidence": 0.8,
        "status": "active",
        "freshness": "structural",
        "user_scope": "test_user",
        "privacy_class": "PUBLIC",
        "source_id": "legacy_source_001",
        "created_at": "2026-01-01T00:00:00+00:00",
        "assumptions": ["假设C成立"],
        "conditions": ["在D条件下"],
    }
