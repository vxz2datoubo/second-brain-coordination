"""Canonical packets recomputed from verified objects, never caller-provided metadata."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping, Sequence

from .atoms import AtomError, CanonicalAtom, ensure_json_value
from .evidence import SourceEvidence
from .ledger import FinalizedLedger
from .registry import RelationFactory, TypedRelation, VerifiedAtomRegistry


class PacketError(ValueError):
    pass


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(ensure_json_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, AtomError) as exc:
        raise PacketError("packet payload is not canonical JSON") from exc


@dataclass(frozen=True, init=False, slots=True)
class CanonicalPacket:
    packet_id: str
    canonical_json: bytes
    source_identity: Mapping[str, object]
    coverage_manifest: Mapping[str, object]
    atom_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("CanonicalPacket must be issued by CanonicalPacketFactory")


class CanonicalPacketFactory:
    __slots__ = ("_evidence", "_ledger", "_registry", "_relations", "_issued")

    def __init__(self, evidence: SourceEvidence, ledger: FinalizedLedger, registry: VerifiedAtomRegistry, relations: RelationFactory) -> None:
        if ledger.evidence is not evidence or registry.evidence is not evidence or not evidence.verify() or not ledger.verify():
            raise PacketError("packet factory requires one exact verified evidence graph")
        self._evidence = evidence
        self._ledger = ledger
        self._registry = registry
        self._relations = relations
        self._issued: dict[str, CanonicalPacket] = {}

    def issue(
        self,
        *,
        atoms: Sequence[CanonicalAtom],
        relations: Sequence[TypedRelation],
        unknowns: Sequence[str] = (),
        conflicts: Sequence[str] = (),
        redaction_lineage: Sequence[str] = (),
        validation: Mapping[str, object] | None = None,
    ) -> CanonicalPacket:
        unique_atoms = {atom.atom_id: atom for atom in atoms}
        if len(unique_atoms) != len(atoms):
            raise PacketError("duplicate atom identity is rejected")
        ordered_atoms = tuple(unique_atoms[key] for key in sorted(unique_atoms))
        for atom in ordered_atoms:
            self._registry.get(atom.atom_id)
        unique_relations = {relation.relation_id: relation for relation in relations}
        if len(unique_relations) != len(relations):
            raise PacketError("duplicate relation identity is rejected")
        ordered_relations = tuple(unique_relations[key] for key in sorted(unique_relations))
        for relation in ordered_relations:
            if not self._relations.verify(relation):
                raise PacketError("packet relation is not verified")
        try:
            normalized_validation = ensure_json_value(validation or {})
        except AtomError as exc:
            raise PacketError("packet validation contains an invalid canonical value") from exc
        body = {
            "schema_version": "e53.1",
            "source_identity": dict(self._evidence.identity),
            "coverage_manifest": dict(self._ledger.coverage_manifest),
            "atoms": [
                {"atom_id": atom.atom_id, "atom_type": atom.atom_type, "source_sha256": atom.source_sha256, "start": atom.start, "end": atom.end, "text": atom.text, "evidence_sha256": atom.evidence_sha256}
                for atom in ordered_atoms
            ],
            "relations": [
                {"relation_id": relation.relation_id, "relation_type": relation.relation_type, "source_atom_id": relation.source_atom_id, "target_atom_id": relation.target_atom_id, "evidence_sha256": relation.evidence_sha256, "start": relation.start, "end": relation.end}
                for relation in ordered_relations
            ],
            "unknowns": sorted(set(unknowns)),
            "conflicts": sorted(set(conflicts)),
            "redaction_lineage": sorted(set(redaction_lineage)),
            "validation": normalized_validation,
        }
        canonical_json = _canonical_bytes(body)
        packet_id = "packet:" + sha256(canonical_json).hexdigest()
        instance = object.__new__(CanonicalPacket)
        object.__setattr__(instance, "packet_id", packet_id)
        object.__setattr__(instance, "canonical_json", canonical_json)
        object.__setattr__(instance, "source_identity", MappingProxyType(dict(self._evidence.identity)))
        object.__setattr__(instance, "coverage_manifest", MappingProxyType(dict(self._ledger.coverage_manifest)))
        object.__setattr__(instance, "atom_ids", tuple(atom.atom_id for atom in ordered_atoms))
        object.__setattr__(instance, "relation_ids", tuple(relation.relation_id for relation in ordered_relations))
        self._issued[packet_id] = instance
        return instance

    def verify(self, packet: CanonicalPacket) -> bool:
        if not isinstance(packet, CanonicalPacket) or self._issued.get(packet.packet_id) is not packet:
            return False
        try:
            loaded = json.loads(packet.canonical_json.decode("utf-8", "strict"))
            expected = _canonical_bytes(loaded)
        except (UnicodeDecodeError, json.JSONDecodeError, PacketError):
            return False
        return (
            packet.canonical_json == expected
            and packet.packet_id == "packet:" + sha256(expected).hexdigest()
            and packet.source_identity == self._evidence.identity
            and packet.coverage_manifest == self._ledger.coverage_manifest
        )
