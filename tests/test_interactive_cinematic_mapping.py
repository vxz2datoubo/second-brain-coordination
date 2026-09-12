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


def payloads() -> tuple[dict, dict, dict, dict]:
    return (
        load("INTERACTIVE-CINEMATIC-SYSTEM-MAP.yaml"),
        load("NUMERIC-ANCHOR-AND-DRIFT-REGISTRY.yaml"),
        load("RESEARCH-SOURCE-LEDGER.yaml"),
        load("CANDIDATE-LINEAGE-AND-INTEGRATION-MAP.yaml"),
    )


class InteractiveCinematicMappingTests(unittest.TestCase):
    def test_repository_candidate_is_valid(self) -> None:
        checks = MODULE.validate_mapping(*payloads())
        self.assertIn("four_layers_complete", checks)
        self.assertIn("metric_semantics_and_unknowns_valid", checks)

    def test_all_four_layers_are_required(self) -> None:
        system, metrics, research, lineage = payloads()
        system["cards"] = [card for card in system["cards"] if card["layer"] != "opaque_unknown"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "every layer"):
            MODULE.validate_mapping(system, metrics, research, lineage)

    def test_unknown_metric_cannot_invent_target(self) -> None:
        system, metrics, research, lineage = payloads()
        unknown = next(metric for metric in metrics["metrics"] if metric["status"] == "UNKNOWN_REQUIRES_MEASUREMENT")
        unknown["target"] = 100
        with self.assertRaisesRegex(MODULE.MappingValidationError, "must not invent"):
            MODULE.validate_mapping(system, metrics, research, lineage)

    def test_card_cannot_reference_unknown_metric(self) -> None:
        system, metrics, research, lineage = payloads()
        system["cards"][0]["metric_anchor_ids"] = ["M-NOT-REAL"]
        with self.assertRaisesRegex(MODULE.MappingValidationError, "unknown metrics"):
            MODULE.validate_mapping(system, metrics, research, lineage)

    def test_private_data_flag_fails_closed(self) -> None:
        system, metrics, research, lineage = payloads()
        research["contains_private_data"] = True
        with self.assertRaisesRegex(MODULE.MappingValidationError, "no private data"):
            MODULE.validate_mapping(system, metrics, research, lineage)

    def test_candidate_cannot_claim_canonical(self) -> None:
        system, metrics, research, lineage = payloads()
        lineage["candidates"][0]["canonical"] = True
        with self.assertRaisesRegex(MODULE.MappingValidationError, "must remain noncanonical"):
            MODULE.validate_mapping(system, metrics, research, lineage)

    def test_research_source_must_be_integrated(self) -> None:
        system, metrics, research, lineage = payloads()
        extra = copy.deepcopy(research["sources"][0])
        extra["source_id"] = "R-UNUSED-PRIMARY"
        extra["url"] = "https://example.org/primary"
        research["sources"].append(extra)
        with self.assertRaisesRegex(MODULE.MappingValidationError, "lack architecture integration"):
            MODULE.validate_mapping(system, metrics, research, lineage)

    def test_complete_metric_requires_baseline(self) -> None:
        system, metrics, research, lineage = payloads()
        metrics["metrics"][0]["baseline"] = None
        with self.assertRaisesRegex(MODULE.MappingValidationError, "requires baseline"):
            MODULE.validate_mapping(system, metrics, research, lineage)


if __name__ == "__main__":
    unittest.main()
