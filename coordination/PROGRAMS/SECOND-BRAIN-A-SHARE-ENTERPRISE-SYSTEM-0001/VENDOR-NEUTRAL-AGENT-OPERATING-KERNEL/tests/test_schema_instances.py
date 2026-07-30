from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from _support import capability, claim, meta
from vendor_neutral_agent_kernel.authority import (
    AuthorityDirective,
    AuthorityKind,
    resolve_authority,
)
from vendor_neutral_agent_kernel.canonical import canonical_value
from vendor_neutral_agent_kernel.completion import audit_completion
from vendor_neutral_agent_kernel.contracts import (
    AgentHandoff,
    ModelBehaviorProfile,
    RequirementEvidence,
)
from vendor_neutral_agent_kernel.epistemic import propose_memory_write
from vendor_neutral_agent_kernel.intent import compile_intent
from vendor_neutral_agent_kernel.recovery import build_checkpoint
from vendor_neutral_agent_kernel.routing import CapabilityRequest, route_capability


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "AgentKernelContracts.schema.json"


def contract_instances():
    authority = resolve_authority(
        meta("schema-authority"),
        (
            AuthorityDirective(
                AuthorityKind.ACTIVE_ROUTE,
                "route:schema",
                task_id="schema-task",
                allowed_paths=("coordination/",),
                allowed_actions=("read",),
            ),
        ),
        agent_id="CODEX",
    )
    task_intent = compile_intent(
        meta("schema-intent"),
        objective="Validate public candidate contracts.",
        explicit_requirements=("schema",),
        success_criteria=("all instances validate",),
    )
    epistemic_claim = claim()
    memory_write = propose_memory_write(
        meta("schema-memory"),
        candidate_claims=(epistemic_claim,),
        destination_scope="candidate:schema",
        source_provenance=("fixture:public",),
    )
    descriptor = capability("schema-provider")
    route = route_capability(
        meta("schema-route"),
        CapabilityRequest("market.snapshot", ("snapshot",)),
        (descriptor,),
    )
    checkpoint = build_checkpoint(
        meta("schema-checkpoint"),
        intent_hash=task_intent.meta.content_hash,
        context_hash="context-hash",
        authority_hash=authority.authority_hash,
        completed_steps=("inspect",),
        remaining_steps=("verify",),
    )
    receipt = audit_completion(
        meta("schema-receipt"),
        requirements=("schema",),
        evidence=(
            RequirementEvidence(
                requirement_id="schema",
                evidence_refs=("test:schema",),
                disposition="PROVES",
                scope="exact",
            ),
        ),
    )
    handoff = AgentHandoff(
        meta=meta("schema-handoff"),
        source_agent="CODEX",
        target_agent="GPT",
        reviewer="GPT",
        task_id="schema-task",
        owned_paths=("coordination/",),
        base="base",
        parent="parent",
        tree="tree",
        head="head",
        completed=("schema",),
        remaining=("review",),
        tests=("test:schema",),
        unknowns=("production",),
        rollback=("close candidate",),
    )
    profile = ModelBehaviorProfile(
        meta=meta("schema-profile"),
        model_family="example",
        model_version="1",
        evaluated_at="2026-07-30",
        evaluation_refs=("eval:synthetic",),
        task_strengths=("structured-output",),
        known_failure_modes=("unverified",),
        verbosity_profile="bounded",
        tool_use_profile="read-only",
        verification_profile="test-backed",
        delegation_profile="none",
        structured_output_profile="strict",
        effective_from="2026-07-30",
        review_after="2026-08-30",
    )
    return {
        "AuthorityResolution": authority,
        "TaskIntent": task_intent,
        "EpistemicClaim": epistemic_claim,
        "MemoryWriteProposal": memory_write,
        "CapabilityDescriptor": descriptor,
        "ToolRouteDecision": route,
        "ExecutionCheckpoint": checkpoint,
        "CompletionReceipt": receipt,
        "AgentHandoff": handoff,
        "ModelBehaviorProfile": profile,
    }


class SchemaInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def test_schema_validates_against_draft_2020_12_meta_schema(self):
        Draft202012Validator.check_schema(self.schema)

    def test_each_public_contract_serializes_to_a_valid_schema_instance(self):
        for name, instance in contract_instances().items():
            with self.subTest(contract=name):
                payload = canonical_value(instance)
                self.validator.validate(payload)

    def test_authority_instance_requires_verified_approval_field(self):
        payload = canonical_value(contract_instances()["AuthorityResolution"])
        del payload["verified_approval_actions"]
        with self.assertRaises(Exception):
            self.validator.validate(payload)


if __name__ == "__main__":
    unittest.main()
