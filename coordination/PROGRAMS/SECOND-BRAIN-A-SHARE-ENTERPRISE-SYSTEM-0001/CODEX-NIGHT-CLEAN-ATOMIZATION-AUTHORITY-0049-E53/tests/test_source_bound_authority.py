from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

from e53_authority import (  # noqa: E402
    AdapterError,
    AtomFactory,
    CanonicalAtom,
    CanonicalPacket,
    CanonicalPacketFactory,
    FieldRule,
    LedgerBuilder,
    RelationFactory,
    SourceEvidence,
    SpanOwner,
    VerifiedAtomRegistry,
    build_ledger,
)
from e53_authority.atoms import AtomError, CanonicalField
from e53_authority.corpus import corpus_digest, fixed_corpus
from e53_authority.ledger import LedgerError
from e53_authority.packet import PacketError
from e53_authority.registry import RegistryError
from e53_authority.utf8_index import Utf8IndexError


class AuthorityFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.data = b"alpha\nbeta\n[[0:6->6:11]]\n"
        self.evidence = SourceEvidence.from_bytes(self.data, source_id="fixture:authority", format_name="text")
        self.ledger = build_ledger(self.evidence)
        self.factory = AtomFactory(self.evidence, self.ledger)
        self.alpha = self.factory.issue(0, 6)
        self.beta = self.factory.issue(6, 11)
        self.registry = VerifiedAtomRegistry(self.factory)
        self.registry.register(self.alpha)
        self.registry.register(self.beta)
        self.relation_factory = RelationFactory(self.registry)
        self.relation = self.relation_factory.issue_explicit(11, len(self.data))
        self.packet_factory = CanonicalPacketFactory(self.evidence, self.ledger, self.registry, self.relation_factory)


class TestSourceEvidence(unittest.TestCase):
    def test_direct_construction_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            SourceEvidence()

    def test_identity_is_derived_from_exact_bytes(self) -> None:
        evidence = SourceEvidence.from_bytes(b"alpha\n", source_id="fixture:one", format_name="text")
        self.assertEqual(evidence.identity["sha256"], evidence.sha256)
        self.assertEqual(evidence.identity["byte_length"], 6)
        self.assertTrue(evidence.verify())

    def test_bad_utf8_is_rejected(self) -> None:
        with self.assertRaises(Utf8IndexError):
            SourceEvidence.from_bytes(b"\xed", source_id="fixture:bad", format_name="text")

    def test_truncated_utf8_is_rejected(self) -> None:
        with self.assertRaises(Utf8IndexError):
            SourceEvidence.from_bytes(b"\xe4\xb8", source_id="fixture:bad", format_name="text")

    def test_unknown_format_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SourceEvidence.from_bytes(b"a", source_id="fixture:bad", format_name="csv")

    def test_blank_source_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SourceEvidence.from_bytes(b"a", source_id=" ", format_name="text")

    def test_byte_slice_out_of_range_is_rejected(self) -> None:
        evidence = SourceEvidence.from_bytes(b"a", source_id="fixture:one", format_name="text")
        with self.assertRaises(Utf8IndexError):
            evidence.bytes_slice(-1, 1)

    def test_codepoint_cut_is_rejected(self) -> None:
        evidence = SourceEvidence.from_bytes("中\n".encode("utf-8"), source_id="fixture:cn", format_name="text")
        with self.assertRaises(Utf8IndexError):
            evidence.text_slice(0, 1)


