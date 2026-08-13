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
) -> CaptureReceipt:
    """Capture a public-safe synthetic owner message through W3 then prove recall."""

    text = _capturable_text(message, previous_owner_message)
    if _SECRET.search(text):
        raise ValueError("memory_palace_secret_denied")
    episode = ConversationEpisode(
        episode_id=source_id, user_scope=user_scope, project_scope=project_scope,
        source_pointer="synthetic://memory-palace/" + source_id,
        source_hash=content_hash({"synthetic_source": source_id}),
        privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at=recorded_at,
        valid_time=recorded_at, provenance_quality="DIRECT",
    )
    derived = _derive_memories(text, recorded_at)
    packets = [_packet_for_derived(episode, item, store=store) for item in derived]
    atom_ids = tuple(atom["id"] for packet in packets for atom in packet["atoms"])
    conflicts = _detect_conflicts(store, atom_ids, derived, user_scope, project_scope)
    # Conflicts travel through the existing, atomic LearningPacket boundary.
    # There is deliberately no direct MemoryStore mutation API for this feature.
    if conflicts:
        packets[0] = _repack(packets[0], conflicts=conflicts)
    results = store.import_learning_packets_atomic(packets)
    verification_time = _verification_time(derived, recorded_at)
    explanations = retrieve_memory_palace(
        store=store, user_scope=user_scope, project_scope=project_scope,
        query_text=text, anchor_time=verification_time, semantic_provider=semantic_provider,
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
    expanded = query_text + " " + temporal["resolved_start"][:10]
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
    for atom in store.all_atoms():
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
        if palace.get("temporal", {}).get("resolved_start", "")[:10] == temporal_date:
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


def _derive_memories(text: str, recorded_at: str) -> list[dict[str, Any]]:
    temporal = normalize_temporal_expression(text, recorded_at)
    result: list[dict[str, Any]] = []
    if "假的" in text or "真的" in text:
        result.append(_derived(
            text, "USER_EVALUATION", temporal,
            stance="BELIEVES_FALSE" if "假的" in text else "BELIEVES_TRUE",
            evaluation_type="AUTHENTICITY",
        ))
    if "偏见" in text:
        result.append(_derived(
            text, "USER_BIAS_JUDGMENT", temporal,
            stance="NOT_BIASED" if "没有偏见" in text else "BIASED", evaluation_type="BIAS",
        ))
    if "不可信" in text or "可信" in text:
        result.append(_derived(
            text, "USER_CREDIBILITY_JUDGMENT", temporal,
            stance="DISTRUSTS_SOURCE" if "不可信" in text else "TRUSTS_SOURCE",
            evaluation_type="CREDIBILITY",
        ))
    if "有用" in text or "没用" in text:
        result.append(_derived(
            text, "USER_EVALUATION", temporal,
            stance="USEFUL" if "有用" in text else "NOT_USEFUL",
            evaluation_type="USEFULNESS",
        ))
    if not result:
        role = "USER_PREFERENCE" if "喜欢" in text else "USER_PLAN" if any(word in text for word in ("我要", "计划", "明天", "后天")) else "USER_ASSERTION"
        result.append(_derived(text, role, temporal))
    return result


def _derived(statement: str, role: str, temporal: dict[str, str], *, stance: str | None = None, evaluation_type: str | None = None) -> dict[str, Any]:
    freshness = "SHORT_CYCLE" if "市场" in statement else "STRUCTURAL" if role in {"USER_PREFERENCE", "USER_EVALUATION", "USER_BIAS_JUDGMENT", "USER_CREDIBILITY_JUDGMENT"} else "MEDIUM_CYCLE"
    return {"statement": statement, "role": role, "temporal": temporal, "stance": stance, "evaluation_type": evaluation_type, "freshness": freshness}


def _packet_for_derived(episode: ConversationEpisode, item: dict[str, Any], *, store: MemoryStore) -> dict[str, Any]:
    replaces = _stance_target(store, episode, item)
    packet = (build_conversation_correction(
        episode=episode, statement=item["statement"], replaces_atom_id=replaces["id"],
        valid_from=item["temporal"]["resolved_start"], candidate_confidence=0.7,
    ) if replaces else build_conversation_candidate(
        episode=episode, statement=item["statement"], claim_role=item["role"],
        valid_from=item["temporal"]["resolved_start"], candidate_confidence=0.7,
    ))
    atom = packet["atoms"][0]
    conversation = atom["memory_metadata"]["conversation"]
    conversation["memory_palace"] = {
        "temporal": item["temporal"], "event_kind": "PLAN" if item["role"] == "USER_PLAN" else "STANCE" if item["stance"] else "ASSERTION",
        "stance": item["stance"], "evaluation_type": item["evaluation_type"],
        "freshness_profile": item["freshness"], "last_verified_at": episode.recorded_at,
        "revalidation_required": item["freshness"] in {"TRANSIENT", "SHORT_CYCLE"}, "freshness_horizon_hours": 24,
        "epistemic_status": "OWNER_STANCE_NOT_OBJECTIVE_FACT" if item["stance"] else "USER_ASSERTION_CANDIDATE",
        "target_id": _stance_identity(item["statement"]) if item["stance"] else None,
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
    new_dates = {item["temporal"]["resolved_start"][:10] for item in derived}
    for old in store.all_atoms():
        if old["id"] in new_ids or old["knowledge_status"] != "candidate":
            continue
        conversation = old.get("memory_metadata", {}).get("conversation", {})
        palace = conversation.get("memory_palace", {})
        old_date = palace.get("temporal", {}).get("resolved_start", "")[:10]
        if conversation.get("user_scope") == user_scope and conversation.get("project_scope") == project_scope and old_date in new_dates:
            for new_id in new_ids:
                if old["id"] != new_id:
                    new_temporal = next(item["temporal"] for item in derived if item["temporal"]["resolved_start"][:10] == old_date)
                    old_temporal = palace.get("temporal", {})
                    conflict_type = "SCHEDULE_HARD_CONFLICT" if _overlaps(old_temporal, new_temporal) else "SCHEDULE_POTENTIAL_CONFLICT"
                    conflicts.append({"atom_id_a": old["id"], "atom_id_b": new_id, "conflict_type": conflict_type, "resolution_note": "overlapping_fixed_intervals" if conflict_type == "SCHEDULE_HARD_CONFLICT" else "missing_time_or_flexibility"})
    return conflicts


def _overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("resolution_granularity") != "interval" or right.get("resolution_granularity") != "interval":
        return False
    return _aware(left["resolved_start"]) < _aware(right["resolved_end"]) and _aware(right["resolved_start"]) < _aware(left["resolved_end"])


def _verification_time(derived: list[dict[str, Any]], recorded_at: str) -> str:
    starts = [item["temporal"]["resolved_start"] for item in derived]
    return max(starts) if starts else recorded_at


def _retrieval_instant(temporal: dict[str, str], fallback: str) -> str:
    return temporal.get("resolved_start") if temporal.get("temporal_confidence") == "HIGH" else fallback


def _stance_identity(statement: str) -> str:
    stripped = re.sub(r"假的|真的|偏见|没有偏见|我觉得|我认为|是|可信|不可信|有用|没用", "", normalize_text(statement))
    return "stance-" + content_hash(stripped)[:20]


def _stance_target(store: MemoryStore, episode: ConversationEpisode, item: dict[str, Any]) -> dict[str, Any] | None:
    if not item.get("stance"):
        return None
    target_id = _stance_identity(item["statement"])
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
