from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
PROGRAM_INDEX = ROOT / "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PROGRAM-INDEX.yaml"
EXECUTION_SEQUENCE = ROOT / "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/ACTIVE-EXECUTION-SEQUENCE-v1.0.yaml"
ACTIVE_TASK = ROOT / "coordination/ACTIVE-CODEX-TASK.yaml"


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def construct_mapping(loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict:
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping,
)


def load_yaml(path: Path) -> object:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_yaml_and_json() -> tuple[int, int]:
    yaml_count = 0
    json_count = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() in {".yaml", ".yml"}:
            load_yaml(path)
            yaml_count += 1
        elif path.suffix.lower() == ".json":
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
    return yaml_count, json_count


def check_utf8_and_secrets() -> int:
    text_suffixes = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".csv"}
    secret_patterns = [
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]
    fixture_allowlist = {
        Path(
            "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
            "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION/tests/test_local_adapter_contracts.py"
        )
    }
    checked = 0
    allowed_fixture_hits = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(ROOT)
        for pattern in secret_patterns:
            match = pattern.search(text)
            if match is not None:
                require(relative_path in fixture_allowlist, f"secret-like value in {relative_path}")
                allowed_fixture_hits += 1
        checked += 1
    require(allowed_fixture_hits == 1, "expected exactly one pre-existing secret-shaped test fixture")
    return checked


def check_required_artifacts() -> None:
    required = {
        "ENTERPRISE-BLUEPRINT-CURRENT-STATE-AUDIT.md",
        "CANONICAL-AUTHORITY-AND-OWNERSHIP-MATRIX.yaml",
        "SHARED-INTERFACE-REGISTRY.yaml",
        "MODULE-MATURITY-LEDGER.yaml",
        "DEPENDENCY-DAG-AND-CRITICAL-PATH.yaml",
        "PARALLEL-SAFETY-AND-WIP-MATRIX.yaml",
        "DUPLICATE-ORPHAN-GHOST-DEPRECATION-REPORT.md",
        "NEXT-VERTICAL-SLICE-SELECTION.md",
        "AMED-AGENT-EXECUTION-RECEIPT.yaml",
        "AMED-RESEARCH-LEDGER.yaml",
        "UNPLANNED-IMPROVEMENT-LEDGER.yaml",
        "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
        "ALTERNATIVE-AND-TRADEOFF-MATRIX.yaml",
        "INDEPENDENT-VALIDATION-PACKAGE.yaml",
        "TEST-RUN-RECEIPT.md",
        "UNKNOWN-REGISTRY.yaml",
        "AI_HANDOFF.yaml",
    }
    missing = sorted(name for name in required if not (PACKAGE / name).is_file())
    require(not missing, f"missing task artifacts: {missing}")


def check_program_references() -> None:
    index = load_yaml(PROGRAM_INDEX)
    sequence = load_yaml(EXECUTION_SEQUENCE)
    route = load_yaml(ACTIVE_TASK)
    require(index["schema_version"] == "1.9", "PROGRAM-INDEX is not schema 1.9")
    require(sequence["authoritative_program_index_schema"] == "1.9", "execution sequence index schema drift")
    for key in ("program_charter", "project_blueprint_integration_index", "blueprint_convergence_map", "authority_interface_registry"):
        require((ROOT / index[key]).is_file(), f"missing PROGRAM-INDEX target {index[key]}")
    require(index["blueprint_convergence_map"] == sequence["blueprint_convergence_map"], "convergence pointer drift")
    require(index["authority_interface_registry"] == sequence["authority_interface_registry"], "authority pointer drift")
    require(route["active_issue"] == index["current_control_issue"] == 72, "active issue drift")
    require(route["task_id"] == "CODEX-0019A-R1-BOUNDED-CONVERGENCE-REMEDIATION", "R1 route drift")
    require(route["status"] == "READY", "R1 route is not ready")
    require(route["branch"] == "codex/enterprise-blueprint-convergence-0019a", "R1 branch drift")
    selection = sequence["first_business_vertical_slice_candidates"]
    require(selection["maximum_simultaneous"] == 1, "business WIP is not one")
    require(selection["selected_candidate"].startswith("0017 BAR_ONLY"), "exactly one selected candidate is not frozen")


