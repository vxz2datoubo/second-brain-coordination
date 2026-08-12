"""SQLite candidate memory base, selectively merged and hardened from PR #46."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

from .canonical import content_hash, normalize_text
from .learning_packet import _conversation_contract_errors, verify_learning_packet


ALLOWED_TRUTH_STATES = {"candidate", "approved", "conflict", "superseded", "unknown", "stale", "revoked"}
DENIED_TRUTH_STATES = {"rejected", "quarantined"}
_SECRET = re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
_SECRET_VALUE_KEYS = {"credential_value", "secret_value", "token_value", "password_value", "api_key_value", "private_key_value"}


SCHEMA = """
CREATE TABLE IF NOT EXISTS atoms (
    id TEXT PRIMARY KEY,
    atom_type TEXT NOT NULL,
    canonical_statement TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL,
    verification_status TEXT NOT NULL,
    evidence_quality TEXT NOT NULL,
    knowledge_status TEXT NOT NULL,
    gpt_access TEXT NOT NULL,
    transport_visibility TEXT NOT NULL,
    authority_level TEXT NOT NULL,
    source_refs TEXT NOT NULL DEFAULT '[]',
    premises TEXT NOT NULL DEFAULT '[]',
    exceptions TEXT NOT NULL DEFAULT '[]',
    failure_conditions TEXT NOT NULL DEFAULT '[]',
    memory_metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    relation_type TEXT NOT NULL,
    source_atom_id TEXT NOT NULL,
    target_atom_id TEXT NOT NULL,
    confidence REAL NOT NULL,
    context TEXT NOT NULL DEFAULT '',
    knowledge_status TEXT NOT NULL,
    FOREIGN KEY(source_atom_id) REFERENCES atoms(id),
    FOREIGN KEY(target_atom_id) REFERENCES atoms(id)
);
CREATE TABLE IF NOT EXISTS conflicts (
    id TEXT PRIMARY KEY,
    atom_id_a TEXT NOT NULL,
    atom_id_b TEXT NOT NULL,
    conflict_type TEXT NOT NULL DEFAULT 'DIRECT',
    resolution_status TEXT NOT NULL DEFAULT 'UNRESOLVED',
    resolution_note TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(atom_id_a) REFERENCES atoms(id),
    FOREIGN KEY(atom_id_b) REFERENCES atoms(id)
);
CREATE TABLE IF NOT EXISTS unknowns (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT '',
    related_atom_ids TEXT NOT NULL DEFAULT '[]',
    source_refs TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'OPEN'
);
CREATE TABLE IF NOT EXISTS packets (
    id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    authority_write INTEGER NOT NULL,
    base_knowledge_version TEXT NOT NULL,
    json_blob TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS packet_atoms (
    packet_id TEXT NOT NULL,
    atom_id TEXT NOT NULL,
    PRIMARY KEY(packet_id, atom_id),
    FOREIGN KEY(packet_id) REFERENCES packets(id),
    FOREIGN KEY(atom_id) REFERENCES atoms(id)
);
CREATE TABLE IF NOT EXISTS revisions (
    revision_id TEXT PRIMARY KEY,
    parent_revision_id TEXT,
    state_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS retrieval_terms (
    atom_id TEXT NOT NULL,
    term TEXT NOT NULL,
    weight REAL NOT NULL,
    PRIMARY KEY(atom_id, term),
    FOREIGN KEY(atom_id) REFERENCES atoms(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_atoms_truth ON atoms(knowledge_status);
CREATE INDEX IF NOT EXISTS idx_atoms_scope ON atoms(scope);
CREATE INDEX IF NOT EXISTS idx_atoms_type ON atoms(atom_type);
CREATE INDEX IF NOT EXISTS idx_terms_term ON retrieval_terms(term);
CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_atom_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_atom_id);
"""


def tokenize(value: str) -> dict[str, float]:
    normalized = normalize_text(value).casefold()
    weighted: dict[str, float] = {}
    for token in re.findall(r"[a-z0-9_]+", normalized):
        weighted[token] = max(weighted.get(token, 0.0), 1.0)
    for sequence in re.findall(r"[\u3400-\u9fff]+", normalized):
        weighted[sequence] = max(weighted.get(sequence, 0.0), 1.5)
        if len(sequence) == 1:
            weighted[sequence] = 1.5
        for width, weight in ((2, 1.0), (3, 1.25)):
            for index in range(max(0, len(sequence) - width + 1)):
                gram = sequence[index:index + width]
                weighted[gram] = max(weighted.get(gram, 0.0), weight)
    return weighted


class MemoryStore:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> "MemoryStore":
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        # Existing Phase 3 databases predate conversation metadata.  This
        # additive migration preserves all atoms and never creates a new store.
        columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(atoms)")}
        if "memory_metadata" not in columns:
            self._conn.execute("ALTER TABLE atoms ADD COLUMN memory_metadata TEXT NOT NULL DEFAULT '{}'")
        self._conn.commit()
        return self

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("memory_store_not_connected")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def insert_atom(self, atom: dict[str, Any]) -> str:
        _validate_atom(atom)
        if atom.get("atom_type") == "conversation_memory":
            raise ValueError("conversation_requires_learning_packet_import")
        with self.transaction() as connection:
            self._upsert_atom(connection, atom)
            self._index_atom(connection, atom)
            self._audit(connection, "ATOM_UPSERT", atom["id"], "automatic_index=true")
        return atom["id"]

    def update_atom(self, atom_id: str, updates: dict[str, Any]) -> bool:
        existing = self.get_atom(atom_id)
        if existing is None:
            return False
        if existing.get("atom_type") == "conversation_memory":
            raise ValueError("conversation_update_requires_learning_packet_import")
        merged = {**existing, **updates, "id": atom_id}
        _validate_atom(merged)
        with self.transaction() as connection:
            self._upsert_atom(connection, merged)
            self._index_atom(connection, merged)
            self._audit(connection, "ATOM_UPDATE", atom_id, "automatic_reindex=true")
        return True

    def get_atom(self, atom_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM atoms WHERE id=?", (atom_id,)).fetchone()
        return _atom(row) if row else None

    def all_atoms(self) -> list[dict[str, Any]]:
        return [_atom(row) for row in self.conn.execute("SELECT * FROM atoms ORDER BY id")]

    def provenance_for_atom(self, atom_id: str) -> list[dict[str, Any]]:
        """Resolve existing W3 packet lineage without exposing a raw pointer."""
        stored_conversation = (self.get_atom(atom_id) or {}).get("memory_metadata", {}).get("conversation", {})
        rows = self.conn.execute(
            """SELECT packets.id, packets.content_hash, packets.json_blob
               FROM packet_atoms JOIN packets ON packets.id=packet_atoms.packet_id
               WHERE packet_atoms.atom_id=? ORDER BY packets.id""",
            (atom_id,),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            packet = json.loads(row["json_blob"])
            validation = packet.get("validation_report", {})
            conversation = next((
                atom.get("memory_metadata", {}).get("conversation", {})
                for atom in packet.get("atoms", []) if atom.get("id") == atom_id
            ), {})
            source_episodes = conversation.get("source_episodes", [])
            result.append({
                "atom_id": atom_id,
                "packet_id": row["id"],
                "packet_content_hash": row["content_hash"],
                "source_manifest_ids": packet.get("source_manifest_ids", []),
                "episode_manifest_id": next(
                    (item for item in packet.get("source_manifest_ids", []) if item.startswith("conversation-episode-")), None
                ),
                "episode": {
                    "episode_id": validation.get("episode_id"),
                    "user_scope": validation.get("user_scope"),
                    "project_scope": validation.get("project_scope"),
                    "claim_role": validation.get("claim_role"),
                    "recorded_at": validation.get("recorded_at"),
                },
                "source_pointer_hash": validation.get("source_pointer_hash"),
                # Every entry is privacy-minimized: source reference hashes and
                # opaque episode identifiers only, never raw pointers/bodies.
                "source_episodes": source_episodes,
                "daily_candidate_id_hashes": stored_conversation.get("daily_candidate_id_hashes", []),
            })
        return result

    def indexed_terms(self, atom_id: str) -> list[str]:
        return [row["term"] for row in self.conn.execute("SELECT term FROM retrieval_terms WHERE atom_id=? ORDER BY term", (atom_id,))]

    def search_term_scores(self, query_text: str) -> dict[str, float]:
        terms = tokenize(query_text)
        if not terms:
            return {atom["id"]: 0.0 for atom in self.all_atoms()}
        scores: dict[str, float] = {}
        for term, query_weight in terms.items():
            for row in self.conn.execute("SELECT atom_id, weight FROM retrieval_terms WHERE term=?", (term,)):
                scores[row["atom_id"]] = scores.get(row["atom_id"], 0.0) + float(row["weight"]) * query_weight
        normalized_query = normalize_text(query_text).casefold()
        for atom_id in list(scores):
            atom = self.get_atom(atom_id)
            if atom and normalized_query and normalized_query in normalize_text(atom["canonical_statement"]).casefold():
                scores[atom_id] += 2.0
        return scores

    def insert_relation(self, relation: dict[str, Any]) -> str:
        with self.transaction() as connection:
            self._insert_relation(connection, relation)
        return relation["id"]

    def relations_around(self, atom_ids: set[str]) -> list[dict[str, Any]]:
        if not atom_ids:
            return []
        placeholders = ",".join("?" for _ in atom_ids)
        values = tuple(sorted(atom_ids)) * 2
        rows = self.conn.execute(
            f"SELECT * FROM relations WHERE source_atom_id IN ({placeholders}) OR target_atom_id IN ({placeholders}) ORDER BY id",
            values,
        ).fetchall()
        return [dict(row) for row in rows]

    def related_atom_ids(self, atom_ids: set[str]) -> set[str]:
        related: set[str] = set()
        for relation in self.relations_around(atom_ids):
            related.update((relation["source_atom_id"], relation["target_atom_id"]))
        return related - atom_ids

    def conflicts_for(self, atom_ids: set[str]) -> list[dict[str, Any]]:
        if not atom_ids:
            return []
        placeholders = ",".join("?" for _ in atom_ids)
        values = tuple(sorted(atom_ids)) * 2
        rows = self.conn.execute(
            f"SELECT * FROM conflicts WHERE atom_id_a IN ({placeholders}) OR atom_id_b IN ({placeholders}) ORDER BY id",
            values,
        ).fetchall()
        return [dict(row) for row in rows]

    def unknowns_for(self, atom_ids: set[str], include_all_open: bool = False) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM unknowns WHERE status='OPEN' ORDER BY id").fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["related_atom_ids"] = json.loads(item["related_atom_ids"])
            item["source_refs"] = json.loads(item["source_refs"])
            if include_all_open or atom_ids.intersection(item["related_atom_ids"]):
                result.append(item)
        return result

    def import_learning_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        """Import one packet through the same atomic batch boundary."""

        return self.import_learning_packets_atomic((packet,))[0]

    def import_learning_packets_atomic(self, packets: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
        """Import all packets in one W3 transaction or persist none of them."""

        for packet in packets:
            verdict = verify_learning_packet(packet)
            if not verdict["valid"]:
                raise ValueError("invalid_learning_packet:" + ",".join(verdict["errors"]))
            if _contains_secret_value(packet):
                raise ValueError("credential_value_denied")
        if not packets:
            return ()
        results: list[dict[str, Any]] = []
        with self.transaction() as connection:
            for packet in packets:
                existing = connection.execute(
                    "SELECT id FROM packets WHERE idempotency_key=?", (packet["idempotency_key"],)
                ).fetchone()
                if existing:
                    results.append({
                        "status": "IDEMPOTENT_DUPLICATE", "packet_id": existing["id"],
                        "atoms_inserted": 0, "revision_id": self.latest_revision_id(),
                    })
                    continue
                results.append(self._import_learning_packet_in_transaction(connection, packet))
        return tuple(results)

    def _import_learning_packet_in_transaction(
        self, connection: sqlite3.Connection, packet: dict[str, Any],
    ) -> dict[str, Any]:
        inserted = 0
        for atom in packet["atoms"]:
            if connection.execute("SELECT 1 FROM atoms WHERE id=?", (atom["id"],)).fetchone() is None:
                inserted += 1
            self._upsert_atom(connection, atom)
            self._index_atom(connection, atom)
        for relation in packet.get("relations", []):
            if relation.get("target_existing") and connection.execute(
                "SELECT 1 FROM atoms WHERE id=?", (relation["target_atom_id"],)
            ).fetchone() is None:
                raise ValueError("supersession_target_missing")
            self._insert_relation(connection, relation)
            if relation["relation_type"] == "supersedes":
                self._supersede_atom(connection, relation, packet["atoms"])
        for conflict in packet.get("conflicts", []):
            conflict_id = conflict.get("id") or "conf-" + content_hash(conflict)[:20]
            connection.execute(
                "INSERT OR IGNORE INTO conflicts(id, atom_id_a, atom_id_b, conflict_type, resolution_status, resolution_note) VALUES(?,?,?,?,?,?)",
                (conflict_id, conflict["atom_id_a"], conflict["atom_id_b"], conflict.get("conflict_type", "DIRECT"), conflict.get("resolution_status", "UNRESOLVED"), conflict.get("resolution_note", "")),
            )
        for unknown in packet.get("unknowns", []):
            unknown_id = unknown.get("id") or "unk-" + content_hash(unknown)[:20]
            connection.execute(
                "INSERT OR IGNORE INTO unknowns(id, question, scope, related_atom_ids, source_refs, status) VALUES(?,?,?,?,?,?)",
                (unknown_id, unknown["question"], unknown.get("scope", ""), json.dumps(unknown.get("related_atom_ids", [])), json.dumps(unknown.get("source_refs", packet["evidence_refs"])), unknown.get("status", "OPEN")),
            )
        connection.execute(
            "INSERT INTO packets(id, content_hash, idempotency_key, status, authority_write, base_knowledge_version, json_blob, ingested_at) VALUES(?,?,?,?,?,?,?,?)",
            (packet["packet_id"], packet["packet_content_hash"], packet["idempotency_key"], packet["status"], 0, packet["base_knowledge_version"], json.dumps(packet, ensure_ascii=False, sort_keys=True), _now()),
        )
        for atom in packet["atoms"]:
            connection.execute("INSERT INTO packet_atoms(packet_id, atom_id) VALUES(?,?)", (packet["packet_id"], atom["id"]))
        revision_id = self._create_revision(connection, packet["packet_id"])
        self._audit(connection, "PACKET_IMPORT", packet["packet_id"], f"atoms_inserted={inserted};revision={revision_id}")
        return {"status": "IMPORTED", "packet_id": packet["packet_id"], "atoms_inserted": inserted, "revision_id": revision_id}

    def latest_revision_id(self) -> str:
        row = self.conn.execute("SELECT revision_id FROM revisions ORDER BY rowid DESC LIMIT 1").fetchone()
        return row["revision_id"] if row else "candidate-r0"

    def stats(self) -> dict[str, int]:
        names = ("atoms", "relations", "conflicts", "unknowns", "packets", "revisions", "audit_events", "retrieval_terms")
        return {name: int(self.conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]) for name in names}

    def integrity_check(self) -> dict[str, Any]:
        orphan_relations = self.conn.execute(
            "SELECT id FROM relations WHERE source_atom_id NOT IN (SELECT id FROM atoms) OR target_atom_id NOT IN (SELECT id FROM atoms)"
        ).fetchall()
        unindexed = self.conn.execute(
            "SELECT id FROM atoms WHERE id NOT IN (SELECT DISTINCT atom_id FROM retrieval_terms) AND length(canonical_statement)>0"
        ).fetchall()
        issues = ["orphan_relation:" + row["id"] for row in orphan_relations] + ["unindexed_atom:" + row["id"] for row in unindexed]
        return {"integrity_ok": not issues, "issues": issues, "stats": self.stats()}

    def _upsert_atom(self, connection: sqlite3.Connection, atom: dict[str, Any]) -> None:
        atom = self._with_merged_daily_candidate_aliases(connection, atom)
        now = _now()
        connection.execute(
            """INSERT INTO atoms(id, atom_type, canonical_statement, scope, confidence, verification_status, evidence_quality,
               knowledge_status, gpt_access, transport_visibility, authority_level, source_refs, premises, exceptions,
               failure_conditions, memory_metadata, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET atom_type=excluded.atom_type, canonical_statement=excluded.canonical_statement,
               scope=excluded.scope, confidence=excluded.confidence, verification_status=excluded.verification_status,
               evidence_quality=excluded.evidence_quality, knowledge_status=excluded.knowledge_status,
               gpt_access=excluded.gpt_access, transport_visibility=excluded.transport_visibility,
               authority_level=excluded.authority_level, source_refs=excluded.source_refs, premises=excluded.premises,
               exceptions=excluded.exceptions, failure_conditions=excluded.failure_conditions,
               memory_metadata=excluded.memory_metadata, updated_at=excluded.updated_at""",
            (atom["id"], atom["atom_type"], normalize_text(atom["canonical_statement"]), atom.get("scope", ""), float(atom.get("confidence", 0.5)), atom.get("verification_status", "UNVERIFIED"), atom.get("evidence_quality", "UNKNOWN"), atom.get("knowledge_status", "candidate"), atom.get("gpt_access", "FULL_SEMANTIC_ACCESS"), atom.get("transport_visibility", "PUBLIC_SAFE_METADATA_ONLY"), "CANDIDATE_ONLY", json.dumps(atom.get("source_refs", [])), json.dumps(atom.get("premises", [])), json.dumps(atom.get("exceptions", [])), json.dumps(atom.get("failure_conditions", [])), json.dumps(atom.get("memory_metadata", {}), sort_keys=True), now, now),
        )

    @staticmethod
    def _with_merged_daily_candidate_aliases(
        connection: sqlite3.Connection, atom: dict[str, Any],
    ) -> dict[str, Any]:
        """Preserve every hashed producer identity for one canonical atom."""

        incoming = atom.get("memory_metadata", {}).get("conversation", {})
        incoming_hash = incoming.get("daily_candidate_id_hash")
        if incoming_hash is None:
            return atom
        existing = connection.execute(
            "SELECT knowledge_status, memory_metadata FROM atoms WHERE id=?", (atom["id"],)
        ).fetchone()
        if existing is None:
            aliases = sorted(set(incoming.get("daily_candidate_id_hashes", []) + [incoming_hash]))
            result = dict(atom)
            metadata = dict(atom.get("memory_metadata", {}))
            conversation = dict(incoming)
            conversation["daily_candidate_id_hashes"] = aliases
            metadata["conversation"] = conversation
            result["memory_metadata"] = metadata
            return result
        existing_conversation = json.loads(existing["memory_metadata"]).get("conversation", {})
        # A packet-backed external identity can enrich an open atom, but never
        # writes through a correction-derived closure.  Explicit rejection is
        # safer than replaying an ordinary candidate over a historical state.
        if (
            existing["knowledge_status"] == "superseded"
            or existing_conversation.get("effective_valid_to") is not None
            or existing_conversation.get("superseded_by") is not None
        ):
            raise ValueError("conversation_alias_enrichment_closed_atom_denied")
        aliases = set(existing_conversation.get("daily_candidate_id_hashes", []))
        aliases.update(incoming.get("daily_candidate_id_hashes", []))
        aliases.update(filter(None, (existing_conversation.get("daily_candidate_id_hash"), incoming_hash)))
        result = dict(atom)
        metadata = dict(atom.get("memory_metadata", {}))
        conversation = dict(incoming)
        # The first observed external identity remains the stable primary; the
        # sorted alias list makes later identity additions deterministic.
        conversation["daily_candidate_id_hash"] = existing_conversation.get("daily_candidate_id_hash") or min(aliases)
        conversation["daily_candidate_id_hashes"] = sorted(aliases)
        metadata["conversation"] = conversation
        result["memory_metadata"] = metadata
        return result

    @staticmethod
    def _supersede_atom(connection: sqlite3.Connection, relation: dict[str, Any], packet_atoms: list[dict[str, Any]]) -> None:
        """Preserve the old statement while closing its derived valid-time."""
        target = connection.execute("SELECT * FROM atoms WHERE id=?", (relation["target_atom_id"],)).fetchone()
        if target is None:
            raise ValueError("supersession_target_missing")
        source = next((item for item in packet_atoms if item["id"] == relation["source_atom_id"]), None)
        if source is None:
            raise ValueError("supersession_source_missing")
        source_conversation = source.get("memory_metadata", {}).get("conversation")
        target_metadata = json.loads(target["memory_metadata"])
        target_conversation = target_metadata.get("conversation")
        if source_conversation or target_conversation:
            if not source_conversation or not target_conversation:
                raise ValueError("conversation_supersession_metadata_required")
            if target["knowledge_status"] == "superseded" or target_conversation.get("superseded_by"):
                raise ValueError("conversation_supersession_target_already_closed")
            if source_conversation.get("claim_role") != "USER_CORRECTION":
                raise ValueError("conversation_supersession_requires_user_correction")
            for key in ("user_scope", "project_scope", "privacy_class"):
                if source_conversation.get(key) != target_conversation.get(key):
                    raise ValueError("conversation_supersession_scope_mismatch")
            if _instant(source_conversation["valid_from"]) <= _instant(target_conversation["valid_from"]):
                raise ValueError("conversation_supersession_valid_time_invalid")
            # Packet-declared valid_to is immutable and packet-bound. Derived
            # closure is monotonic: it may only shorten, never extend, the
            # historical interval.
            closure_bounds = [source_conversation["valid_from"]]
            for field in ("valid_to", "effective_valid_to"):
                if target_conversation.get(field) is not None:
                    closure_bounds.append(target_conversation[field])
            target_conversation["effective_valid_to"] = _canonical_instant(
                min(closure_bounds, key=_instant)
            )
            target_conversation["superseded_by"] = source["id"]
            target_metadata["conversation"] = target_conversation
        connection.execute(
            "UPDATE atoms SET knowledge_status='superseded', memory_metadata=?, updated_at=? WHERE id=?",
            (json.dumps(target_metadata, sort_keys=True), _now(), relation["target_atom_id"]),
        )
        MemoryStore._audit(connection, "ATOM_SUPERSEDED", relation["target_atom_id"], "by=" + relation["source_atom_id"])

    def _index_atom(self, connection: sqlite3.Connection, atom: dict[str, Any]) -> None:
        connection.execute("DELETE FROM retrieval_terms WHERE atom_id=?", (atom["id"],))
        combined = " ".join((atom.get("canonical_statement", ""), atom.get("scope", ""), atom.get("atom_type", "")))
        for term, weight in sorted(tokenize(combined).items()):
            connection.execute("INSERT INTO retrieval_terms(atom_id, term, weight) VALUES(?,?,?)", (atom["id"], term, weight))

    @staticmethod
    def _insert_relation(connection: sqlite3.Connection, relation: dict[str, Any]) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO relations(id, relation_type, source_atom_id, target_atom_id, confidence, context, knowledge_status) VALUES(?,?,?,?,?,?,?)",
            (relation["id"], relation["relation_type"], relation["source_atom_id"], relation["target_atom_id"], float(relation.get("confidence", 0.5)), relation.get("context", ""), relation.get("knowledge_status", "candidate")),
        )

    def _create_revision(self, connection: sqlite3.Connection, cause_id: str) -> str:
        state = {
            "packets": [row[0] for row in connection.execute("SELECT id FROM packets ORDER BY id")],
            "atoms": [row[0] for row in connection.execute("SELECT id FROM atoms ORDER BY id")],
            "relations": [row[0] for row in connection.execute("SELECT id FROM relations ORDER BY id")],
        }
        state_hash = content_hash(state)
        revision_id = "rev-" + content_hash({"state_hash": state_hash, "cause": cause_id})[:20]
        parent = self.latest_revision_id()
        connection.execute("INSERT OR IGNORE INTO revisions(revision_id, parent_revision_id, state_hash, created_at) VALUES(?,?,?,?)", (revision_id, None if parent == "candidate-r0" else parent, state_hash, _now()))
        return revision_id

    @staticmethod
    def _audit(connection: sqlite3.Connection, event_type: str, object_id: str, detail: str) -> None:
        connection.execute("INSERT INTO audit_events(event_type, object_id, detail, created_at) VALUES(?,?,?,?)", (event_type, object_id, detail, _now()))


def _validate_atom(atom: dict[str, Any]) -> None:
    required = {"id", "atom_type", "canonical_statement"}
    if required - set(atom):
        raise ValueError("atom_required_fields_missing")
    state = atom.get("knowledge_status", "candidate")
    if state not in ALLOWED_TRUTH_STATES | DENIED_TRUTH_STATES:
        raise ValueError("atom_truth_state_invalid")
    if atom.get("authority_level", "CANDIDATE_ONLY") != "CANDIDATE_ONLY":
        raise ValueError("atom_authority_promotion_denied")
    if not isinstance(atom.get("memory_metadata", {}), dict):
        raise ValueError("atom_memory_metadata_invalid")
    conversation_errors = _conversation_contract_errors(atom)
    if conversation_errors:
        raise ValueError("invalid_conversation_atom:" + ",".join(conversation_errors))
    if _contains_secret_value(atom):
        raise ValueError("credential_value_denied")


def _contains_secret_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_SECRET.search(value))
    if isinstance(value, list):
        return any(_contains_secret_value(item) for item in value)
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in _SECRET_VALUE_KEYS and item not in (None, ""):
                return True
            if _contains_secret_value(item):
                return True
    return False


def _atom(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    for field in ("source_refs", "premises", "exceptions", "failure_conditions", "memory_metadata"):
        result[field] = json.loads(result[field])
    return result


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("conversation_time_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _canonical_instant(value: str) -> str:
    return _instant(value).isoformat().replace("+00:00", "Z")