class TestLedgerAndAdapters(unittest.TestCase):
    def test_text_adapter_builds_total_partition(self) -> None:
        evidence = SourceEvidence.from_bytes(b"alpha\n\nbeta\n", source_id="fixture:text", format_name="text")
        ledger = build_ledger(evidence)
        self.assertTrue(ledger.verify())
        self.assertEqual(ledger.coverage_manifest["byte_length"], len(b"alpha\n\nbeta\n"))

    def test_json_adapter_accepts_valid_source(self) -> None:
        evidence = SourceEvidence.from_bytes(b'{"claim":"alpha"}', source_id="fixture:json", format_name="json")
        self.assertTrue(build_ledger(evidence).verify())

    def test_json_adapter_rejects_invalid_source(self) -> None:
        evidence = SourceEvidence.from_bytes(b'{"claim":', source_id="fixture:json", format_name="json")
        with self.assertRaises(AdapterError):
            build_ledger(evidence)

    def test_jsonl_adapter_rejects_bad_line(self) -> None:
        evidence = SourceEvidence.from_bytes(b'{"a":1}\n{', source_id="fixture:jsonl", format_name="jsonl")
        with self.assertRaises(AdapterError):
            build_ledger(evidence)

    def test_empty_source_is_not_atomized(self) -> None:
        evidence = SourceEvidence.from_bytes(b"", source_id="fixture:empty", format_name="text")
        with self.assertRaises(AdapterError):
            build_ledger(evidence)

    def test_overlapping_ledger_spans_are_rejected(self) -> None:
        evidence = SourceEvidence.from_bytes(b"alpha\n", source_id="fixture:overlap", format_name="text")
        builder = LedgerBuilder(evidence)
        builder.add(0, 3, SpanOwner.ATOM_CANDIDATE).add(2, 6, SpanOwner.ATOM_CANDIDATE)
        with self.assertRaises(LedgerError):
            builder.finalize()

    def test_incomplete_ledger_is_rejected(self) -> None:
        evidence = SourceEvidence.from_bytes(b"alpha\n", source_id="fixture:incomplete", format_name="text")
        builder = LedgerBuilder(evidence)
        builder.add(0, 3, SpanOwner.ATOM_CANDIDATE)
        with self.assertRaises(LedgerError):
            builder.finalize()

    def test_non_boundary_ledger_span_is_rejected(self) -> None:
        evidence = SourceEvidence.from_bytes("中\n".encode("utf-8"), source_id="fixture:mid", format_name="text")
        with self.assertRaises(LedgerError):
            LedgerBuilder(evidence).add(0, 1, SpanOwner.ATOM_CANDIDATE)

    def test_markdown_heading_has_structural_ownership(self) -> None:
        evidence = SourceEvidence.from_bytes(b"# Heading\nclaim\n", source_id="fixture:md", format_name="markdown")
        ledger = build_ledger(evidence)
        self.assertEqual(ledger.owner_for(0, 10), SpanOwner.STRUCTURAL)
        self.assertTrue(ledger.is_exact_atom_candidate(10, 16))

    def test_markdown_redaction_cannot_be_an_atom_candidate(self) -> None:
        evidence = SourceEvidence.from_bytes(b"[REDACTED]\n", source_id="fixture:redaction", format_name="markdown")
        ledger = build_ledger(evidence)
        self.assertEqual(ledger.owner_for(0, 11), SpanOwner.REDACTED)
        factory = AtomFactory(evidence, ledger)
        with self.assertRaises(AtomError):
            factory.issue(0, 11)


class TestCanonicalAtoms(AuthorityFixture):
    def test_direct_atom_construction_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            CanonicalAtom()

    def test_atom_is_exact_source_slice(self) -> None:
        self.assertEqual(self.alpha.text, "alpha\n")
        self.assertTrue(self.factory.verify(self.alpha))

    def test_non_exact_subspan_is_rejected(self) -> None:
        with self.assertRaises(AtomError):
            self.factory.issue(0, 1)

    def test_wrong_type_is_rejected(self) -> None:
        with self.assertRaises(AtomError):
            self.factory.issue(0, 6, atom_type="Not Stable")

    def test_lexical_fact_promotion_is_rejected(self) -> None:
        with self.assertRaises(AtomError):
            self.factory.issue(0, 6, atom_type="fact")

    def test_mutated_atom_text_fails_verification(self) -> None:
        object.__setattr__(self.alpha, "text", "forged")
        self.assertFalse(self.factory.verify(self.alpha))

    def test_mutated_atom_digest_fails_verification(self) -> None:
        object.__setattr__(self.alpha, "evidence_sha256", "0" * 64)
        self.assertFalse(self.factory.verify(self.alpha))

    def test_mutated_atom_span_fails_verification(self) -> None:
        object.__setattr__(self.alpha, "end", 1)
        self.assertFalse(self.factory.verify(self.alpha))

    def test_foreign_factory_atom_is_rejected(self) -> None:
        other = AtomFactory(self.evidence, self.ledger)
        foreign = other.issue(0, 6)
        with self.assertRaises(RegistryError):
            self.registry.register(foreign)

    def test_field_exact_value_is_source_derived(self) -> None:
        field = self.factory.extract_field(self.alpha, name="claim", start=0, end=5, rule=FieldRule.EXACT_UTF8_SLICE)
        self.assertEqual(field.value, "alpha")
        self.assertTrue(self.factory.verify_field(self.alpha, field))

    def test_field_value_forgery_fails_verification(self) -> None:
        field = self.factory.extract_field(self.alpha, name="claim", start=0, end=5, rule=FieldRule.EXACT_UTF8_SLICE)
        forged = CanonicalField(field.name, field.rule, field.start, field.end, "beta", field.value_sha256)
        self.assertFalse(self.factory.verify_field(self.alpha, forged))

    def test_field_outside_atom_is_rejected(self) -> None:
        with self.assertRaises(AtomError):
            self.factory.extract_field(self.alpha, name="bad", start=0, end=7, rule=FieldRule.EXACT_UTF8_SLICE)

    def test_ascii_rule_rejects_non_ascii(self) -> None:
        evidence = SourceEvidence.from_bytes("中\n".encode("utf-8"), source_id="fixture:cn", format_name="text")
        factory = AtomFactory(evidence, build_ledger(evidence))
        atom = factory.issue(0, len("中\n".encode("utf-8")))
        with self.assertRaises(AtomError):
            factory.extract_field(atom, name="bad", start=0, end=3, rule=FieldRule.ASCII_LOWER_STRIP)


