"""Verified registry and relation authority for factory-issued atoms."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .atoms import AtomFactory, CanonicalAtom
from .evidence import SourceEvidence


class RegistryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TypedRelation:
    relation_id: str
    relation_type: str
    source_atom_id: str
    target_atom_id: str
    evidence_sha256: str
    start: int
    end: int


class VerifiedAtomRegistry:
    __slots__ = ("_factory", "_atoms")

    def __init__(self, factory: AtomFactory) -> None:
        self._factory = factory
        self._atoms: dict[str, CanonicalAtom] = {}

    @property
    def evidence(self) -> SourceEvidence:
        return self._factory.evidence

    def register(self, atom: CanonicalAtom) -> CanonicalAtom:
        if not self._factory.verify(atom):
            raise RegistryError("registry admits only factory-issued verified atoms")
        prior = self._atoms.get(atom.atom_id)
        if prior is not None and prior is not atom:
            raise RegistryError("atom identity collision")
        self._atoms[atom.atom_id] = atom
        return atom

    def get(self, atom_id: str) -> CanonicalAtom:
        atom = self._atoms.get(atom_id)
        if atom is None or not self._factory.verify(atom):
            raise RegistryError("atom is not in the verified registry")
        return atom

    def all_atoms(self) -> tuple[CanonicalAtom, ...]:
        return tuple(self._atoms[key] for key in sorted(self._atoms))


class RelationFactory:
    __slots__ = ("_registry", "_issued")

    def __init__(self, registry: VerifiedAtomRegistry) -> None:
        self._registry = registry
        self._issued: dict[str, TypedRelation] = {}

    def issue_explicit(self, start: int, end: int, *, relation_type: str = "supports") -> TypedRelation:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", relation_type):
            raise RegistryError("relation_type must be a stable public token")
        raw = self._registry.evidence.text_slice(start, end).rstrip("\r\n")
        match = re.fullmatch(r"\[\[(\d+):(\d+)->(\d+):(\d+)\]\]", raw)
        if not match:
            raise RegistryError("relation source must name exact source spans")
        source = self._atom_for_span(int(match.group(1)), int(match.group(2)))
        target = self._atom_for_span(int(match.group(3)), int(match.group(4)))
        payload = {"type": relation_type, "source": source.atom_id, "target": target.atom_id, "evidence": self._registry.evidence.sha256, "start": start, "end": end}
        relation_id = "rel:" + sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        relation = TypedRelation(relation_id, relation_type, source.atom_id, target.atom_id, self._registry.evidence.sha256, start, end)
        self._issued[relation_id] = relation
        return relation

    def _atom_for_span(self, start: int, end: int) -> CanonicalAtom:
        for atom in self._registry.all_atoms():
            if atom.start == start and atom.end == end:
                return atom
        raise RegistryError("relation endpoint does not name a registered exact atom span")

    def verify(self, relation: TypedRelation) -> bool:
        if not isinstance(relation, TypedRelation) or self._issued.get(relation.relation_id) is not relation:
            return False
        try:
            raw = self._registry.evidence.text_slice(relation.start, relation.end).rstrip("\r\n")
            source = self._registry.get(relation.source_atom_id)
            target = self._registry.get(relation.target_atom_id)
            expected = f"[[{source.start}:{source.end}->{target.start}:{target.end}]]"
        except (RegistryError, ValueError):
            return False
        payload = {
            "type": relation.relation_type,
            "source": relation.source_atom_id,
            "target": relation.target_atom_id,
            "evidence": self._registry.evidence.sha256,
            "start": relation.start,
            "end": relation.end,
        }
        expected_id = "rel:" + sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return raw == expected and relation.evidence_sha256 == self._registry.evidence.sha256 and relation.relation_id == expected_id
