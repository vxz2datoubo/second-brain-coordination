"""Factory-issued atoms and field values, all derived from exact source bytes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import math
import re
from types import MappingProxyType
from typing import Mapping

from .evidence import SourceEvidence
from .ledger import FinalizedLedger, SpanOwner


class AtomError(ValueError):
    pass


class FieldRule(str, Enum):
    EXACT_UTF8_SLICE = "EXACT_UTF8_SLICE"
    ASCII_LOWER_STRIP = "ASCII_LOWER_STRIP"
    JSON_STRING = "JSON_STRING"


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AtomError("value is outside the canonical JSON domain") from exc


def _atom_id(evidence: SourceEvidence, start: int, end: int, atom_type: str) -> str:
    payload = _canonical_json({"sha256": evidence.sha256, "start": start, "end": end, "atom_type": atom_type})
    return "atom:" + sha256(payload).hexdigest()


@dataclass(frozen=True, init=False, slots=True)
class CanonicalAtom:
    atom_id: str
    atom_type: str
    source_sha256: str
    start: int
    end: int
    text: str
    evidence_sha256: str

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("CanonicalAtom must be issued by AtomFactory")


@dataclass(frozen=True, slots=True)
class CanonicalField:
    name: str
    rule: FieldRule
    start: int
    end: int
    value: object
    value_sha256: str


class AtomFactory:
    """Issue atoms only for exact ledger-owned candidate spans."""

    __slots__ = ("_evidence", "_ledger", "_issued")

    def __init__(self, evidence: SourceEvidence, ledger: FinalizedLedger) -> None:
        if ledger.evidence is not evidence or not evidence.verify() or not ledger.verify():
            raise AtomError("atom factory requires the exact verified evidence and ledger")
        self._evidence = evidence
        self._ledger = ledger
        self._issued: dict[str, CanonicalAtom] = {}

    @property
    def evidence(self) -> SourceEvidence:
        return self._evidence

    def issue(self, start: int, end: int, *, atom_type: str = "claim") -> CanonicalAtom:
        # E53_ATOM_FACTORY_GUARD: do not weaken this exact ledger admission check.
        if not isinstance(atom_type, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", atom_type):
            raise AtomError("atom_type must be a stable public token")
        if atom_type == "fact":
            raise AtomError("FACT requires a separate verified-evidence workflow")
        if not self._ledger.is_exact_atom_candidate(start, end):
            raise AtomError("atom range is not an exact ATOM_CANDIDATE ledger span")
        text = self._evidence.text_slice(start, end)
        atom_id = _atom_id(self._evidence, start, end, atom_type)
        evidence_digest = sha256(
            _canonical_json({"source_sha256": self._evidence.sha256, "start": start, "end": end, "text": text})
        ).hexdigest()
        instance = object.__new__(CanonicalAtom)
        object.__setattr__(instance, "atom_id", atom_id)
        object.__setattr__(instance, "atom_type", atom_type)
        object.__setattr__(instance, "source_sha256", self._evidence.sha256)
        object.__setattr__(instance, "start", start)
        object.__setattr__(instance, "end", end)
        object.__setattr__(instance, "text", text)
        object.__setattr__(instance, "evidence_sha256", evidence_digest)
        self._issued[atom_id] = instance
        return instance

    def verify(self, atom: CanonicalAtom) -> bool:
        if not isinstance(atom, CanonicalAtom) or self._issued.get(atom.atom_id) is not atom:
            return False
        if atom.source_sha256 != self._evidence.sha256 or not self._ledger.is_exact_atom_candidate(atom.start, atom.end):
            return False
        try:
            exact_text = self._evidence.text_slice(atom.start, atom.end)
        except Exception:
            return False
        expected_id = _atom_id(self._evidence, atom.start, atom.end, atom.atom_type)
        expected_evidence = sha256(
            _canonical_json({"source_sha256": self._evidence.sha256, "start": atom.start, "end": atom.end, "text": exact_text})
        ).hexdigest()
        return atom.text == exact_text and atom.atom_id == expected_id and atom.evidence_sha256 == expected_evidence

    def extract_field(self, atom: CanonicalAtom, *, name: str, start: int, end: int, rule: FieldRule) -> CanonicalField:
        if not self.verify(atom):
            raise AtomError("field extraction requires a factory-issued atom")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name):
            raise AtomError("field name must be a stable public token")
        if not (atom.start <= start < end <= atom.end):
            raise AtomError("field range must be within the issued atom")
        raw = self._evidence.text_slice(start, end)
        if rule is FieldRule.EXACT_UTF8_SLICE:
            value: object = raw
        elif rule is FieldRule.ASCII_LOWER_STRIP:
            if any(ord(char) > 127 for char in raw):
                raise AtomError("ASCII_LOWER_STRIP rejects non-ASCII source")
            value = raw.strip().lower()
        elif rule is FieldRule.JSON_STRING:
            try:
                candidate = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise AtomError("JSON_STRING field is invalid JSON") from exc
            if not isinstance(candidate, str):
                raise AtomError("JSON_STRING field must decode to a string")
            value = candidate
        else:
            raise AtomError("unknown field rule")
        digest = sha256(_canonical_json({"name": name, "rule": rule.value, "value": value, "start": start, "end": end})).hexdigest()
        return CanonicalField(name, rule, start, end, value, digest)

    def verify_field(self, atom: CanonicalAtom, field: CanonicalField) -> bool:
        if not self.verify(atom):
            return False
        try:
            expected = self.extract_field(atom, name=field.name, start=field.start, end=field.end, rule=field.rule)
        except (AtomError, ValueError):
            return False
        return expected == field


def ensure_json_value(value: object) -> object:
    """Return only finite JSON values, recursively validated for packet construction."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AtomError("non-finite floats are forbidden")
        return value
    if isinstance(value, (list, tuple)):
        return [ensure_json_value(item) for item in value]
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise AtomError("canonical mappings require string keys")
        return {key: ensure_json_value(value[key]) for key in sorted(value)}
    raise AtomError("value is outside the canonical JSON domain")
