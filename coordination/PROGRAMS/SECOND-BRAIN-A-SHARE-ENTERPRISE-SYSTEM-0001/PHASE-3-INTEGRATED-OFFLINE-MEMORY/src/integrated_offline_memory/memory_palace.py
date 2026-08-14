"""Synthetic-only manual Memory Palace built on the existing W3 candidate path.

This module deliberately accepts caller-supplied public-safe synthetic inputs.
It neither discovers conversation sources nor opens the operational/private store.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Callable, Iterable

from .canonical import content_hash, normalize_text
from .conversation_memory import ConversationEpisode, build_conversation_candidate, build_conversation_correction
from .learning_packet import build_learning_packet
from .memory_store import MemoryStore
from .retrieval import ContextAssembler, QueryPlan


TRIGGERS = ("采集记忆", "数据采集")
COGNITIVE_STATES = {
    "KNOWN_SAID", "KNOWN_UNSAID_INFERRED", "UNKNOWN_BUT_ACCESSIBLE", "UNKNOWN_REQUIRES_SCAFFOLDING",
}
CONFLICT_TYPES = {
    "DIRECT_FACT_CONTRADICTION", "SCHEDULE_HARD_CONFLICT", "SCHEDULE_POTENTIAL_CONFLICT",
    "PREFERENCE_TENSION", "PLAN_SUPERSESSION_CANDIDATE", "STANCE_CONFLICT",
    "SOURCE_CREDIBILITY_CONFLICT", "UNKNOWN_CONSTRAINT",
}
FRESHNESS_PROFILES = {"TRANSIENT", "SHORT_CYCLE", "MEDIUM_CYCLE", "STRUCTURAL", "UNKNOWN"}
_SECRET = re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")


@dataclass(frozen=True)
class CaptureReceipt:
    status: str
    atom_ids: tuple[str, ...]
    normalized_dates: tuple[str, ...]
    conflict_types: tuple[str, ...]
    exact_recall_passed: bool
    candidate_authority_only: bool = True
    formal_project_global_write: str = "LOCKED"

    def public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidate_authority_only": self.candidate_authority_only,
            "formal_project_global_write": self.formal_project_global_write,
            "atom_count": len(self.atom_ids),
            "normalized_dates": list(self.normalized_dates),
            "conflict_types": list(self.conflict_types),
            "exact_recall_passed": self.exact_recall_passed,
        }


def capture_text(
    *, store: MemoryStore, user_scope: str, project_scope: str, message: str,
    recorded_at: str, source_id: str, previous_owner_message: str | None = None,
    semantic_provider: Callable[[str], Iterable[str]] | None = None,
    freshness_policy: Callable[[str, str], str] | None = None,
) -> CaptureReceipt:
    """Capture a public-safe synthetic owner message through W3 then prove recall."""

    text = _capturable_text(message, previous_owner_message)
    if _SECRET.search(text):
        raise ValueError("memory_palace_secret_denied")
    normalized_content = normalize_text(text)
    source_content_hash = content_hash({"normalized_captured_content": normalized_content})
    episode = ConversationEpisode(
        episode_id=source_id, user_scope=user_scope, project_scope=project_scope,
        source_pointer="synthetic://memory-palace/" + source_id,
        # Public-safe content hash binds synthetic provenance without putting
        # source text into a receipt or public identifier.
        source_hash=source_content_hash,
        privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at=recorded_at,
        valid_time=recorded_at, provenance_quality="DIRECT",
    )
    derived = _derive_memories(text, recorded_at, freshness_policy=freshness_policy)
    packets = [_packet_for_derived(episode, item, store=store) for item in derived]
    atom_ids = tuple(atom["id"] for packet in packets for atom in packet["atoms"])
    conflicts = _detect_conflicts(store, atom_ids, derived, user_scope, project_scope)
    # Conflicts travel through the existing, atomic LearningPacket boundary.
    # There is deliberately no direct MemoryStore mutation API for this feature.
    if conflicts:
        packets[0] = _repack(packets[0], conflicts=conflicts)
    results = store.import_learning_packets_atomic(packets)
    explanations = retrieve_memory_palace(
        store=store, user_scope=user_scope, project_scope=project_scope,
        query_text=text, anchor_time=recorded_at, valid_at=recorded_at,
        semantic_provider=semantic_provider,
    )
    recalled_ids = {item["atom"]["id"] for item in explanations}
    if not set(atom_ids).issubset(recalled_ids):
        raise ValueError("memory_palace_exact_recall_failed")
    if any(result["status"] not in {"IMPORTED", "IDEMPOTENT_DUPLICATE"} for result in results):
        raise ValueError("memory_palace_import_result_invalid")
    return CaptureReceipt(
        status="CAPTURED_CANDIDATE_ONLY", atom_ids=atom_ids,
        normalized_dates=tuple(sorted({item["temporal"]["resolved_start"][:10] for item in derived if item["temporal"].get("resolved_start")})),
        conflict_types=tuple(sorted({item["conflict_type"] for item in conflicts})),
        exact_recall_passed=True,
    )


def retrieve_memory_palace(
    *, store: MemoryStore, user_scope: str, project_scope: str, query_text: str,
    anchor_time: str, valid_at: str | None = None, intent: str = "CURRENT", semantic_provider: Callable[[str], Iterable[str]] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Hybrid lexical + deterministic temporal + graph retrieval explanations."""

    temporal = normalize_temporal_expression(query_text, anchor_time)
    temporal_active = temporal["temporal_confidence"] == "HIGH"
    expanded = query_text
    if temporal_active:
        expanded += " " + temporal["resolved_start"][:10]
    if semantic_provider is not None:
        expanded += " " + " ".join(str(item) for item in semantic_provider(query_text))
    plan = QueryPlan(
        query_text=expanded, scopes=(project_scope,), user_scope=user_scope,
        valid_at=valid_at or _retrieval_instant(temporal, anchor_time), intent=intent,
        truth_states=("candidate", "approved", "conflict", "superseded") if intent == "HISTORICAL" else ("candidate", "approved", "conflict", "unknown"),
        relation_depth=1, include_conflicts=True,
    )
    assembler = ContextAssembler(store)
    bundle = assembler.assemble(plan)
    temporal_date = temporal["resolved_start"][:10]
    # The existing lexical index intentionally does not index every metadata
    # field.  Add an exact temporal-window channel while applying the same W3
    # QueryPlan admission gate as the lexical channel.
    admitted: dict[str, dict[str, Any]] = {atom["id"]: atom for atom in bundle.atoms}
    for atom in store.all_atoms() if temporal_active else ():
        palace = atom.get("memory_metadata", {}).get("conversation", {}).get("memory_palace", {})
        if palace.get("temporal", {}).get("resolved_start", "")[:10] == temporal_date and assembler._allowed(atom, plan):
            admitted[atom["id"]] = atom
    graph_ids = store.related_atom_ids(set(admitted))
    for atom_id in graph_ids:
        atom = store.get_atom(atom_id)
        if atom is not None and assembler._allowed(atom, plan):
            admitted[atom_id] = atom
    # A shared source-manifest is also a provenance graph edge.  It lets a
    # multi-claim utterance remain in independent, claim-role-bound packets
    # without weakening the existing one-claim packet validation contract.
    provenance_graph_ids: set[str] = set()
    admitted_sources = {source for atom in admitted.values() for source in atom.get("source_refs", [])}
    for atom in store.all_atoms():
        if admitted_sources.intersection(atom.get("source_refs", [])) and assembler._allowed(atom, plan):
            admitted[atom["id"]] = atom
            provenance_graph_ids.add(atom["id"])
    result: list[dict[str, Any]] = []
    lexical_ids = {atom["id"] for atom in bundle.atoms}
    relation_ids = {
        endpoint for relation in store.relations_around(set(admitted))
        for endpoint in (relation["source_atom_id"], relation["target_atom_id"])
    }
    for atom in sorted(admitted.values(), key=lambda item: item["id"]):
        palace = atom.get("memory_metadata", {}).get("conversation", {}).get("memory_palace", {})
        channels = ["lexical"] if atom["id"] in lexical_ids else []
        if temporal_active and palace.get("temporal", {}).get("resolved_start", "")[:10] == temporal_date:
            channels.append("temporal")
        if atom["id"] in relation_ids or atom["id"] in provenance_graph_ids:
            channels.append("graph")
        result.append({
            "atom": atom,
            "explanation": {
                "channels": channels,
                "current_validity": atom["knowledge_status"],
                "freshness": palace.get("freshness_profile", "UNKNOWN"),
                "owner_stance": palace.get("stance"),
            },
        })
    return tuple(result)


