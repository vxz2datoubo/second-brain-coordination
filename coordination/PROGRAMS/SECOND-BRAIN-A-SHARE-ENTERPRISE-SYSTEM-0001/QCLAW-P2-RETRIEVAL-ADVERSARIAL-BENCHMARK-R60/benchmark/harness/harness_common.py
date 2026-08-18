"""R60 adversarial retrieval benchmark harness, remediation generation 2.

This is a read-only evaluator for the checked-out canonical Phase-3 runtime.
Historical R60 60/60 evidence is REJECTED_INVALID_FALSE_GREEN and is never
reused as current evidence.

Q60-B01: reject grading scans the complete caller-observable bundle surface,
not only bundle.atoms.
Q60-B02: conversation fixture mutations are rebuilt through the canonical
LearningPacket builder/import path; supersession is created through the
canonical correction path.
Q60-B03: forbidden identities are derived from persisted canonical objects,
not optional fixture id_hint values.
"""

from __future__ import annotations

import copy
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
R60_DIR = HERE.parent.parent
REPO_ROOT = R60_DIR
for parent in (HERE, *HERE.parents):
    if (parent / "coordination").is_dir():
        REPO_ROOT = parent
        break

PROG = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001"
PHASE3_SRC = REPO_ROOT / PROG / "PHASE-3-INTEGRATED-OFFLINE-MEMORY" / "src"
LOCAL_ADAPTER_SRC = REPO_ROOT / PROG / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src"
PHASE2_SRC = REPO_ROOT / PROG / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src"
CASES_PATH = R60_DIR / "benchmark" / "cases" / "benchmark_cases.json"
DENIED_STATUSES = {"stale", "revoked", "superseded", "rejected", "quarantined"}

for path in (str(PHASE3_SRC), str(LOCAL_ADAPTER_SRC), str(PHASE2_SRC), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)


@dataclass(frozen=True)
class PersistedFixture:
    index: int
    spec: dict[str, Any]
    atom_id: str
    atom: dict[str, Any]


def load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def _result(case_id: str, observed: str, verdict: str, note: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "observed": observed, "verdict": verdict, "note": note, **extra}




def _plain_atom(stmt: str, scope: str, status: str) -> dict[str, Any]:
    from integrated_offline_memory.canonical import atom_id
    return {
        "id": atom_id(stmt, "observation", scope),
        "atom_type": "observation",
        "canonical_statement": stmt,
        "scope": scope,
        "confidence": 0.5,
        "knowledge_status": status,
        "gpt_access": "FULL_SEMANTIC_ACCESS",
        "transport_visibility": "PUBLIC_SAFE_METADATA_ONLY",
        "authority_level": "CANDIDATE_ONLY",
        "source_refs": [],
        "memory_metadata": {},
    }


def _episode(user: str, project: str, suffix: str):
    from integrated_offline_memory.conversation_memory import ConversationEpisode
    return ConversationEpisode(
        episode_id=f"r60-{suffix}-{user}-{project}",
        user_scope=user,
        project_scope=project,
        source_pointer=f"synthetic://r60/{suffix}/{user}/{project}",
        source_hash="0" * 64,
        privacy_class="PUBLIC_SAFE_SYNTHETIC",
        recorded_at="2026-08-14T00:00:00Z",
    )


def _rebuild_packet(base: dict[str, Any], atom: dict[str, Any]) -> dict[str, Any]:
    from integrated_offline_memory.learning_packet import build_learning_packet
    return build_learning_packet(
        source_manifest_ids=base["source_manifest_ids"],
        source_hash=base["source_hash"],
        validation_report=base["validation_report"],
        evidence_refs=base["evidence_refs"],
        atoms=[atom],
        relations=base.get("relations", []),
        unknowns=base.get("unknowns", []),
        conflicts=base.get("conflicts", []),
        base_knowledge_version=base.get("base_knowledge_version", "candidate-r0"),
    )

def _resolve_alias(value: str, aliases: dict[str, str]) -> str:
    if value in aliases:
        return aliases[value]
    raise ValueError(f"fixture_relation_endpoint_unresolved:{value}")

def _relation_target_ids(setup: dict[str, Any], aliases: dict[str, str]) -> set[str]:
    result: set[str] = set()
    for relation in setup.get("relations", []):
        target = str(relation.get("target", ""))
        if target in aliases:
            result.add(aliases[target])
    return result

