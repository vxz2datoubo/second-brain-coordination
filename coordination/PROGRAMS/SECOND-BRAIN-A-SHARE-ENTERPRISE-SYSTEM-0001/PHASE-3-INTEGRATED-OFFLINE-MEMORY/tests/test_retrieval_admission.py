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
from integrated_offline_memory.knowledge_reconciliation import KnowledgeEpisode, capture_knowledge
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

    def _conversation_atom(
        self, *, user_scope: str = USER, project_scope: str = PROJECT, statement: str = "bounded conversation memory",
    ) -> dict[str, object]:
        episode = ConversationEpisode(
            episode_id="r117-episode",
            user_scope=user_scope,
            project_scope=project_scope,
            source_pointer="synthetic://r117/opaque-source-pointer",
            source_hash="e" * 64,
            privacy_class="PUBLIC_SAFE_SYNTHETIC",
            recorded_at=NOW,
            valid_time=NOW,
            provenance_quality="DIRECT",
        )
        candidate = build_conversation_candidate(
            episode=episode,
            statement=statement,
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
            "rejected_counts": {},
        })
        self.assertNotIn(provisional["atoms"][1]["id"], repr(report))
        self.assertNotIn("synthetic://", repr(report))
        report["rejected_counts"]["synthetic_mutation"] = 999
        self.assertEqual(self.assembler.last_admission_report["rejected_counts"], {})

    def test_foreign_and_restricted_rare_terms_are_publicly_indistinguishable_from_no_match(self) -> None:
        def empty_report(plan: QueryPlan) -> dict[str, object]:
            empty_store = MemoryStore().connect()
            try:
                empty_assembler = ContextAssembler(empty_store)
                empty_assembler.assemble(plan)
                return empty_assembler.last_admission_report
            finally:
                empty_store.close()

        cases: list[tuple[str, QueryPlan]] = []
        self._conversation_atom(user_scope="foreign-user", statement="rareforeignuser")
        cases.append((
            "foreign_user",
            QueryPlan(query_text="rareforeignuser", scopes=(PROJECT,), user_scope=USER, valid_at=NOW),
        ))
        self._conversation_atom(project_scope="foreign-project", statement="rareforeignproject")
        cases.append((
            "foreign_project",
            QueryPlan(query_text="rareforeignproject", scopes=(PROJECT,), user_scope=USER, valid_at=NOW),
        ))
        privacy_episode = KnowledgeEpisode(
            episode_id="r118-privacy",
            user_scope=USER,
            project_scope=PROJECT,
            privacy_domain="synthetic-foreign",
            source_pointer="synthetic://r118/foreign-privacy",
            source_text="Fact: rareforeignprivacy evidence",
            recorded_at=NOW,
            available_at=NOW,
        )
        capture_knowledge(store=self.store, episode=privacy_episode, semantic_query="evidence context")
        cases.append((
            "foreign_privacy",
            QueryPlan(
                query_text="rareforeignprivacy", scopes=(PROJECT,), user_scope=USER,
                privacy_domains=("synthetic-visible",), valid_at=NOW, atom_types=("knowledge_atom",),
            ),
        ))
        self.store.import_learning_packet(packet([atom("rarerestricted", transport_visibility="RESTRICTED_NEVER_SYNC")]))
        cases.append(("restricted_transport", QueryPlan(query_text="rarerestricted")))

        for name, plan in cases:
            with self.subTest(name=name):
                bundle = self.assembler.assemble(plan)
                self.assertEqual(bundle.atoms, ())
                self.assertEqual(self.assembler.last_admission_report, empty_report(plan))

    def test_observable_rejection_is_counted_once_across_lexical_and_relation_channels(self) -> None:
        root = atom("visible root")
        low_confidence = atom("visible low confidence", confidence=0.1)
        provisional = packet([root, low_confidence])
        governed = packet([root, low_confidence], relations=[{
            "source_atom_id": provisional["atoms"][0]["id"],
            "target_atom_id": provisional["atoms"][1]["id"],
            "relation_type": "supports",
        }])
        self.store.import_learning_packet(governed)

        bundle = self.assembler.assemble(
            QueryPlan(query_text="visible root confidence", relation_depth=1, min_confidence=0.8)
        )

        self.assertEqual([item["canonical_statement"] for item in bundle.atoms], ["visible root"])
        self.assertEqual(self.assembler.last_admission_report, {
            "admitted_count": 1,
            "rejected_counts": {"confidence_below_minimum": 1},
        })

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
        revoked = copy.deepcopy(stored)
        revoked["knowledge_status"] = "revoked"
        revoked_decision = self.assembler._admission_decision(
            revoked,
            QueryPlan(query_text="bounded", truth_states=("revoked",)),
        )

        self.assertEqual((current.admitted, current.reason), (False, "lifecycle_not_current"))
        self.assertEqual((historical.admitted, historical.reason), (True, "admitted"))
        self.assertEqual((stale_decision.admitted, stale_decision.reason), (False, "lifecycle_not_current"))
        self.assertEqual((revoked_decision.admitted, revoked_decision.reason), (False, "lifecycle_not_current"))

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
