from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R175"
SPEC = importlib.util.spec_from_file_location(
    "validate_interactive_cinematic_mapping",
    ROOT / "tools/validate_interactive_cinematic_mapping.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load(name: str) -> dict:
    return json.loads((PROGRAM / name).read_text(encoding="utf-8"))


def payloads() -> tuple[dict, dict, dict, dict, dict, dict, dict]:
    return (
        load("INTERACTIVE-CINEMATIC-SYSTEM-MAP.yaml"),
        load("NUMERIC-ANCHOR-AND-DRIFT-REGISTRY.yaml"),
        load("RESEARCH-SOURCE-LEDGER.yaml"),
        load("CANDIDATE-LINEAGE-AND-INTEGRATION-MAP.yaml"),
        load("CREATIVE-EXPERIENCE-EVALUATION-PROTOCOL.yaml"),
        load("SYSTEM-CAPABILITY-DEPENDENCY-MAP.yaml"),
        load("PLATFORM-CONTRACT-CATALOG.yaml"),
    )


class InteractiveCinematicMappingTests(unittest.TestCase):
    def test_repository_candidate_is_valid(self) -> None:
        checks = MODULE.validate_mapping(*payloads())
        self.assertIn("four_layers_complete", checks)
        self.assertIn("metric_semantics_and_unknowns_valid", checks)
        self.assertIn("capability_maturity_and_dependency_graph_valid", checks)

    def test_all_four_layers_are_required(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        system["cards"] = [card for card in system["cards"] if card["layer"] != "opaque_unknown"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "every layer"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_unknown_metric_cannot_invent_target(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        unknown = next(metric for metric in metrics["metrics"] if metric["status"] == "UNKNOWN_REQUIRES_MEASUREMENT")
        unknown["target"] = 100
        with self.assertRaisesRegex(MODULE.MappingValidationError, "must not invent"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_card_cannot_reference_unknown_metric(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        system["cards"][0]["metric_anchor_ids"] = ["M-NOT-REAL"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "unknown metrics"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_private_data_flag_fails_closed(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        research["contains_private_data"] = True
        with self.assertRaisesRegex(MODULE.MappingValidationError, "no private data"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_candidate_cannot_claim_canonical(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        lineage["candidates"][0]["canonical"] = True
        with self.assertRaisesRegex(MODULE.MappingValidationError, "must remain noncanonical"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_research_source_must_be_integrated(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        extra = copy.deepcopy(research["sources"][0])
        extra["source_id"] = "R-UNUSED-PRIMARY"
        extra["url"] = "https://example.org/primary"
        research["sources"].append(extra)
        with self.assertRaisesRegex(MODULE.MappingValidationError, "lack architecture integration"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_complete_metric_requires_baseline(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        metrics["metrics"][0]["baseline"] = None
        with self.assertRaisesRegex(MODULE.MappingValidationError, "requires baseline"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_composite_quality_score_is_forbidden(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        evaluation["principles"]["composite_score"] = "ALLOWED"
        with self.assertRaisesRegex(MODULE.MappingValidationError, "forbid a composite"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_uncalibrated_rubric_cannot_invent_passing_target(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        evaluation["rubric_contract"]["dimension_targets"] = {"HX-AGENCY": 4}
        with self.assertRaisesRegex(MODULE.MappingValidationError, "cannot invent dimension_targets"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_human_dimension_must_reference_known_source(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        evaluation["human_dimensions"][0]["source_ids"] = ["R-NOT-REAL"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "unknown sources"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_hard_gate_cannot_point_to_unknown_human_metric(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        evaluation["hard_gates"][0]["metric_id"] = "M-HUMAN-CINEMATIC-QUALITY-v1"
        with self.assertRaisesRegex(MODULE.MappingValidationError, "hard-gate metric"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_second_brain_promotion_requires_human_review(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        evaluation["second_brain_bridge"]["promotion"] = "AUTO"
        with self.assertRaisesRegex(MODULE.MappingValidationError, "cannot auto-promote"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_capability_dependency_cycle_fails_closed(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        root = next(item for item in capabilities["capabilities"] if item["capability_id"] == "CAP-CONTROL-PLANE")
        root["depends_on"] = ["CAP-CORE-EVENT-LEDGER"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "dependency cycle"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_mapped_capability_cannot_claim_implemented_without_evidence(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        script_registry = next(
            item for item in capabilities["capabilities"]
            if item["capability_id"] == "CAP-SCRIPT-PACKAGE-REGISTRY"
        )
        script_registry["maturity"] = "IMPLEMENTED_OFFLINE"
        with self.assertRaisesRegex(MODULE.MappingValidationError, "requires implementation and test evidence"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_capability_cannot_reference_unknown_metric(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        capabilities["capabilities"][0]["metric_ids"] = ["M-NOT-REAL"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "references unknown metrics"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_capability_cannot_reference_unknown_source(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        capabilities["capabilities"][0]["source_ids"] = ["R-NOT-REAL"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "references unknown sources"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_stage_gate_cannot_reference_unknown_capability(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        capabilities["stage_gates"][0]["required_capabilities"] = ["CAP-NOT-REAL"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "references unknown capabilities"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_contract_identity_must_be_required(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        contracts["contracts"][0]["identity_fields"].append("not_a_required_field")
        with self.assertRaisesRegex(MODULE.MappingValidationError, "identity fields are not required"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_contract_cannot_reference_unknown_module(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        contracts["contracts"][0]["module_id"] = "NOT_A_MODULE"
        with self.assertRaisesRegex(MODULE.MappingValidationError, "unknown module"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_contract_relation_cannot_bind_unknown_field(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        contracts["relations"][0]["from_fields"][0] = "missing_source_field"
        with self.assertRaisesRegex(MODULE.MappingValidationError, "binds unknown fields"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_interface_contract_must_be_catalogued(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        capabilities["interfaces"][0]["contract"] = "Uncatalogued/v1"
        with self.assertRaisesRegex(MODULE.MappingValidationError, "uncatalogued contract"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)

    def test_contract_catalog_cannot_grant_runtime_authority(self) -> None:
        system, metrics, research, lineage, evaluation, capabilities, contracts = payloads()
        contracts["rules"]["contract_acceptance_does_not_grant_implementation_authority"] = False
        with self.assertRaisesRegex(MODULE.MappingValidationError, "contract rule must remain true"):
            MODULE.validate_mapping(system, metrics, research, lineage, evaluation, capabilities, contracts)


if __name__ == "__main__":
    unittest.main()