class TestRegistryRelationsAndPackets(AuthorityFixture):
    def test_registry_returns_exact_registered_atom(self) -> None:
        self.assertIs(self.registry.get(self.alpha.atom_id), self.alpha)

    def test_registry_rejects_unknown_atom(self) -> None:
        with self.assertRaises(RegistryError):
            self.registry.get("atom:missing")

    def test_relation_is_bound_to_explicit_source_spans(self) -> None:
        self.assertTrue(self.relation_factory.verify(self.relation))
        self.assertEqual(self.relation.source_atom_id, self.alpha.atom_id)
        self.assertEqual(self.relation.target_atom_id, self.beta.atom_id)

    def test_relation_text_tampering_fails(self) -> None:
        object.__setattr__(self.relation, "end", self.relation.end - 2)
        self.assertFalse(self.relation_factory.verify(self.relation))

    def test_relation_with_unregistered_endpoint_fails(self) -> None:
        evidence = SourceEvidence.from_bytes(b"a\nb\n[[0:2->2:4]]\n", source_id="fixture:rel", format_name="text")
        ledger = build_ledger(evidence)
        factory = AtomFactory(evidence, ledger)
        first, second = factory.issue(0, 2), factory.issue(2, 4)
        registry = VerifiedAtomRegistry(factory)
        registry.register(first)
        with self.assertRaises(RegistryError):
            RelationFactory(registry).issue_explicit(4, len(b"a\nb\n[[0:2->2:4]]\n"))

    def test_direct_packet_construction_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            CanonicalPacket()

    def test_packet_recomputes_identity_and_coverage(self) -> None:
        packet = self.packet_factory.issue(atoms=[self.beta, self.alpha], relations=[self.relation], unknowns=["volume_unit"], validation={"ok": True})
        self.assertTrue(self.packet_factory.verify(packet))
        self.assertEqual(packet.source_identity, self.evidence.identity)
        self.assertEqual(packet.coverage_manifest, self.ledger.coverage_manifest)
        self.assertEqual(packet.atom_ids, tuple(sorted((self.alpha.atom_id, self.beta.atom_id))))

    def test_packet_rejects_duplicate_atom_identity(self) -> None:
        with self.assertRaises(PacketError):
            self.packet_factory.issue(atoms=[self.alpha, self.alpha], relations=[])

    def test_packet_rejects_unverified_relation(self) -> None:
        object.__setattr__(self.relation, "relation_type", "forged")
        with self.assertRaises(PacketError):
            self.packet_factory.issue(atoms=[self.alpha, self.beta], relations=[self.relation])

    def test_packet_rejects_nonfinite_value(self) -> None:
        with self.assertRaises(PacketError):
            self.packet_factory.issue(atoms=[self.alpha, self.beta], relations=[self.relation], validation={"bad": math.nan})

    def test_packet_is_deterministic_for_input_permutation(self) -> None:
        left = self.packet_factory.issue(atoms=[self.alpha, self.beta], relations=[self.relation], unknowns=["b", "a"])
        right = self.packet_factory.issue(atoms=[self.beta, self.alpha], relations=[self.relation], unknowns=["a", "b"])
        self.assertEqual(left.packet_id, right.packet_id)
        self.assertEqual(left.canonical_json, right.canonical_json)

    def test_packet_tampering_fails_verification(self) -> None:
        packet = self.packet_factory.issue(atoms=[self.alpha, self.beta], relations=[self.relation])
        object.__setattr__(packet, "canonical_json", b"{}")
        self.assertFalse(self.packet_factory.verify(packet))


class TestCorpus(unittest.TestCase):
    def test_corpus_digest_is_stable(self) -> None:
        self.assertEqual(corpus_digest(), corpus_digest())


def _make_corpus_test(case):
    def test(self):
        try:
            evidence = SourceEvidence.from_bytes(case.payload, source_id="corpus:" + case.case_id, format_name=case.format_name)
            build_ledger(evidence)
            accepted = True
        except (ValueError, Utf8IndexError, AdapterError):
            accepted = False
        self.assertEqual(accepted, case.accepted, case.reason)
    return test


for _case in fixed_corpus():
    setattr(TestCorpus, "test_case_" + _case.case_id.replace("-", "_"), _make_corpus_test(_case))