def normalize_temporal_expression(text: str, anchor_time: str) -> dict[str, str]:
    """Resolve covered Chinese relative days deterministically in anchor timezone."""

    anchor = _aware(anchor_time)
    explicit = re.search(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)", text)
    expression, days = next(((word, offset) for word, offset in (("后天", 2), ("明天", 1), ("今天", 0)) if word in text), (None, 0))
    local_date = explicit.group(1) if explicit else (anchor + timedelta(days=days)).date().isoformat()
    clock_range = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\s*[-~至]\s*([01]?\d|2[0-3]):([0-5]\d)\b", text)
    start_clock = "00:00:00"
    end_clock = "23:59:59"
    granularity = "day"
    if clock_range:
        start_clock = f"{int(clock_range.group(1)):02d}:{clock_range.group(2)}:00"
        end_clock = f"{int(clock_range.group(3)):02d}:{clock_range.group(4)}:00"
        granularity = "interval"
    return {
        "original_time_expression": expression or (explicit.group(1) if explicit else "UNKNOWN"),
        "anchor_time": anchor.isoformat(), "resolved_start": local_date + "T" + start_clock + _offset(anchor),
        "resolved_end": local_date + "T" + end_clock + _offset(anchor),
        "resolution_granularity": granularity, "resolution_method": "deterministic_rule",
        "temporal_confidence": "HIGH" if expression or explicit else "UNKNOWN",
    }


