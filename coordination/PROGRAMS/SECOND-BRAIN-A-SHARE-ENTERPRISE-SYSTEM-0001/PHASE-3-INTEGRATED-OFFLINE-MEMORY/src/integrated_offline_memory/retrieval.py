"""Structured multilingual retrieval and deterministic ContextBundle assembly."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re
from typing import Any

from .canonical import content_hash
from .memory_store import ALLOWED_TRUTH_STATES, DENIED_TRUTH_STATES, MemoryStore


@dataclass(frozen=True)
class QueryPlan:
    query_text: str = ""
    scopes: tuple[str, ...] = ()
    atom_types: tuple[str, ...] = ()
    truth_states: tuple[str, ...] = ("candidate", "approved", "conflict", "unknown")
    min_confidence: float = 0.0
    time_start: str | None = None
    time_end: str | None = None
    include_conflicts: bool = True
    include_unknowns: bool = True
    relation_depth: int = 0
    budget: int = 50
    intent: str = "CURRENT"
    user_scope: str | None = None
    privacy_domains: tuple[str, ...] = ()
    privacy_aggregate_mode: str = "ISOLATED"
    valid_at: str | None = None
    schema_version: str = "1.0.0"

    def validate(self) -> None:
        if self.schema_version.split(".", 1)[0] != "1":
            raise ValueError("query_plan_schema_major_unsupported")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("query_plan_confidence_invalid")
        if not 1 <= self.budget <= 1000:
            raise ValueError("query_plan_budget_invalid")
        if not 0 <= self.relation_depth <= 4:
            raise ValueError("query_plan_relation_depth_invalid")
        states = set(self.truth_states)
        if states.intersection(DENIED_TRUTH_STATES) or not states.issubset(ALLOWED_TRUTH_STATES):
            raise ValueError("query_plan_truth_state_denied_or_unknown")
        if self.intent not in {"CURRENT", "HISTORICAL"}:
            raise ValueError("query_plan_intent_invalid")
        # Legacy 1.0 payloads could explicitly include superseded.  Preserve
        # their ability to load, but ContextAssembler still excludes that state
        # for CURRENT admission below.
        if self.intent == "CURRENT" and "superseded" in states and self.schema_version != "1.0.0":
            raise ValueError("query_plan_current_superseded_denied")
        if self.intent == "HISTORICAL" and not self.valid_at:
            raise ValueError("query_plan_historical_valid_time_required")
        if self.valid_at:
            _parse_instant(self.valid_at)
        if self.user_scope is not None and not self.user_scope:
            raise ValueError("query_plan_user_scope_invalid")
        if any(not isinstance(item, str) or not item for item in self.privacy_domains):
            raise ValueError("query_plan_privacy_domains_invalid")
        if self.privacy_aggregate_mode not in {"ISOLATED", "SYNTHETIC_AGGREGATE_NO_VOTE"}:
            raise ValueError("query_plan_privacy_aggregate_mode_invalid")
        if len(self.privacy_domains) > 1 and self.privacy_aggregate_mode != "SYNTHETIC_AGGREGATE_NO_VOTE":
            raise ValueError("query_plan_multi_privacy_requires_explicit_aggregate")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        for field_name in ("scopes", "atom_types", "truth_states", "privacy_domains"):
            payload[field_name] = list(payload[field_name])
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QueryPlan":
        unknown = set(payload) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError("query_plan_unknown_field")
        data = dict(payload)
        for field_name in ("scopes", "atom_types", "truth_states", "privacy_domains"):
            if field_name in data:
                data[field_name] = tuple(data[field_name])
        result = cls(**data)
        result.validate()
        return result

    @property
    def plan_hash(self) -> str:
        return content_hash(self.to_dict())


@dataclass(frozen=True)
class ContextBundle:
    schema_version: str
    query_id: str
    query_plan_hash: str
    knowledge_version: str
    atoms: tuple[dict[str, Any], ...]
    relations: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    unknowns: tuple[dict[str, Any], ...]
    source_lineage: tuple[str, ...]
    omitted_due_to_budget: tuple[str, ...]
    context_budget: int
    semantic_access_state: str
    trust_gate: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[dict[str, Any], ...] = ()
    authority_write: bool = False
    no_trade_gate: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for field_name in ("atoms", "relations", "conflicts", "unknowns", "source_lineage", "omitted_due_to_budget", "provenance"):
            payload[field_name] = list(payload[field_name])
        return payload


@dataclass(frozen=True)
class GPTSecondBrainContextBundle:
    """A compatible, public-safe projection for GPT consumers.

    ``ContextBundle`` remains the stable W3 retrieval return value.  This
    versioned view deliberately carries only already-admitted evidence and
    redacted provenance, so it cannot become a side channel around admission.
    """

    schema_version: str
    request: dict[str, Any]
    admission: dict[str, Any]
    evidence: dict[str, tuple[dict[str, Any], ...]]
    context: dict[str, Any]
    provenance: dict[str, tuple[dict[str, Any], ...]]
    ranking: dict[str, Any]
    trust_gate: dict[str, Any]
    authority: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for section in ("evidence", "context", "provenance"):
            payload[section] = {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in payload[section].items()
            }
        return payload


@dataclass(frozen=True)
class CandidateAdmissionDecision:
    """A stable, public-safe outcome for one pre-ranking candidate check.

    Reason codes deliberately describe only a policy class.  They never carry
    an atom identifier, source pointer, source body, or metadata value.
    """

    admitted: bool
    reason: str


@dataclass
class _CandidateSet:
    """Internal candidate collection shared by every P2.1 retrieval channel."""

    scores: dict[str, float] = field(default_factory=dict)
    score_components: dict[str, dict[str, float]] = field(default_factory=dict)
    supplemental_ids: set[str] = field(default_factory=set)
    channels: dict[str, set[str]] = field(default_factory=dict)
    rejected_counts: dict[str, int] = field(default_factory=dict)
    public_accounted_atom_ids: set[str] = field(default_factory=set)

    def consider(
        self, atom: dict[str, Any], score: float | None, decision: CandidateAdmissionDecision, *, caller_observable: bool,
        channel: str,
    ) -> bool:
        """Record only facts the caller is permitted to observe.

        A non-observable candidate is deliberately identical to no candidate in
        the public report.  Its decision still remains internal to the
        assembler so candidate admission semantics are not weakened.
        """

        if not decision.admitted:
            atom_id = atom["id"]
            if caller_observable and atom_id not in self.public_accounted_atom_ids:
                self.rejected_counts[decision.reason] = self.rejected_counts.get(decision.reason, 0) + 1
                self.public_accounted_atom_ids.add(atom_id)
            return False
        atom_id = atom["id"]
        self.channels.setdefault(atom_id, set()).add(channel)
        if score is None:
            # Temporal and provenance discovery are authority migrations, not a
            # new business ranking policy.  Preserve their deterministic
            # compatibility placement without minting an arbitrary score.
            if atom_id not in self.scores:
                self.supplemental_ids.add(atom_id)
            return True
        self.scores[atom_id] = max(self.scores.get(atom_id, score), score)
        self.supplemental_ids.discard(atom_id)
        components = self.score_components.setdefault(atom_id, {})
        components[channel] = max(components.get(channel, score), score)
        return True

    @property
    def atom_ids(self) -> set[str]:
        return set(self.scores).union(self.supplemental_ids)

    def public_report(self) -> dict[str, Any]:
        """Return counts only, in deterministic order, for public-safe audit."""

        return {
            "admitted_count": len(self.atom_ids),
            "rejected_counts": dict(sorted(self.rejected_counts.items())),
        }


class ContextAssembler:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self._last_admission_report: dict[str, Any] = {
            "admitted_count": 0,
            "rejected_counts": {},
        }
        self._last_score_components: dict[str, dict[str, float]] = {}
        self._last_candidate_channels: dict[str, tuple[str, ...]] = {}

    @property
    def last_admission_report(self) -> dict[str, Any]:
        """Counts-only report for the most recent assembly.

        This is intentionally outside ``ContextBundle`` in P2.1, preserving
        the existing bundle schema and semantic hash while exposing the new
        boundary for callers and tests.  The returned structure is copied so a
        caller cannot mutate assembler state.
        """

        return {
            "admitted_count": self._last_admission_report["admitted_count"],
            "rejected_counts": dict(self._last_admission_report["rejected_counts"]),
        }

    @property
    def last_candidate_channels(self) -> dict[str, tuple[str, ...]]:
        """Return deterministic assembler-side channel attribution only."""

        return {atom_id: tuple(channels) for atom_id, channels in self._last_candidate_channels.items()}

    def assemble(self, plan: QueryPlan) -> ContextBundle:
        plan.validate()
        score_map = self.store.search_term_scores(plan.query_text)
        candidate_set = _CandidateSet()
        for atom_id, score in score_map.items():
            atom = self.store.get_atom(atom_id)
            if atom is not None:
                self._consider_candidate(candidate_set, atom, score, plan, channel="lexical")

        temporal_dates = set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", plan.query_text))
        if temporal_dates:
            # The lexical index intentionally omits metadata-only event dates.
            # This exact date channel is active only when the caller supplied a
            # normalized temporal date, and every match goes through the same
            # observability and admission boundary before it can affect recall.
            for atom in self.store.all_atoms():
                palace = atom.get("memory_metadata", {}).get("conversation", {}).get("memory_palace", {})
                resolved_start = palace.get("temporal", {}).get("resolved_start", "")
                if isinstance(resolved_start, str) and resolved_start[:10] in temporal_dates:
                    self._consider_candidate(candidate_set, atom, None, plan, channel="temporal")

        frontier = candidate_set.atom_ids
        visited = set(frontier)
        for depth in range(plan.relation_depth):
            related = self.store.related_atom_ids(frontier) - visited
            next_frontier: set[str] = set()
            for atom_id in related:
                atom = self.store.get_atom(atom_id)
                if atom is not None and self._consider_candidate(
                    candidate_set, atom, 0.5 / (depth + 1), plan, channel="relation",
                ):
                    next_frontier.add(atom_id)
            visited.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break

        # A shared source manifest is an admissible provenance edge.  It is
        # resolved only from already admitted candidate lineage and never adds
        # source identities or rejected candidates to public output.
        admitted_sources = {
            source for atom_id in candidate_set.atom_ids
            for atom in (self.store.get_atom(atom_id),) if atom
            for source in atom.get("source_refs", [])
        }
        if admitted_sources:
            for atom in self.store.all_atoms():
                if admitted_sources.intersection(atom.get("source_refs", [])):
                    self._consider_candidate(candidate_set, atom, None, plan, channel="provenance")

        self._last_admission_report = candidate_set.public_report()
        self._last_score_components = {
            atom_id: dict(sorted(components.items()))
            for atom_id, components in candidate_set.score_components.items()
        }
        ranked_ids = sorted(candidate_set.scores, key=lambda atom_id: (-candidate_set.scores[atom_id], atom_id))
        ranked_ids.extend(sorted(candidate_set.supplemental_ids.difference(candidate_set.scores)))
        selected_ids = ranked_ids[:plan.budget]
        omitted = ranked_ids[plan.budget:]
        self._last_candidate_channels = {
            atom_id: tuple(sorted(channels)) for atom_id, channels in candidate_set.channels.items()
        }
        atoms = tuple(self.store.get_atom(atom_id) for atom_id in selected_ids)
        selected_set = set(selected_ids)
        relations = self._safe_relations(plan, selected_set)
        conflicts = self._safe_conflicts(plan, selected_set) if plan.include_conflicts else ()
        unknowns = self._safe_unknowns(plan, selected_set, include_all_open=not bool(plan.query_text)) if plan.include_unknowns else ()
        source_lineage = tuple(sorted({source for atom in atoms if atom for source in atom.get("source_refs", [])}))
        provenance = tuple(item for atom in atoms if atom for item in self.store.provenance_for_atom(atom["id"]))
        gate = self._trust_gate(plan, atoms)
        return ContextBundle(
            schema_version="1.0.0",
            query_id="query-" + plan.plan_hash[:16],
            query_plan_hash=plan.plan_hash,
            knowledge_version=self.store.latest_revision_id(),
            atoms=tuple(atom for atom in atoms if atom is not None),
            relations=relations,
            conflicts=conflicts,
            unknowns=unknowns,
            source_lineage=source_lineage,
            omitted_due_to_budget=tuple(omitted),
            context_budget=plan.budget,
            semantic_access_state="FULL_SEMANTIC_ACCESS_CANDIDATE_ONLY",
            trust_gate=gate,
            provenance=provenance,
        )

    def _consider_candidate(
        self, candidate_set: _CandidateSet, atom: dict[str, Any], score: float | None, plan: QueryPlan, *, channel: str,
    ) -> bool:
        """The only candidate-set entry point for every retrieval channel."""

        return candidate_set.consider(
            atom,
            score,
            self._admission_decision(atom, plan),
            caller_observable=self._caller_observable(atom, plan),
            channel=channel,
        )

    def assemble_gpt_context_bundle_v1(self, plan: QueryPlan) -> GPTSecondBrainContextBundle:
        """Assemble the existing bundle then project only its safe public view."""

        bundle = self.assemble(plan)
        atoms_by_id = {atom["id"]: atom for atom in bundle.atoms}
        all_relation_items = tuple(self._redacted_relation(relation) for relation in bundle.relations)
        all_conflict_items = tuple(self._redacted_conflict(conflict) for conflict in bundle.conflicts)
        all_unknown_items = tuple(self._redacted_unknown(unknown) for unknown in bundle.unknowns)
        relation_items = all_relation_items[:plan.budget]
        conflict_items = all_conflict_items[:plan.budget]
        unknown_items = all_unknown_items[:plan.budget]
        support, counter = self._support_and_counter(bundle.relations, atoms_by_id)
        heads = tuple(
            self._evidence_item(atom, "current_lineage_head")
            for atom in bundle.atoms if self._objective_evidence(atom)
        )
        owner_context = tuple(
            self._evidence_item(atom, "owner_context")
            for atom in bundle.atoms if self._owner_context(atom)
        )
        interpretation_context = tuple(
            self._evidence_item(atom, "non_objective_interpretation")
            for atom in bundle.atoms if self._interpretation_context(atom)
        )
        trust_gate = dict(bundle.trust_gate)
        if trust_gate.get("outcome") != "ABSTAIN" and (conflict_items or unknown_items):
            trust_gate["materiality"] = {
                "state": "UNKNOWN",
                "reason": "canonical_blocking_predicate_not_available",
                "conflict_count": len(conflict_items),
                "unknown_count": len(unknown_items),
            }
        return GPTSecondBrainContextBundle(
            schema_version="GPTSecondBrainContextBundle/v1",
            request={
                "query_id": bundle.query_id,
                "plan_hash": bundle.query_plan_hash,
                "intent": plan.intent,
                "valid_at": plan.valid_at,
                "scope_fingerprint": content_hash({"scopes": sorted(plan.scopes), "user_scope": plan.user_scope}),
                "privacy_mode": plan.privacy_aggregate_mode.lower(),
            },
            admission=self.last_admission_report,
            evidence={
                "current_lineage_heads": heads,
                "strongest_support": support,
                "strongest_counter_or_alternative": counter,
                "conflicts": conflict_items,
                "unknowns": unknown_items,
            },
            context={
                "relations": relation_items,
                "temporal_context": (),
                "stance_context": tuple(item for item in owner_context if item.get("claim_role") in {
                    "USER_EVALUATION", "USER_CREDIBILITY_JUDGMENT", "USER_BIAS_JUDGMENT",
                }),
                "owner_context": owner_context,
                "interpretation_context": interpretation_context,
                "analogies": (),
                "omitted_due_to_budget": {
                    "relations": len(all_relation_items) - len(relation_items),
                    "conflicts": len(all_conflict_items) - len(conflict_items),
                    "unknowns": len(all_unknown_items) - len(unknown_items),
                },
                "unknown_omission_counts": {
                    "unbound_explicit_unknown_omitted": 0,
                },
                "unknown_omission_capability": "UNBOUND_UNKNOWN_BINDING_UNAVAILABLE",
            },
            provenance={"adjacency": self._redacted_provenance(bundle.atoms)},
            ranking={
                "policy_version": "existing-lexical-relation-v1",
                "ordered_ids": tuple(atom["id"] for atom in bundle.atoms),
                "score_components": tuple(
                    {"atom_id": atom_id, "components": self._score_components(atom_id)}
                    for atom_id in (atom["id"] for atom in bundle.atoms)
                ),
                "omitted_due_to_budget": len(bundle.omitted_due_to_budget),
            },
            trust_gate=trust_gate,
            authority={"formal_project_global_write": "LOCKED", "no_trade": True, "authority_write": False},
        )

    def assemble_v1(self, plan: QueryPlan) -> GPTSecondBrainContextBundle:
        """Short compatibility alias for the versioned GPT projection."""

        return self.assemble_gpt_context_bundle_v1(plan)

    def _safe_relations(self, plan: QueryPlan, selected_ids: set[str]) -> tuple[dict[str, Any], ...]:
        return tuple(
            relation for relation in self.store.relations_around(selected_ids)
            if self._endpoints_admitted(
                relation.get("source_atom_id"), relation.get("target_atom_id"), plan=plan, selected_ids=selected_ids,
            )
        )

    def _safe_conflicts(self, plan: QueryPlan, selected_ids: set[str]) -> tuple[dict[str, Any], ...]:
        return tuple(
            conflict for conflict in self.store.conflicts_for(selected_ids)
            if self._endpoints_admitted(
                conflict.get("atom_id_a"), conflict.get("atom_id_b"), plan=plan, selected_ids=selected_ids,
            )
        )

    def _safe_unknowns(
        self, plan: QueryPlan, selected_ids: set[str], *, include_all_open: bool,
    ) -> tuple[dict[str, Any], ...]:
        safe: list[dict[str, Any]] = []
        for unknown in self.store.unknowns_for(selected_ids, include_all_open=include_all_open):
            related = unknown.get("related_atom_ids")
            if not isinstance(related, list) or not related:
                # Endpoint-free unknowns have no canonical user/privacy/public
                # binding.  They must remain indistinguishable from absence
                # until that schema is separately designed and approved.
                continue
            if plan.scopes and unknown.get("scope") not in set(plan.scopes):
                continue
            if self._endpoints_admitted(*related, plan=plan, selected_ids=selected_ids):
                safe.append(unknown)
        return tuple(safe)

    def _endpoints_admitted(self, *atom_ids: Any, plan: QueryPlan, selected_ids: set[str]) -> bool:
        for atom_id in atom_ids:
            if not isinstance(atom_id, str):
                return False
            atom = self.store.get_atom(atom_id)
            if atom is None or not self._caller_observable(atom, plan) or not self._admission_decision(atom, plan).admitted:
                return False
        return bool(atom_ids)

    def _score_components(self, atom_id: str) -> dict[str, float]:
        components = dict(self._last_score_components.get(atom_id, {}))
        components["combined"] = max(components.values(), default=0.0)
        return dict(sorted(components.items()))

    def _evidence_item(self, atom: dict[str, Any], role: str) -> dict[str, Any]:
        item = {
            "atom_id": atom["id"], "atom_type": atom.get("atom_type"), "role": role,
            "confidence": atom.get("confidence"), "score_components": self._score_components(atom["id"]),
            "lifecycle": atom.get("knowledge_status"),
        }
        metadata = atom.get("memory_metadata", {})
        conversation = metadata.get("conversation", {}) if isinstance(metadata, dict) else {}
        knowledge = metadata.get("knowledge", {}) if isinstance(metadata, dict) else {}
        if isinstance(conversation, dict) and isinstance(conversation.get("claim_role"), str):
            item["claim_role"] = conversation["claim_role"]
        if isinstance(knowledge, dict) and isinstance(knowledge.get("epistemic_role"), str):
            item["epistemic_role"] = knowledge["epistemic_role"]
        return item

    @staticmethod
    def _objective_evidence(atom: dict[str, Any]) -> bool:
        metadata = atom.get("memory_metadata", {})
        conversation = metadata.get("conversation", {}) if isinstance(metadata, dict) else {}
        if isinstance(conversation, dict) and conversation:
            return False
        knowledge = metadata.get("knowledge", {}) if isinstance(metadata, dict) else {}
        role = knowledge.get("epistemic_role") if isinstance(knowledge, dict) else None
        return role not in {
            "SOURCE_INTERPRETATION", "VALUE_JUDGMENT", "USER_STANCE", "ASSISTANT_ANALYSIS", "MODEL_INFERENCE", "OPEN_QUESTION",
        }

    @staticmethod
    def _owner_context(atom: dict[str, Any]) -> bool:
        metadata = atom.get("memory_metadata", {})
        conversation = metadata.get("conversation", {}) if isinstance(metadata, dict) else {}
        return isinstance(conversation, dict) and bool(conversation)

    def _interpretation_context(self, atom: dict[str, Any]) -> bool:
        metadata = atom.get("memory_metadata", {})
        knowledge = metadata.get("knowledge", {}) if isinstance(metadata, dict) else {}
        return isinstance(knowledge, dict) and bool(knowledge) and not self._objective_evidence(atom)

    def _support_and_counter(
        self, relations: tuple[dict[str, Any], ...], atoms_by_id: dict[str, dict[str, Any]],
    ) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        groups = (({"supports", "support", "strengthens"}, "support"), ({"contradicts", "conflicts", "weakens", "alternative"}, "counter_or_alternative"))
        result: list[tuple[dict[str, Any], ...]] = []
        for relation_types, role in groups:
            candidates = [
                atoms_by_id[relation["source_atom_id"]] for relation in relations
                if relation.get("relation_type") in relation_types and relation.get("source_atom_id") in atoms_by_id
                and self._objective_evidence(atoms_by_id[relation["source_atom_id"]])
            ]
            candidates.sort(key=lambda atom: (-self._score_components(atom["id"])["combined"], atom["id"]))
            result.append(tuple(self._evidence_item(atom, role) for atom in candidates[:1]))
        return result[0], result[1]

    @staticmethod
    def _redacted_relation(relation: dict[str, Any]) -> dict[str, Any]:
        return {key: relation[key] for key in ("id", "relation_type", "source_atom_id", "target_atom_id", "confidence", "knowledge_status") if key in relation}

    @staticmethod
    def _redacted_conflict(conflict: dict[str, Any]) -> dict[str, Any]:
        return {key: conflict[key] for key in ("id", "atom_id_a", "atom_id_b", "conflict_type", "resolution_status") if key in conflict}

    @staticmethod
    def _redacted_unknown(unknown: dict[str, Any]) -> dict[str, Any]:
        return {key: unknown[key] for key in ("id", "question", "scope", "related_atom_ids", "status") if key in unknown}

    def _redacted_provenance(self, atoms: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        adjacency: list[dict[str, Any]] = []
        for atom in atoms:
            records = self.store.provenance_for_atom(atom["id"])
            adjacency.append({
                "atom_id": atom["id"],
                "packet_ids": tuple(record["packet_id"] for record in records),
                "manifest_ids": tuple(sorted({manifest for record in records for manifest in record["source_manifest_ids"]})),
            })
        return tuple(adjacency)

    def _caller_observable(self, atom: dict[str, Any], plan: QueryPlan) -> bool:
        """Fail closed before an admission rejection can become public telemetry.

        This intentionally has no public reason output.  It only decides
        whether a caller can safely know that a candidate exists at all.
        """

        if atom.get("gpt_access") != "FULL_SEMANTIC_ACCESS":
            return False
        if atom.get("transport_visibility") == "RESTRICTED_NEVER_SYNC":
            return False
        if plan.scopes and atom.get("scope") not in set(plan.scopes):
            return False
        metadata = atom.get("memory_metadata", {})
        if not isinstance(metadata, dict):
            return False
        conversation = metadata.get("conversation")
        knowledge = metadata.get("knowledge")
        if conversation:
            if not isinstance(conversation, dict) or not plan.scopes or plan.user_scope is None or not plan.valid_at:
                return False
            if conversation.get("project_scope") not in set(plan.scopes):
                return False
            if conversation.get("user_scope") != plan.user_scope:
                return False
            if (conversation.get("privacy_class"), conversation.get("coverage"), conversation.get("source_class")) not in {
                ("PUBLIC_SAFE_SYNTHETIC", "synthetic", "SYNTHETIC_PUBLIC_SAFE"),
                ("PRIVATE_LOCAL_CANDIDATE", "private_local", "PRIVATE_LOCAL_AUTHORIZED"),
            }:
                return False
            if conversation.get("claim_role") not in {
                "USER_ASSERTION", "USER_PREFERENCE", "USER_DECISION", "USER_CORRECTION",
                "USER_PLAN", "USER_GOAL", "USER_COMMITMENT", "USER_EVENT_REPORT",
                "USER_EVALUATION", "USER_CREDIBILITY_JUDGMENT", "USER_BIAS_JUDGMENT",
            }:
                return False
            return bool(atom.get("source_refs")) and bool(self.store.provenance_for_atom(atom.get("id", "")))
        if knowledge:
            if not isinstance(knowledge, dict) or not plan.scopes or plan.user_scope is None or not plan.privacy_domains or not plan.valid_at:
                return False
            if knowledge.get("project_scope") not in set(plan.scopes):
                return False
            if knowledge.get("user_scope") != plan.user_scope or knowledge.get("privacy_domain") not in set(plan.privacy_domains):
                return False
            if knowledge.get("safety_class") != "PUBLIC_SAFE_SYNTHETIC":
                return False
            if knowledge.get("privacy_domain") != "PUBLIC_SAFE_SYNTHETIC" and not str(knowledge.get("privacy_domain", "")).startswith("synthetic-"):
                return False
            if knowledge.get("epistemic_role") not in {
                "FACT_CLAIM", "SOURCE_CLAIM", "SOURCE_INTERPRETATION", "VALUE_JUDGMENT", "MECHANISM", "CONDITION",
                "COUNTEREXAMPLE", "METHOD", "OPEN_QUESTION", "USER_STANCE", "ASSISTANT_ANALYSIS", "MODEL_INFERENCE",
            }:
                return False
            if not knowledge.get("proposition_id") or not knowledge.get("identity_domain_hash"):
                return False
            return bool(atom.get("source_refs")) and bool(self.store.provenance_for_atom(atom.get("id", "")))
        return plan.user_scope is None

    def _allowed(self, atom: dict[str, Any], plan: QueryPlan) -> bool:
        """Compatibility facade; policy is implemented exactly once below."""

        return self._admission_decision(atom, plan).admitted

    def _admission_decision(self, atom: dict[str, Any], plan: QueryPlan) -> CandidateAdmissionDecision:
        """Apply one fail-closed, pre-ranking policy with stable reason codes."""

        status = atom.get("knowledge_status")
        if status not in set(plan.truth_states):
            return CandidateAdmissionDecision(False, "truth_state_not_requested")
        if status in DENIED_TRUTH_STATES:
            return CandidateAdmissionDecision(False, "truth_state_denied")
        if status in {"stale", "revoked"}:
            return CandidateAdmissionDecision(False, "lifecycle_not_current")
        if plan.intent == "CURRENT" and status == "superseded":
            return CandidateAdmissionDecision(False, "lifecycle_not_current")
        if atom.get("gpt_access") != "FULL_SEMANTIC_ACCESS":
            return CandidateAdmissionDecision(False, "semantic_access_denied")
        if atom.get("transport_visibility") == "RESTRICTED_NEVER_SYNC":
            return CandidateAdmissionDecision(False, "transport_visibility_denied")
        try:
            confidence = float(atom.get("confidence"))
        except (TypeError, ValueError):
            return CandidateAdmissionDecision(False, "confidence_invalid")
        if confidence < plan.min_confidence:
            return CandidateAdmissionDecision(False, "confidence_below_minimum")
        if plan.scopes and atom.get("scope") not in set(plan.scopes):
            return CandidateAdmissionDecision(False, "project_scope_mismatch")
        if plan.atom_types and atom.get("atom_type") not in set(plan.atom_types):
            return CandidateAdmissionDecision(False, "atom_type_not_requested")
        updated_at = atom.get("updated_at")
        if plan.time_start and (not isinstance(updated_at, str) or updated_at < plan.time_start):
            return CandidateAdmissionDecision(False, "updated_before_time_window")
        if plan.time_end and (not isinstance(updated_at, str) or updated_at > plan.time_end):
            return CandidateAdmissionDecision(False, "updated_after_time_window")
        conversation = atom.get("memory_metadata", {}).get("conversation")
        knowledge = atom.get("memory_metadata", {}).get("knowledge")
        if conversation:
            # CLTM data fails closed: caller must bind both scopes and a valid
            # instant.  Non-conversation W3 atoms retain historic defaults.
            if not plan.scopes or plan.user_scope is None or not plan.valid_at:
                return CandidateAdmissionDecision(False, "conversation_query_binding_missing")
            if atom.get("scope") not in set(plan.scopes) or conversation.get("project_scope") not in set(plan.scopes):
                return CandidateAdmissionDecision(False, "conversation_project_scope_mismatch")
            if conversation.get("user_scope") != plan.user_scope:
                return CandidateAdmissionDecision(False, "conversation_user_scope_mismatch")
            if (conversation.get("privacy_class"), conversation.get("coverage"), conversation.get("source_class")) not in {
                ("PUBLIC_SAFE_SYNTHETIC", "synthetic", "SYNTHETIC_PUBLIC_SAFE"),
                ("PRIVATE_LOCAL_CANDIDATE", "private_local", "PRIVATE_LOCAL_AUTHORIZED"),
            }:
                return CandidateAdmissionDecision(False, "conversation_privacy_binding_invalid")
            if conversation.get("claim_role") not in {
                "USER_ASSERTION", "USER_PREFERENCE", "USER_DECISION", "USER_CORRECTION",
                "USER_PLAN", "USER_GOAL", "USER_COMMITMENT", "USER_EVENT_REPORT",
                "USER_EVALUATION", "USER_CREDIBILITY_JUDGMENT", "USER_BIAS_JUDGMENT",
            }:
                return CandidateAdmissionDecision(False, "conversation_claim_role_denied")
            if plan.intent == "HISTORICAL" and not atom.get("source_refs"):
                return CandidateAdmissionDecision(False, "historical_provenance_missing")
            if not self.store.provenance_for_atom(atom.get("id", "")):
                return CandidateAdmissionDecision(False, "packet_provenance_missing")
            try:
                instant = _parse_instant(plan.valid_at)
                valid_at = _is_valid_at(conversation, instant)
            except (KeyError, TypeError, ValueError):
                return CandidateAdmissionDecision(False, "conversation_valid_time_invalid")
            if not valid_at:
                return CandidateAdmissionDecision(False, "conversation_not_valid_at_query_time")
            try:
                requires_revalidation = _memory_palace_requires_revalidation(conversation, instant)
            except (KeyError, TypeError, ValueError):
                return CandidateAdmissionDecision(False, "conversation_revalidation_invalid")
            if plan.intent == "CURRENT" and requires_revalidation:
                return CandidateAdmissionDecision(False, "lifecycle_not_current")
        elif knowledge:
            if not plan.scopes or plan.user_scope is None or not plan.privacy_domains or not plan.valid_at:
                return CandidateAdmissionDecision(False, "knowledge_query_binding_missing")
            if atom.get("scope") not in set(plan.scopes) or knowledge.get("project_scope") not in set(plan.scopes):
                return CandidateAdmissionDecision(False, "knowledge_project_scope_mismatch")
            if knowledge.get("user_scope") != plan.user_scope or knowledge.get("privacy_domain") not in set(plan.privacy_domains):
                return CandidateAdmissionDecision(False, "knowledge_scope_or_privacy_mismatch")
            if knowledge.get("safety_class") != "PUBLIC_SAFE_SYNTHETIC":
                return CandidateAdmissionDecision(False, "knowledge_safety_class_denied")
            if knowledge.get("privacy_domain") != "PUBLIC_SAFE_SYNTHETIC" and not str(knowledge.get("privacy_domain", "")).startswith("synthetic-"):
                return CandidateAdmissionDecision(False, "knowledge_privacy_domain_denied")
            if knowledge.get("epistemic_role") not in {
                "FACT_CLAIM", "SOURCE_CLAIM", "SOURCE_INTERPRETATION", "VALUE_JUDGMENT", "MECHANISM", "CONDITION",
                "COUNTEREXAMPLE", "METHOD", "OPEN_QUESTION", "USER_STANCE", "ASSISTANT_ANALYSIS", "MODEL_INFERENCE",
            }:
                return CandidateAdmissionDecision(False, "knowledge_epistemic_role_denied")
            if not knowledge.get("proposition_id") or not knowledge.get("identity_domain_hash"):
                return CandidateAdmissionDecision(False, "knowledge_identity_missing")
            if plan.intent == "HISTORICAL" and not atom.get("source_refs"):
                return CandidateAdmissionDecision(False, "historical_provenance_missing")
            if not self.store.provenance_for_atom(atom.get("id", "")):
                return CandidateAdmissionDecision(False, "packet_provenance_missing")
            try:
                instant = _parse_instant(plan.valid_at)
                valid_at = _is_valid_at(knowledge, instant)
            except (KeyError, TypeError, ValueError):
                return CandidateAdmissionDecision(False, "knowledge_valid_time_invalid")
            if not valid_at:
                return CandidateAdmissionDecision(False, "knowledge_not_valid_at_query_time")
            try:
                requires_revalidation = _knowledge_requires_revalidation(knowledge, instant)
            except (KeyError, TypeError, ValueError):
                return CandidateAdmissionDecision(False, "knowledge_revalidation_invalid")
            if plan.intent == "CURRENT" and requires_revalidation:
                return CandidateAdmissionDecision(False, "lifecycle_not_current")
        elif plan.user_scope is not None:
            return CandidateAdmissionDecision(False, "user_scope_requires_governed_metadata")
        return CandidateAdmissionDecision(True, "admitted")

    @staticmethod
    def _trust_gate(plan: QueryPlan, atoms: tuple[dict[str, Any] | None, ...]) -> dict[str, Any]:
        admitted = [atom for atom in atoms if atom is not None]
        if not admitted:
            return {"outcome": "ABSTAIN", "reason": "no_in_scope_valid_candidate", "intent": plan.intent}
        aggregate_keys = {
            atom.get("memory_metadata", {}).get("knowledge", {}).get("aggregate_equivalence_key", atom["id"])
            for atom in admitted if atom.get("memory_metadata", {}).get("knowledge")
        }
        return {
            "outcome": "ADMIT_CANDIDATE_ONLY",
            "reason": "scope_privacy_status_and_valid_time_passed",
            "intent": plan.intent,
            "privacy_aggregate_mode": plan.privacy_aggregate_mode,
            "semantic_vote_count": len(aggregate_keys) if plan.privacy_aggregate_mode == "SYNTHETIC_AGGREGATE_NO_VOTE" else len(admitted),
        }


def _parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("query_plan_or_memory_time_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _is_valid_at(conversation: dict[str, Any], instant: datetime) -> bool:
    valid_from = _parse_instant(conversation["valid_from"])
    ends = [
        _parse_instant(value)
        for value in (conversation.get("valid_to"), conversation.get("effective_valid_to"))
        if value is not None
    ]
    return instant >= valid_from and (not ends or instant < min(ends))


def _memory_palace_requires_revalidation(conversation: dict[str, Any], instant: datetime) -> bool:
    """Keep short-lived market clues historical until explicitly revalidated."""

    palace = conversation.get("memory_palace")
    if not isinstance(palace, dict) or not palace.get("revalidation_required"):
        return False
    if palace.get("freshness_profile") not in {"TRANSIENT", "SHORT_CYCLE"}:
        return False
    last_verified = palace.get("last_verified_at")
    horizon_hours = palace.get("freshness_horizon_hours")
    if not isinstance(last_verified, str) or not isinstance(horizon_hours, int) or horizon_hours < 1:
        return True
    from datetime import timedelta
    return instant > _parse_instant(last_verified) + timedelta(hours=horizon_hours)


def _knowledge_requires_revalidation(knowledge: dict[str, Any], instant: datetime) -> bool:
    if not knowledge.get("revalidation_required"):
        return False
    if knowledge.get("freshness_profile") not in {"TRANSIENT", "SHORT_CYCLE"}:
        return False
    last_verified = knowledge.get("last_verified_at")
    horizon_hours = knowledge.get("freshness_horizon_hours")
    if not isinstance(last_verified, str) or not isinstance(horizon_hours, int) or horizon_hours < 1:
        return True
    from datetime import timedelta
    return instant > _parse_instant(last_verified) + timedelta(hours=horizon_hours)