def _forbidden_record(record: PersistedFixture, query: dict[str, Any]) -> bool:
    """Return whether the *persisted* canonical object is forbidden for this query.

    This oracle intentionally resolves policy from the stored object rather than
    fixture aliases.  It covers lifecycle, scope/privacy, valid-time and
    short-cycle revalidation so a future runtime regression cannot disappear
    behind an empty forbidden-ID set.
    """
    from datetime import datetime, timedelta, timezone

    def instant(value: Any) -> datetime:
        if not isinstance(value, str):
            raise ValueError("missing_or_invalid_instant")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone_required")
        return parsed.astimezone(timezone.utc)

    spec = record.spec
    q_scopes = set(query.get("scopes", []))
    q_user = query.get("user_scope")
    q_domains = set(query.get("privacy_domains", []))
    persisted = record.atom
    status = persisted.get("knowledge_status")
    requested_states = set(query.get("truth_states", ["candidate", "approved", "conflict", "unknown"]))

    if status not in requested_states or status in DENIED_STATUSES:
        return True
    if persisted.get("gpt_access") != "FULL_SEMANTIC_ACCESS":
        return True
    if persisted.get("transport_visibility") == "RESTRICTED_NEVER_SYNC":
        return True
    if q_scopes and persisted.get("scope") not in q_scopes:
        return True

    valid_at_raw = query.get("valid_at")
    metadata = persisted.get("memory_metadata", {})
    conversation = metadata.get("conversation", {}) if isinstance(metadata, dict) else {}
    knowledge = metadata.get("knowledge", {}) if isinstance(metadata, dict) else {}

    if conversation:
        if not q_scopes or q_user is None or not valid_at_raw:
            return True
        if conversation.get("project_scope") not in q_scopes or conversation.get("user_scope") != q_user:
            return True
        if spec.get("no_packet_lineage"):
            return True
        try:
            point = instant(valid_at_raw)
            start = instant(conversation.get("valid_from"))
            ends = [instant(value) for value in (conversation.get("valid_to"), conversation.get("effective_valid_to")) if value is not None]
        except ValueError:
            return True
        if point < start or (ends and point >= min(ends)):
            return True
        if query.get("intent", "CURRENT") == "CURRENT":
            palace = conversation.get("memory_palace", {})
            if isinstance(palace, dict) and palace.get("revalidation_required") and palace.get("freshness_profile") in {"TRANSIENT", "SHORT_CYCLE"}:
                try:
                    horizon = int(palace.get("freshness_horizon_hours"))
                    last = instant(palace.get("last_verified_at"))
                except (TypeError, ValueError):
                    return True
                if horizon < 1 or point > last + timedelta(hours=horizon):
                    return True
        return False

    if knowledge:
        if not q_scopes or q_user is None or not q_domains or not valid_at_raw:
            return True
        if knowledge.get("project_scope") not in q_scopes or knowledge.get("user_scope") != q_user:
            return True
        if knowledge.get("privacy_domain") not in q_domains:
            return True
        if knowledge.get("safety_class") != "PUBLIC_SAFE_SYNTHETIC":
            return True
        if not knowledge.get("proposition_id") or not knowledge.get("identity_domain_hash"):
            return True
        try:
            point = instant(valid_at_raw)
            start = instant(knowledge.get("valid_from"))
            ends = [instant(value) for value in (knowledge.get("valid_to"), knowledge.get("effective_valid_to")) if value is not None]
        except ValueError:
            return True
        if point < start or (ends and point >= min(ends)):
            return True
        if query.get("intent", "CURRENT") == "CURRENT" and knowledge.get("revalidation_required") and knowledge.get("freshness_profile") in {"TRANSIENT", "SHORT_CYCLE"}:
            try:
                horizon = int(knowledge.get("freshness_horizon_hours"))
                last = instant(knowledge.get("last_verified_at"))
            except (TypeError, ValueError):
                return True
            if horizon < 1 or point > last + timedelta(hours=horizon):
                return True
        return False

    # Ungoverned/plain atoms must fail closed whenever caller identity is bound.
    if q_user is not None:
        return True
    return False

def _forbidden_ids(
    records: list[PersistedFixture], query: dict[str, Any], setup: dict[str, Any], aliases: dict[str, str],
) -> set[str]:
    # B03: actual persisted identities are the oracle. id_hint is only an input alias
    # resolved to the current canonical object identity. It is never itself an oracle ID.
    forbidden = {record.atom_id for record in records if _forbidden_record(record, query)}
    # Corpus case r60-057: relation_depth=0 makes graph-only target identities
    # forbidden even when the target would otherwise be admissible. Resolve the
    # target through the persisted alias map rather than trusting fixture prose.
    if int(query.get("relation_depth", 0)) == 0 and setup.get("relations"):
        forbidden.update(_relation_target_ids(setup, aliases))
    return forbidden


def _walk_exact_ids(value: Any, forbidden: set[str], path: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, str):
        if value in forbidden:
            matches.append(path)
        return matches
    if isinstance(value, dict):
        for key, item in value.items():
            matches.extend(_walk_exact_ids(item, forbidden, f"{path}.{key}"))
        return matches
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            matches.extend(_walk_exact_ids(item, forbidden, f"{path}[{index}]"))
    return matches


def _observable_surfaces(bundle: Any, assembler: Any) -> dict[str, Any]:
    # B01: bundle.to_dict covers atoms, relations, conflicts, unknowns, provenance,
    # source lineage and trust gate. Add assembler caller-visible telemetry/channels.
    return {
        "bundle": bundle.to_dict(),
        "admission_telemetry": assembler.last_admission_report,
        "candidate_channels": assembler.last_candidate_channels,
    }


def _leak_paths(bundle: Any, assembler: Any, forbidden: set[str]) -> dict[str, list[str]]:
    leaks: dict[str, list[str]] = {}
    for name, surface in _observable_surfaces(bundle, assembler).items():
        paths = _walk_exact_ids(surface, forbidden, f"${name}")
        if paths:
            leaks[name] = paths
    return leaks


def _plan(case: dict[str, Any]):
    from integrated_offline_memory.retrieval import QueryPlan
    query = case["query_and_intent"]
    setup = case["setup"]
    return QueryPlan(
        query_text=str(query.get("query_text") or setup.get("query_text") or ""),
        scopes=tuple(query.get("scopes", [])),
        truth_states=tuple(query.get("truth_states", ["candidate", "approved", "conflict", "unknown"])),
        intent=query.get("intent", "CURRENT"),
        user_scope=query.get("user_scope"),
        privacy_domains=tuple(query.get("privacy_domains", [])),
        privacy_aggregate_mode=query.get("privacy_aggregate_mode", "ISOLATED"),
        valid_at=query.get("valid_at"),
        relation_depth=query.get("relation_depth", 0),
        budget=query.get("budget", 50),
        include_unknowns=query.get("include_unknowns", True),
        include_conflicts=query.get("include_conflicts", True),
    )

__all__ = [name for name in globals() if not name.startswith("__")]
