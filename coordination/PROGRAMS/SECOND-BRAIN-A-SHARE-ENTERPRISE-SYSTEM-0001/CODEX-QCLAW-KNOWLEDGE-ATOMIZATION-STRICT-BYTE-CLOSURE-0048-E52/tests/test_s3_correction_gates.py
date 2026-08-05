"""Regression gates added after the independent S3 correction review."""
from __future__ import annotations

import hashlib
import sys
import unittest
from dataclasses import replace
from pathlib import Path


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from e52_strict_byte.adapters import adapt
from e52_strict_byte.hygiene import assert_delivery_paths_clean, assert_source_tree_clean
from e52_strict_byte.ledger import Owner, OwnershipSpan
from e52_strict_byte.semantics import (
    Atom,
    AtomClassification,
    CanonicalPacket,
    FIELD_SPECS,
    FieldProvenance,
    RelationType,
    SemanticFieldValue,
    extract_claim,
    extract_explicit_link_relation,
    unknown_field_values,
    validate_relation,
)


def _digest(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _packet(source: bytes, atoms: tuple[Atom, ...], relations=()):
    return CanonicalPacket(
        source_identity={"sha256": _digest(source), "byte_length": len(source), "format": "synthetic"},
        atoms=atoms,
        relations=relations,
        unknowns=("synthetic-unknown",),
        conflicts=(),
        redaction_lineage={"applied": False, "policy": "none"},
        coverage_manifest={"total_bytes": len(source), "finalized": True},
        config={"schema_version": "1"},
        validator_results={"semantic": True},
    )


class TestCorrectionHygieneAndLedger(unittest.TestCase):
    def test_generated_paths_are_rejected_and_current_program_tree_is_clean(self):
        with self.assertRaises(ValueError):
            assert_delivery_paths_clean(("src/__pycache__/module.pyc", "artifacts/canonical-evidence.json"))
        assert_source_tree_clean(PROGRAM_ROOT)

    def test_finalized_ledger_rejects_direct_item_and_alias_mutation(self):
        ledger = adapt(b"text\n", "txt").ledger
        with self.assertRaises(AttributeError):
            ledger._total_bytes = 99
        with self.assertRaises(TypeError):
            ledger.manifest()["owner_bytes"][Owner.ATOM_CANDIDATE.value] = 0
        exposed = ledger.spans()
        with self.assertRaises(AttributeError):
            exposed[0].label = "rewritten"
        self.assertEqual(ledger.total_bytes, 5)


class TestFormatSpecificOwnership(unittest.TestCase):
    def test_markdown_assigns_required_structural_roles(self):
        source = b"# Heading\n\n> quote\n- item\n| a | b |\n|---|---|\n```py\ncode()\n```\n"
        labels = {span.label for span in adapt(source, "markdown").ledger.spans()}
        self.assertTrue(
            {
                "markdown_heading_marker",
                "markdown_blank_separator",
                "markdown_blockquote_marker",
                "markdown_list_marker",
                "markdown_table_pipe",
                "markdown_table_separator",
                "markdown_code_fence",
                "markdown_code_body",
                "markdown_terminator",
            }.issubset(labels)
        )

    def test_json_keys_and_escape_bytes_are_never_atom_candidates(self):
        source = b'{"structural_key":"value\\ntext","n":12}'
        result = adapt(source, "json")
        spans = result.ledger.spans()
        key_body = next(span for span in spans if span.label == "json_key_body")
        self.assertEqual(key_body.owner, Owner.STRUCTURE)
        self.assertTrue(any(span.label == "json_value_escape" and span.owner is Owner.STRUCTURE for span in spans))
        self.assertTrue(any(span.label == "json_value_string_content" and span.owner is Owner.ATOM_CANDIDATE for span in spans))


class TestSemanticIdentityAndFinalization(unittest.TestCase):
    def test_claim_recomputes_digest_and_validates_utf8_boundaries(self):
        source = "甲 claim".encode("utf-8")
        claim = extract_claim(OwnershipSpan(3, len(source), Owner.ATOM_CANDIDATE, "claim"), source, _digest(source))
        self.assertEqual(claim.source_digest, _digest(source))
        with self.assertRaises(ValueError):
            extract_claim(OwnershipSpan(1, len(source), Owner.ATOM_CANDIDATE, "split"), source, _digest(source))
        with self.assertRaises(ValueError):
            extract_claim(OwnershipSpan(3, len(source), Owner.ATOM_CANDIDATE, "claim"), source, "0" * 64)

    def test_field_rules_are_field_specific_and_frozen(self):
        source = b"claim"
        atom = extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "claim"), source)
        self.assertEqual(set(atom.fields), {"condition", "exception", "negation", "temporal_scope", "assumption", "evidence_status", "applicability"})
        self.assertEqual(len({value.unknown_reason for value in atom.fields.values()}), 7)
        with self.assertRaises(TypeError):
            atom.fields["condition"] = atom.fields["condition"]

    def test_declared_defaults_and_extracted_evidence_are_field_validated(self):
        source = b"claim"
        fields = unknown_field_values()
        for name, spec in FIELD_SPECS.items():
            fields[name] = SemanticFieldValue(spec.default_value, FieldProvenance.DEFAULT, spec.default_rule)
        default_atom = Atom("default-atom", "claim", (0, 5), _digest(source), AtomClassification.CLAIM, fields, ("byte-span:0:5",), True)
        self.assertEqual(default_atom.fields["condition"].provenance, FieldProvenance.DEFAULT)
        extracted = dict(unknown_field_values())
        extracted["condition"] = SemanticFieldValue("claim", FieldProvenance.EXTRACTED, "extract:explicit_source_span", (0, 5))
        Atom("extracted-atom", "claim", (0, 5), _digest(source), AtomClassification.CLAIM, extracted, ("byte-span:0:5",), True)
        extracted["condition"] = SemanticFieldValue("claim", FieldProvenance.EXTRACTED, "extract:explicit_source_span")
        with self.assertRaises(ValueError):
            Atom("bad-extracted", "claim", (0, 5), _digest(source), AtomClassification.CLAIM, extracted, ("byte-span:0:5",), True)

    def test_atom_and_packet_canonical_bytes_ignore_caller_alias_mutation(self):
        source = b"claim"
        fields = unknown_field_values()
        atom = Atom("atom-1", "claim", (0, 5), _digest(source), AtomClassification.CLAIM, fields, ("byte-span:0:5",), True)
        packet_source_identity = {"sha256": _digest(source), "byte_length": len(source), "format": "synthetic"}
        packet_config = {"schema_version": "1", "nested": {"mode": "strict"}}
        packet = CanonicalPacket(
            source_identity=packet_source_identity,
            atoms=[atom],
            relations=[],
            unknowns=["synthetic-unknown"],
            conflicts=[],
            redaction_lineage={"applied": False, "policy": "none"},
            coverage_manifest={"total_bytes": len(source), "finalized": True},
            config=packet_config,
            validator_results={"semantic": True},
        )
        before = packet.canonical_bytes()
        fields["condition"] = fields["exception"]
        packet_source_identity["format"] = "tampered"
        packet_config["nested"]["mode"] = "tampered"
        self.assertEqual(before, packet.canonical_bytes())
        with self.assertRaises(TypeError):
            packet.config["schema_version"] = "2"

    def test_relation_checks_exact_source_bytes_type_and_registry_identity(self):
        source = b"left [[left-id->right-id]] right"
        digest = _digest(source)
        fields = unknown_field_values()
        left = Atom("left-id", "left", (0, 4), digest, AtomClassification.CLAIM, fields, ("byte-span:0:4",), True)
        right = Atom("right-id", "right", (27, 32), digest, AtomClassification.CLAIM, fields, ("byte-span:27:32",), True)
        atoms = {left.atom_id: left, right.atom_id: right}
        span = (5, 26)
        relation = extract_explicit_link_relation(source, span, atoms)
        self.assertIs(relation.relation_type, RelationType.EXPLICIT_LINK)
        validate_relation(relation, atoms, source)
        with self.assertRaises(ValueError):
            validate_relation(relation, atoms, source.replace(b"->", b"=>"))

    def test_packet_finalization_rejects_incomplete_identity_and_invalid_results(self):
        source = b"claim"
        atom = extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "claim"), source)
        packet = _packet(source, (atom,))
        self.assertEqual(packet.finalize().packet_id(), packet.packet_id())
        bad = CanonicalPacket(
            source_identity={},
            atoms=(atom,),
            relations=(),
            unknowns=(),
            conflicts=(),
            redaction_lineage={"applied": False},
            coverage_manifest={"finalized": False},
            config={},
            validator_results={"semantic": False},
        )
        with self.assertRaises(ValueError):
            bad.canonical_bytes()

    def test_packet_finalization_rejects_coverage_validator_and_atom_identity_conflicts(self):
        source = b"claim"
        atom = extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "claim"), source)
        packet = _packet(source, (atom,))
        for changed in (
            replace(packet, coverage_manifest={"total_bytes": 6, "finalized": True}),
            replace(packet, config={"mode": "strict"}),
            replace(packet, validator_results={"semantic": False}),
            replace(packet, atoms=(extract_claim(OwnershipSpan(0, 5, Owner.ATOM_CANDIDATE, "other"), b"other"),)),
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    changed.finalize()


if __name__ == "__main__":
    unittest.main(verbosity=2)
