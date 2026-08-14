"""Synthetic-only P1 KnowledgeEpisode capture and governed reconciliation.

This adapter is intentionally narrow: it creates candidate-only LearningPackets
for public-safe synthetic passages and uses the existing W3 store/query boundary.
It does not discover sources, open a private store, or promote knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Mapping

from .canonical import content_hash, normalize_text
from .learning_packet import build_learning_packet, knowledge_atom_id
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, QueryPlan


TAXONOMY_VERSION = "knowledge-taxonomy-v1"
IDENTITY_VERSION = "knowledge-proposition-domain-v1"
EXTRACTION_BINDING_VERSION = "knowledge-extraction-binding-v1"
PUBLIC_SAFE_EXECUTION_CLASS = "PUBLIC_SAFE_SYNTHETIC"
_LEGACY_PUBLIC_SAFE_DOMAIN = "PUBLIC_SAFE_SYNTHETIC"
RECONCILIATION_ACTIONS = frozenset({
    "NEW", "DUPLICATE", "MERGE", "REFINE", "SUPPORT", "WEAKEN", "CONTRADICT",
    "SUPERSEDE", "REVOKE", "REVALIDATE", "RESOLVE_UNKNOWN", "UNKNOWN",
})
EPISTEMIC_ROLES = frozenset({
    "FACT_CLAIM", "SOURCE_CLAIM", "SOURCE_INTERPRETATION", "VALUE_JUDGMENT",
    "MECHANISM", "CONDITION", "COUNTEREXAMPLE", "METHOD", "OPEN_QUESTION",
    "USER_STANCE", "ASSISTANT_ANALYSIS", "MODEL_INFERENCE",
})
_SECRET = re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
_INERT_CONTROL_MARKERS = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|earlier)\s+instructions|disregard\s+(?:all\s+)?instructions|"
    r"system\s+prompt|developer\s+message|jailbreak|<\s*system\s*>|忽略(?:之前|先前|所有)?指令|系统提示|开发者消息)",
    re.IGNORECASE,
)
_ROLE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("fact:", "FACT_CLAIM"), ("事实:", "FACT_CLAIM"), ("事实：", "FACT_CLAIM"),
    ("source:", "SOURCE_CLAIM"), ("来源:", "SOURCE_CLAIM"), ("来源：", "SOURCE_CLAIM"),
    ("interpretation:", "SOURCE_INTERPRETATION"), ("author thinks:", "SOURCE_INTERPRETATION"), ("作者认为:", "SOURCE_INTERPRETATION"), ("作者认为：", "SOURCE_INTERPRETATION"),
    ("value:", "VALUE_JUDGMENT"), ("评价:", "VALUE_JUDGMENT"), ("评价：", "VALUE_JUDGMENT"),
    ("mechanism:", "MECHANISM"), ("机制:", "MECHANISM"), ("机制：", "MECHANISM"),
    ("condition:", "CONDITION"), ("条件:", "CONDITION"), ("条件：", "CONDITION"),
    ("counterexample:", "COUNTEREXAMPLE"), ("反例:", "COUNTEREXAMPLE"), ("反例：", "COUNTEREXAMPLE"),
    ("method:", "METHOD"), ("方法:", "METHOD"), ("方法：", "METHOD"),
    ("question:", "OPEN_QUESTION"), ("问题:", "OPEN_QUESTION"), ("问题：", "OPEN_QUESTION"),
    ("user stance:", "USER_STANCE"), ("用户立场:", "USER_STANCE"), ("用户立场：", "USER_STANCE"),
    ("assistant analysis:", "ASSISTANT_ANALYSIS"), ("助手分析:", "ASSISTANT_ANALYSIS"), ("助手分析：", "ASSISTANT_ANALYSIS"),
    ("model inference:", "MODEL_INFERENCE"), ("模型推断:", "MODEL_INFERENCE"), ("模型推断：", "MODEL_INFERENCE"),
)
_ACTION_EVIDENCE_BASIS = {
    "MERGE": "EQUIVALENCE_PROOF",
    "REFINE": "REFINEMENT_DELTA",
    "SUPPORT": "INDEPENDENT_SUPPORT",
    "WEAKEN": "WEAKENING_EVIDENCE",
    "CONTRADICT": "CONTRADICTION_EVIDENCE",
    "SUPERSEDE": "SUCCESSOR_BASIS",
    "REVOKE": "REVOCATION_BASIS",
    "REVALIDATE": "REVALIDATION_RECEIPT",
    "RESOLVE_UNKNOWN": "RESOLUTION_BASIS",
}
_ACTION_EVIDENCE_FIELDS = {
    "MERGE": "equivalence_key",
    "REFINE": "refinement_delta",
    "SUPPORT": "independent_source_id",
    "WEAKEN": "weakening_dimension",
    "CONTRADICT": "contradiction_axis",
    "SUPERSEDE": "successor_basis",
    "REVOKE": "revocation_basis",
    "REVALIDATE": "revalidation_receipt",
    "RESOLVE_UNKNOWN": "resolution_basis",
}
_NON_EQUIVALENCE_BASIS = "NON_EQUIVALENCE_PROOF"


@dataclass(frozen=True)
class KnowledgeEpisode:
    episode_id: str
    user_scope: str
    project_scope: str
    privacy_domain: str
    source_pointer: str
    source_text: str
    recorded_at: str
    safety_class: str = PUBLIC_SAFE_EXECUTION_CLASS
    available_at: str | None = None
    source_span: str = "full"
    provenance_quality: str = "DIRECT"

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value for value in (
            self.episode_id, self.user_scope, self.project_scope, self.source_pointer,
            self.source_text, self.recorded_at, self.source_span, self.provenance_quality,
        )):
            raise ValueError("knowledge_episode_identity_required")
        if self.safety_class != PUBLIC_SAFE_EXECUTION_CLASS or not _public_safe_domain(self.privacy_domain):
            raise ValueError("knowledge_episode_private_source_denied")
        if not self.source_pointer.startswith("synthetic://"):
            raise ValueError("knowledge_episode_source_pointer_denied")
        _instant(self.recorded_at)
        _instant(self.available_at or self.recorded_at)
        if _SECRET.search(self.source_text):
            raise ValueError("knowledge_episode_secret_denied")

    @property
    def source_hash(self) -> str:
        return content_hash({"normalized_source_text": normalize_text(self.source_text)})

    @property
    def manifest_id(self) -> str:
        return "knowledge-episode-" + content_hash({
            "episode_id": self.episode_id, "source_hash": self.source_hash,
            "recorded_at": _canonical_instant(self.recorded_at),
            "identity_domain_hash": identity_domain_hash(self.user_scope, self.project_scope, self.privacy_domain),
        })[:20]


@dataclass(frozen=True)
class KnowledgeCandidate:
    statement: str
    epistemic_role: str
    source_span: str


@dataclass(frozen=True)
class ReconciliationReceipt:
    status: str
    packet_ids: tuple[str, ...]
    atom_ids: tuple[str, ...]
    actions: tuple[tuple[str, str], ...]
    exact_scoped_recall_passed: bool
    semantic_recall_passed: bool
    foreign_domain_zero_recall: bool
    reconciliation_evidence: tuple[dict[str, Any], ...] = ()
    post_write_recall_mode: str = "PER_ATOM_NONEXACT_LEXICAL_OR_RELATION_ASSISTED"
    post_write_proofs: tuple[dict[str, str], ...] = ()
    nonexact_or_relation_recall_passed: bool = False
    candidate_authority_only: bool = True
    formal_project_global_write: str = "LOCKED"

    def public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "packet_ids": list(self.packet_ids),
            "atom_ids": list(self.atom_ids),
            "actions": [list(item) for item in self.actions],
            "exact_scoped_recall_passed": self.exact_scoped_recall_passed,
            "semantic_recall_passed": self.semantic_recall_passed,
            "foreign_domain_zero_recall": self.foreign_domain_zero_recall,
            "reconciliation_evidence": list(self.reconciliation_evidence),
            "post_write_recall_mode": self.post_write_recall_mode,
            "post_write_proofs": list(self.post_write_proofs),
            "nonexact_or_relation_recall_passed": self.nonexact_or_relation_recall_passed,
            "candidate_authority_only": self.candidate_authority_only,
            "formal_project_global_write": self.formal_project_global_write,
        }


def identity_domain_hash(user_scope: str, project_scope: str, privacy_domain: str) -> str:
    if not all(isinstance(value, str) and value for value in (user_scope, project_scope, privacy_domain)):
        raise ValueError("knowledge_identity_domain_required")
    return content_hash({"user_scope": user_scope, "project_scope": project_scope, "privacy_domain": privacy_domain})


def proposition_id(statement: str, epistemic_role: str, *, user_scope: str, project_scope: str, privacy_domain: str) -> str:
    if epistemic_role not in EPISTEMIC_ROLES:
        raise ValueError("knowledge_epistemic_role_denied")
    return "proposition-" + content_hash({
        "identity_version": IDENTITY_VERSION,
        "statement": normalize_text(statement),
        "epistemic_role": epistemic_role,
        "taxonomy_version": TAXONOMY_VERSION,
        "identity_domain_hash": identity_domain_hash(user_scope, project_scope, privacy_domain),
    })[:20]


def decompose_knowledge_passage(passage: str) -> tuple[KnowledgeCandidate, ...]:
    """Deterministic, faithful clause decomposition; it never upgrades a role."""
    if not normalize_text(passage):
        raise ValueError("knowledge_passage_required")
    if _SECRET.search(passage):
        raise ValueError("knowledge_secret_denied")
    candidates: list[KnowledgeCandidate] = []
    # Split before normalizing so ordinary newline-separated source passages
    # retain their material claim boundaries.
    for index, raw in enumerate(re.split(r"[\n;；]+", passage)):
        clause = normalize_text(raw)
        if not clause:
            continue
        role = "SOURCE_CLAIM"
        statement = clause
        lowered = clause.casefold()
        for prefix, candidate_role in _ROLE_PREFIXES:
            if lowered.startswith(prefix.casefold()):
                role = candidate_role
                statement = normalize_text(clause[len(prefix):])
                break
        if not statement:
            raise ValueError("knowledge_clause_empty_after_role")
        candidates.append(KnowledgeCandidate(statement=statement, epistemic_role=role, source_span=f"clause:{index}"))
    if not candidates:
        raise ValueError("knowledge_passage_no_candidates")
    return tuple(candidates)


def capture_knowledge(
    *, store: MemoryStore, episode: KnowledgeEpisode, passage: str | None = None,
    valid_from: str | None = None, valid_to: str | None = None,
    freshness_profile: str = "STRUCTURAL", reconciliation_directives: Mapping[str, Mapping[str, str]] | None = None,
    semantic_query: str | None = None,
) -> ReconciliationReceipt:
    """Preflight all candidates, atomically import them, then prove scoped recall."""
    extracted_passage = passage if passage is not None else episode.source_text
    extraction_binding = _bind_extracted_passage(episode, extracted_passage)
    candidates = decompose_knowledge_passage(extracted_passage)
    valid_from = _canonical_instant(valid_from or episode.available_at or episode.recorded_at)
    valid_to = _canonical_instant(valid_to) if valid_to is not None else None
    if valid_to is not None and _instant(valid_to) <= _instant(valid_from):
        raise ValueError("knowledge_valid_time_invalid")
    # This is a post-write proof contract, so reject an invalid proof query
    # before planning/importing any candidate.  A source-statement echo cannot
    # masquerade as semantic recall.
    semantic_query = normalize_text(semantic_query or "")
    candidate_statements = {normalize_text(item.statement) for item in candidates}
    if not semantic_query or semantic_query in candidate_statements:
        raise ValueError("knowledge_paraphrase_or_relation_query_required")
    directives = reconciliation_directives or {}
    assembler = ContextAssembler(store)
    packets: list[dict[str, Any]] = []
    actions: list[tuple[str, str]] = []
    action_evidence: list[dict[str, Any]] = []
    planned: list[tuple[KnowledgeCandidate, str]] = []
    # This loop is entirely pre-write.  Any invalid target/directive fails before
    # the one existing MemoryStore transaction is opened.
    for candidate in candidates:
        metadata = _knowledge_metadata(episode, candidate, valid_from, valid_to, freshness_profile, extraction_binding)
        atom_id = knowledge_atom_id(candidate.statement, metadata)
        directive = directives.get(candidate.statement)
        comparison_query = _comparison_query(candidate.statement, directive)
        preflight_plan = _plan_for(episode, comparison_query, valid_from, intent="CURRENT")
        comparison_bundle = assembler.assemble(preflight_plan)
        action, target_atom_id, evidence = _reconciliation_action(
            store, atom_id, metadata, comparison_bundle.atoms, directive,
        )
        actions.append((atom_id, action))
        action_evidence.append({**evidence, "candidate_atom_id": atom_id, "compared_atom_ids": [item["id"] for item in comparison_bundle.atoms]})
        if action == "UNKNOWN":
            continue
        if target_atom_id:
            _validate_target(store, target_atom_id, metadata)
        metadata["reconciliation_action"] = action
        metadata["reconciliation_evidence_basis"] = evidence["evidence_basis"]
        relations: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        if target_atom_id and action in {"SUPPORT", "WEAKEN", "CONTRADICT", "MERGE", "REFINE", "SUPERSEDE", "REVOKE", "REVALIDATE", "RESOLVE_UNKNOWN"}:
            relations.append({
                "source_atom_id": atom_id, "target_atom_id": target_atom_id,
                # Do not use the conversation-only `supersedes` transition in P1.
                "relation_type": "knowledge_" + action.casefold(), "target_existing": True,
                "context": "evidence_bound_reconciliation",
            })
            if action == "CONTRADICT":
                conflicts.append({"atom_id_a": atom_id, "atom_id_b": target_atom_id, "conflict_type": "DIRECT", "resolution_status": "UNRESOLVED"})
        packets.append(_packet_for(episode, candidate, metadata, relations=relations, conflicts=conflicts))
        planned.append((candidate, atom_id))
    if not packets:
        return ReconciliationReceipt("ABSTAIN_UNKNOWN", (), (), tuple(actions), False, False, True, tuple(action_evidence))
    results = store.import_learning_packets_atomic(packets)
    if any(result["status"] not in {"IMPORTED", "IDEMPOTENT_DUPLICATE"} for result in results):
        raise ValueError("knowledge_import_result_invalid")
    exact_ok = all(
        atom_id in _recall_ids(assembler, _plan_for(episode, candidate.statement, valid_from, intent="CURRENT"))
        for candidate, atom_id in planned
    )
    semantic_bundle = assembler.assemble(_plan_for(episode, semantic_query, valid_from, intent="CURRENT", relation_depth=1))
    semantic_ids = {atom["id"] for atom in semantic_bundle.atoms}
    linked = {
        endpoint for relation in semantic_bundle.relations
        for endpoint in (relation["source_atom_id"], relation["target_atom_id"])
    }
    proof_query_hash = content_hash({"query": semantic_query})
    post_write_proofs: list[dict[str, str]] = []
    for _, atom_id in planned:
        mode = (
            "NONEXACT_LEXICAL" if atom_id in semantic_ids else
            "RELATION_ASSISTED" if atom_id in linked else
            "NOT_PROVEN"
        )
        post_write_proofs.append({"atom_id": atom_id, "mode": mode, "query_hash": proof_query_hash})
    nonexact_or_relation_ok = all(item["mode"] != "NOT_PROVEN" for item in post_write_proofs)
    foreign_plan = QueryPlan(
        query_text=candidates[0].statement, scopes=(episode.project_scope,), user_scope=episode.user_scope + "-foreign",
        privacy_domains=(episode.privacy_domain,), valid_at=valid_from, atom_types=("knowledge_atom",), truth_states=("candidate",),
    )
    foreign_zero = not assembler.assemble(foreign_plan).atoms
    if not (exact_ok and nonexact_or_relation_ok and foreign_zero):
        raise ValueError("knowledge_post_write_scoped_recall_failed")
    return ReconciliationReceipt(
        "CAPTURED_CANDIDATE_ONLY", tuple(packet["packet_id"] for packet in packets), tuple(atom_id for _, atom_id in planned), tuple(actions),
        # P1 has only deterministic lexical/graph lookup, not an embedding or
        # semantic-paraphrase engine. Keep this false rather than overclaiming.
        exact_ok, False, foreign_zero, tuple(action_evidence),
        "PER_ATOM_NONEXACT_LEXICAL_OR_RELATION_ASSISTED", tuple(post_write_proofs), nonexact_or_relation_ok,
    )


def _reconciliation_action(
    store: MemoryStore, atom_id: str, metadata: dict[str, Any], compared_atoms: tuple[dict[str, Any], ...],
    directive: Mapping[str, str] | None,
) -> tuple[str, str | None, dict[str, str]]:
    compared_ids = {item["id"] for item in compared_atoms}
    if store.get_atom(atom_id) is not None:
        if atom_id not in compared_ids:
            return "UNKNOWN", None, _evidence("retrieval_missed_existing_lineage", "exact lineage was not admitted by bounded query")
        return "DUPLICATE", None, _evidence("exact_proposition_identity", "retrieval found the existing identical proposition")
    if directive is None:
        if compared_ids:
            return "UNKNOWN", None, _evidence(
                "related_lineage_requires_governed_decision",
                "bounded same-domain retrieval returned potentially related lineage without an evidence-bound classification",
            )
        return "NEW", None, _evidence("no_same_domain_match", "bounded same-domain retrieval returned no admitted lineage")
    action = str(directive.get("action", "UNKNOWN")).upper()
    target_atom_id = directive.get("target_atom_id")
    if action not in RECONCILIATION_ACTIONS:
        return "UNKNOWN", None, _evidence("invalid_action", "directive action is not governed")
    if action == "UNKNOWN":
        return "UNKNOWN", None, _evidence("directive_abstain", "no evidence-bound nontrivial action requested")
    if action == "NEW":
        if not compared_ids:
            return "NEW", None, _evidence("no_same_domain_match", "bounded same-domain retrieval returned no admitted lineage")
        if (
            directive.get("evidence_basis") != _NON_EQUIVALENCE_BASIS
            or not isinstance(directive.get("non_equivalence_reason"), str)
            or not normalize_text(directive["non_equivalence_reason"])
        ):
            return "UNKNOWN", None, _evidence(
                "non_equivalence_proof_required",
                "NEW with retrieved lineage requires governed non-equivalence evidence",
            )
        return "NEW", None, _evidence(_NON_EQUIVALENCE_BASIS, "retrieved lineage was explicitly classified non-equivalent")
    if action == "DUPLICATE":
        return "UNKNOWN", None, _evidence("duplicate_without_existing_lineage", "duplicate requires retrieved exact existing identity")
    if not isinstance(target_atom_id, str) or not target_atom_id or target_atom_id not in compared_ids:
        return "UNKNOWN", None, _evidence("retrieved_target_required", "target must be returned by the bounded comparison query")
    required_basis = _ACTION_EVIDENCE_BASIS[action]
    if directive.get("evidence_basis") != required_basis:
        return "UNKNOWN", None, _evidence("action_evidence_basis_missing", "action-specific evidence basis did not match")
    required_field = _ACTION_EVIDENCE_FIELDS[action]
    if not isinstance(directive.get(required_field), str) or not normalize_text(directive[required_field]):
        return "UNKNOWN", None, _evidence(
            "action_precondition_missing",
            "action-specific precondition " + required_field + " is required",
        )
    if not isinstance(directive.get("comparison_query"), str) or not normalize_text(directive["comparison_query"]):
        return "UNKNOWN", None, _evidence("comparison_query_required", "nontrivial action requires an evidence-bearing comparison query")
    target = store.get_atom(target_atom_id)
    if action == "RESOLVE_UNKNOWN" and (target or {}).get("knowledge_status") != "unknown":
        return "UNKNOWN", None, _evidence("unknown_target_required", "RESOLVE_UNKNOWN requires an unknown target")
    if action == "SUPERSEDE":
        target_meta = (target or {}).get("memory_metadata", {}).get("knowledge", {})
        if not isinstance(target_meta, dict) or _instant(metadata["valid_from"]) <= _instant(target_meta["valid_from"]):
            return "UNKNOWN", None, _evidence("successor_time_required", "SUPERSEDE requires a later candidate instant")
    return action, target_atom_id, _evidence(required_basis, "retrieved target and action-specific evidence preconditions passed")


def _validate_target(store: MemoryStore, target_atom_id: str, metadata: dict[str, Any]) -> None:
    target = store.get_atom(target_atom_id)
    target_knowledge = (target or {}).get("memory_metadata", {}).get("knowledge")
    if not isinstance(target_knowledge, dict):
        raise ValueError("knowledge_reconciliation_target_missing")
    for field in ("user_scope", "project_scope", "privacy_domain", "identity_domain_hash"):
        if target_knowledge.get(field) != metadata.get(field):
            raise ValueError("knowledge_reconciliation_target_scope_denied")
    if not store.provenance_for_atom(target_atom_id):
        raise ValueError("knowledge_reconciliation_target_provenance_missing")


def _knowledge_metadata(
    episode: KnowledgeEpisode, candidate: KnowledgeCandidate, valid_from: str, valid_to: str | None, freshness_profile: str,
    extraction_binding: dict[str, Any],
) -> dict[str, Any]:
    domain_hash = identity_domain_hash(episode.user_scope, episode.project_scope, episode.privacy_domain)
    manifest_id = episode.manifest_id
    source_episode = {
        "episode_manifest_id": manifest_id, "episode_id": episode.episode_id,
        "source_pointer_hash": content_hash(episode.source_pointer), "recorded_at": _canonical_instant(episode.recorded_at),
        "available_at": _canonical_instant(episode.available_at or episode.recorded_at), "source_span": candidate.source_span,
        "provenance_quality": episode.provenance_quality,
        "source_trust": _source_trust(episode.source_text),
        "extraction_binding": extraction_binding,
    }
    return {
        "schema_version": "knowledge-atom-v1", "episode_manifest_ids": [manifest_id], "source_episodes": [source_episode],
        "user_scope": episode.user_scope, "project_scope": episode.project_scope, "privacy_domain": episode.privacy_domain,
        "safety_class": episode.safety_class,
        "identity_domain_hash": domain_hash,
        "aggregate_equivalence_key": "aggregate-" + content_hash({
            "statement": normalize_text(candidate.statement), "epistemic_role": candidate.epistemic_role,
            "taxonomy_version": TAXONOMY_VERSION, "user_scope": episode.user_scope, "project_scope": episode.project_scope,
        })[:20],
        "proposition_id": proposition_id(candidate.statement, candidate.epistemic_role, user_scope=episode.user_scope, project_scope=episode.project_scope, privacy_domain=episode.privacy_domain),
        "epistemic_role": candidate.epistemic_role, "taxonomy_version": TAXONOMY_VERSION,
        "valid_from": valid_from, "valid_to": valid_to, "recorded_at": _canonical_instant(episode.recorded_at),
        "provenance_quality": episode.provenance_quality, "freshness_profile": freshness_profile,
        "source_trust": _source_trust(episode.source_text),
    }


def _packet_for(episode: KnowledgeEpisode, candidate: KnowledgeCandidate, metadata: dict[str, Any], *, relations: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    atom = {
        "id": knowledge_atom_id(candidate.statement, metadata), "statement": candidate.statement, "atom_type": "knowledge_atom",
        "scope": episode.project_scope, "confidence": 0.5, "source_refs": ["knowledge://" + episode.manifest_id],
        "knowledge_status": "candidate", "transport_visibility": "PUBLIC_SAFE_METADATA_ONLY", "memory_metadata": {"knowledge": metadata},
    }
    validation = {key: value for key, value in metadata.items() if key != "reconciliation_action"}
    validation["source_pointer_hash"] = content_hash(episode.source_pointer)
    return build_learning_packet(
        source_manifest_ids=metadata["episode_manifest_ids"], source_hash=episode.source_hash,
        validation_report=validation, evidence_refs=atom["source_refs"], atoms=[atom], relations=relations, conflicts=conflicts,
    )


def _plan_for(episode: KnowledgeEpisode, query_text: str, valid_at: str, *, intent: str, relation_depth: int = 0) -> QueryPlan:
    return QueryPlan(
        query_text=query_text, scopes=(episode.project_scope,), user_scope=episode.user_scope,
        privacy_domains=(episode.privacy_domain,), valid_at=valid_at, atom_types=("knowledge_atom",),
        truth_states=("candidate", "approved", "conflict", "unknown", "superseded") if intent == "HISTORICAL" else ("candidate", "approved", "conflict", "unknown"),
        intent=intent, relation_depth=relation_depth,
    )


def _recall_ids(assembler: ContextAssembler, plan: QueryPlan) -> set[str]:
    return {atom["id"] for atom in assembler.assemble(plan).atoms}


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("knowledge_time_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _canonical_instant(value: str) -> str:
    return _instant(value).isoformat().replace("+00:00", "Z")


def _comparison_query(statement: str, directive: Mapping[str, str] | None) -> str:
    extra = directive.get("comparison_query", "") if directive else ""
    return normalize_text(statement + " " + str(extra))


def _evidence(basis: str, reason: str) -> dict[str, str]:
    return {"evidence_basis": basis, "action_reason": reason}


def _source_trust(source_text: str) -> str:
    return "UNTRUSTED_INERT" if _INERT_CONTROL_MARKERS.search(source_text) else "SOURCE_DATA"


def _bind_extracted_passage(episode: KnowledgeEpisode, passage: str) -> dict[str, Any]:
    """Create a privacy-minimized proof that extraction is from this source."""
    normalized_source = normalize_text(episode.source_text)
    normalized_passage = normalize_text(passage)
    if not normalized_passage:
        raise ValueError("knowledge_passage_required")
    start = normalized_source.find(normalized_passage)
    if start < 0:
        # This is deliberately before decomposition, packet construction and
        # store import: arbitrary caller text cannot inherit episode lineage.
        raise ValueError("knowledge_passage_not_derived_from_source")
    return {
        "schema_version": EXTRACTION_BINDING_VERSION,
        "full_source_hash": episode.source_hash,
        "extracted_passage_hash": content_hash({"normalized_extracted_passage": normalized_passage}),
        "normalized_start": start,
        "normalized_end": start + len(normalized_passage),
    }


def _public_safe_domain(value: str) -> bool:
    return value == _LEGACY_PUBLIC_SAFE_DOMAIN or bool(re.fullmatch(r"synthetic-[a-z0-9][a-z0-9-]{0,63}", value))
