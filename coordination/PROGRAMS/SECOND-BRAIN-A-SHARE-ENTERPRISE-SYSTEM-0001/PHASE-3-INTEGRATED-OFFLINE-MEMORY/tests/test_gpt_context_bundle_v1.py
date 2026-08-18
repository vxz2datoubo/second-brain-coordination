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

from integrated_offline_memory.learning_packet import build_learning_packet
from integrated_offline_memory.conversation_memory import ConversationEpisode, build_conversation_candidate
from integrated_offline_memory.knowledge_reconciliation import KnowledgeEpisode, capture_knowledge
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.retrieval import ContextAssembler, GPTSecondBrainContextBundle, QueryPlan


def atom(statement: str, **extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "atom_type": "fact",
        "statement": statement,
        "scope": "synthetic-project",
        "confidence": 0.8,
    }
    value.update(extra)
    return value


def packet(
    atoms: list[dict[str, object]], *, relations: list[dict[str, object]],
    conflicts: list[dict[str, object]], unknowns: list[dict[str, object]],
) -> dict[str, object]:
    return build_learning_packet(
        source_manifest_ids=["manifest-r119"],
        source_hash="f" * 64,
        validation_report={"status": "SYNTHETIC_TEST", "research_only": True},
        evidence_refs=["evidence-r119"],
        atoms=atoms,
        relations=relations,
        conflicts=conflicts,
        unknowns=unknowns,
    )


NOW = "2026-08-15T12:00:00Z"
USER = "synthetic-user"
PROJECT = "synthetic-project"


