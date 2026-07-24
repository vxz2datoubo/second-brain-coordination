"""Structural validator for the public-safe 0022 D0 admission-contract package."""

from __future__ import annotations

from pathlib import Path

import yaml
from yaml.constructor import ConstructorError


ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "PROJECT-PLAN.yaml",
    "CURRENT-DATA-ADMISSION-AND-NON-DUPLICATION-AUDIT.md",
    "PR51-REUSE-AND-AUTHORITY-MATRIX.yaml",
    "SOURCE-ADMISSION-REQUIREMENTS-AND-EVIDENCE-MATRIX.yaml",
    "PIT-FIELD-TIME-UNIT-ADJUSTMENT-CONTRACT.yaml",
    "HISTORICAL-SECURITY-STATUS-AND-RULE-SNAPSHOT-CONTRACT.yaml",
    "W2-W3-W7-READONLY-OWNERSHIP-AND-DEPENDENCY-MAP.yaml",
    "ONE-SOURCE-ADMISSION-DECISION-PROCEDURE.yaml",
    "WORKBUDDY-ISSUE92-LOCAL-EVIDENCE-EXECUTION-CONTRACT.yaml",
    "OFFICIAL-SOURCE-EVIDENCE-REGISTER.yaml",
    "NEGATIVE-ABSTENTION-AND-FAILURE-TEST-MATRIX.yaml",
    "UNKNOWN-REGISTRY.yaml",
    "TEST-RUN-RECEIPT.md",
    "CODEX-FEEDBACK-v2.yaml",
    "AI_HANDOFF.yaml",
}


class DuplicateKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys at every level."""


def _construct_unique_mapping(loader: DuplicateKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict:
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError("while constructing a mapping", node.start_mark, f"duplicate key: {key}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DuplicateKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


EXPECTED_ENTRIES = {
    "SSE-2026-TRADING-RULES": {
        "publisher": "Shanghai Stock Exchange",
        "document_id": "上证发〔2026〕41号",
        "official_url": "https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20260424_10816492.shtml",
        "publication_date": "2026-04-24",
        "effective_from": "2026-07-06",
        "supersedes": "Shanghai Stock Exchange Trading Rules (2023 revision), 上证发〔2023〕32号",
        "deferred_provision_status": "EXPLICIT_ATTACHMENT_AND_SEPARATE_IMPLEMENTATION_NOTICE_REQUIRED",
    },
    "SZSE-2026-TRADING-RULES": {
        "publisher": "Shenzhen Stock Exchange",
        "document_id": "深证上〔2026〕551号",
        "official_url": "https://www.szse.cn/lawrules/rule/allrules/bussiness/t20260424_620190.html",
        "publication_date": "2026-04-24",
        "effective_from": "2026-07-06",
        "supersedes": "Shenzhen Stock Exchange Trading Rules (2023 revision), 深证上〔2023〕98号",
        "deferred_provision_status": "NO_DEFERRED_CLAUSE_CLAIM_FROM_NOTICE_PROVISION_LEVEL_REVIEW_REQUIRED",
    },
    "BSE-2026-TRADING-RULES": {
        "publisher": "Beijing Stock Exchange",
        "document_id": "北证公告〔2026〕17号",
        "official_url": "https://www.bse.cn/jygl_list/200028217.html",
        "publication_date": "2026-04-24",
        "effective_from": "2026-07-06",
        "deferred_provision_status": "RULES_3_6_5_P2_P3_3_7_1_TO_3_7_10_AND_4_5_1_TO_4_5_4_REQUIRE_SEPARATE_IMPLEMENTATION_TIMING",
    },
}
COMMON_ENTRY_FIELDS = {
    "page_access_status": "VERIFIED_ACCESSIBLE",
    "document_authority_status": "VERIFIED_OFFICIAL_EXCHANGE_RULE",
    "effective_date_status": "VERIFIED_OFFICIAL_SOURCE",
    "document_hash_status": "UNKNOWN_NOT_CAPTURED",
    "historical_coverage_status": "UNKNOWN_REMAINS_OPEN",
}


def load_yaml(name: str) -> object:
    return yaml.load((ROOT / name).read_text(encoding="utf-8"), Loader=DuplicateKeyLoader)


def check_register() -> list[str]:
    errors: list[str] = []
    try:
        register = load_yaml("OFFICIAL-SOURCE-EVIDENCE-REGISTER.yaml")
    except (OSError, yaml.YAMLError) as error:
        return [f"official register rejected: {error}"]
    if not isinstance(register, dict) or not isinstance(register.get("entries"), list):
        return ["official register must contain an entries list"]
    entries = register["entries"]
    observed_ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
    if len(entries) != 3 or set(observed_ids) != set(EXPECTED_ENTRIES) or len(set(observed_ids)) != len(observed_ids):
        errors.append("official register must contain exactly one SSE, SZSE and BSE entry")
        return errors
    by_id = {entry["id"]: entry for entry in entries}
    for entry_id, expected in EXPECTED_ENTRIES.items():
        entry = by_id[entry_id]
        for field, value in {**expected, **COMMON_ENTRY_FIELDS}.items():
            if str(entry.get(field)) != value:
                errors.append(f"{entry_id}.{field} must equal {value}")
    return errors


def self_test_duplicate_keys() -> list[str]:
    try:
        yaml.load("key: first\\nkey: second\\n", Loader=DuplicateKeyLoader)
    except ConstructorError:
        return []
    return ["duplicate-key loader self-test did not reject duplicate input"]


def main() -> int:
    errors = [f"missing: {name}" for name in sorted(REQUIRED) if not (ROOT / name).is_file()]
    if not errors:
        errors += check_register()
        errors += self_test_duplicate_keys()
    if errors:
        print("D0 admission contract package invalid")
        print("\n".join(errors))
        return 1
    print("D0 admission contract package valid: no source selected and Issue92 remains queued")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
