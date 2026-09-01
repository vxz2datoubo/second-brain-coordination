"""Validate the task-local interactive-cinematic mapping candidate.

This checks reference integrity and fail-closed measurement semantics. It does
not make the mapping canonical or grant execution, provider, review or merge
authority.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
LAYERS = {"explicit_known", "implicit_known", "explainable_unknown", "opaque_unknown"}
EVIDENCE_TIERS = {"E0_RECORDED", "E1_DETERMINISTIC", "E2_CLEAN_REPRODUCED", "E3_INDEPENDENTLY_ATTESTED"}
METRIC_STATUSES = {"FIXED_CONTRACT", "EXTERNAL_VERSIONED_CONSTRAINT", "MEASURED", "UNKNOWN_REQUIRES_MEASUREMENT"}
MATURITY_LEVELS = {
    "ABSENT": 0,
    "MAPPED": 1,
    "CONTRACTED": 2,
    "IMPLEMENTED_OFFLINE": 3,
    "REPRODUCED_CLEAN": 4,
    "PILOT_VALIDATED": 5,
    "PRODUCTION_APPROVED": 6,
}
CONTRACT_STATUSES = {
    "CONTRACTED_CANDIDATE",
    "CONTRACTED_CANDIDATE_AUTHORITY_RESERVED",
    "CONTRACTED_IMPLEMENTED_NONCANONICAL",
}
CONTRACT_REJECTION_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")


class MappingValidationError(ValueError):
    """Raised when candidate mapping evidence is incomplete or contradictory."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MappingValidationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MappingValidationError(f"{path} must contain an object")
    return value


def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise MappingValidationError(f"{where}.{key} is required")
    return mapping[key]


