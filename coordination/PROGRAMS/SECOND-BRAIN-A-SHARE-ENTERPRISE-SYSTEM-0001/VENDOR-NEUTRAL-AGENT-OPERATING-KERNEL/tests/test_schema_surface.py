from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
import unittest

from vendor_neutral_agent_kernel.contracts import (
    AgentHandoff,
    AuthorityResolution,
    CapabilityDescriptor,
    CompletionReceipt,
    ContractMeta,
    EpistemicClaim,
    ExecutionCheckpoint,
    MemoryWriteProposal,
    ModelBehaviorProfile,
    TaskIntent,
    ToolRouteDecision,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "AgentKernelContracts.schema.json"


class SchemaSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_uses_draft_2020_12(self) -> None:
        self.assertEqual(
            self.schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )

    def test_schema_has_exactly_ten_public_contracts(self) -> None:
        names = {
            item["$ref"].rsplit("/", 1)[-1]
            for item in self.schema["oneOf"]
        }
        self.assertEqual(
            names,
            {
                "AuthorityResolution",
                "TaskIntent",
                "EpistemicClaim",
                "MemoryWriteProposal",
                "CapabilityDescriptor",
                "ToolRouteDecision",
                "ExecutionCheckpoint",
                "CompletionReceipt",
                "AgentHandoff",
                "ModelBehaviorProfile",
            },
        )

    def test_schema_required_fields_match_dataclasses(self) -> None:
        classes = (
            AuthorityResolution,
            TaskIntent,
            EpistemicClaim,
            MemoryWriteProposal,
            CapabilityDescriptor,
            ToolRouteDecision,
            ExecutionCheckpoint,
            CompletionReceipt,
            AgentHandoff,
            ModelBehaviorProfile,
        )
        definitions = self.schema["$defs"]
        for contract_class in classes:
            with self.subTest(contract=contract_class.__name__):
                expected = {item.name for item in fields(contract_class)}
                actual = set(definitions[contract_class.__name__]["required"])
                self.assertEqual(expected, actual)

    def test_meta_required_fields_match_dataclass(self) -> None:
        expected = {item.name for item in fields(ContractMeta)}
        actual = set(self.schema["$defs"]["ContractMeta"]["required"])
        self.assertEqual(expected, actual)

    def test_every_required_field_has_a_property_schema(self) -> None:
        for name, definition in self.schema["$defs"].items():
            if "required" not in definition:
                continue
            with self.subTest(definition=name):
                self.assertEqual(
                    set(definition["required"]),
                    set(definition["properties"]),
                )

    def test_contract_objects_reject_unknown_fields(self) -> None:
        contract_names = {
            item["$ref"].rsplit("/", 1)[-1]
            for item in self.schema["oneOf"]
        }
        for name in contract_names | {"ContractMeta"}:
            with self.subTest(definition=name):
                self.assertFalse(
                    self.schema["$defs"][name]["additionalProperties"]
                )

    def test_memory_schema_forbids_authority_write(self) -> None:
        authority_write = self.schema["$defs"]["MemoryWriteProposal"][
            "properties"
        ]["authority_write"]
        self.assertIs(authority_write["const"], False)

    def test_model_profile_schema_forbids_authority_overrides(self) -> None:
        overrides = self.schema["$defs"]["ModelBehaviorProfile"]["properties"][
            "authority_overrides"
        ]
        self.assertEqual(overrides["maxItems"], 0)


if __name__ == "__main__":
    unittest.main()