def check_authorities_and_interfaces() -> None:
    matrix = load_yaml(PACKAGE / "CANONICAL-AUTHORITY-AND-OWNERSHIP-MATRIX.yaml")
    authorities = matrix["authorities"]
    ids = [item["authority_id"] for item in authorities]
    require(len(ids) == len(set(ids)), "duplicate authority IDs")
    require(all(isinstance(item["owner"], str) and item["owner"] for item in authorities), "authority without one logical owner")
    require(matrix["conflicts"]["duplicate_logical_writer_count"] == 0, "duplicate logical writer remains")
    for authority in authorities:
        require("implementation_maturity" in authority, f"authority lacks implementation maturity: {authority['authority_id']}")
        require(
            "canonical_authority_readiness" in authority,
            f"authority lacks canonical readiness: {authority['authority_id']}",
        )

    maturity = load_yaml(PACKAGE / "MODULE-MATURITY-LEDGER.yaml")
    require(
        "implementation_maturity_scale" in maturity and "canonical_authority_readiness_scale" in maturity,
        "maturity ledger must expose separate evidence axes",
    )
    modules = {item["module_id"]: item for item in maturity["modules"]}
    require(
        all("implementation_maturity" in item and "canonical_authority_readiness" in item for item in modules.values()),
        "every module must have both maturity axes",
    )
    require(modules["W3"]["implementation_maturity"] == "IMPLEMENTED_NOT_A_SHARE_VALIDATED", "W3 implementation evidence erased")
    require(modules["W3"]["canonical_authority_readiness"] == "UNKNOWN_MIGRATION_REQUIRED", "W3 migration unknown lost")
    require(modules["W7"]["canonical_authority_readiness"] == "LOGICAL_OWNER_DECLARED_NOT_CANONICAL_READY", "W7 canonical readiness overstated")
    require(modules["W12_0012"]["implementation_maturity"] == "CONTRACTED_NOT_IMPLEMENTED", "W12 main maturity overstated")
    require(modules["W12_0012"]["candidate_evidence"] == ["PR #66 Draft", "GPT bounded acceptance"], "W12 draft evidence lost")

    registry = load_yaml(PACKAGE / "SHARED-INTERFACE-REGISTRY.yaml")
    interfaces = registry["interfaces"]
    interface_ids = [item["interface_id"] for item in interfaces]
    require(len(interface_ids) == 11, "shared interface count must be eleven")
    require(len(interface_ids) == len(set(interface_ids)), "duplicate shared interface IDs")
    require(all(isinstance(item["producer"], str) and item["producer"] for item in interfaces), "interface without producer")
    require("assessment_axes" in registry, "shared interfaces must declare two assessment axes")
    require(
        all("implementation_maturity" in item and "canonical_authority_readiness" in item for item in interfaces),
        "every shared interface must have both maturity axes",
    )
    c3 = next(item for item in interfaces if item["interface_id"] == "C3_KNOWLEDGE_AND_EVIDENCE")
    c7 = next(item for item in interfaces if item["interface_id"] == "C7_PROBABILITY_ESTIMATE")
    c10 = next(item for item in interfaces if item["interface_id"] == "C10_VALIDATION_AND_RISK")
    require(c3["canonical_authority_readiness"] == "UNKNOWN_MIGRATION_REQUIRED", "C3 migration boundary lost")
    require(c7["implementation_maturity"] == "CONTRACTED_NOT_IMPLEMENTED", "C7 draft maturity overstated")
    require(c10["canonical_authority_readiness"] == "LOGICAL_OWNER_DECLARED_NOT_CANONICAL_READY", "C10 veto readiness overstated")


def check_r1_boundaries_and_counterevidence() -> None:
    selection = (PACKAGE / "NEXT-VERTICAL-SLICE-SELECTION.md").read_text(encoding="utf-8")
    required_exclusions = [
        "L2/order-book",
        "displayed-depth",
        "raw tick/order",
        "L3",
        "DDX/DDY",
        "synthetic Delta/CVD/OFI",
        "participant identity",
        "hidden-stop",
        "main-force intent",
    ]
    for exclusion in required_exclusions:
        require(exclusion in selection, f"BAR_ONLY exclusion missing: {exclusion}")
    require("preregistered procedural independence was not proven" in selection, "PR #75 independence language overstated")

    audit = (PACKAGE / "ENTERPRISE-BLUEPRINT-CURRENT-STATE-AUDIT.md").read_text(encoding="utf-8")
    require("PR #66 is candidate evidence only" in audit, "W12 Draft boundary absent from audit")
    require("UNKNOWN_MIGRATION_REQUIRED" in audit, "W3 migration boundary absent from audit")


def check_dependency_dag() -> None:
    dag = load_yaml(PACKAGE / "DEPENDENCY-DAG-AND-CRITICAL-PATH.yaml")
    graph = {item["id"]: list(item["prerequisites"]) for item in dag["nodes"]}
    visited: set[str] = set()
    active: set[str] = set()

    def visit(node: str) -> None:
        require(node in graph, f"unknown DAG node {node}")
        require(node not in active, f"dependency cycle at {node}")
        if node in visited:
            return
        active.add(node)
        for parent in graph[node]:
            visit(parent)
        active.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def main() -> int:
    yaml_count, json_count = check_yaml_and_json()
    text_count = check_utf8_and_secrets()
    check_required_artifacts()
    check_program_references()
    check_authorities_and_interfaces()
    check_r1_boundaries_and_counterevidence()
    check_dependency_dag()
    print(
        json.dumps(
            {
                "status": "PASS",
                "yaml_files": yaml_count,
                "json_files": json_count,
                "utf8_secret_scanned_files": text_count,
                "logical_authority_conflicts": 0,
                "selected_business_slices": 1,
                "business_runtime_executed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
