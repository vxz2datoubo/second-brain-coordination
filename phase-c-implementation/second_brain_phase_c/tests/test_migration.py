"""Tests for Compatibility Migration: lossless, reversible, on-demand."""
import pytest
from second_brain_phase_c.models import (
    KnowledgeAtom, AtomType, AtomStatus, FreshnessClass,
    EpistemicRole, PrivacyClass,
)
from second_brain_phase_c.migration import CompatibilityMigrator


class TestCompatibilityMigration:
    def test_migrate_basic_atom(self, migrator, legacy_atom_data):
        new_atom = migrator.migrate_atom(legacy_atom_data)
        assert new_atom.migrated_from_legacy is True
        assert new_atom.legacy_atom_ref == "legacy_001"
        assert new_atom.atom_type == AtomType.MECHANISM
        assert new_atom.epistemic_role == EpistemicRole.SOURCE_FACT
        assert new_atom.current_status == AtomStatus.ACTIVE
        assert new_atom.freshness_class == FreshnessClass.STRUCTURAL

    def test_migrate_preserves_content(self, migrator, legacy_atom_data):
        new_atom = migrator.migrate_atom(legacy_atom_data)
        assert "测试机制" in new_atom.canonical_statement
        assert "A" in new_atom.entities
        assert "B" in new_atom.entities

    def test_migrate_preserves_confidence(self, migrator, legacy_atom_data):
        new_atom = migrator.migrate_atom(legacy_atom_data)
        assert abs(new_atom.confidence - 0.8) < 0.01

    def test_reverse_migration(self, migrator, legacy_atom_data):
        new_atom = migrator.migrate_atom(legacy_atom_data)
        reversed_data = migrator.reverse_migrate(new_atom)
        assert reversed_data is not None
        assert reversed_data["id"] == "legacy_001"

    def test_reverse_non_migrated_returns_none(self, migrator):
        non_migrated = KnowledgeAtom(canonical_statement="not migrated")
        assert migrator.reverse_migrate(non_migrated) is None

    def test_batch_migrate(self, migrator):
        atoms = [
            {"id": "l1", "type": "concept", "statement": "概念1"},
            {"id": "l2", "type": "fact", "statement": "事实1"},
            {"id": "l3", "type": "method", "statement": "方法1"},
        ]
        result = migrator.batch_migrate(atoms)
        assert len(result) == 3
        assert all(a.migrated_from_legacy for a in result)

    def test_migration_log(self, migrator, legacy_atom_data):
        migrator.migrate_atom(legacy_atom_data)
        log = migrator.get_migration_log()
        assert len(log) == 1
        assert log[0]["legacy_id"] == "legacy_001"

    def test_migration_stats(self, migrator, legacy_atom_data):
        migrator.migrate_atom(legacy_atom_data)
        stats = migrator.get_migration_stats()
        assert stats["total_migrated"] == 1
        assert stats["reversible_count"] == 1

    def test_lossless_verification(self, migrator, legacy_atom_data):
        new_atom = migrator.migrate_atom(legacy_atom_data)
        is_lossless, missing = migrator.verify_lossless(new_atom, legacy_atom_data)
        assert is_lossless is True
        assert len(missing) == 0

    def test_migrate_unknown_type_defaults(self, migrator):
        legacy = {"id": "l_unknown", "type": "weird_type", "statement": "test"}
        new_atom = migrator.migrate_atom(legacy)
        assert new_atom.atom_type == AtomType.CONCEPT

    def test_migrate_episode(self, migrator):
        legacy_source = {
            "type": "article", "pointer": "https://example.com",
            "content_hash": "abc", "content": "test content", "language": "en",
        }
        episode = migrator.migrate_episode(legacy_source)
        assert episode.source_pointer == "https://example.com"
        assert episode.content_language == "en"
