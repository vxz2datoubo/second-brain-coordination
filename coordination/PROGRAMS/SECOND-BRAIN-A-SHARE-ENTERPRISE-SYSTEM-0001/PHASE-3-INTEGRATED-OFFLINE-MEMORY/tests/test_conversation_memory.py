from __future__ import annotations

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
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan


def episode() -> ConversationEpisode:
    return ConversationEpisode(
        episode_id="synthetic-episode-001",
        user_scope="synthetic-user-a",
        project_scope="synthetic-project-a",
        source_pointer="synthetic://episode/001",
        source_hash="a" * 64,
        privacy_class="PUBLIC_SAFE_SYNTHETIC",
        recorded_at="2026-08-12T00:00:00Z",
    )


class ConversationCandidateTestCase(unittest.TestCase):
    def test_user_candidate_is_deterministic_and_candidate_only(self) -> None:
        first = build_conversation_candidate(
            episode=episode(), statement="synthetic durable preference", claim_role="USER_PREFERENCE", valid_from="2026-08-12T00:00:00Z"
        )
        second = build_conversation_candidate(
            episode=episode(), statement="synthetic durable preference", claim_role="USER_PREFERENCE", valid_from="2026-08-12T00:00:00Z"
        )
        self.assertEqual(first["packet_id"], second["packet_id"])
        self.assertFalse(first["authority_write"])
        self.assertEqual(first["atoms"][0]["atom_type"], "conversation_memory")

    def test_assistant_analysis_is_not_admitted_as_user_memory(self) -> None:
        with self.assertRaisesRegex(ValueError, "assistant_claim_cannot_be_user_memory"):
            build_conversation_candidate(
                episode=episode(), statement="synthetic assistant analysis", claim_role="ASSISTANT_ANALYSIS", valid_from="2026-08-12T00:00:00Z"
            )

    def test_sessions_a_and_b_use_existing_packet_store_query_and_bundle(self) -> None:
        # Session A: a public-safe synthetic episode becomes an existing W3 packet.
        candidate = build_conversation_candidate(
            episode=episode(),
            statement="synthetic durable preference",
            claim_role="USER_PREFERENCE",
            valid_from="2026-08-12T00:00:00Z",
        )
        store = MemoryStore().connect()
        try:
            first = store.import_learning_packet(candidate)
            duplicate = store.import_learning_packet(candidate)
            self.assertEqual(first["status"], "IMPORTED")
            self.assertEqual(duplicate["status"], "IDEMPOTENT_DUPLICATE")

            # Session B: existing QueryPlan/ContextBundle recalls it by project scope.
            bundle = ContextAssembler(store).assemble(QueryPlan(
                query_text="synthetic durable preference",
                scopes=("synthetic-project-a",),
                truth_states=("candidate",),
            ))
            self.assertEqual(len(bundle.atoms), 1)
            self.assertEqual(bundle.atoms[0]["canonical_statement"], "synthetic durable preference")
            self.assertEqual(bundle.source_lineage, ("conversation://" + episode().manifest_id,))
            self.assertEqual(bundle.semantic_access_state, "FULL_SEMANTIC_ACCESS_CANDIDATE_ONLY")
        finally:
            store.close()
