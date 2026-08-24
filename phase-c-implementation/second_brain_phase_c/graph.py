"""
Graph Evolution Manager: KnowledgeRelation, ConflictSet, lineage chain management.
Manages the knowledge graph edges, conflict sets, and ensures
lineage chains remain acyclic and consistent.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Set, Tuple, Any
from collections import deque

from .models import (
    KnowledgeAtom, AtomStatus, RelationType, RelationStatus,
    ConflictType, ConflictResolutionStatus, _now_iso, _new_id,
)


@dataclass
class KnowledgeRelation:
    relation_id: str = field(default_factory=lambda: _new_id("kr_"))
    source_atom_id: str = ""
    target_atom_id: str = ""
    relation_type: RelationType = RelationType.IS_A
    confidence: float = 0.5
    rationale: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    created_by: str = "GPT"
    status: RelationStatus = RelationStatus.ACTIVE
    is_unknown: bool = False
    human_confirmed: Optional[bool] = None

    def to_dict(self):
        d = asdict(self)
        d["relation_type"] = self.relation_type.value
        d["status"] = self.status.value
        return d


@dataclass
class ConflictSet:
    conflict_set_id: str = field(default_factory=lambda: _new_id("cs_"))
    member_atom_ids: List[str] = field(default_factory=list)
    conflict_type: ConflictType = ConflictType.FACTUAL
    description: str = ""
    discovered_at: str = field(default_factory=_now_iso)
    discovered_by: str = "GPT"
    resolution_status: ConflictResolutionStatus = ConflictResolutionStatus.OPEN
    resolution_at: Optional[str] = None
    resolution_notes: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d["conflict_type"] = self.conflict_type.value
        d["resolution_status"] = self.resolution_status.value
        return d


class GraphEvolutionManager:
    def __init__(self, atom_store: Dict[str, KnowledgeAtom]):
        self._atoms = atom_store
        self._relations: Dict[str, KnowledgeRelation] = {}
        self._conflict_sets: Dict[str, ConflictSet] = {}

    def create_relation(
        self, source_atom_id, target_atom_id, relation_type,
        confidence=0.5, rationale="", evidence_refs=None,
        created_by="GPT", is_unknown=False,
    ):
        if source_atom_id not in self._atoms:
            raise ValueError(f"Source atom {source_atom_id} not found")
        if target_atom_id not in self._atoms:
            raise ValueError(f"Target atom {target_atom_id} not found")
        for rel in self._relations.values():
            if (rel.source_atom_id == source_atom_id
                and rel.target_atom_id == target_atom_id
                and rel.relation_type == relation_type
                and rel.status == RelationStatus.ACTIVE):
                return rel
        rel = KnowledgeRelation(
            source_atom_id=source_atom_id, target_atom_id=target_atom_id,
            relation_type=relation_type, confidence=confidence,
            rationale=rationale, evidence_refs=evidence_refs or [],
            created_by=created_by, is_unknown=is_unknown,
        )
        self._relations[rel.relation_id] = rel
        self._atoms[source_atom_id].relation_ids.append(rel.relation_id)
        if source_atom_id != target_atom_id:
            self._atoms[target_atom_id].relation_ids.append(rel.relation_id)
        return rel

    def revoke_relation(self, relation_id):
        if relation_id in self._relations:
            self._relations[relation_id].status = RelationStatus.REVOKED

    def get_relations_for_atom(self, atom_id, active_only=True):
        result = []
        for rel in self._relations.values():
            if rel.source_atom_id == atom_id or rel.target_atom_id == atom_id:
                if not active_only or rel.status == RelationStatus.ACTIVE:
                    result.append(rel)
        return result

    def create_conflict_set(self, member_atom_ids, conflict_type=ConflictType.FACTUAL,
                            description="", discovered_by="GPT"):
        for atom_id in member_atom_ids:
            if atom_id not in self._atoms:
                raise ValueError(f"Atom {atom_id} not found")
        cs = ConflictSet(
            member_atom_ids=list(member_atom_ids), conflict_type=conflict_type,
            description=description, discovered_by=discovered_by,
        )
        self._conflict_sets[cs.conflict_set_id] = cs
        for atom_id in member_atom_ids:
            self._atoms[atom_id].current_status = AtomStatus.CONFLICTED
            self._atoms[atom_id].conflict_set_id = cs.conflict_set_id
        return cs

    def resolve_conflict_set(self, conflict_set_id, resolution_notes="",
                             surviving_atom_id=None):
        cs = self._conflict_sets.get(conflict_set_id)
        if not cs:
            raise ValueError(f"Conflict set {conflict_set_id} not found")
        cs.resolution_status = ConflictResolutionStatus.RESOLVED
        cs.resolution_at = _now_iso()
        cs.resolution_notes = resolution_notes
        if surviving_atom_id:
            for atom_id in cs.member_atom_ids:
                atom = self._atoms[atom_id]
                if atom_id == surviving_atom_id:
                    atom.current_status = AtomStatus.ACTIVE
                    atom.conflict_set_id = None
                else:
                    atom.current_status = AtomStatus.SUPERSEDED
                    atom.lineage_head = False
                    atom.successor_atom_ids.append(surviving_atom_id)
                    self._atoms[surviving_atom_id].predecessor_atom_ids.append(atom_id)

    def get_conflict_set(self, conflict_set_id):
        return self._conflict_sets.get(conflict_set_id)

    def set_supersession(self, old_atom_id, new_atom_id):
        if old_atom_id not in self._atoms or new_atom_id not in self._atoms:
            raise ValueError("Atom not found")
        old = self._atoms[old_atom_id]
        new = self._atoms[new_atom_id]
        if self._would_create_cycle(old_atom_id, new_atom_id):
            raise ValueError(f"Supersession would create cycle: {old_atom_id} -> {new_atom_id}")
        old.current_status = AtomStatus.SUPERSEDED
        old.lineage_head = False
        old.successor_atom_ids.append(new_atom_id)
        new.predecessor_atom_ids.append(old_atom_id)
        new.lineage_head = True
        self.create_relation(
            source_atom_id=new_atom_id, target_atom_id=old_atom_id,
            relation_type=RelationType.SUPERSEDES, confidence=1.0,
            rationale="Explicit supersession",
        )

    def get_lineage_chain(self, atom_id):
        if atom_id not in self._atoms:
            return []
        predecessors = []
        current = atom_id
        visited = set()
        while current:
            if current in visited:
                break
            visited.add(current)
            atom = self._atoms.get(current)
            if not atom or not atom.predecessor_atom_ids:
                break
            current = atom.predecessor_atom_ids[0]
            predecessors.append(current)
        predecessors.reverse()
        successors = []
        current = atom_id
        visited = set()
        while current:
            if current in visited:
                break
            visited.add(current)
            atom = self._atoms.get(current)
            if not atom or not atom.successor_atom_ids:
                break
            current = atom.successor_atom_ids[0]
            successors.append(current)
        return predecessors + [atom_id] + successors

    def get_current_head(self, atom_id):
        chain = self.get_lineage_chain(atom_id)
        if not chain:
            return None
        return self._atoms.get(chain[-1])

    def _would_create_cycle(self, old_atom_id, new_atom_id):
        visited = set()
        queue = deque([old_atom_id])
        while queue:
            current = queue.popleft()
            if current == new_atom_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            atom = self._atoms.get(current)
            if atom:
                queue.extend(atom.predecessor_atom_ids)
        return False

    def check_lineage_acyclic(self):
        for atom_id in self._atoms:
            if self._has_cycle_from(atom_id):
                return False, self.get_lineage_chain(atom_id)
        return True, []

    def _has_cycle_from(self, start):
        visited = set()
        rec_stack = set()
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            atom = self._atoms.get(node)
            if atom:
                for succ in atom.successor_atom_ids:
                    if succ not in visited:
                        if dfs(succ):
                            return True
                    elif succ in rec_stack:
                        return True
            rec_stack.discard(node)
            return False
        return dfs(start)

    def check_conflict_set_integrity(self):
        errors = []
        for cs in self._conflict_sets.values():
            for atom_id in cs.member_atom_ids:
                atom = self._atoms.get(atom_id)
                if not atom:
                    errors.append(f"Conflict set {cs.conflict_set_id} references missing atom {atom_id}")
                elif atom.current_status != AtomStatus.CONFLICTED and cs.resolution_status == ConflictResolutionStatus.OPEN:
                    errors.append(f"Atom {atom_id} in conflict set {cs.conflict_set_id} but status is {atom.current_status}")
        return len(errors) == 0, errors

    def check_edge_completeness(self):
        errors = []
        for rel in self._relations.values():
            if rel.source_atom_id not in self._atoms:
                errors.append(f"Relation {rel.relation_id} has missing source {rel.source_atom_id}")
            if rel.target_atom_id not in self._atoms:
                errors.append(f"Relation {rel.relation_id} has missing target {rel.target_atom_id}")
        return len(errors) == 0, errors

    def run_all_consistency_checks(self):
        acyclic, cycle = self.check_lineage_acyclic()
        conflict_ok, conflict_errors = self.check_conflict_set_integrity()
        edge_ok, edge_errors = self.check_edge_completeness()
        return {
            "lineage_acyclic": acyclic,
            "lineage_cycle": cycle,
            "conflict_set_integrity": conflict_ok,
            "conflict_set_errors": conflict_errors,
            "edge_completeness": edge_ok,
            "edge_errors": edge_errors,
            "all_passed": acyclic and conflict_ok and edge_ok,
        }
