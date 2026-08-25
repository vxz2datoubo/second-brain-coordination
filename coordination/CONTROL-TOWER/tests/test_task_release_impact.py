from __future__ import annotations

import copy
import unittest

from task_release_impact import ImpactGateError, evaluate_release_candidate


def base_candidate() -> dict:
    return {
        "schema_version": "TaskReleaseCandidate/v1",
        "release_candidate_id": "R149-CASE-001",
        "source_signal_refs": ["issue://451"],
        "desired_effect": "Add a bounded capability without duplicating authority or breaking consumers.",
        "observations": [
            {
                "scope": "second-brain/main",
                "revision": "71c70f6bc3683eff4c19020a7d4cc998517c6ba1",
                "evidence_ref": "git://second-brain/main@71c70f6",
                "status": "CURRENT",
            }
        ],
        "proposed_target_domain": "SECOND_BRAIN_SYSTEM",
        "proposed_write_surface": {
            "write_paths": ["coordination/CONTROL-TOWER/task_release_impact.py"],
            "read_paths": ["coordination/CONTROL-TOWER/control_tower.py"],
            "interfaces": [
                {"name": "ProgramControlTowerReleaseEvidence", "mode": "write", "frozen": True}
            ],
            "read_domains": ["SECOND_BRAIN_SYSTEM"],
            "write_domains": ["SECOND_BRAIN_SYSTEM"],
            "authority_claims": [],
        },
        "materiality": "MATERIAL",
        "risk": ["consumer drift"],
        "out_of_scope": ["automatic task execution"],
        "capability_inventory": [
            {
                "component_id": "ProgramControlTower",
                "decision": "EXTEND",
                "satisfies_requirement": False,
                "evidence_refs": ["coordination/CONTROL-TOWER/control_tower.py"],
            }
        ],
        "relations": [],
        "reverse_consumers": [
            {
                "consumer_id": "lane_claims",
                "impact": "CONSUMER_REVALIDATION_ONLY",
                "evidence_refs": ["coordination/CONTROL-TOWER/lane_claims.py"],
            }
        ],
        "consumer_inventory_complete": True,
        "authority_binding": {
            "owner_domain": "SECOND_BRAIN_SYSTEM",
            "writeback_owner": "PROGRAM_CONTROL_TOWER",
            "compatible": True,
            "would_create_second_writer": False,
            "would_create_second_truth": False,
        },
        "composition": {
            "optional": False,
            "can_compose": False,
            "core_invariant": True,
            "missing_capability_behavior": "NOT_APPLICABLE",
            "removal_preserves_unrelated_core": "UNKNOWN",
            "justification": "Release governance is a foundational Control Tower invariant, not an optional provider.",
        },
        "synchronized_change_set": ["ProgramControlTowerReleaseEvidence"],
        "regression_revalidation_set": ["control_tower", "lane_claims"],
        "unaffected_set": [
            {
                "component_id": "SignalTower",
                "evidence_refs": ["boundary://signal-is-not-task"],
            }
        ],
        "unresolved_unknowns": [],
        "existing_work_items": [],
    }


