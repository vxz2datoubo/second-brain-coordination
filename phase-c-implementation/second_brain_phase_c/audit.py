"""
Reconciliation Audit Log with rollback mechanism.
Every reconciliation action is recorded in an audit log.
Executed actions can be rolled back, restoring the pre-action state.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from .models import (
    KnowledgeAtom, AtomStatus, ReconciliationAction,
    AuditExecutionStatus, _now_iso, _new_id,
)


@dataclass
class ReconciliationAuditLog:
    audit_id: str = field(default_factory=lambda: _new_id("ra_"))
    timestamp: str = field(default_factory=_now_iso)
    candidate_atom_id: str = ""
    action: ReconciliationAction = ReconciliationAction.UNKNOWN
    target_atom_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    rationale: str = ""
    retrieval_evidence_summary: str = ""
    execution_status: AuditExecutionStatus = AuditExecutionStatus.EXECUTED
    executed_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    rollback_reason: Optional[str] = None
    rollback_by: Optional[str] = None
    rollback_of: Optional[str] = None
    pre_action_snapshots: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["action"] = self.action.value
        d["execution_status"] = self.execution_status.value
        return d

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["action"] = ReconciliationAction(d.get("action", "UNKNOWN"))
        d["execution_status"] = AuditExecutionStatus(d.get("execution_status", "EXECUTED"))
        return cls(**d)


class AuditLogStore:
    def __init__(self):
        self._logs: Dict[str, ReconciliationAuditLog] = {}
        self._atom_store: Dict[str, KnowledgeAtom] = {}

    def set_atom_store(self, store):
        self._atom_store = store

    def record(self, log):
        if log.execution_status == AuditExecutionStatus.EXECUTED and not log.executed_at:
            log.executed_at = _now_iso()
        self._logs[log.audit_id] = log
        return log.audit_id

    def get(self, audit_id):
        return self._logs.get(audit_id)

    def list_for_atom(self, atom_id):
        return [
            log for log in self._logs.values()
            if log.candidate_atom_id == atom_id or atom_id in log.target_atom_ids
        ]

    def rollback(self, audit_id, reason="", by="USER"):
        original = self._logs.get(audit_id)
        if not original:
            raise ValueError(f"Audit log {audit_id} not found")
        if original.execution_status != AuditExecutionStatus.EXECUTED:
            raise ValueError(f"Cannot roll back audit log with status {original.execution_status}")
        if original.action == ReconciliationAction.ROLLBACK:
            raise ValueError("Cannot roll back a rollback entry")
        for atom_id in [original.candidate_atom_id] + original.target_atom_ids:
            later_logs = [
                log for log in self._logs.values()
                if log.timestamp > original.timestamp
                and log.execution_status == AuditExecutionStatus.EXECUTED
                and (log.candidate_atom_id == atom_id or atom_id in log.target_atom_ids)
                and log.audit_id != audit_id
            ]
            if later_logs:
                dependent_ids = [log.audit_id for log in later_logs]
                raise ValueError(
                    f"Cannot roll back {audit_id}: dependent actions exist: {dependent_ids}. "
                    f"Roll back those first."
                )
        for atom_id, snapshot in original.pre_action_snapshots.items():
            if atom_id in self._atom_store:
                self._atom_store[atom_id] = KnowledgeAtom.from_dict(snapshot)
        original.execution_status = AuditExecutionStatus.ROLLED_BACK
        original.rolled_back_at = _now_iso()
        original.rollback_reason = reason
        original.rollback_by = by
        rollback_log = ReconciliationAuditLog(
            action=ReconciliationAction.ROLLBACK,
            candidate_atom_id=original.candidate_atom_id,
            target_atom_ids=original.target_atom_ids,
            confidence=1.0,
            rationale=f"Rollback of {audit_id}: {reason}",
            retrieval_evidence_summary=f"rollback_of={audit_id}",
            execution_status=AuditExecutionStatus.EXECUTED,
            rollback_of=audit_id,
            pre_action_snapshots={},
        )
        self._logs[rollback_log.audit_id] = rollback_log
        return rollback_log

    def get_all(self):
        return sorted(self._logs.values(), key=lambda x: x.timestamp)
