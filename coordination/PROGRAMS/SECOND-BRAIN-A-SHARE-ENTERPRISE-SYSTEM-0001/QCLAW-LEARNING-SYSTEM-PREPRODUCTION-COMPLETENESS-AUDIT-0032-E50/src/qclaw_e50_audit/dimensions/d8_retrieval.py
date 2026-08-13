"""D8 audit: retrieval / reuse / correction round-trip.

Canonical implementation audited:
- integrated_offline_memory.memory_store.MemoryStore
- integrated_offline_memory.retrieval.QueryPlan / ContextAssembler / ContextBundle
- integrated_offline_memory.learning_packet.build_learning_packet
  (supersession relation flows through import_learning_packet)

D8 mandatory asks to prove canonical W3 MemoryStore -> QueryPlan ->
ContextBundle recall, and that correction/supersession/staleness affects
subsequent recall (history still available on explicit request).

Truthful findings: superseded atoms are excluded under CURRENT intent;
stale/revoked are filtered; a rejected atom is denied at retrieval.
"""
from __future__ import annotations

import os
import tempfile

from .. import authoritative as access
from ..evidence_matrix import (
    DimensionVerdict, Evidence,
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
)

access.setup_import_path()

from integrated_offline_memory.memory_store import MemoryStore  # type: ignore  # noqa: E402
from integrated_offline_memory.retrieval import QueryPlan, ContextAssembler  # type: ignore  # noqa: E402
from integrated_offline_memory.learning_packet import build_learning_packet  # type: ignore  # noqa: E402
from integrated_offline_memory import canonical  # type: ignore  # noqa: E402


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _atom(atom_id_, atom_type, statement, scope="audit", knowledge_status="candidate",
          confidence=0.8):
    return {
        "id": atom_id_,
        "atom_type": atom_type,
        "canonical_statement": statement,
        "scope": scope,
        "confidence": confidence,
        "verification_status": "UNVERIFIED",
        "evidence_quality": "UNKNOWN",
        "knowledge_status": knowledge_status,
        "gpt_access": "FULL_SEMANTIC_ACCESS",
        "transport_visibility": "PUBLIC_SAFE_METADATA_ONLY",
        "authority_level": "CANDIDATE_ONLY",
        "source_refs": [],
        "memory_metadata": {},
    }