class TaskReleaseImpactAcceptanceTests(unittest.TestCase):
    def test_01_existing_capability_already_satisfies_no_new_task(self) -> None:
        candidate = base_candidate()
        candidate["capability_inventory"] = [
            {
                "component_id": "ExistingSubsystem",
                "decision": "REUSE_AS_IS",
                "satisfies_requirement": True,
                "evidence_refs": ["canonical://existing-subsystem"],
            }
        ]
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "NO_TASK_ALREADY_SATISFIED")

    def test_02_overlap_two_modules_preserves_merge_retire_decision_not_third_module(self) -> None:
        candidate = base_candidate()
        candidate["capability_inventory"] = [
            {
                "component_id": "OldRouterA",
                "decision": "MERGE",
                "satisfies_requirement": False,
                "evidence_refs": ["canonical://router-a"],
            },
            {
                "component_id": "OldRouterB",
                "decision": "DEPRECATE",
                "satisfies_requirement": False,
                "evidence_refs": ["canonical://router-b"],
            },
        ]
        receipt = evaluate_release_candidate(candidate)
        decisions = {item["component_id"]: item["decision"] for item in receipt["capability_reuse_decisions"]}
        self.assertEqual(decisions, {"OldRouterA": "MERGE", "OldRouterB": "DEPRECATE"})
        self.assertNotIn("NEW_MODULE_JUSTIFIED", decisions.values())
        self.assertEqual(receipt["final_disposition"], "RELEASE_BOUNDED_TASK")

    def test_03_shared_schema_all_known_consumers_are_explicit(self) -> None:
        candidate = base_candidate()
        candidate["relations"] = [
            {
                "relation": "MUST_CHANGE_WITH",
                "source": "SharedSchema",
                "target": "ConsumerA",
                "evidence_refs": ["code://a"],
            },
            {
                "relation": "MUST_CHANGE_WITH",
                "source": "SharedSchema",
                "target": "ConsumerB",
                "evidence_refs": ["code://b"],
            },
            {
                "relation": "MUST_CHANGE_WITH",
                "source": "SharedSchema",
                "target": "ConsumerC",
                "evidence_refs": ["code://c"],
            },
        ]
        candidate["synchronized_change_set"] += ["ConsumerA", "ConsumerB", "ConsumerC"]
        candidate["reverse_consumers"] = [
            {"consumer_id": name, "impact": "SYNCHRONIZED_CHANGE_REQUIRED", "evidence_refs": [f"code://{name}"]}
            for name in ("ConsumerA", "ConsumerB", "ConsumerC")
        ]
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "RELEASE_AS_EXTENSION")
        self.assertEqual({row["consumer_id"] for row in receipt["reverse_consumer_analysis"]}, {"ConsumerA", "ConsumerB", "ConsumerC"})

    def test_04_optional_provider_routes_to_removable_adapter(self) -> None:
        candidate = base_candidate()
        candidate["capability_inventory"] = [
            {
                "component_id": "OptionalProvider",
                "decision": "WRAP_ADAPT",
                "satisfies_requirement": False,
                "evidence_refs": ["contract://stable-provider"],
            }
        ]
        candidate["composition"] = {
            "optional": True,
            "can_compose": True,
            "core_invariant": False,
            "missing_capability_behavior": "UNSUPPORTED",
            "removal_preserves_unrelated_core": True,
            "justification": "Provider is optional and consumed through a stable capability contract.",
        }
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "RELEASE_AS_ADAPTER_OR_PLUGIN")

    def test_05_foundational_invariant_is_not_forced_into_plugin_model(self) -> None:
        candidate = base_candidate()
        candidate["capability_inventory"] = [
            {
                "component_id": "SingleWriterInvariant",
                "decision": "MODIFY",
                "satisfies_requirement": False,
                "evidence_refs": ["governance://single-writer"],
            }
        ]
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "RELEASE_BOUNDED_TASK")
        self.assertTrue(receipt["composition_removability_decision"]["core_invariant"])

    def test_06_second_canonical_writer_fails_closed(self) -> None:
        candidate = base_candidate()
        candidate["authority_binding"]["would_create_second_writer"] = True
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "ARCHITECTURE_CONFLICT")

    def test_07_cross_domain_authority_mismatch_fails_closed(self) -> None:
        candidate = base_candidate()
        candidate["proposed_target_domain"] = "AI_FILM_SYSTEM"
        candidate["authority_binding"] = {
            "owner_domain": "AI_FILM_SYSTEM",
            "writeback_owner": "SECOND_BRAIN_SYSTEM",
            "compatible": False,
            "would_create_second_writer": False,
            "would_create_second_truth": False,
        }
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "ARCHITECTURE_CONFLICT")

    def test_08_interface_overlap_detected_even_without_path_overlap(self) -> None:
        candidate = base_candidate()
        candidate["existing_work_items"] = [
            {
                "task_id": "ACTIVE-OTHER",
                "owns_coherent_change_surface": False,
                "write_paths": ["unrelated/path.py"],
                "read_paths": [],
                "interfaces": [
                    {"name": "ProgramControlTowerReleaseEvidence", "mode": "write", "frozen": False}
                ],
                "read_domains": [],
                "write_domains": [],
                "authority_claims": [],
            }
        ]
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["collision_analysis"][0]["reason"], "MUTABLE_INTERFACE")
        self.assertEqual(receipt["final_disposition"], "DEFER_DEPENDENCY")

    def test_09_incomplete_material_consumer_inventory_blocks_release(self) -> None:
        candidate = base_candidate()
        candidate["consumer_inventory_complete"] = False
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "NEEDS_REVALIDATION")

    def test_10_existing_active_task_owning_change_surface_merges(self) -> None:
        candidate = base_candidate()
        candidate["existing_work_items"] = [
            {
                "task_id": "ACTIVE-RUNTIME-GATE",
                "owns_coherent_change_surface": True,
                "write_paths": ["coordination/CONTROL-TOWER"],
                "read_paths": [],
                "interfaces": [],
                "read_domains": [],
                "write_domains": ["SECOND_BRAIN_SYSTEM"],
                "authority_claims": [],
            }
        ]
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "MERGE_WITH_EXISTING_TASK")

    def test_11_wrapper_facade_solves_requirement_without_core_fork(self) -> None:
        candidate = base_candidate()
        candidate["capability_inventory"] = [
            {
                "component_id": "StableExistingContract",
                "decision": "WRAP_ADAPT",
                "satisfies_requirement": False,
                "evidence_refs": ["contract://stable"],
            }
        ]
        candidate["composition"] = {
            "optional": True,
            "can_compose": True,
            "core_invariant": False,
            "missing_capability_behavior": "ABSTAIN",
            "removal_preserves_unrelated_core": True,
            "justification": "A facade preserves the stable core contract and removes vendor branching.",
        }
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "RELEASE_AS_ADAPTER_OR_PLUGIN")

    def test_12_must_change_with_cannot_be_artificially_omitted(self) -> None:
        candidate = base_candidate()
        candidate["relations"] = [
            {
                "relation": "MUST_CHANGE_WITH",
                "source": "ContractA",
                "target": "ConsumerB",
                "evidence_refs": ["code://consumer-b"],
            }
        ]
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "ARCHITECTURE_CONFLICT")
        candidate["synchronized_change_set"].append("ConsumerB")
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "RELEASE_AS_EXTENSION")

    def test_13_optional_component_removal_must_leave_unrelated_core_valid(self) -> None:
        candidate = base_candidate()
        candidate["capability_inventory"] = [
            {
                "component_id": "PluginX",
                "decision": "WRAP_ADAPT",
                "satisfies_requirement": False,
                "evidence_refs": ["plugin://x"],
            }
        ]
        candidate["composition"] = {
            "optional": True,
            "can_compose": True,
            "core_invariant": False,
            "missing_capability_behavior": "UNSUPPORTED",
            "removal_preserves_unrelated_core": False,
            "justification": "Candidate plugin.",
        }
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "ARCHITECTURE_CONFLICT")

    def test_14_receipt_never_grants_execution_authority(self) -> None:
        receipt = evaluate_release_candidate(base_candidate())
        boundary = receipt["authority_boundary"]
        self.assertTrue(boundary["evidence_only"])
        self.assertFalse(boundary["creates_task"])
        self.assertFalse(boundary["creates_route"])
        self.assertFalse(boundary["creates_work_claim"])
        self.assertFalse(boundary["grants_execution_authority"])
        self.assertFalse(boundary["grants_domain_write"])
        self.assertFalse(boundary["grants_merge_authority"])

    def test_unknown_component_decisions_abstain(self) -> None:
        candidate = base_candidate()
        candidate["materiality"] = "NORMAL"
        candidate["capability_inventory"] = [
            {
                "component_id": "UnobservedSubsystem",
                "decision": "UNKNOWN",
                "satisfies_requirement": False,
                "evidence_refs": ["inventory://unknown"],
            }
        ]
        receipt = evaluate_release_candidate(candidate)
        self.assertEqual(receipt["final_disposition"], "ABSTAIN")

    def test_new_module_requires_positive_insufficiency_proof(self) -> None:
        candidate = base_candidate()
        candidate["capability_inventory"] = [
            {
                "component_id": "NewThing",
                "decision": "NEW_MODULE_JUSTIFIED",
                "evidence_refs": ["inventory://no-fit"],
                "new_module_justification": "Existing contracts cannot express the capability without authority coupling.",
                "existing_capabilities_insufficient": False,
            }
        ]
        with self.assertRaises(ImpactGateError) as caught:
            evaluate_release_candidate(candidate)
        self.assertEqual(caught.exception.code, "EXISTING_CAPABILITY_INSUFFICIENCY_NOT_PROVEN")

    def test_caller_cannot_inject_final_disposition(self) -> None:
        candidate = base_candidate()
        candidate["final_disposition"] = "RELEASE_BOUNDED_TASK"
        with self.assertRaises(ImpactGateError) as caught:
            evaluate_release_candidate(candidate)
        self.assertEqual(caught.exception.code, "UNRECOGNIZED_FIELD")

    def test_integer_truthy_values_cannot_impersonate_booleans(self) -> None:
        attacks = [
            ("authority", lambda c: c["authority_binding"].__setitem__("compatible", 1), "INVALID_AUTHORITY_COMPATIBILITY"),
            ("removal", lambda c: c["composition"].__setitem__("removal_preserves_unrelated_core", 1), "INVALID_REMOVAL_PROOF"),
            ("satisfies", lambda c: c["capability_inventory"][0].__setitem__("satisfies_requirement", 1), "INVALID_BOOLEAN"),
        ]
        for name, mutate, code in attacks:
            with self.subTest(name=name):
                candidate = base_candidate()
                mutate(candidate)
                with self.assertRaises(ImpactGateError) as caught:
                    evaluate_release_candidate(candidate)
                self.assertEqual(caught.exception.code, code)

    def test_receipt_is_deterministic_and_input_bound(self) -> None:
        candidate = base_candidate()
        first = evaluate_release_candidate(candidate)
        second = evaluate_release_candidate(copy.deepcopy(candidate))
        self.assertEqual(first, second)
        changed = copy.deepcopy(candidate)
        changed["desired_effect"] += " changed"
        third = evaluate_release_candidate(changed)
        self.assertNotEqual(first["input_digest"], third["input_digest"])
        self.assertNotEqual(first["receipt_digest"], third["receipt_digest"])


if __name__ == "__main__":
    unittest.main()