def _unique(records: list[dict[str, Any]], key: str, where: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise MappingValidationError(f"{where}[{index}] must be an object")
        identity = _require(record, key, f"{where}[{index}]")
        if not isinstance(identity, str) or not identity:
            raise MappingValidationError(f"{where}[{index}].{key} must be non-empty")
        if identity in result:
            raise MappingValidationError(f"duplicate {key}: {identity}")
        result[identity] = record
    return result


def _string_list(value: Any, where: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise MappingValidationError(f"{where} must be a {'possibly empty ' if allow_empty else 'non-empty '}string list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise MappingValidationError(f"{where} must contain non-empty strings")
    return value


def _public_safe(payloads: list[dict[str, Any]]) -> None:
    for payload in payloads:
        if payload.get("contains_private_data") is not False:
            raise MappingValidationError("candidate must explicitly contain no private data")
        if payload.get("contains_credentials") is not False:
            raise MappingValidationError("candidate must explicitly contain no credentials")


def _assert_acyclic_capabilities(capabilities: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(capability_id: str) -> None:
        if capability_id in visiting:
            raise MappingValidationError(f"capability dependency cycle contains {capability_id}")
        if capability_id in visited:
            return
        visiting.add(capability_id)
        dependencies = _string_list(
            _require(capabilities[capability_id], "depends_on", capability_id),
            f"{capability_id}.depends_on",
            allow_empty=True,
        )
        for dependency in dependencies:
            if dependency not in capabilities:
                raise MappingValidationError(f"{capability_id} references unknown capability {dependency}")
            visit(dependency)
        visiting.remove(capability_id)
        visited.add(capability_id)

    for capability_id in capabilities:
        visit(capability_id)


def validate_mapping(
    system_map: dict[str, Any],
    metrics: dict[str, Any],
    research: dict[str, Any],
    lineage: dict[str, Any],
    evaluation: dict[str, Any],
    capability_map: dict[str, Any],
    contract_catalog: dict[str, Any],
) -> list[str]:
    expected_schemas = {
        "system": "InteractiveCinematicSystemMap/v1",
        "metrics": "InteractiveCinematicMetricRegistry/v1",
        "research": "InteractiveCinematicResearchLedger/v1",
        "lineage": "InteractiveCinematicCandidateLineage/v1",
        "evaluation": "CreativeExperienceEvaluationProtocol/v1",
        "capabilities": "InteractiveCinematicCapabilityDependencyMap/v1",
        "contracts": "InteractiveCinematicContractCatalog/v1",
    }
    observed = {
        "system": system_map.get("schema"),
        "metrics": metrics.get("schema"),
        "research": research.get("schema"),
        "lineage": lineage.get("schema"),
        "evaluation": evaluation.get("schema"),
        "capabilities": capability_map.get("schema"),
        "contracts": contract_catalog.get("schema"),
    }
    if observed != expected_schemas:
        raise MappingValidationError(f"schema mismatch: {observed}")
    _public_safe([system_map, metrics, research, lineage, evaluation, capability_map, contract_catalog])

    contract_rules = _require(contract_catalog, "rules", "contract_catalog")
    for rule in (
        "github_contains_contracts_not_private_payloads",
        "contract_acceptance_does_not_grant_implementation_authority",
        "model_proposal_never_becomes_story_truth_without_validation",
        "style_change_never_changes_narrative_truth",
        "downstream_output_never_rewrites_upstream_history",
        "unknown_or_mismatched_revision_fails_closed",
    ):
        if contract_rules.get(rule) is not True:
            raise MappingValidationError(f"contract rule must remain true: {rule}")

    modules = _unique(_require(contract_catalog, "modules", "contract_catalog"), "module_id", "modules")
    for module_id, module in modules.items():
        for field in ("source_of_record", "codex_role", "workbuddy_role", "gpt_role"):
            value = _require(module, field, module_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{module_id}.{field} must be non-empty")

    contracts = _unique(
        _require(contract_catalog, "contracts", "contract_catalog"),
        "contract_id",
        "contracts",
    )
    for contract_id, contract in contracts.items():
        module_id = _require(contract, "module_id", contract_id)
        if module_id not in modules:
            raise MappingValidationError(f"{contract_id} references unknown module {module_id}")
        status = _require(contract, "status", contract_id)
        if status not in CONTRACT_STATUSES:
            raise MappingValidationError(f"unsupported contract status: {contract_id}:{status}")
        for field in (
            "producer", "owner", "rejection_behavior", "compatibility", "implementation_authority",
        ):
            value = _require(contract, field, contract_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{contract_id}.{field} must be non-empty")
        _string_list(_require(contract, "consumers", contract_id), f"{contract_id}.consumers")
        required_fields = _string_list(
            _require(contract, "required_fields", contract_id), f"{contract_id}.required_fields"
        )
        identity_fields = _string_list(
            _require(contract, "identity_fields", contract_id), f"{contract_id}.identity_fields"
        )
        immutable_fields = _string_list(
            _require(contract, "immutable_fields", contract_id), f"{contract_id}.immutable_fields"
        )
        for label, values in (
            ("required_fields", required_fields),
            ("identity_fields", identity_fields),
            ("immutable_fields", immutable_fields),
        ):
            if len(values) != len(set(values)):
                raise MappingValidationError(f"{contract_id}.{label} contains duplicates")
        missing_identity = sorted(set(identity_fields) - set(required_fields))
        missing_immutable = sorted(set(immutable_fields) - set(required_fields))
        if missing_identity:
            raise MappingValidationError(f"{contract_id} identity fields are not required: {missing_identity}")
        if missing_immutable:
            raise MappingValidationError(f"{contract_id} immutable fields are not required: {missing_immutable}")
        _string_list(
            _require(contract, "prohibited_payloads", contract_id),
            f"{contract_id}.prohibited_payloads",
        )
        rejection_codes = _string_list(
            _require(contract, "rejection_codes", contract_id), f"{contract_id}.rejection_codes"
        )
        if len(rejection_codes) != len(set(rejection_codes)):
            raise MappingValidationError(f"{contract_id}.rejection_codes contains duplicates")
        invalid_codes = [code for code in rejection_codes if not CONTRACT_REJECTION_RE.fullmatch(code)]
        if invalid_codes:
            raise MappingValidationError(f"{contract_id} has invalid rejection codes: {invalid_codes}")

    relations = _unique(
        _require(contract_catalog, "relations", "contract_catalog"),
        "relation_id",
        "relations",
    )
    for relation_id, relation in relations.items():
        source_id = _require(relation, "from_contract", relation_id)
        target_id = _require(relation, "to_contract", relation_id)
        if source_id not in contracts or target_id not in contracts:
            raise MappingValidationError(f"{relation_id} references an unknown contract")
        source_fields = _string_list(
            _require(relation, "from_fields", relation_id), f"{relation_id}.from_fields"
        )
        target_fields = _string_list(
            _require(relation, "to_fields", relation_id), f"{relation_id}.to_fields"
        )
        if len(source_fields) != len(target_fields):
            raise MappingValidationError(f"{relation_id} field bindings must have equal length")
        unknown_source = sorted(set(source_fields) - set(contracts[source_id]["required_fields"]))
        unknown_target = sorted(set(target_fields) - set(contracts[target_id]["required_fields"]))
        if unknown_source or unknown_target:
            raise MappingValidationError(
                f"{relation_id} binds unknown fields: source={unknown_source}, target={unknown_target}"
            )
        invariant = _require(relation, "invariant", relation_id)
        if not isinstance(invariant, str) or not invariant.strip():
            raise MappingValidationError(f"{relation_id}.invariant must be non-empty")

    sources = _unique(_require(research, "sources", "research"), "source_id", "sources")
    for source_id, source in sources.items():
        parsed = urlparse(_require(source, "url", source_id))
        if parsed.scheme != "https" or not parsed.netloc:
            raise MappingValidationError(f"{source_id} must use an https primary/official URL")
        for field in ("source_class", "publisher", "proposition_used", "integration", "limitation", "revalidate_when"):
            value = _require(source, field, source_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{source_id}.{field} must be non-empty")

    metric_records = _unique(_require(metrics, "metrics", "metrics"), "metric_id", "metrics")
    for metric_id, metric in metric_records.items():
        status = _require(metric, "status", metric_id)
        if status not in METRIC_STATUSES:
            raise MappingValidationError(f"unsupported metric status: {metric_id}:{status}")
        for field in (
            "name", "unit", "direction", "formula_revision", "population", "window",
            "source_ref", "owner", "cadence", "response",
        ):
            value = _require(metric, field, metric_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{metric_id}.{field} must be non-empty")
        if not isinstance(_require(metric, "hard_gate", metric_id), bool):
            raise MappingValidationError(f"{metric_id}.hard_gate must be boolean")
        for field in ("baseline", "target", "warning_threshold", "failure_threshold"):
            _require(metric, field, metric_id)
        if status == "UNKNOWN_REQUIRES_MEASUREMENT":
            if metric["baseline"] is not None or metric["target"] is not None:
                raise MappingValidationError(f"unknown metric {metric_id} must not invent baseline or target")
            if metric["hard_gate"] is not False:
                raise MappingValidationError(f"unknown metric {metric_id} cannot be a hard gate")
            plan = metric.get("discovery_plan")
            if not isinstance(plan, str) or not plan.strip():
                raise MappingValidationError(f"unknown metric {metric_id} requires discovery_plan")
        elif metric["baseline"] is None or metric["target"] is None:
            raise MappingValidationError(f"known metric {metric_id} requires baseline and target")
        source_ref = metric["source_ref"]
        if source_ref.startswith("R-") and source_ref not in sources:
            raise MappingValidationError(f"metric {metric_id} references unknown research source {source_ref}")

    checks = _unique(_require(system_map, "drift_checks", "system_map"), "check_id", "drift_checks")
    for check_id, check in checks.items():
        for field in ("method", "cadence", "owner", "failure"):
            value = _require(check, field, check_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{check_id}.{field} must be non-empty")

    declared_layers = set(_string_list(_require(system_map, "layers", "system_map"), "system_map.layers"))
    if declared_layers != LAYERS:
        raise MappingValidationError(f"system_map.layers must be exactly {sorted(LAYERS)}")
    cards = _unique(_require(system_map, "cards", "system_map"), "card_id", "cards")
    populated_layers: set[str] = set()
    combined_source_usage = (
        json.dumps(system_map, ensure_ascii=False)
        + json.dumps(metrics, ensure_ascii=False)
        + json.dumps(evaluation, ensure_ascii=False)
        + json.dumps(capability_map, ensure_ascii=False)
    )
    for card_id, card in cards.items():
        layer = _require(card, "layer", card_id)
        if layer not in LAYERS:
            raise MappingValidationError(f"unsupported layer: {card_id}:{layer}")
        populated_layers.add(layer)
        tier = _require(card, "evidence_tier", card_id)
        if tier not in EVIDENCE_TIERS:
            raise MappingValidationError(f"unsupported evidence tier: {card_id}:{tier}")
        confidence = _require(card, "confidence", card_id)
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise MappingValidationError(f"{card_id}.confidence must be between 0 and 1")
        for field in (
            "subject", "statement", "authority_ref", "owner", "source_of_record",
            "allowed_writer", "failure_behavior", "user_action", "human_explanation",
        ):
            value = _require(card, field, card_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{card_id}.{field} must be non-empty")
        _string_list(_require(card, "modules", card_id), f"{card_id}.modules")
        _string_list(_require(card, "interfaces", card_id), f"{card_id}.interfaces")
        anchor_ids = _string_list(_require(card, "metric_anchor_ids", card_id), f"{card_id}.metric_anchor_ids")
        drift_ids = _string_list(_require(card, "drift_check_ids", card_id), f"{card_id}.drift_check_ids")
        unknown_anchors = [item for item in anchor_ids if item not in metric_records]
        unknown_checks = [item for item in drift_ids if item not in checks]
        if unknown_anchors:
            raise MappingValidationError(f"{card_id} references unknown metrics: {unknown_anchors}")
        if unknown_checks:
            raise MappingValidationError(f"{card_id} references unknown drift checks: {unknown_checks}")
    if populated_layers != LAYERS:
        raise MappingValidationError(f"every layer requires at least one card: observed={sorted(populated_layers)}")
    unused_sources = [source_id for source_id in sources if source_id not in combined_source_usage]
    if unused_sources:
        raise MappingValidationError(f"research sources lack architecture integration references: {unused_sources}")

    principles = _require(evaluation, "principles", "evaluation")
    if principles.get("correctness_and_experience") != "SEPARATE_DECISION_LAYERS":
        raise MappingValidationError("evaluation must separate correctness and experience")
    if principles.get("composite_score") != "FORBIDDEN":
        raise MappingValidationError("evaluation must forbid a composite quality score")
    if principles.get("machine_proxy") != "MAY_DIAGNOSE_BUT_NEVER_REPLACE_HUMAN_EXPERIENCE":
        raise MappingValidationError("machine diagnostics cannot replace human experience")

    hard_gates = _unique(_require(evaluation, "hard_gates", "evaluation"), "gate_id", "hard_gates")
    for gate_id, gate in hard_gates.items():
        metric_id = _require(gate, "metric_id", gate_id)
        metric = metric_records.get(metric_id)
        if metric is None:
            raise MappingValidationError(f"{gate_id} references unknown metric {metric_id}")
        if metric.get("hard_gate") is not True:
            raise MappingValidationError(f"{gate_id} must reference a hard-gate metric")
        for field in ("stage", "owner", "failure_action"):
            value = _require(gate, field, gate_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{gate_id}.{field} must be non-empty")

    dimensions = _unique(
        _require(evaluation, "human_dimensions", "evaluation"),
        "dimension_id",
        "human_dimensions",
    )
    for dimension_id, dimension in dimensions.items():
        for field in ("name", "question", "artifact_scope", "owner"):
            value = _require(dimension, field, dimension_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{dimension_id}.{field} must be non-empty")
        metric_id = _require(dimension, "metric_id", dimension_id)
        if metric_id not in metric_records:
            raise MappingValidationError(f"{dimension_id} references unknown metric {metric_id}")
        source_ids = _string_list(_require(dimension, "source_ids", dimension_id), f"{dimension_id}.source_ids")
        missing_sources = [source_id for source_id in source_ids if source_id not in sources]
        if missing_sources:
            raise MappingValidationError(f"{dimension_id} references unknown sources: {missing_sources}")

    rubric = _require(evaluation, "rubric_contract", "evaluation")
    if rubric.get("status") != "CANDIDATE_UNCALIBRATED_NOT_A_RELEASE_GATE":
        raise MappingValidationError("uncalibrated rubric cannot be a release gate")
    for field in ("baseline", "dimension_targets", "minimum_raters", "minimum_sessions", "agreement_threshold"):
        if _require(rubric, field, "rubric_contract") is not None:
            raise MappingValidationError(f"uncalibrated rubric cannot invent {field}")
    scale = _require(rubric, "response_scale", "rubric_contract")
    if (
        not isinstance(scale, dict)
        or not isinstance(scale.get("min"), int)
        or not isinstance(scale.get("max"), int)
        or scale["min"] >= scale["max"]
    ):
        raise MappingValidationError("rubric response scale must have ordered integer bounds")
    forbidden = _string_list(_require(rubric, "forbidden", "rubric_contract"), "rubric_contract.forbidden")
    if not any("overall quality score" in item for item in forbidden):
        raise MappingValidationError("rubric must explicitly forbid an overall quality score")

    cycles = _unique(_require(evaluation, "evaluation_cycles", "evaluation"), "cycle_id", "evaluation_cycles")
    for cycle_id, cycle in cycles.items():
        for field in ("cadence", "method", "owner"):
            value = _require(cycle, field, cycle_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{cycle_id}.{field} must be non-empty")
        _string_list(_require(cycle, "artifacts", cycle_id), f"{cycle_id}.artifacts")

    bridge = _require(evaluation, "second_brain_bridge", "evaluation")
    if bridge.get("promotion") != "HUMAN_REVIEW_REQUIRED":
        raise MappingValidationError("creative evaluation cannot auto-promote second-brain knowledge")
    _string_list(_require(bridge, "required_links", "second_brain_bridge"), "second_brain_bridge.required_links")

    maturity_records = _require(capability_map, "maturity_model", "capability_map")
    if not isinstance(maturity_records, list) or len(maturity_records) != len(MATURITY_LEVELS):
        raise MappingValidationError("capability maturity model must define every ordered level")
    observed_maturity = {
        _require(record, "name", "maturity_model"): _require(record, "level", "maturity_model")
        for record in maturity_records
    }
    if observed_maturity != MATURITY_LEVELS:
        raise MappingValidationError("capability maturity levels or order drifted")
    for record in maturity_records:
        proof = _require(record, "proof", f"maturity:{record.get('name')}")
        if not isinstance(proof, str) or not proof.strip():
            raise MappingValidationError("every maturity level requires explicit proof")

    rules = _require(capability_map, "rules", "capability_map")
    for rule in (
        "no_maturity_by_intent",
        "downstream_cannot_rewrite_upstream_truth",
        "contract_validation_is_not_semantic_validation",
        "provenance_is_not_quality_judgment",
        "unknown_measurement_is_not_zero",
        "external_capability_requires_fresh_observation",
    ):
        if rules.get(rule) is not True:
            raise MappingValidationError(f"capability rule must remain true: {rule}")

    capabilities = _unique(
        _require(capability_map, "capabilities", "capability_map"),
        "capability_id",
        "capabilities",
    )
    _assert_acyclic_capabilities(capabilities)
    for capability_id, capability in capabilities.items():
        maturity = _require(capability, "maturity", capability_id)
        if maturity not in MATURITY_LEVELS:
            raise MappingValidationError(f"unsupported capability maturity: {capability_id}:{maturity}")
        for field in ("name", "owner", "failure_action", "next_upgrade_condition"):
            value = _require(capability, field, capability_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{capability_id}.{field} must be non-empty")
        _string_list(_require(capability, "consumers", capability_id), f"{capability_id}.consumers")
        _string_list(_require(capability, "contract_refs", capability_id), f"{capability_id}.contract_refs")
        implementation_refs = _string_list(
            _require(capability, "implementation_refs", capability_id),
            f"{capability_id}.implementation_refs",
            allow_empty=True,
        )
        test_refs = _string_list(
            _require(capability, "test_refs", capability_id),
            f"{capability_id}.test_refs",
            allow_empty=True,
        )
        if MATURITY_LEVELS[maturity] >= MATURITY_LEVELS["IMPLEMENTED_OFFLINE"]:
            if not implementation_refs or not test_refs:
                raise MappingValidationError(
                    f"implemented capability {capability_id} requires implementation and test evidence"
                )
        metric_ids = _string_list(_require(capability, "metric_ids", capability_id), f"{capability_id}.metric_ids")
        unknown_metrics = [metric_id for metric_id in metric_ids if metric_id not in metric_records]
        if unknown_metrics:
            raise MappingValidationError(f"{capability_id} references unknown metrics: {unknown_metrics}")
        source_ids = _string_list(_require(capability, "source_ids", capability_id), f"{capability_id}.source_ids")
        unknown_sources = [source_id for source_id in source_ids if source_id not in sources]
        if unknown_sources:
            raise MappingValidationError(f"{capability_id} references unknown sources: {unknown_sources}")

    interfaces = _unique(_require(capability_map, "interfaces", "capability_map"), "interface_id", "interfaces")
    for interface_id, interface in interfaces.items():
        for field in ("producer", "consumer", "contract", "rejection_owner", "rejection_behavior"):
            value = _require(interface, field, interface_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{interface_id}.{field} must be non-empty")
        bindings = _string_list(_require(interface, "required_bindings", interface_id), f"{interface_id}.required_bindings")
        if len(bindings) != len(set(bindings)):
            raise MappingValidationError(f"{interface_id} contains duplicate required bindings")
        contract_id = interface["contract"]
        if contract_id not in contracts:
            raise MappingValidationError(f"{interface_id} references uncatalogued contract {contract_id}")
        missing_bindings = sorted(set(bindings) - set(contracts[contract_id]["required_fields"]))
        if missing_bindings:
            raise MappingValidationError(
                f"{interface_id} bindings are absent from {contract_id}: {missing_bindings}"
            )

    stages = _unique(_require(capability_map, "stage_gates", "capability_map"), "stage_id", "stage_gates")
    if set(stages) != {"A0", "A1", "A2", "A3", "A4", "A5"}:
        raise MappingValidationError("stage gates must cover exactly A0 through A5")
    for stage_id, stage in stages.items():
        for field in ("name", "exit_evidence"):
            value = _require(stage, field, stage_id)
            if not isinstance(value, str) or not value.strip():
                raise MappingValidationError(f"{stage_id}.{field} must be non-empty")
        required = _string_list(_require(stage, "required_capabilities", stage_id), f"{stage_id}.required_capabilities")
        missing = [capability_id for capability_id in required if capability_id not in capabilities]
        if missing:
            raise MappingValidationError(f"{stage_id} references unknown capabilities: {missing}")

    candidates = _unique(_require(lineage, "candidates", "lineage"), "candidate_id", "candidates")
    for candidate_id, candidate in candidates.items():
        head = _require(candidate, "exact_head", candidate_id)
        if not isinstance(head, str) or not SHA_RE.fullmatch(head):
            raise MappingValidationError(f"{candidate_id}.exact_head must be a 40-character SHA")
        if candidate.get("canonical") is not False:
            raise MappingValidationError(f"candidate {candidate_id} must remain noncanonical")
        branch = _require(candidate, "branch", candidate_id)
        if not isinstance(branch, str) or not branch.startswith("codex/"):
            raise MappingValidationError(f"{candidate_id}.branch must identify CODEX")
        _string_list(_require(candidate, "capabilities", candidate_id), f"{candidate_id}.capabilities")
        _string_list(_require(candidate, "safe_source_paths", candidate_id), f"{candidate_id}.safe_source_paths")
        _string_list(_require(candidate, "known_risks", candidate_id), f"{candidate_id}.known_risks")
        mode = _require(candidate, "import_mode", candidate_id)
        if not isinstance(mode, str) or not mode or "CHERRY_PICK" in mode:
            raise MappingValidationError(f"{candidate_id}.import_mode must require a governed mechanical port")

    return [
        "schemas_valid",
        "public_safe_flags_valid",
        "research_sources_primary_and_integrated",
        "metric_semantics_and_unknowns_valid",
        "four_layers_complete",
        "card_metric_and_drift_refs_valid",
        "correctness_and_human_experience_separated",
        "creative_rubric_unknowns_fail_closed",
        "evaluation_cycles_and_second_brain_bridge_valid",
        "capability_maturity_and_dependency_graph_valid",
        "contract_catalog_ownership_identity_and_rejections_valid",
        "cross_contract_relations_and_interface_bindings_valid",
        "department_interfaces_and_stage_gates_valid",
        "candidate_lineage_exact_and_noncanonical",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument(
        "--program-dir",
        default="coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R175",
    )
    args = parser.parse_args()
    root = args.repo.resolve(strict=True)
    program = root / args.program_dir
    try:
        checks = validate_mapping(
            _load(program / "INTERACTIVE-CINEMATIC-SYSTEM-MAP.yaml"),
            _load(program / "NUMERIC-ANCHOR-AND-DRIFT-REGISTRY.yaml"),
            _load(program / "RESEARCH-SOURCE-LEDGER.yaml"),
            _load(program / "CANDIDATE-LINEAGE-AND-INTEGRATION-MAP.yaml"),
            _load(program / "CREATIVE-EXPERIENCE-EVALUATION-PROTOCOL.yaml"),
            _load(program / "SYSTEM-CAPABILITY-DEPENDENCY-MAP.yaml"),
            _load(program / "PLATFORM-CONTRACT-CATALOG.yaml"),
        )
    except MappingValidationError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "checks": checks}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
