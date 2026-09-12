"""SQLite-backed shadow store for the cognitive loop.

Isolated from the production W3 capture surface by construction: it owns its
own database file and never touches any other store. Every atom carries
provenance, and conflict detection is exposed as a first-class query.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping

from .atom import FeedbackRecord, KnowledgeAtom, Provenance


class StoreViolation(ValueError):
    """Raised for schema or identity problems inside the shadow store."""


_ATOM_COLUMNS = (
    "atom_id",
    "content",
    "subject",
    "topic",
    "nature",
    "confidence",
    "source_type",
    "retriever",
    "retrieved_at",
    "url",
    "raw_ref",
    "revision",
    "time_valid_from",
    "time_valid_to",
    "evidence_refs",
    "created_at",
    "updated_at",
)


class ShadowStore:
    """A single-file store. Pass ``":memory:"`` for tests."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS atoms (
                atom_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                nature TEXT NOT NULL,
                confidence REAL NOT NULL,
                source_type TEXT NOT NULL,
                retriever TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                url TEXT,
                raw_ref TEXT,
                revision TEXT,
                time_valid_from TEXT NOT NULL,
                time_valid_to TEXT,
                evidence_refs TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_atoms_subject_topic
                ON atoms (subject, topic);
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                predicted_subject TEXT NOT NULL,
                predicted_answer TEXT NOT NULL,
                predicted_confidence REAL NOT NULL,
                observed_subject TEXT,
                observed_answer TEXT,
                resolved_at TEXT,
                was_correct INTEGER
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _atom_row_to_atom(self, row: sqlite3.Row) -> KnowledgeAtom:
        return KnowledgeAtom(
            content=row["content"],
            subject=row["subject"],
            topic=row["topic"],
            nature=row["nature"],
            confidence=float(row["confidence"]),
            provenance=Provenance(
                source_type=row["source_type"],
                retriever=row["retriever"],
                retrieved_at=row["retrieved_at"],
                url=row["url"],
                raw_ref=row["raw_ref"],
                revision=row["revision"],
            ),
            time_valid_from=row["time_valid_from"],
            time_valid_to=row["time_valid_to"],
            evidence_refs=tuple(json.loads(row["evidence_refs"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def upsert_atom(self, atom: KnowledgeAtom) -> KnowledgeAtom:
        row = self._conn.execute(
            "SELECT atom_id FROM atoms WHERE atom_id = ?", (atom.atom_id,)
        ).fetchone()
        if row is not None:
            self._conn.execute(
                """
                UPDATE atoms SET content=?, subject=?, topic=?, nature=?,
                    confidence=?, source_type=?, retriever=?, retrieved_at=?,
                    url=?, raw_ref=?, revision=?, time_valid_from=?,
                    time_valid_to=?, evidence_refs=?, updated_at=?
                WHERE atom_id=?
                """,
                (
                    atom.content,
                    atom.subject,
                    atom.topic,
                    atom.nature,
                    atom.confidence,
                    atom.provenance.source_type,
                    atom.provenance.retriever,
                    atom.provenance.retrieved_at,
                    atom.provenance.url,
                    atom.provenance.raw_ref,
                    atom.provenance.revision,
                    atom.time_valid_from,
                    atom.time_valid_to,
                    json.dumps(list(atom.evidence_refs)),
                    atom.updated_at or atom.created_at,
                    atom.atom_id,
                ),
            )
        else:
            self._conn.execute(
                f"INSERT INTO atoms ({', '.join(_ATOM_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _ATOM_COLUMNS)})",
                (
                    atom.atom_id,
                    atom.content,
                    atom.subject,
                    atom.topic,
                    atom.nature,
                    atom.confidence,
                    atom.provenance.source_type,
                    atom.provenance.retriever,
                    atom.provenance.retrieved_at,
                    atom.provenance.url,
                    atom.provenance.raw_ref,
                    atom.provenance.revision,
                    atom.time_valid_from,
                    atom.time_valid_to,
                    json.dumps(list(atom.evidence_refs)),
                    atom.created_at,
                    atom.updated_at or atom.created_at,
                ),
            )
        self._conn.commit()
        return atom

    def get_atom(self, atom_id: str) -> KnowledgeAtom | None:
        row = self._conn.execute(
            "SELECT * FROM atoms WHERE atom_id = ?", (atom_id,)
        ).fetchone()
        return self._atom_row_to_atom(row) if row is not None else None

    def list_atoms(
        self,
        *,
        subject: str | None = None,
        topic: str | None = None,
        nature: str | None = None,
    ) -> list[KnowledgeAtom]:
        clauses: list[str] = []
        params: list[Any] = []
        if subject is not None:
            clauses.append("subject = ?")
            params.append(subject)
        if topic is not None:
            clauses.append("topic = ?")
            params.append(topic)
        if nature is not None:
            clauses.append("nature = ?")
            params.append(nature)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._conn.execute(f"SELECT * FROM atoms{where}", params).fetchall()
        return [self._atom_row_to_atom(row) for row in rows]

    def all_atoms(self) -> list[KnowledgeAtom]:
        return self.list_atoms()

    def delete_atom(self, atom_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM atoms WHERE atom_id = ?", (atom_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def add_feedback(self, record: FeedbackRecord) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO feedback (
                question, predicted_subject, predicted_answer,
                predicted_confidence, observed_subject, observed_answer,
                resolved_at, was_correct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.question,
                record.predicted_subject,
                record.predicted_answer,
                record.predicted_confidence,
                record.observed_subject,
                record.observed_answer,
                record.resolved_at,
                None if record.was_correct is None else int(record.was_correct),
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def list_feedback(self) -> list[FeedbackRecord]:
        rows = self._conn.execute("SELECT * FROM feedback ORDER BY id").fetchall()
        return [
            FeedbackRecord(
                question=row["question"],
                predicted_subject=row["predicted_subject"],
                predicted_answer=row["predicted_answer"],
                predicted_confidence=float(row["predicted_confidence"]),
                observed_subject=row["observed_subject"],
                observed_answer=row["observed_answer"],
                resolved_at=row["resolved_at"],
                was_correct=row["was_correct"],
            )
            for row in rows
        ]

    def resolve_feedback(
        self, feedback_id: int, observed_subject: str, observed_answer: str, resolved_at: str
    ) -> FeedbackRecord | None:
        row = self._conn.execute(
            "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
        ).fetchone()
        if row is None:
            return None
        record = FeedbackRecord(
            question=row["question"],
            predicted_subject=row["predicted_subject"],
            predicted_answer=row["predicted_answer"],
            predicted_confidence=float(row["predicted_confidence"]),
            observed_subject=row["observed_subject"],
            observed_answer=row["observed_answer"],
            resolved_at=row["resolved_at"],
            was_correct=row["was_correct"],
        )
        resolved = record.resolve(observed_subject, observed_answer, resolved_at)
        self._conn.execute(
            """
            UPDATE feedback SET observed_subject=?, observed_answer=?,
                resolved_at=?, was_correct=? WHERE id=?
            """,
            (
                resolved.observed_subject,
                resolved.observed_answer,
                resolved.resolved_at,
                None if resolved.was_correct is None else int(resolved.was_correct),
                feedback_id,
            ),
        )
        self._conn.commit()
        return resolved
