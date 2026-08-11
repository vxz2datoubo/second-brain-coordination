"""Local stub of the E47 module surface used by E48 tests.

E48 reuses E47 (PR #207 head ``476d2a287cffb084c01b54c1d5e5eaf22016aac7``)
by import only — E47 code is NOT copied into this branch. For tests run
in environments where the E47 worktree is not on sys.path, we provide a
deterministic stub that mirrors the E47 public surface we depend on.

If the real E47 worktree is on sys.path (e.g. when run inside the same
worktree as PR #207), ``import qclaw_e47_digest`` will succeed and this
stub is unused.

The stub is intentionally small — it is a *test scaffolding* artifact, NOT
E47 source code.
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# This stub is the test-only substitute for E47. When ``tests.test_l3_projection``
# runs, it loads this file under the alias ``qclaw_e47_digest`` and installs the
# loaded module into ``sys.modules`` BEFORE executing it. That means by the time
# the ``@dataclass`` decorator runs below, ``sys.modules`` already has an entry
# for ``qclaw_e47_digest``, which is exactly what ``dataclasses`` needs to look
# up the ``__module__`` for the resulting classes.
#
# To make this work even when the module is imported via its real path
# (``tests._e47_stub``), we register an alias here too. dataclass picks up the
# original module name from the class statement itself; the aliasing only
# matters for production-side ``import qclaw_e47_digest``.

from qclaw_e48_reconstruction.l1_schema import NormalizedSemanticView  # noqa: E402


@dataclass
class SourceSnapshot:
    source_id: str
    source_url: str
    source_title: str
    source_hash: str
    source_size_bytes: int
    source_content: str
    ingested_at: str = ""


@dataclass
class SourceSpan:
    byte_start: int
    byte_end: int
    line_start: int
    line_end: int
    span_label: str = ""


@dataclass
class Atom:
    atom_id: str
    atom_type: str
    content: str
    source_spans: Tuple[SourceSpan, ...]
    evidence_kind: str
    confidence: str
    scope: str = ""
    invalidation_conditions: str = ""


@dataclass
class Relation:
    source_atom_id: str
    target_atom_id: str
    relation_type: str
    span_index: int = -1


@dataclass
class CandidateKnowledgePackage:
    package_id: str
    source: SourceSnapshot
    package_version: int = 1
    atoms: Tuple[Atom, ...] = ()
    relations: Tuple[Relation, ...] = ()
    contradictions: Tuple = ()
    unknowns: Tuple = ()
    memory_records: Tuple = ()
    skills: Tuple = ()
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "schema": "QCLAW-CANDIDATE-KNOWLEDGE-PACKAGE-V1",
            "package_id": self.package_id,
            "package_version": self.package_version,
            "content_hash": "0" * 16,
            "source": {
                "source_id": self.source.source_id,
                "source_url": self.source.source_url,
                "source_title": self.source.source_title,
                "source_hash": self.source.source_hash,
                "source_size_bytes": self.source.source_size_bytes,
                "ingested_at": self.source.ingested_at,
            },
            "summary": self.summary,
            "atoms": [
                {
                    "atom_id": a.atom_id,
                    "atom_type": a.atom_type,
                    "content": a.content,
                    "source_spans": [
                        {
                            "byte_start": s.byte_start,
                            "byte_end": s.byte_end,
                            "line_start": s.line_start,
                            "line_end": s.line_end,
                            **({"span_label": s.span_label} if s.span_label else {}),
                        }
                        for s in a.source_spans
                    ],
                    "evidence_kind": a.evidence_kind,
                    "confidence": a.confidence,
                    "scope": a.scope,
                    "invalidation_conditions": a.invalidation_conditions,
                }
                for a in self.atoms
            ],
            "relations": [
                {
                    "source_atom_id": r.source_atom_id,
                    "target_atom_id": r.target_atom_id,
                    "relation_type": r.relation_type,
                    "span_index": r.span_index,
                }
                for r in self.relations
            ],
            "contradictions": [c if isinstance(c, dict) else {} for c in self.contradictions],
            "unknowns": [u if isinstance(u, dict) else {} for u in self.unknowns],
            "memory_records": [m if isinstance(m, dict) else {} for m in self.memory_records],
            "skills": [s if isinstance(s, dict) else {} for s in self.skills],
        }


def ingest_source(source_text: str, source_url: str, source_title: str, source_id: str) -> SourceSnapshot:
    b = source_text.encode("utf-8")
    return SourceSnapshot(
        source_id=source_id,
        source_url=source_url,
        source_title=source_title,
        source_hash=hashlib.sha256(b).hexdigest(),
        source_size_bytes=len(b),
        source_content=source_text,
        ingested_at="1970-01-01T00:00:00Z",  # deterministic
    )


def build_package(package_id: str, source: SourceSnapshot, atoms: List[Atom],
                  relations: List[Relation] | None = None,
                  contradictions=None, unknowns=None,
                  memory_records=None, skills=None, summary: str = "") -> CandidateKnowledgePackage:
    return CandidateKnowledgePackage(
        package_id=package_id, source=source,
        atoms=tuple(atoms),
        relations=tuple(relations or []),
        contradictions=tuple(contradictions or []),
        unknowns=tuple(unknowns or []),
        memory_records=tuple(memory_records or []),
        skills=tuple(skills or []),
        summary=summary,
    )


def _make_span(source_text: str, char_start: int, char_end: int, label: str = "") -> SourceSpan:
    src_bytes = source_text.encode("utf-8")
    byte_start = len(source_text[:char_start].encode("utf-8"))
    byte_end = byte_start + len(source_text[char_start:char_end].encode("utf-8"))
    lines_before = source_text[:char_start].count("\n")
    excerpt = source_text[char_start:char_end]
    return SourceSpan(
        byte_start=byte_start,
        byte_end=byte_end,
        line_start=lines_before + 1,
        line_end=lines_before + 1 + excerpt.count("\n"),
        span_label=label,
    )


def source_extract(atom_id: str, atom_type: str, source_text: str,
                   char_start: int, char_end: int, confidence: str,
                   scope: str = "", invalidation: str = "", label: str = "") -> Atom:
    content = source_text[char_start:char_end]
    span = _make_span(source_text, char_start, char_end, label)
    return Atom(atom_id, atom_type, content, (span,), "SOURCE_EXTRACT",
                confidence, scope, invalidation)