def cognitive_coverage(*, topic: str, state: str, evidence_atom_ids: Iterable[str]) -> dict[str, Any]:
    if state not in COGNITIVE_STATES:
        raise ValueError("memory_palace_cognitive_state_denied")
    return {"topic": normalize_text(topic), "state": state, "evidence_atom_ids": sorted(set(evidence_atom_ids)), "explicit_assertion": state == "KNOWN_SAID"}


def _capturable_text(message: str, previous: str | None) -> str:
    normalized = normalize_text(message)
    found = [trigger for trigger in TRIGGERS if trigger in normalized]
    if not found:
        raise ValueError("memory_palace_capture_trigger_required")
    text = normalize_text(normalized)
    for trigger in TRIGGERS:
        text = normalize_text(text.replace(trigger, ""))
    if not text:
        text = normalize_text(previous or "")
    if not text:
        raise ValueError("memory_palace_substantive_owner_message_required")
    return text


def _derive_memories(
    text: str, recorded_at: str, *, freshness_policy: Callable[[str, str], str] | None = None,
) -> list[dict[str, Any]]:
    """Deterministically atomize a synthetic long owner passage offline.

    This intentionally stays modest: clause boundaries and explicit Chinese
    cue words are the correctness path; an optional caller provider may enrich
    retrieval but never determines atomization correctness.
    """

    result: list[dict[str, Any]] = []
    for clause in _owner_clauses(text):
        temporal = normalize_temporal_expression(clause if _has_time(clause) else text, recorded_at)
        result.extend(_derive_clause(clause, temporal, freshness_policy=freshness_policy))
    return result or [_derived(text, "USER_ASSERTION", normalize_temporal_expression(text, recorded_at), freshness_policy=freshness_policy)]


