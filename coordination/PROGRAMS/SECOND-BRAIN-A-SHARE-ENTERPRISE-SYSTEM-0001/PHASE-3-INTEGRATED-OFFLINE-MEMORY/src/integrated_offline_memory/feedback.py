"""Candidate-only feedback, correction, revocation, and learning workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import content_hash
from .learning_packet import build_learning_packet
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, QueryPlan
from .security import assert_no_credential_value


FEEDBACK_TYPES = {
    "DUPLICATE",
    "SUPPLEMENT",
    "REFINEMENT",
    "CONFLICT",
    "CORRECTION",
    "SUPERSEDES",
    "UNKNOWN_RESOLVED",
}
TARGET_REQUIRED = {"DUPLICATE", "REFINEMENT", "CONFLICT", "CORRECTION", "SUPERSEDES"}
STATEMENT_REQUIRED = FEEDBACK_TYPES - {"DUPLICATE"}


@dataclass(frozen=True)
class FeedbackRecord:
    feedback_type: str
    statement: str = ""
    scope: str = "user_feedback"
    target_atom_ids: tuple[str, ...] = ()
    target_unknown_ids: tuple[str, ...] = ()
    source_manifest_ids: tuple[str, ...] = ("feedback-local-user",)
    evidence_refs: tuple[str, ...] = ("feedback:user-authorized-local",)
    confidence: float = 0.6
    verification_status: str = "USER_FEEDBACK_UNVERIFIED"
    evidence_quality: str = "USER_PROVIDED_CANDIDATE"
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if self.schema_version.split(".", 1)[0] != "1":
            raise ValueError("feedback_schema_major_unsupported")
        if self.feedback_type not in FEEDBACK_TYPES:
            raise ValueError("feedback_type_invalid")
        if self.feedback_type in STATEMENT_REQUIRED and not self.statement.strip():
            raise ValueError("feedback_statement_required")
        if self.feedback_type in TARGET_REQUIRED and not self.target_atom_ids:
            raise ValueError("feedback_atom_target_required")
        if self.feedback_type == "UNKNOWN_RESOLVED" and not self.target_unknown_ids:
            raise ValueError("feedback_unknown_target_required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("feedback_confidence_invalid")
        assert_no_credential_value(asdict(self))

    @property
    def feedback_id(self) -> str:
        self.validate()
        return "fb-" + content_hash(asdict(self))[:20]


@dataclass(frozen=True)
class FeedbackLearningPacket:
    schema_version: str
    feedback_id: str
    feedback_type: str
    packet: dict[str, Any]
    primary_atom_id: str
    expected_actions: tuple[str, ...]
    impact_query_plan: dict[str, Any]
    before_atom_ids: tuple[str, ...]
    preview_hash: str
    status: str = "candidate"
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["expected_actions"] = list(self.expected_actions)
        payload["before_atom_ids"] = list(self.before_atom_ids)
        return payload


@dataclass(frozen=True)
class FeedbackCommitReceipt:
    schema_version: str
    feedback_id: str
    feedback_type: str
    preview_hash: str
    packet_id: str
    import_status: str
    revision_id: str
    before_atom_ids: tuple[str, ...]
    after_atom_ids: tuple[str, ...]
    added_atom_ids: tuple[str, ...]
    removed_atom_ids: tuple[str, ...]
    resolved_unknown_ids: tuple[str, ...]
    status: str = "COMMITTED_CANDIDATE"
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for name in (
            "before_atom_ids", "after_atom_ids", "added_atom_ids",
            "removed_atom_ids", "resolved_unknown_ids",
        ):
            payload[name] = list(payload[name])
        return payload

    def public_receipt(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(frozen=True)
class RevocationReceipt:
    schema_version: str
    revocation_id: str
    manifest_id: str
    reason_code: str
    previous_status: str
    current_status: str
    changed: bool
    removed_current_atom_ids: tuple[str, ...]
    historical_atom_ids: tuple[str, ...]
    status: str = "REVOKED"
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["removed_current_atom_ids"] = list(self.removed_current_atom_ids)
        payload["historical_atom_ids"] = list(self.historical_atom_ids)
        return payload


class FeedbackProcessor:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.assembler = ContextAssembler(store)

    def preview(self, record: FeedbackRecord, query_plan: QueryPlan | None = None) -> FeedbackLearningPacket:
        record.validate()
        targets = [self._required_atom(atom_id) for atom_id in record.target_atom_ids]
        for unknown_id in record.target_unknown_ids:
            if self.store.get_unknown(unknown_id) is None:
                raise ValueError("feedback_unknown_target_missing")
        statement = record.statement.strip()
        if record.feedback_type == "DUPLICATE":
            statement = targets[0]["canonical_statement"]
        aliases = tuple(atom["canonical_statement"] for atom in targets)
        plan = query_plan or QueryPlan(
            query_text=statement,
            query_aliases=aliases,
            include_conflicts=True,
            include_unknowns=True,
            relation_depth=1,
            budget=100,
        )
        before = self.assembler.assemble(plan)
        packet, actions = self._build_packet(record, statement, targets)
        core = {
            "schema_version": "1.0.0",
            "feedback_id": record.feedback_id,
            "feedback_type": record.feedback_type,
            "packet": packet,
            "primary_atom_id": _primary_atom_id(record.feedback_type, packet, targets),
            "expected_actions": actions,
            "impact_query_plan": plan.to_dict(),
            "before_atom_ids": [atom["id"] for atom in before.atoms],
            "status": "candidate",
            "authority_write": False,
            "no_trade_gate": True,
        }
        preview_hash = content_hash(core)
        result = FeedbackLearningPacket(
            schema_version="1.0.0",
            feedback_id=record.feedback_id,
            feedback_type=record.feedback_type,
            packet=packet,
            primary_atom_id=core["primary_atom_id"],
            expected_actions=tuple(actions),
            impact_query_plan=plan.to_dict(),
            before_atom_ids=tuple(core["before_atom_ids"]),
            preview_hash=preview_hash,
        )
        assert_no_credential_value(result.to_dict())
        return result

    def commit(self, preview: FeedbackLearningPacket) -> FeedbackCommitReceipt:
        assert_no_credential_value(preview.to_dict())
        if preview.status != "candidate" or preview.authority_write or not preview.no_trade_gate:
            raise ValueError("feedback_candidate_boundary_required")
        if preview.preview_hash != _preview_hash(preview):
            raise ValueError("feedback_preview_hash_mismatch")
        existing = self.store.get_feedback_receipt(preview.feedback_id)
        if existing:
            return _receipt_from_store(existing)

        import_result = self.store.import_learning_packet(preview.packet)
        resolution_atom_id = preview.primary_atom_id
        resolved: list[str] = []
        for action in preview.expected_actions:
            if action.startswith("RESOLVE_UNKNOWN:"):
                unknown_id = action.split(":", 1)[1]
                self.store.resolve_unknown(unknown_id, resolution_atom_id)
                resolved.append(unknown_id)
        plan = QueryPlan.from_dict(preview.impact_query_plan)
        after = self.assembler.assemble(plan)
        before_ids = tuple(preview.before_atom_ids)
        after_ids = tuple(atom["id"] for atom in after.atoms)
        receipt = FeedbackCommitReceipt(
            schema_version="1.0.0",
            feedback_id=preview.feedback_id,
            feedback_type=preview.feedback_type,
            preview_hash=preview.preview_hash,
            packet_id=preview.packet["packet_id"],
            import_status=import_result["status"],
            revision_id=import_result["revision_id"],
            before_atom_ids=before_ids,
            after_atom_ids=after_ids,
            added_atom_ids=tuple(sorted(set(after_ids) - set(before_ids))),
            removed_atom_ids=tuple(sorted(set(before_ids) - set(after_ids))),
            resolved_unknown_ids=tuple(sorted(resolved)),
        )
        self.store.record_feedback_receipt(receipt.public_receipt())
        return receipt

    def revoke_source(self, manifest_id: str, reason_code: str) -> RevocationReceipt:
        current_plan = QueryPlan(query_text="", source_manifest_ids=(manifest_id,), budget=1000)
        before = self.assembler.assemble(current_plan)
        result = self.store.revoke_knowledge_source(manifest_id, reason_code)
        after = self.assembler.assemble(current_plan)
        history = self.assembler.assemble(QueryPlan(
            query_text="",
            source_manifest_ids=(manifest_id,),
            include_revoked_sources=True,
            history_mode="HISTORY",
            budget=1000,
        ))
        removed = tuple(sorted({atom["id"] for atom in before.atoms} - {atom["id"] for atom in after.atoms}))
        historical = tuple(atom["id"] for atom in history.atoms)
        core = {
            "manifest_id": manifest_id,
            "reason_code": reason_code,
            "previous_status": result["previous_status"],
            "current_status": result["status"],
            "changed": result["changed"],
            "removed_current_atom_ids": removed,
            "historical_atom_ids": historical,
        }
        receipt = RevocationReceipt(
            schema_version="1.0.0",
            revocation_id="revocation-" + content_hash(core)[:20],
            manifest_id=manifest_id,
            reason_code=reason_code,
            previous_status=result["previous_status"],
            current_status=result["status"],
            changed=result["changed"],
            removed_current_atom_ids=removed,
            historical_atom_ids=historical,
        )
        assert_no_credential_value(receipt.to_dict())
        return receipt

    def _required_atom(self, atom_id: str) -> dict[str, Any]:
        atom = self.store.get_atom(atom_id)
        if atom is None:
            raise ValueError("feedback_atom_target_missing")
        return atom

    def _build_packet(
        self,
        record: FeedbackRecord,
        statement: str,
        targets: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], list[str]]:
        if record.feedback_type != "DUPLICATE" and any(
            target["canonical_statement"] == statement and target["scope"] == record.scope
            for target in targets
        ):
            raise ValueError("feedback_new_atom_duplicates_target")
        feedback_ref = "feedback:" + record.feedback_id
        evidence_refs = sorted(set(record.evidence_refs + (feedback_ref,)))
        atoms: list[dict[str, Any]] = []
        if record.feedback_type == "DUPLICATE":
            new_atom_id = targets[0]["id"]
        else:
            atoms.append({
                "atom_type": "feedback_observation",
                "statement": statement,
                "scope": record.scope,
                "confidence": record.confidence,
                "verification_status": record.verification_status,
                "evidence_quality": record.evidence_quality,
                "knowledge_status": "conflict" if record.feedback_type in {"CONFLICT", "CORRECTION"} else "candidate",
                "source_refs": evidence_refs + ["manifest:" + item for item in record.source_manifest_ids],
            })
            probe = build_learning_packet(
                source_manifest_ids=list(record.source_manifest_ids),
                source_hash=content_hash(asdict(record)),
                validation_report={"feedback_id": record.feedback_id, "feedback_type": record.feedback_type},
                evidence_refs=evidence_refs,
                atoms=atoms,
            )
            new_atom_id = probe["atoms"][0]["id"]
        atoms.extend(_atom_to_spec(target) for target in targets)

        relations: list[dict[str, Any]] = []
        relation_types = {
            "SUPPLEMENT": "supplements",
            "REFINEMENT": "refines",
            "CORRECTION": "corrects",
            "SUPERSEDES": "supersedes",
        }
        relation_type = relation_types.get(record.feedback_type)
        if relation_type:
            relations.extend({
                "source_atom_id": new_atom_id,
                "target_atom_id": target["id"],
                "relation_type": relation_type,
                "context": "candidate_user_feedback",
                "knowledge_status": "candidate",
            } for target in targets)
        conflicts = []
        if record.feedback_type in {"CONFLICT", "CORRECTION"}:
            conflicts = [{
                "atom_id_a": target["id"],
                "atom_id_b": new_atom_id,
                "conflict_type": record.feedback_type,
                "resolution_status": "UNRESOLVED",
            } for target in targets]
        actions = [record.feedback_type]
        actions.extend("RESOLVE_UNKNOWN:" + unknown_id for unknown_id in record.target_unknown_ids)
        packet = build_learning_packet(
            source_manifest_ids=list(record.source_manifest_ids),
            source_hash=content_hash(asdict(record)),
            validation_report={
                "feedback_id": record.feedback_id,
                "feedback_type": record.feedback_type,
                "status": "CANDIDATE_ONLY",
                "research_only": True,
                "no_trade_gate": True,
                "authority_write": False,
            },
            evidence_refs=evidence_refs,
            atoms=atoms,
            relations=relations,
            conflicts=conflicts,
            base_knowledge_version=self.store.latest_revision_id(),
        )
        return packet, actions


def _atom_to_spec(atom: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": atom["id"],
        "atom_type": atom["atom_type"],
        "statement": atom["canonical_statement"],
        "scope": atom["scope"],
        "confidence": atom["confidence"],
        "verification_status": atom["verification_status"],
        "evidence_quality": atom["evidence_quality"],
        "knowledge_status": atom["knowledge_status"],
        "gpt_access": atom["gpt_access"],
        "transport_visibility": atom["transport_visibility"],
        "source_refs": atom["source_refs"],
        "premises": atom["premises"],
        "exceptions": atom["exceptions"],
        "failure_conditions": atom["failure_conditions"],
    }


def _preview_hash(preview: FeedbackLearningPacket) -> str:
    payload = preview.to_dict()
    payload.pop("preview_hash")
    return content_hash(payload)


def _primary_atom_id(
    feedback_type: str,
    packet: dict[str, Any],
    targets: list[dict[str, Any]],
) -> str:
    if feedback_type == "DUPLICATE":
        return targets[0]["id"]
    target_ids = {target["id"] for target in targets}
    candidates = [atom["id"] for atom in packet["atoms"] if atom["id"] not in target_ids]
    if len(candidates) != 1:
        raise ValueError("feedback_primary_atom_ambiguous")
    return candidates[0]


def _receipt_from_store(value: dict[str, Any]) -> FeedbackCommitReceipt:
    return FeedbackCommitReceipt(
        schema_version="1.0.0",
        feedback_id=value["feedback_id"],
        feedback_type=value["feedback_type"],
        preview_hash=value["preview_hash"],
        packet_id=value["packet_id"],
        import_status=value["import_status"],
        revision_id=value["revision_id"],
        before_atom_ids=tuple(value["before_atom_ids"]),
        after_atom_ids=tuple(value["after_atom_ids"]),
        added_atom_ids=tuple(value["added_atom_ids"]),
        removed_atom_ids=tuple(value["removed_atom_ids"]),
        resolved_unknown_ids=tuple(value.get("resolved_unknown_ids", [])),
    )