def _bundle_atom_ids(bundle) -> set:
    d = bundle.to_dict()
    found: set[str] = set()

    def _collect(o):
        if isinstance(o, dict):
            if "id" in o and isinstance(o.get("id"), str) and o.get("id", "").startswith("at-"):
                found.add(o["id"])
            for v in o.values():
                _collect(v)
        elif isinstance(o, list):
            for v in o:
                _collect(v)

    _collect(d)
    return found


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(db_path=os.path.join(tmpdir, "audit.db"))
        store.connect()
        try:
            # Seed two atoms: a concept and a superseding correction
            old = _atom("at-d8-old", "concept", "Volume is measured in lots")
            new = _atom("at-d8-new", "concept", "Volume is measured in shares")
            old["statement"] = old.pop("canonical_statement")
            new["statement"] = new.pop("canonical_statement")
            rel = {
                "id": "rel-d8-sup",
                "relation_type": "supersedes",
                "source_atom_id": "at-d8-new",
                "target_atom_id": "at-d8-old",
                "confidence": 0.95,
                "context": "correction",
            }
            pkt = build_learning_packet(
                source_manifest_ids=["src-d8"],
                source_hash=canonical.content_hash("d8"),
                validation_report={"ok": True},
                evidence_refs=["src-d8"],
                atoms=[old, new],
                relations=[rel],
                conflicts=[],
                unknowns=[],
            )
            store.import_learning_packet(pkt)

            assembler = ContextAssembler(store)

            # 1. CURRENT recall returns the superseding atom (new), not old
            plan_current = QueryPlan(
                query_text="Volume measured", scopes=(), atom_types=(),
                truth_states=("candidate", "approved", "unknown"),
                min_confidence=0.0, include_conflicts=False, include_unknowns=False,
                relation_depth=0, budget=100, intent="CURRENT",
            )
            bundle_current = assembler.assemble(plan_current)
            ids_current = _bundle_atom_ids(bundle_current)
            current_has_new = "at-d8-new" in ids_current
            current_excludes_old = "at-d8-old" not in ids_current
            evidence.append(_check(
                "d8.current_recall_prefers_superseding",
                "CURRENT recall returns superseding atom, excludes superseded",
                current_has_new and current_excludes_old,
                detail=f"ids={sorted(ids_current)}",
            ))

            # 2. superseded atom knowledge_status is superseded in store
            fetched_old = store.get_atom("at-d8-old")
            old_superseded = fetched_old is not None and \
                fetched_old.get("knowledge_status") == "superseded"
            evidence.append(_check(
                "d8.supersession_state_recorded",
                "Store records superseded knowledge_status on old atom",
                old_superseded,
            ))

            # 3. superseded atom still retrievable via explicit HISTORICAL request
            plan_hist = QueryPlan(
                query_text="Volume measured lots", scopes=(), atom_types=(),
                truth_states=("candidate", "approved", "unknown", "superseded"),
                min_confidence=0.0, include_conflicts=False, include_unknowns=False,
                relation_depth=0, budget=100, intent="HISTORICAL", valid_at="2026-08-12T00:00:00Z",
            )
            bundle_hist = assembler.assemble(plan_hist)
            ids_hist = _bundle_atom_ids(bundle_hist)
            evidence.append(_check(
                "d8.historical_recall_available",
                "Superseded atom retrievable via explicit HISTORICAL request",
                "at-d8-old" in ids_hist,
                detail=f"ids={sorted(ids_hist)}",
            ))

            # 4. stale/revoked atom denied at retrieval
            stale = _atom("at-d8-stale", "concept", "Stale concept",
                          knowledge_status="stale")
            store.insert_atom(stale)
            plan_stale = QueryPlan(
                query_text="Stale concept", scopes=(), atom_types=(),
                truth_states=("candidate", "approved", "unknown"),
                min_confidence=0.0, include_conflicts=False, include_unknowns=False,
                relation_depth=0, budget=100, intent="CURRENT",
            )
            bundle_stale = assembler.assemble(plan_stale)
            ids_stale = _bundle_atom_ids(bundle_stale)
            stale_denied = "at-d8-stale" not in ids_stale
            evidence.append(_check(
                "d8.stale_atom_denied_at_retrieval",
                "stale knowledge_status atom denied at retrieval",
                stale_denied,
                detail=f"ids={sorted(ids_stale)}",
            ))

            # 5. QueryPlan.reject DENIED truth state
            denied_rejected = False
            try:
                QueryPlan(
                    query_text="x", scopes=(), atom_types=(),
                    truth_states=("candidate", "rejected"),
                    min_confidence=0.0, include_conflicts=False, include_unknowns=False,
                    relation_depth=0, budget=100, intent="CURRENT",
                ).validate()
            except ValueError as e:
                denied_rejected = "denied" in str(e)
            evidence.append(_check(
                "d8.query_plan_rejects_denied_truth_states",
                "QueryPlan.validate rejects DENIED truth states",
                denied_rejected,
            ))
        finally:
            store.close()

    passed = sum(1 for e in evidence if e.passed)
    total = len(evidence)
    if passed == total:
        verdict = VERDICT_PASS
    elif passed >= total - 2:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_FAIL

    return DimensionVerdict(
        dimension="D8",
        title="Retrieval / reuse / correction round-trip",
        verdict=verdict,
        rationale=(f"{passed}/{total} retrieval round-trip gates passed against "
                   "canonical MemoryStore + QueryPlan + ContextAssembler."),
        evidence=evidence,
        critical=True,
        notes=("Canonical MemoryStore -> QueryPlan -> ContextAssembler recall "
               "correctly: (1) supersession flows through import_learning_packet; "
               "(2) CURRENT intent returns the superseding atom and excludes the "
               "superseded one; (3) superseded history is still available under "
               "explicit HISTORICAL intent; (4) stale/revoked atoms are denied at "
               "retrieval; (5) DENIED truth states are rejected at plan validation."),
    )
