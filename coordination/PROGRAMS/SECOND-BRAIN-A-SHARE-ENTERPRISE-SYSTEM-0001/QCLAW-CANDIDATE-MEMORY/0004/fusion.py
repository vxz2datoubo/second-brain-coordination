"""Candidate Memory Library — Incremental Fusion Engine

Work Package B: handles 9 merge states when importing LearningPackets:
  NEW, DUPLICATE, SUPPLEMENT, REFINEMENT, CONFLICT, CORRECTION,
  REPLACEMENT, OUTDATED, UNRESOLVED.

Design rules:
  - Duplicates must not create orphan atoms
  - Supplements/refinements must not be swallowed as duplicates
  - Conflicts must preserve both sides
  - Corrections must establish UPDATES/REPLACES/SUPERSEDES chains
  - Old knowledge is never physically deleted
  - Same input → same merge decision (deterministic)
  - Every fusion must produce a MergeDecision + audit record
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


# ── Merge States ───────────────────────────────────────────────────────

class MergeState(str, Enum):
    NEW = "NEW"
    DUPLICATE = "DUPLICATE"
    SUPPLEMENT = "SUPPLEMENT"
    REFINEMENT = "REFINEMENT"
    CONFLICT = "CONFLICT"
    CORRECTION = "CORRECTION"
    REPLACEMENT = "REPLACEMENT"
    OUTDATED = "OUTDATED"
    UNRESOLVED = "UNRESOLVED"

# ── Merge Actions ─────────────────────────────────────────────────────

class MergeAction(str, Enum):
    INSERT_ATOM = "INSERT_ATOM"
    UPDATE_ATOM = "UPDATE_ATOM"
    INSERT_RELATION = "INSERT_RELATION"
    INSERT_CONFLICT = "INSERT_CONFLICT"
    SUPERSEDES = "SUPERSEDES"
    PRESERVE_EXISTING = "PRESERVE_EXISTING"
    NO_ACTION = "NO_ACTION"


# ── Merge Decision ─────────────────────────────────────────────────────

class MergeDecision:
    """Result of classifying an incoming item against the store."""

    __slots__ = ("state", "incoming_id", "existing_id", "reason", "actions", "data")

    def __init__(self, state: MergeState, incoming_id: str, existing_id: Optional[str],
                 reason: str, actions: List[MergeAction],
                 data: Optional[Dict[str, Any]] = None):
        self.state = state
        self.incoming_id = incoming_id
        self.existing_id = existing_id
        self.reason = reason
        self.actions = actions
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "incoming_id": self.incoming_id,
            "existing_id": self.existing_id,
            "reason": self.reason,
            "actions": [a.value for a in self.actions],
        }

    def __repr__(self):
        return f"MergeDecision({self.state.value}, {self.incoming_id[:12]}...)"


# ── Fusion Report ──────────────────────────────────────────────────────

class FusionReport:
    """Summary of a packet fusion operation."""

    def __init__(self, packet_id: str):
        self.packet_id = packet_id
        self.source_id = ""
        self.atoms_inserted = 0
        self.atoms_updated = 0
        self.relations_inserted = 0
        self.conflicts_inserted = 0
        self.unknowns_inserted = 0
        self.skills_inserted = 0
        self.decisions: List[MergeDecision] = []
        self._state_counts: Dict[str, int] = {}

    @property
    def duplicates(self) -> int:
        return self._state_counts.get("DUPLICATE", 0)

    @property
    def conflicts(self) -> int:
        return self._state_counts.get("CONFLICT", 0)

    @property
    def corrections(self) -> int:
        return self._state_counts.get("CORRECTION", 0)

    @property
    def refinements(self) -> int:
        return self._state_counts.get("REFINEMENT", 0)

    def add_decision(self, d: MergeDecision):
        self.decisions.append(d)
        self._state_counts[d.state.value] = self._state_counts.get(d.state.value, 0) + 1

    def summary(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "source_id": self.source_id,
            "atoms": {"inserted": self.atoms_inserted, "updated": self.atoms_updated,
                      "duplicates": self.duplicates},
            "relations": {"inserted": self.relations_inserted},
            "conflicts": {"inserted": self.conflicts_inserted, "detected": self.conflicts},
            "unknowns": {"inserted": self.unknowns_inserted},
            "skills": {"inserted": self.skills_inserted},
            "merge_states": self._state_counts,
            "total_decisions": len(self.decisions),
        }

    def __repr__(self):
        s = self.summary()
        return (f"FusionReport({self.packet_id}: "
                f"atoms={s['atoms']}, rels={s['relations']}, "
                f"conflicts={s['conflicts']})")


class FusionEngine:
    """Determines merge state for incoming atoms/relations against existing store."""

    SIMILARITY_THRESHOLD = 0.85  # For fuzzy statement comparison
    CONFIDENCE_IMPROVEMENT = 0.1  # Min confidence gain to count as REFINEMENT
    CONFLICT_SEMANTIC_OPPOSITES = {
        ("SUPPORTS", "CONTRADICTS"),
        ("CAUSES", "PREVENTS"),
        ("IS_A", "IS_NOT_A"),
    }

    def __init__(self, store):
        """store: MemoryStore instance"""
        self.store = store

    # ── Atom-Level Merge ────────────────────────────────────────────

    def classify_atom(self, incoming: Dict[str, Any]) -> MergeDecision:
        """
        Classify an incoming atom against existing store.
        Returns MergeDecision with state, reasoning, and actions.
        """
        existing = self._find_matching_atom(incoming)

        if not existing:
            return MergeDecision(
                state=MergeState.NEW,
                incoming_id=incoming["id"],
                existing_id=None,
                reason="No existing atom matches by exact id or canonical statement.",
                actions=[MergeAction.INSERT_ATOM],
                data={"atom": incoming},
            )

        # Same semantic id
        return self._classify_by_semantic_match(incoming, existing)

    def _find_matching_atom(self, atom: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find existing atom by id first, then by canonical statement."""
        # Exact ID match
        if atom.get("id"):
            existing = self.store.get_atom(atom["id"])
            if existing:
                return existing

        # Canonical statement match (via FTS)
        stmt = atom.get("canonical_statement", "")
        if stmt:
            # Try direct search first
            terms = stmt.lower().split()
            query = " OR ".join(terms[:6])  # first 6 words
            results = self.store.search_fts(query, limit=5)
            for r in results:
                if r["canonical_statement"] == stmt:
                    return r

        return None

    def _classify_by_semantic_match(self, incoming: Dict[str, Any],
                                     existing: Dict[str, Any]) -> "MergeDecision":
        """Compare incoming with existing atom to determine merge state."""
        actions = []
        data = {"atom": incoming, "existing": existing}

        same_statement = (incoming.get("canonical_statement") ==
                          existing.get("canonical_statement"))

        if same_statement:
            # Check confidence
            inc_conf = incoming.get("confidence", 0) or 0
            ex_conf = existing.get("confidence", 0) or 0

            if inc_conf == ex_conf and incoming.get("verification_status") == existing.get("verification_status"):
                return MergeDecision(
                    state=MergeState.DUPLICATE,
                    incoming_id=incoming["id"],
                    existing_id=existing["id"],
                    reason="Same statement, same confidence, same verification.",
                    actions=[],
                    data=data,
                )

            if inc_conf > ex_conf + self.CONFIDENCE_IMPROVEMENT:
                return MergeDecision(
                    state=MergeState.REFINEMENT,
                    incoming_id=incoming["id"],
                    existing_id=existing["id"],
                    reason=f"Confidence improved: {ex_conf} → {inc_conf}",
                    actions=[MergeAction.UPDATE_ATOM],
                    data={"atom": incoming, "existing_id": existing["id"],
                          "updates": {"confidence": inc_conf, "verification_status": incoming.get("verification_status", existing.get("verification_status", "UNVERIFIED"))}},
                )

            # Check for corrections (incoming has newer evidence)
            inc_evidence = incoming.get("evidence_quality", "")
            ex_evidence = existing.get("evidence_quality", "")
            evidence_hierarchy = {"none": 0, "low": 1, "medium": 2, "high": 3, "synthetic": 0}

            if evidence_hierarchy.get(inc_evidence, 0) > evidence_hierarchy.get(ex_evidence, 0) + 1:
                return MergeDecision(
                    state=MergeState.CORRECTION,
                    incoming_id=incoming["id"],
                    existing_id=existing["id"],
                    reason=f"Evidence quality improved: {ex_evidence} → {inc_evidence}",
                    actions=[MergeAction.UPDATE_ATOM],
                    data={"atom": incoming, "existing_id": existing["id"],
                          "updates": {"evidence_quality": inc_evidence, "knowledge_status": "SUPERSEDED", "verification_status": incoming.get("verification_status", "VERIFIED")}},
                )

            return MergeDecision(
                state=MergeState.SUPPLEMENT,
                incoming_id=incoming["id"],
                existing_id=existing["id"],
                reason="Same statement, incoming adds supplementary context.",
                actions=[MergeAction.UPDATE_ATOM],
                data={"atom": incoming, "existing_id": existing["id"],
                      "updates": self._merge_supplement(incoming, existing)},
            )

        # Different statements — check for contradiction
        inc_type = incoming.get("atom_type", "")
        ex_type = existing.get("atom_type", "")
        if inc_type == ex_type:
            # Check semantic opposition
            for r in self.store.get_relations_around(existing["id"]):
                if r["relation_type"] == "CONTRADICTS":
                    return MergeDecision(
                        state=MergeState.CONFLICT,
                        incoming_id=incoming["id"],
                        existing_id=existing["id"],
                        reason=f"Existing atom has CONTRADICTS relation to atom {r['to_atom_id'] or r['from_atom_id']}.",
                        actions=[MergeAction.INSERT_ATOM, MergeAction.INSERT_CONFLICT],
                        data={"atom": incoming, "existing": existing,
                              "conflict": {"atom_id_a": incoming["id"], "atom_id_b": existing["id"],
                                           "conflict_type": "DIRECT"}},
                    )

        # Default: NEW with different content
        return MergeDecision(
            state=MergeState.NEW,
            incoming_id=incoming["id"],
            existing_id=None,
            reason="Similar but not identical statement — treated as distinct atom.",
            actions=[MergeAction.INSERT_ATOM],
            data={"atom": incoming},
        )

    def _merge_supplement(self, incoming: Dict, existing: Dict) -> Dict[str, Any]:
        """Merge supplementary fields without losing existing data."""
        updates = {}
        for field in ["premises", "exceptions", "failure_conditions"]:
            inc_val = incoming.get(field, [])
            ex_val = json.loads(existing.get(field, "[]")) if isinstance(existing.get(field, "[]"), str) else existing.get(field, [])
            if inc_val and inc_val != ex_val:
                merged = list(set((ex_val or []) + inc_val))
                updates[field] = merged
        return updates

    # ── Relation-Level Merge ────────────────────────────────────────

    def classify_relation(self, incoming: Dict[str, Any]) -> "MergeDecision":
        """Classify an incoming relation against existing store."""
        existing = self.store.get_relation(incoming["id"]) if incoming.get("id") else None

        if not existing:
            return MergeDecision(
                state=MergeState.NEW,
                incoming_id=incoming["id"],
                existing_id=None,
                reason="No existing relation with this ID.",
                actions=[MergeAction.INSERT_RELATION],
                data={"relation": incoming},
            )

        # Check contradiction
        inc_type = incoming.get("relation_type")
        ex_type = existing.get("relation_type")
        if (inc_type, ex_type) in self.CONFLICT_SEMANTIC_OPPOSITES or \
           (ex_type, inc_type) in self.CONFLICT_SEMANTIC_OPPOSITES:
            return MergeDecision(
                state=MergeState.CONFLICT,
                incoming_id=incoming["id"],
                existing_id=existing["id"],
                reason=f"Relation types are semantically opposed: {inc_type} vs {ex_type}",
                actions=[MergeAction.INSERT_RELATION, MergeAction.PRESERVE_EXISTING],
                data={"relation": incoming, "existing": existing},
            )

        # Same relation type → check confidence
        inc_conf = incoming.get("confidence", 0) or 0
        ex_conf = existing.get("confidence", 0) or 0
        if inc_conf > ex_conf + self.CONFIDENCE_IMPROVEMENT:
            return MergeDecision(
                state=MergeState.REFINEMENT,
                incoming_id=incoming["id"],
                existing_id=existing["id"],
                reason=f"Relation confidence improved: {ex_conf} → {inc_conf}",
                actions=[MergeAction.INSERT_RELATION],
                data={"relation": incoming, "existing_id": existing["id"]},
            )

        return MergeDecision(
            state=MergeState.DUPLICATE,
            incoming_id=incoming["id"],
            existing_id=existing["id"],
            reason="Same relation type and confidence.",
            actions=[],
            data={"relation": incoming},
        )

    # ── Full Packet Fusion ──────────────────────────────────────────

    def fuse_packet(self, packet: Dict[str, Any]) -> "FusionReport":
        """Fuse a full LearningPacket into the store. Returns FusionReport."""
        report = FusionReport(packet_id=packet.get("id", packet.get("semantic_id", "unknown")))

        # 1. Source
        if packet.get("source"):
            src = packet["source"]
            if isinstance(src, str):
                src = {"id": src, "source_type": "SYNTHETIC"}
            src.setdefault("id", src.get("source_id", hashlib.sha256(str(src).encode()).hexdigest()[:16]))
            report.source_id = src.get("id")
            self.store.insert_source(src)

        # 2. Atoms
        for atom in packet.get("atoms", []):
            if not atom.get("id"):
                atom["id"] = hashlib.sha256(
                    json.dumps(atom, sort_keys=True, default=str).encode()
                ).hexdigest()
            decision = self.classify_atom(atom)
            report.add_decision(decision)

            for action in decision.actions:
                if action == MergeAction.INSERT_ATOM:
                    self.store.insert_atom(atom)
                    report.atoms_inserted += 1
                elif action == MergeAction.UPDATE_ATOM:
                    self.store.update_atom(decision.data.get("existing_id", decision.existing_id),
                                           decision.data.get("updates", {}))
                    report.atoms_updated += 1
                elif action == MergeAction.INSERT_CONFLICT:
                    con = decision.data.get("conflict", {})
                    con.setdefault("id", hashlib.sha256(
                        f"{con.get('atom_id_a','')}|{con.get('atom_id_b','')}".encode()
                    ).hexdigest())
                    self.store.insert_conflict(con)
                    report.conflicts_inserted += 1
                elif action == MergeAction.SUPERSEDES:
                    old_id = decision.data.get("existing_id", decision.existing_id)
                    if old_id:
                        sup_rel = {
                            "id": hashlib.sha256(
                                f"SUPERSEDES|{atom['id']}|{old_id}".encode()
                            ).hexdigest(),
                            "relation_type": "SUPERSEDES",
                            "from_atom_id": atom["id"],
                            "to_atom_id": old_id,
                            "context": decision.reason,
                        }
                        self.store.insert_relation(sup_rel)
                        self.store.update_atom(old_id,
                            {"knowledge_status": "SUPERSEDED", "verification_status": "OUTDATED"})
                        report.relations_inserted += 1

        # 3. Relations
        for rel in packet.get("relations", []):
            if not rel.get("id"):
                rel["id"] = hashlib.sha256(
                    f"{rel.get('from_atom_id','')}|{rel.get('relation_type','')}|{rel.get('to_atom_id','')}".encode()
                ).hexdigest()
            decision = self.classify_relation(rel)
            report.add_decision(decision)

            for action in decision.actions:
                if action in (MergeAction.INSERT_RELATION, MergeAction.PRESERVE_EXISTING):
                    self.store.insert_relation(rel)
                    report.relations_inserted += 1

        # 4. Unknowns
        for unk in packet.get("unknowns", []):
            if not unk.get("id"):
                unk["id"] = hashlib.sha256(unk["question"].encode()).hexdigest()
            self.store.insert_unknown(unk)
            report.unknowns_inserted += 1

        # 5. Conflicts (explicit in packet)
        for con in packet.get("conflicts", []):
            if not con.get("id"):
                con["id"] = hashlib.sha256(
                    f"{con.get('atom_id_a','')}|{con.get('atom_id_b','')}".encode()
                ).hexdigest()
            self.store.insert_conflict(con)
            report.conflicts_inserted += 1

        # 6. Skills/Structures
        for sk in packet.get("skills", []) + packet.get("structures", []):
            if not sk.get("id"):
                sk["id"] = hashlib.sha256(
                    json.dumps(sk, sort_keys=True, default=str).encode()
                ).hexdigest()
            self.store.insert_skill(sk)
            report.skills_inserted += 1

        # 7. Record packet
        self.store.import_packet_dict({**packet,
            "atom_ids": [a["id"] for a in packet.get("atoms", [])],
            "relation_ids": [r["id"] for r in packet.get("relations", [])],
        })

        # 8. Audit
        self.store.audit(
            "MERGE",
            f"Fused packet: {report.packet_id} — "
            f"atoms(new={report.atoms_inserted}, upd={report.atoms_updated}, dup={report.duplicates}), "
            f"rels={report.relations_inserted}, "
            f"conflicts={report.conflicts_inserted}",
            packet_id=report.packet_id,
        )

        return report
