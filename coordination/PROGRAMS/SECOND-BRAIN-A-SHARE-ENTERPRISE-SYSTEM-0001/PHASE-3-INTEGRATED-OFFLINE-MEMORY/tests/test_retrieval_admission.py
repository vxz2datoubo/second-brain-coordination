from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


PHASE_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PHASE_ROOT.parent
for source_root in (
    PHASE_ROOT / "src",
    PROGRAM_ROOT / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src",
    PROGRAM_ROOT / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src",
):
    sys.path.insert(0, str(source_root))

from integrated_offline_memory.conversation_memory import ConversationEpisode, build_conversation_candidate
from integrated_offline_memory.learning_packet import build_learning_packet
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan


NOW = "2026-08-14T12:00:00Z"
USER = "synthetic-user"
PROJECT = "synthetic-project"


def atom(statement: str, **extra: object) -> dict[str, object]:
    result: dict[str, object] = {
        "atom_type": "fact",
        "statement": statement,
        "scope": "synthetic-project",
        "confidence": 0.8,
    }
    result.update(extra)
    return result


def packet(atoms: list[dict[str, object]], *, relations: list[dict[str, object]] | None = None) -> dict[str, object]:
    return build_learning_packet(
        source_manifest_ids=["manifest-r117"],
        source_hash="d" * 64,
        validation_report={"status": "SYNTHETIC_TEST", "research_only": True},
        evidence_refs=["evidence-r117"],
        atoms=atoms,
        relations=relations or [],
    )


class RetrievalAdmissionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)
        self.assembler = ContextAssembler(self.store)

    def _conversation_atom(self) -> dict[str, object]:
        episode = ConversationEpisode(
            episode_id="r117-episode",
            user_scope=USER,
            project_scope=PROJECT,
            source_pointer="synthetic://r117/opaque-source-pointer",
            source_hash="e" * 64,
            privacy_class="PUBLIC_SAFE_SYNTHETIC",
            recorded_at=NOW,
            valid_time=NOW,
            provenance_quality="DIRECT",
        )
        candidate = build_conversation_candidate(
            episode=episode,
            statement="bounded conversation memory",
            claim_role="USER_PREFERENCE",
            valid_from=NOW,
        )
        self.store.import_learning_packet(candidate)
        return self.store.get_atom(candidate["atoms"][0]["id"])

    @staticmethod
    def _conversation_plan(*, intent: str = "CURRENT") -> QueryPlan:
        return QueryPlan(
            query_text="bounded",
            scopes=(PROJECT,),
            user_scope=USER,
            valid_at=NOW,
            intent=intent,
            truth_states=("candidate", "superseded") if intent == "HISTORICAL" else ("candidate",),
        )

    def test_lexical_and_relation_candidates_share_one_redacted_decision_boundary(self) -> None:
        root = atom("root lexical")
        hidden = atom("hidden lexical", transport_visibility="RESTRICTED_NEVER_SYNC")
        provisional = packet([root, hidden])
        relation = {
            "source_atom_id": provisional["atoms"][0]["id"],
            "target_atom_id": provisional["atoms"][1]["id"],
            "relation_type": "supports",
        }
        governed = packet([root, hidden], relations=[relation])
        self.store.import_learning_packet(governed)

        bundle = self.assembler.assemble(QueryPlan(query_text="root hidden", relation_depth=1))
        report = self.assembler.last_admission_report

        self.assertEqual([item["canonical_statement"] for item in bundle.atoms], ["root lexical"])
        self.assertEqual(report, {
            "admitted_count": 1,
            "rejected_counts": {"transport_visibility_denied": 2},
        })
        self.assertNotIn(provisional["atoms"][1]["id"], repr(report))
        self.assertNotIn("synthetic://", repr(report))
        report["rejected_counts"]["transport_visibility_denied"] = 999
        self.assertEqual(self.assembler.last_admission_report["rejected_counts"]["transport_visibility_denied"], 2)

    def test_malformed_conversation_scope_privacy_and_time_bindings_fail_closed_with_codes(self) -> None:
        stored = self._conversation_atom()
        cases = (
            ("project_scope", None, "conversation_project_scope_mismatch"),
            ("user_scope", None, "conversation_user_scope_mismatch"),
            ("privacy_class", "UNCLASSIFIED", "conversation_privacy_binding_invalid"),
            ("valid_from", "not-a-time", "conversation_valid_time_invalid"),
        )
        for field, value, reason in cases:
            with self.subTest(field=field):
                malformed = copy.deepcopy(stored)
                if value is None:
                    malformed["memory_metadata"]["conversation"].pop(field)
                else:
                    malformed["memory_metadata"]["conversation"][field] = value
                decision = self.assembler._admission_decision(malformed, self._conversation_plan())
                self.assertFalse(decision.admitted)
                self.assertEqual(decision.reason, reason)

    def test_current_no_resurrection_and_historical_superseded_are_explicit(self) -> None:
        stored = self._conversation_atom()
        closed = copy.deepcopy(stored)
        closed["knowledge_status"] = "superseded"
        current = self.assembler._admission_decision(
            closed,
            QueryPlan(
                query_text="bounded", scopes=(PROJECT,), user_scope=USER, valid_at=NOW,
                truth_states=("candidate", "superseded"), schema_version="1.0.0",
            ),
        )
        historical = self.assembler._admission_decision(closed, self._conversation_plan(intent="HISTORICAL"))
        stale = copy.deepcopy(stored)
        stale["knowledge_status"] = "stale"
        stale_decision = self.assembler._admission_decision(
            stale,
            QueryPlan(query_text="bounded", truth_states=("stale",)),
        )

        self.assertEqual((current.admitted, current.reason), (False, "lifecycle_not_current"))
        self.assertEqual((historical.admitted, historical.reason), (True, "admitted"))
        self.assertEqual((stale_decision.admitted, stale_decision.reason), (False, "lifecycle_not_current"))

    def test_packet_provenance_is_required_and_reason_never_discloses_identity(self) -> None:
        stored = self._conversation_atom()
        unbound = copy.deepcopy(stored)
        unbound["id"] = "synthetic-unbound-identity"
        decision = self.assembler._admission_decision(unbound, self._conversation_plan())

        self.assertEqual((decision.admitted, decision.reason), (False, "packet_provenance_missing"))
        self.assertNotIn(unbound["id"], decision.reason)
        self.assertNotIn("opaque-source-pointer", decision.reason)


if __name__ == "__main__":
    unittest.main()