def _owner_clauses(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
    pieces = re.split(r"[。；;！!？?]+|(?:，并且)|(?:，同时)|(?:，另外)", normalized)
    clauses = tuple(piece.strip(" ，,") for piece in pieces if normalize_text(piece.strip(" ，,")))
    # Do not rewrite a single captured source statement just to atomize it.
    return (normalized,) if len(clauses) <= 1 else clauses


def _has_time(text: str) -> bool:
    return bool(re.search(r"20\d{2}-\d{2}-\d{2}|今天|明天|后天", text))


def _derive_clause(
    clause: str, temporal: dict[str, str], *, freshness_policy: Callable[[str, str], str] | None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    stance_rules = (
        ("AUTHENTICITY", "USER_EVALUATION", "BELIEVES_FALSE", ("假的", "不真实")),
        ("AUTHENTICITY", "USER_EVALUATION", "BELIEVES_TRUE", ("真的", "真实")),
        ("BIAS", "USER_BIAS_JUDGMENT", "NOT_BIASED", ("没有偏见",)),
        ("BIAS", "USER_BIAS_JUDGMENT", "BIASED", ("偏见",)),
        ("CREDIBILITY", "USER_CREDIBILITY_JUDGMENT", "DISTRUSTS_SOURCE", ("不可信",)),
        ("CREDIBILITY", "USER_CREDIBILITY_JUDGMENT", "TRUSTS_SOURCE", ("可信",)),
        ("GOOD_BAD", "USER_EVALUATION", "BAD", ("不好", "很差", "坏")),
        ("GOOD_BAD", "USER_EVALUATION", "GOOD", ("很好", "好")),
        ("RISK", "USER_EVALUATION", "RISKY", ("有风险", "风险高")),
        ("RISK", "USER_EVALUATION", "LOW_RISK", ("风险低", "没风险")),
        ("USEFULNESS", "USER_EVALUATION", "NOT_USEFUL", ("没用", "无用")),
        ("USEFULNESS", "USER_EVALUATION", "USEFUL", ("有用",)),
        ("ACCURACY", "USER_EVALUATION", "INACCURATE", ("不准确", "错误")),
        ("ACCURACY", "USER_EVALUATION", "ACCURATE", ("准确",)),
    )
    matched_types: set[str] = set()
    for evaluation_type, role, stance, cues in stance_rules:
        if evaluation_type not in matched_types and any(cue in clause for cue in cues):
            matched_types.add(evaluation_type)
            result.append(_derived(
                clause, role, temporal, stance=stance, evaluation_type=evaluation_type,
                target_id=_structured_target_id(clause, evaluation_type), freshness_policy=freshness_policy,
            ))
    if result:
        return result
    role = _claim_role_for_clause(clause, temporal)
    return [_derived(clause, role, temporal, freshness_policy=freshness_policy)]


def _claim_role_for_clause(clause: str, temporal: dict[str, str]) -> str:
    if any(word in clause for word in ("目标", "希望", "想要达成")):
        return "USER_GOAL"
    if any(word in clause for word in ("承诺", "保证", "一定会")):
        return "USER_COMMITMENT"
    if "喜欢" in clause or "偏好" in clause:
        return "USER_PREFERENCE"
    if any(word in clause for word in ("决定", "决定了")):
        return "USER_DECISION"
    if any(word in clause for word in ("我要", "计划", "明天", "后天")):
        return "USER_PLAN"
    if temporal["temporal_confidence"] == "HIGH" and any(word in clause for word in (
        "有", "参加", "运动", "会议", "会", "晨会", "午会", "复盘", "发生", "约", "安排",
    )):
        return "USER_EVENT_REPORT"
    return "USER_ASSERTION"


def _derived(
    statement: str, role: str, temporal: dict[str, str], *, stance: str | None = None,
    evaluation_type: str | None = None, target_id: str | None = None,
    freshness_policy: Callable[[str, str], str] | None = None,
) -> dict[str, Any]:
    freshness = classify_freshness(statement, role, policy=freshness_policy)
    return {
        "statement": statement, "role": role, "temporal": temporal, "stance": stance,
        "evaluation_type": evaluation_type, "target_id": target_id, "freshness": freshness,
    }


def classify_freshness(
    statement: str, role: str, *, policy: Callable[[str, str], str] | None = None,
) -> str:
    """Explicit policy boundary; callers may provide a public-safe policy."""

    selected = policy(statement, role) if policy is not None else None
    if selected is not None:
        if selected not in FRESHNESS_PROFILES:
            raise ValueError("memory_palace_freshness_policy_denied")
        return selected
    if any(word in statement for word in ("市场", "股票", "股价", "证券", "交易", "行情", "涨停", "做多", "做空")):
        return "SHORT_CYCLE"
    if role in {"USER_PREFERENCE", "USER_EVALUATION", "USER_BIAS_JUDGMENT", "USER_CREDIBILITY_JUDGMENT"}:
        return "STRUCTURAL"
    return "MEDIUM_CYCLE"


def _packet_for_derived(episode: ConversationEpisode, item: dict[str, Any], *, store: MemoryStore) -> dict[str, Any]:
    replaces = _stance_target(store, episode, item)
    packet = (build_conversation_correction(
        episode=episode, statement=item["statement"], replaces_atom_id=replaces["id"],
        valid_from=episode.recorded_at, candidate_confidence=0.7,
    ) if replaces else build_conversation_candidate(
        episode=episode, statement=item["statement"], claim_role=item["role"],
        valid_from=episode.recorded_at, candidate_confidence=0.7,
    ))
    atom = packet["atoms"][0]
    conversation = atom["memory_metadata"]["conversation"]
    conversation["memory_palace"] = {
        # Claim validity begins when the owner speaks.  The referenced event
        # interval remains independent, so tomorrow plans are usable tonight
        # while their scheduled event still means tomorrow.
        "temporal": item["temporal"], "event_interval": item["temporal"],
        "event_kind": (
            "PLAN" if item["role"] == "USER_PLAN" else
            "COMMITMENT" if item["role"] == "USER_COMMITMENT" else
            "EVENT" if item["role"] == "USER_EVENT_REPORT" else
            "STANCE" if item["stance"] else "ASSERTION"
        ),
        "stance": item["stance"], "evaluation_type": item["evaluation_type"],
        "freshness_profile": item["freshness"], "last_verified_at": episode.recorded_at,
        "revalidation_required": item["freshness"] in {"TRANSIENT", "SHORT_CYCLE"}, "freshness_horizon_hours": 24,
        "epistemic_status": "OWNER_STANCE_NOT_OBJECTIVE_FACT" if item["stance"] else "USER_ASSERTION_CANDIDATE",
        "target_id": item.get("target_id") if item["stance"] else None,
        "stance_update_of": replaces["id"] if replaces else None,
    }
    packet["validation_report"]["memory_palace"] = conversation["memory_palace"]
    return build_learning_packet(
        source_manifest_ids=packet["source_manifest_ids"], source_hash=packet["source_hash"],
        validation_report=packet["validation_report"], evidence_refs=packet["evidence_refs"], atoms=[atom],
        relations=packet.get("relations", []),
    )


def _repack(packet: dict[str, Any], *, conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    return build_learning_packet(
        source_manifest_ids=packet["source_manifest_ids"], source_hash=packet["source_hash"],
        validation_report=packet["validation_report"], evidence_refs=packet["evidence_refs"],
        atoms=packet["atoms"], relations=packet.get("relations", []), conflicts=conflicts,
    )


def _detect_conflicts(store: MemoryStore, new_ids: tuple[str, ...], derived: list[dict[str, Any]], user_scope: str, project_scope: str) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    # Keep the atom identity attached to its own derived event.  A date-keyed
    # map would collapse multiple events on one day and would let a
    # schedulable sibling leak a schedule conflict onto a preference/stance.
    schedulable_pairs = tuple(
        (new_id, item) for new_id, item in zip(new_ids, derived) if _is_schedulable(item)
    )
    for old in store.all_atoms():
        if old["id"] in new_ids or old["knowledge_status"] != "candidate":
            continue
        conversation = old.get("memory_metadata", {}).get("conversation", {})
        palace = conversation.get("memory_palace", {})
        old_temporal = palace.get("event_interval", palace.get("temporal", {}))
        old_date = old_temporal.get("resolved_start", "")[:10]
        if conversation.get("user_scope") != user_scope or conversation.get("project_scope") != project_scope:
            continue
        if _is_schedulable_atom(old):
            for new_id, item in schedulable_pairs:
                new_temporal = item["temporal"]
                if old["id"] == new_id or old_date != new_temporal.get("resolved_start", "")[:10]:
                    continue
                conflict_type = _schedule_conflict_type(old_temporal, new_temporal)
                if conflict_type is None:
                    continue
                conflicts.append({"atom_id_a": old["id"], "atom_id_b": new_id, "conflict_type": conflict_type, "resolution_note": "overlapping_fixed_intervals" if conflict_type == "SCHEDULE_HARD_CONFLICT" else "missing_time_or_flexibility"})
                if conflict_type == "SCHEDULE_POTENTIAL_CONFLICT":
                    conflicts.append({"atom_id_a": old["id"], "atom_id_b": new_id, "conflict_type": "UNKNOWN_CONSTRAINT", "resolution_note": "time_or_flexibility_not_evidenced"})
        for new_id, item in zip(new_ids, derived):
            old_palace = palace
            if not item.get("stance") or not old_palace.get("stance"):
                continue
            if item.get("target_id") != old_palace.get("target_id"):
                continue
            if item.get("stance") == old_palace.get("stance"):
                continue
            conflict_type = "SOURCE_CREDIBILITY_CONFLICT" if item.get("evaluation_type") == "CREDIBILITY" else "STANCE_CONFLICT"
            conflicts.append({
                "atom_id_a": old["id"], "atom_id_b": new_id, "conflict_type": conflict_type,
                "resolution_note": "append_preserving_owner_stance_update",
            })
        old_role = conversation.get("claim_role")
        for new_id, item in zip(new_ids, derived):
            if old_role == "USER_PLAN" and item.get("role") == "USER_PLAN" and _plan_key(old["canonical_statement"]) == _plan_key(item["statement"]):
                conflicts.append({
                    "atom_id_a": old["id"], "atom_id_b": new_id, "conflict_type": "PLAN_SUPERSESSION_CANDIDATE",
                    "resolution_note": "same_plan_subject_requires_owner_resolution",
                })
    return conflicts


def _is_schedulable(item: dict[str, Any]) -> bool:
    return item.get("role") in {"USER_PLAN", "USER_COMMITMENT", "USER_EVENT_REPORT"}


def _is_schedulable_atom(atom: dict[str, Any]) -> bool:
    conversation = atom.get("memory_metadata", {}).get("conversation", {})
    palace = conversation.get("memory_palace", {})
    return conversation.get("claim_role") in {"USER_PLAN", "USER_COMMITMENT", "USER_EVENT_REPORT"} and palace.get("event_kind") in {"PLAN", "EVENT", "COMMITMENT"}


def _plan_key(statement: str) -> str:
    return normalize_text(re.sub(r"20\d{2}-\d{2}-\d{2}|[0-2]?\d:[0-5]\d|今天|明天|后天|我要|计划|去", "", statement))


def _overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("resolution_granularity") != "interval" or right.get("resolution_granularity") != "interval":
        return False
    return _aware(left["resolved_start"]) < _aware(right["resolved_end"]) and _aware(right["resolved_start"]) < _aware(left["resolved_end"])


def _schedule_conflict_type(left: dict[str, Any], right: dict[str, Any]) -> str | None:
    """Classify only genuine interval overlap or under-specified mutual exclusion."""

    left_fixed = left.get("resolution_granularity") == "interval"
    right_fixed = right.get("resolution_granularity") == "interval"
    if left_fixed and right_fixed:
        return "SCHEDULE_HARD_CONFLICT" if _overlaps(left, right) else None
    return "SCHEDULE_POTENTIAL_CONFLICT"


def _retrieval_instant(temporal: dict[str, str], fallback: str) -> str:
    # Temporal retrieval is about an event interval, not a change to claim
    # validity.  The caller's query instant governs current/historical gates.
    return fallback


def _structured_target_id(statement: str, evaluation_type: str) -> str:
    """Stable public-safe target identity, distinct for claim and source stance."""

    normalized = normalize_text(statement)
    if evaluation_type in {"BIAS", "CREDIBILITY"}:
        marker = next((item for item in ("这个来源", "该来源", "来源", "source") if item.casefold() in normalized.casefold()), None)
        target = "source:" + (marker or normalized)
    elif evaluation_type == "AUTHENTICITY":
        marker = next((item for item in ("这个消息", "该消息", "消息", "事件", "内容", "claim") if item.casefold() in normalized.casefold()), None)
        target = "claim:" + (marker or normalized)
    else:
        target = "subject:" + normalized
    target = re.sub(r"假的|真的|真实|不真实|偏见|没有偏见|可信|不可信|我觉得|我认为|是|很好|很差|不好|好|有风险|风险高|风险低|没风险|有用|没用|无用|准确|不准确|错误", "", target)
    return "stance-target-" + content_hash({"evaluation_type": evaluation_type, "target": normalize_text(target)})[:20]


def _stance_target(store: MemoryStore, episode: ConversationEpisode, item: dict[str, Any]) -> dict[str, Any] | None:
    if not item.get("stance"):
        return None
    target_id = item.get("target_id")
    for atom in store.all_atoms():
        conversation = atom.get("memory_metadata", {}).get("conversation", {})
        palace = conversation.get("memory_palace", {})
        if (atom.get("knowledge_status") == "candidate" and conversation.get("user_scope") == episode.user_scope
                and conversation.get("project_scope") == episode.project_scope and palace.get("target_id") == target_id):
            return atom
    return None


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("memory_palace_timezone_required")
    return parsed


def _offset(value: datetime) -> str:
    return value.strftime("%z")[:3] + ":" + value.strftime("%z")[3:]
