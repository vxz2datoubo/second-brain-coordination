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


class GPTContextBundleV1TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryStore().connect()
        self.addCleanup(self.store.close)
        self.assembler = ContextAssembler(self.store)

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
        self.assertEqual(projection.trust_gate["reason"], "material_conflict_present")
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


if __name__ == "__main__":
    unittest.main()