class GPTContextBundleV1TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)
        self.assembler = ContextAssembler(self.store)

    def _conversation(self, statement: str, claim_role: str) -> None:
        episode = ConversationEpisode(
            episode_id="r120-" + claim_role.lower(), user_scope=USER, project_scope=PROJECT,
            source_pointer="synthetic://r120/owner-context", source_hash="a" * 64,
            privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at=NOW, valid_time=NOW, provenance_quality="DIRECT",
        )
        self.store.import_learning_packet(build_conversation_candidate(
            episode=episode, statement=statement, claim_role=claim_role, valid_from=NOW,
        ))

    def test_endpoint_safe_projection_keeps_evidence_roles_and_deterministic_scores(self) -> None:
        root = atom("r119 root evidence")
        support = atom("r119 supporting evidence")
        counter = atom("r119 alternative evidence")
        hidden = atom("r119 hidden endpoint", transport_visibility="RESTRICTED_NEVER_SYNC")
        provisional = packet([root, support, counter, hidden], relations=[], conflicts=[], unknowns=[])
        atom_ids = {item["canonical_statement"]: item["id"] for item in provisional["atoms"]}
        root_id = atom_ids["r119 root evidence"]
        support_id = atom_ids["r119 supporting evidence"]
        counter_id = atom_ids["r119 alternative evidence"]
        hidden_id = atom_ids["r119 hidden endpoint"]
        governed = packet(
            [root, support, counter, hidden],
            relations=[
                {"source_atom_id": support_id, "target_atom_id": root_id, "relation_type": "supports"},
                {"source_atom_id": counter_id, "target_atom_id": root_id, "relation_type": "contradicts"},
                {"source_atom_id": root_id, "target_atom_id": hidden_id, "relation_type": "supports"},
            ],
            conflicts=[
                {"atom_id_a": root_id, "atom_id_b": hidden_id, "conflict_type": "DIRECT"},
                {"atom_id_a": support_id, "atom_id_b": counter_id, "conflict_type": "DIRECT"},
            ],
            unknowns=[
                {"question": "safe unresolved item", "scope": "synthetic-project", "related_atom_ids": [root_id, support_id]},
                {"question": "hidden unresolved item", "scope": "synthetic-project", "related_atom_ids": [root_id, hidden_id]},
            ],
        )
        self.store.import_learning_packet(governed)
        plan = QueryPlan(query_text="r119 root", relation_depth=1, budget=3)

        legacy = self.assembler.assemble(plan)
        projection = self.assembler.assemble_v1(plan)
        repeated = self.assembler.assemble_gpt_context_bundle_v1(plan)

        self.assertIsInstance(projection, GPTSecondBrainContextBundle)
        self.assertEqual(projection.schema_version, "GPTSecondBrainContextBundle/v1")
        self.assertEqual(projection.to_dict(), repeated.to_dict())
        self.assertNotIn(hidden_id, repr(legacy.relations))
        self.assertNotIn(hidden_id, repr(legacy.conflicts))
        self.assertNotIn(hidden_id, repr(legacy.unknowns))
        self.assertNotIn(hidden_id, repr(projection.to_dict()))
        self.assertEqual(len(projection.evidence["conflicts"]), 1)
        self.assertEqual([item["atom_id"] for item in projection.evidence["strongest_support"]], [support_id])
        self.assertEqual([item["atom_id"] for item in projection.evidence["strongest_counter_or_alternative"]], [counter_id])
        self.assertEqual([item["question"] for item in projection.evidence["unknowns"]], ["safe unresolved item"])
        self.assertEqual(projection.trust_gate["reason"], "scope_privacy_status_and_valid_time_passed")
        self.assertEqual(projection.trust_gate["materiality"]["state"], "UNKNOWN")
        self.assertEqual(projection.ranking["omitted_due_to_budget"], 0)
        self.assertEqual(
            [item["atom_id"] for item in projection.ranking["score_components"]],
            [atom["id"] for atom in legacy.atoms],
        )
        for item in projection.provenance["adjacency"]:
            self.assertNotIn("pointer", repr(item))
            self.assertNotIn("r119 root evidence", repr(item))

    def test_no_eligible_evidence_projects_only_a_non_sensitive_abstain(self) -> None:
        self.store.import_learning_packet(packet(
            [atom("r119 foreign", scope="foreign-project")], relations=[], conflicts=[], unknowns=[],
        ))
        projection = self.assembler.assemble_v1(QueryPlan(query_text="r119 foreign", scopes=("synthetic-project",)))

        self.assertEqual(projection.trust_gate, {
            "outcome": "ABSTAIN", "reason": "no_in_scope_valid_candidate", "intent": "CURRENT",
        })
        self.assertEqual(projection.admission, {"admitted_count": 0, "rejected_counts": {}})
        self.assertNotIn("foreign", repr(projection.to_dict()))

    def test_v1_context_budgets_emit_only_omission_counts(self) -> None:
        root, first, second = atom("r119 budget root"), atom("r119 budget first"), atom("r119 budget second")
        provisional = packet([root, first, second], relations=[], conflicts=[], unknowns=[])
        atom_ids = {item["canonical_statement"]: item["id"] for item in provisional["atoms"]}
        root_id = atom_ids["r119 budget root"]
        first_id = atom_ids["r119 budget first"]
        second_id = atom_ids["r119 budget second"]
        self.store.import_learning_packet(packet(
            [root, first, second],
            relations=[
                {"source_atom_id": root_id, "target_atom_id": first_id, "relation_type": "supports"},
                {"source_atom_id": root_id, "target_atom_id": second_id, "relation_type": "supports"},
            ],
            conflicts=[],
            unknowns=[],
        ))
        plan = QueryPlan(query_text="r119 budget root", budget=1)
        legacy = self.assembler.assemble(plan)
        projection = self.assembler.assemble_v1(plan)

        self.assertEqual(len(legacy.relations), 2)
        self.assertEqual(len(projection.context["relations"]), 1)
        self.assertEqual(projection.context["omitted_due_to_budget"], {
            "relations": 1, "conflicts": 0, "unknowns": 0,
        })
        omitted_relation_id = next(
            relation["id"] for relation in legacy.relations
            if relation["id"] != projection.context["relations"][0]["id"]
        )
        self.assertNotIn(omitted_relation_id, repr(projection.context["relations"]))

    def test_r132_structural_analogy_is_default_off_non_evidentiary_and_independently_budgeted(self) -> None:
        atoms = [
            atom("r132 analogue alpha"), atom("r132 analogue beta"), atom("r132 analogue gamma"),
        ]
        self.store.import_learning_packet(packet(atoms, relations=[], conflicts=[], unknowns=[]))
        disabled = QueryPlan(query_text="r132 analogue", budget=3)
        explicitly_disabled = QueryPlan(
            query_text="r132 analogue", budget=3, include_structural_analogies=False, analogy_budget=1,
        )
        enabled = QueryPlan(
            query_text="r132 analogue", budget=3, include_structural_analogies=True, analogy_budget=1,
        )
        self.assertEqual(disabled.plan_hash, explicitly_disabled.plan_hash)

        default_projection = self.assembler.assemble_v1(disabled)
        enabled_projection = self.assembler.assemble_v1(enabled)
        repeated = self.assembler.assemble_v1(enabled)

        self.assertEqual(default_projection.evidence, enabled_projection.evidence)
        self.assertEqual(default_projection.ranking, enabled_projection.ranking)
        self.assertEqual(default_projection.trust_gate, enabled_projection.trust_gate)
        self.assertEqual(default_projection.admission, enabled_projection.admission)
        self.assertEqual(enabled_projection.to_dict(), repeated.to_dict())
        self.assertEqual(len(enabled_projection.context["analogies"]), 1)
        self.assertEqual(enabled_projection.context["omitted_due_to_budget"]["analogies"], 2)
        item = enabled_projection.context["analogies"][0]
        self.assertEqual(item["schema_version"], "AnalogyItem/v1")
        self.assertTrue(item["non_evidentiary"])
        self.assertNotIn("atom_id", item)
        self.assertNotIn("r132 analogue", repr(item))

    def test_r132_hidden_relation_neighbors_are_oracle_equivalent_before_features(self) -> None:
        def projection_with(hidden_count: int):
            store = MemoryStore().connect()
            self.addCleanup(store.close)
            visible_source = atom("r132 visible source")
            visible_target = atom("r132 visible target")
            hidden = [
                atom("opaque-neighbor-" + str(index), transport_visibility="RESTRICTED_NEVER_SYNC")
                for index in range(hidden_count)
            ]
            all_atoms = [visible_source, visible_target, *hidden]
            provisional = packet(all_atoms, relations=[], conflicts=[], unknowns=[])
            ids = {item["canonical_statement"]: item["id"] for item in provisional["atoms"]}
            relations = [
                {
                    "source_atom_id": ids["r132 visible source"],
                    "target_atom_id": ids["opaque-neighbor-" + str(index)],
                    "relation_type": "supports",
                }
                for index in range(hidden_count)
            ]
            store.import_learning_packet(packet(all_atoms, relations=relations, conflicts=[], unknowns=[]))
            return ContextAssembler(store).assemble_v1(QueryPlan(
                query_text="r132 visible", relation_depth=1, budget=4,
                include_structural_analogies=True, analogy_budget=4,
            ))

        projections = [projection_with(count) for count in (0, 1, 3)]
        first = projections[0]
        for projection in projections[1:]:
            self.assertEqual(projection.context["analogies"], first.context["analogies"])
            self.assertEqual(projection.context["omitted_due_to_budget"], first.context["omitted_due_to_budget"])
            self.assertEqual(projection.admission, first.admission)
            self.assertEqual(projection.evidence, first.evidence)
            self.assertEqual(projection.ranking, first.ranking)
            self.assertEqual(projection.trust_gate, first.trust_gate)
            self.assertNotIn("opaque-neighbor", repr(projection.to_dict()))

    def test_r132_foreign_revoked_and_invalid_time_endpoints_are_suppressed(self) -> None:
        for label, blocked_extra in (
            ("foreign", {"scope": "foreign-project"}),
            ("revoked", {"knowledge_status": "revoked"}),
        ):
            with self.subTest(label=label):
                store = MemoryStore().connect()
                self.addCleanup(store.close)
                visible_a = atom("r132 endpoint visible alpha")
                visible_b = atom("r132 endpoint visible beta")
                blocked = atom("r132 endpoint blocked " + label, **blocked_extra)
                store.import_learning_packet(packet([visible_a, visible_b, blocked], relations=[], conflicts=[], unknowns=[]))
                projection = ContextAssembler(store).assemble_v1(QueryPlan(
                    query_text="r132 endpoint", scopes=(PROJECT,), budget=3,
                    include_structural_analogies=True, analogy_budget=4,
                ))
                self.assertEqual(len(projection.context["analogies"]), 1)
                self.assertNotIn("blocked " + label, repr(projection.to_dict()))

        visible_a = ConversationEpisode(
            episode_id="r132-time-visible-a", user_scope=USER, project_scope=PROJECT,
            source_pointer="synthetic://r132/time/a", source_hash="1" * 64,
            privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at=NOW, valid_time=NOW, provenance_quality="DIRECT",
        )
        visible_b = ConversationEpisode(
            episode_id="r132-time-visible-b", user_scope=USER, project_scope=PROJECT,
            source_pointer="synthetic://r132/time/b", source_hash="2" * 64,
            privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at=NOW, valid_time=NOW, provenance_quality="DIRECT",
        )
        expired = ConversationEpisode(
            episode_id="r132-time-expired", user_scope=USER, project_scope=PROJECT,
            source_pointer="synthetic://r132/time/expired", source_hash="3" * 64,
            privacy_class="PUBLIC_SAFE_SYNTHETIC", recorded_at="2026-08-10T12:00:00Z",
            valid_time="2026-08-10T12:00:00Z", provenance_quality="DIRECT",
        )
        packets = (
            build_conversation_candidate(episode=visible_a, statement="r132 time visible alpha", claim_role="USER_ASSERTION", valid_from=NOW),
            build_conversation_candidate(episode=visible_b, statement="r132 time visible beta", claim_role="USER_ASSERTION", valid_from=NOW),
            build_conversation_candidate(
                episode=expired, statement="r132 time expired", claim_role="USER_ASSERTION",
                valid_from="2026-08-10T12:00:00Z", valid_to="2026-08-11T12:00:00Z",
            ),
        )
        for item in packets:
            self.store.import_learning_packet(item)
        projection = self.assembler.assemble_v1(QueryPlan(
            query_text="r132 time", scopes=(PROJECT,), user_scope=USER, valid_at=NOW,
            include_structural_analogies=True, analogy_budget=4,
        ))
        self.assertEqual(len(projection.context["analogies"]), 1)
        self.assertNotIn("r132 time expired", repr(projection.to_dict()))

    def test_r132_lifecycle_and_fresh_store_construction_are_deterministic(self) -> None:
        current_a = atom("r132 lifecycle current alpha")
        current_b = atom("r132 lifecycle current beta")
        superseded = atom("r132 lifecycle former", knowledge_status="superseded")
        governed = packet([current_a, current_b, superseded], relations=[], conflicts=[], unknowns=[])
        ids = {item["canonical_statement"]: item["id"] for item in governed["atoms"]}
        current_plan = QueryPlan(
            query_text="r132 lifecycle", budget=3, include_structural_analogies=True, analogy_budget=4,
        )
        historical_plan = QueryPlan(
            query_text="r132 lifecycle", budget=3, intent="HISTORICAL", valid_at=NOW,
            truth_states=("candidate", "superseded"), include_structural_analogies=True, analogy_budget=4,
        )
        self.store.import_learning_packet(governed)
        current = self.assembler.assemble_v1(current_plan)
        historical = self.assembler.assemble_v1(historical_plan)
        self.assertNotIn(ids["r132 lifecycle former"], repr(current.to_dict()))
        self.assertIn(ids["r132 lifecycle former"], repr(historical.to_dict()))

        rebuilt = MemoryStore().connect()
        self.addCleanup(rebuilt.close)
        rebuilt.import_learning_packet(governed)
        self.assertEqual(
            current.to_dict(), ContextAssembler(rebuilt).assemble_v1(current_plan).to_dict(),
        )

    def test_owner_and_source_interpretation_roles_never_become_unlabeled_objective_evidence(self) -> None:
        self._conversation("r120 preference", "USER_PREFERENCE")
        self._conversation("r120 plan", "USER_PLAN")
        owner_projection = self.assembler.assemble_v1(QueryPlan(
            query_text="r120", scopes=(PROJECT,), user_scope=USER, valid_at=NOW,
        ))

        self.assertEqual(owner_projection.evidence["current_lineage_heads"], ())
        self.assertEqual(owner_projection.evidence["strongest_support"], ())
        self.assertEqual(
            {item["claim_role"] for item in owner_projection.context["owner_context"]},
            {"USER_PREFERENCE", "USER_PLAN"},
        )

        episode = KnowledgeEpisode(
            episode_id="r120-interpretation", user_scope=USER, project_scope=PROJECT,
            privacy_domain="synthetic-r120", source_pointer="synthetic://r120/interpretation",
            source_text="Interpretation: r120 source interpretation", recorded_at=NOW, available_at=NOW,
        )
        capture_knowledge(store=self.store, episode=episode, semantic_query="source context")
        interpretation_projection = self.assembler.assemble_v1(QueryPlan(
            query_text="r120 source interpretation", scopes=(PROJECT,), user_scope=USER,
            privacy_domains=("synthetic-r120",), valid_at=NOW,
        ))

        self.assertEqual(interpretation_projection.evidence["current_lineage_heads"], ())
        self.assertEqual(interpretation_projection.evidence["strongest_support"], ())
        self.assertEqual(
            [item["epistemic_role"] for item in interpretation_projection.context["interpretation_context"]],
            ["SOURCE_INTERPRETATION"],
        )

    def test_same_scope_unbound_explicit_open_unknown_is_fail_closed_without_count(self) -> None:
        self.store.import_learning_packet(packet(
            [atom("r120 explicit root")], relations=[], conflicts=[],
            unknowns=[{"question": "r121 scoped unbound explicit unknown", "scope": PROJECT, "related_atom_ids": []}],
        ))

        projection = self.assembler.assemble_v1(QueryPlan(query_text="", scopes=(PROJECT,)))

        self.assertEqual(projection.evidence["unknowns"], ())
        self.assertEqual(projection.context["unknown_omission_counts"], {"unbound_explicit_unknown_omitted": 0})
        self.assertEqual(projection.context["unknown_omission_capability"], "UNBOUND_UNKNOWN_BINDING_UNAVAILABLE")
        self.assertNotIn("r121 scoped unbound explicit unknown", repr(projection.to_dict()))

    def test_foreign_scope_unbound_unknown_does_not_change_public_omission_count(self) -> None:
        self.store.import_learning_packet(packet(
            [atom("r121 root")], relations=[], conflicts=[],
            unknowns=[{"question": "r121 foreign unbound unknown", "scope": "foreign-project", "related_atom_ids": []}],
        ))

        projection = self.assembler.assemble_v1(QueryPlan(query_text="", scopes=(PROJECT,)))

        self.assertEqual(projection.context["unknown_omission_counts"], {"unbound_explicit_unknown_omitted": 0})
        self.assertNotIn("foreign", repr(projection.to_dict()))

    def test_user_or_privacy_bound_plan_cannot_count_unbound_unknown(self) -> None:
        self.store.import_learning_packet(packet(
            [atom("r121 private root")], relations=[], conflicts=[],
            unknowns=[{"question": "r121 unbound private unknown", "scope": PROJECT, "related_atom_ids": []}],
        ))

        for plan in (
            QueryPlan(query_text="", scopes=(PROJECT,), user_scope=USER),
            QueryPlan(query_text="", scopes=(PROJECT,), privacy_domains=("synthetic-r121",)),
        ):
            with self.subTest(plan=plan):
                projection = self.assembler.assemble_v1(plan)
                self.assertEqual(
                    projection.context["unknown_omission_counts"], {"unbound_explicit_unknown_omitted": 0},
                )
                self.assertNotIn("r121 unbound private unknown", repr(projection.to_dict()))

    def test_zero_one_many_unbound_unknowns_have_identical_complete_public_bundle(self) -> None:
        plans = (
            QueryPlan(query_text=""),
            QueryPlan(query_text="", scopes=(PROJECT,)),
            QueryPlan(query_text="", scopes=(PROJECT,), user_scope=USER),
            QueryPlan(query_text="", scopes=(PROJECT,), privacy_domains=("synthetic-r122",)),
        )
        baseline_projections: list[dict[str, object]] | None = None
        internal_packet_hashes: list[str] = []

        for count in (0, 1, 3):
            store = MemoryStore().connect()
            try:
                value = packet(
                    [atom("r122 stable root")], relations=[], conflicts=[],
                    unknowns=[
                        {
                            "question": f"r122 endpoint-free unknown {index}",
                            "scope": PROJECT,
                            "related_atom_ids": [],
                        }
                        for index in range(count)
                    ],
                )
                store.import_learning_packet(value)
                internal_packet_hashes.append(value["packet_content_hash"])
                self.assertEqual(
                    store.provenance_for_atom(value["atoms"][0]["id"])[0]["packet_content_hash"],
                    value["packet_content_hash"],
                )
                projections = [ContextAssembler(store).assemble_v1(plan) for plan in plans]
                public_projections = [projection.to_dict() for projection in projections]
                if baseline_projections is None:
                    baseline_projections = public_projections
                else:
                    self.assertEqual(public_projections, baseline_projections)
                for projection in projections:
                    self.assertEqual(projection.evidence["unknowns"], ())
                    self.assertEqual(
                        projection.context["unknown_omission_capability"], "UNBOUND_UNKNOWN_BINDING_UNAVAILABLE",
                    )
                    self.assertNotIn("packet_content_hashes", repr(projection.provenance))
                    self.assertNotIn("r122 endpoint-free unknown", repr(projection.to_dict()))
            finally:
                store.close()
        self.assertEqual(len(set(internal_packet_hashes)), 3)


if __name__ == "__main__":
    unittest.main()
