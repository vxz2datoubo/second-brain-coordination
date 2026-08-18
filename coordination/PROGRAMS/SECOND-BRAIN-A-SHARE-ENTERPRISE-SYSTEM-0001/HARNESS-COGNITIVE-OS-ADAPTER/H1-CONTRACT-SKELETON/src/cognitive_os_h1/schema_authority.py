"""The sole H1 structural authority: canonical DSL compiled to Draft 2020-12."""
from __future__ import annotations

from functools import lru_cache
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


CANONICAL_DSL_RELATIVE = Path("coordination/PROPOSALS/PROGRAM-LANES/LANE-A-HARNESS-INTEGRATION/COGNITIVE-OS-CONTRACT-SCHEMAS.yaml")
TIMESTAMP_FIELDS = {"created_at", "closed_at", "completed_at", "generated_at", "observed_at"}


def canonical_dsl_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / CANONICAL_DSL_RELATIVE
        if candidate.is_file():
            return candidate
    raise RuntimeError("CANONICAL_COGNITIVE_DSL_NOT_FOUND")


def _compile_rule(rule: Mapping[str, Any]) -> dict[str, Any]:
    compiled: dict[str, Any] = {}
    for key in ("type", "const", "enum", "minLength", "minimum", "minItems", "uniqueItems"):
        if key in rule:
            compiled[key] = rule[key]
    if "required" in rule:
        compiled["required"] = rule["required"]
    if "properties" in rule:
        compiled["properties"] = {}
        for name, value in rule["properties"].items():
            field = _compile_rule(value)
            if name in TIMESTAMP_FIELDS and "string" in field.get("type", [] if isinstance(field.get("type"), list) else [field.get("type")]):
                field["format"] = "date-time"
            compiled["properties"][name] = field
    if "items" in rule:
        compiled["items"] = _compile_rule(rule["items"])
    return compiled


@lru_cache(maxsize=1)
def compiled_draft_2020_12() -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - CI installs the explicit test dependency.
        raise RuntimeError("PYAML_REQUIRED_FOR_CANONICAL_SCHEMA_COMPILATION") from exc
    dsl = yaml.safe_load(canonical_dsl_path().read_text(encoding="utf-8"))
    definitions = {
        name: _compile_rule(rule)
        for name, rule in dsl.items()
        if name.endswith("_v1") and isinstance(rule, Mapping) and rule.get("type") == "object"
    }
    refs = [{"$ref": "#/$defs/" + name} for name in sorted(definitions)]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "CognitiveOS-H1/canonical-compiled/v1",
        "$comment": "Generated in memory from canonical COGNITIVE-OS-CONTRACT-SCHEMAS.yaml; Python semantic validation is separate.",
        "$defs": definitions,
        "oneOf": refs,
    }


def schema_validation_errors(record: Mapping[str, Any]) -> list[tuple[str, str]]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:  # pragma: no cover - CI installs the explicit test dependency.
        raise RuntimeError("JSONSCHEMA_REQUIRED_FOR_H1_STRUCTURAL_VALIDATION") from exc
    version = record.get("schema_version")
    definition = str(version).replace("/", "_")
    bundle = compiled_draft_2020_12()
    if definition not in bundle["$defs"]:
        return [("/schema_version", "unsupported canonical schema version")]
    schema = {"$schema": bundle["$schema"], "$defs": bundle["$defs"], "$ref": "#/$defs/" + definition}
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [("/" + "/".join(str(part) for part in error.absolute_path), error.message) for error in sorted(validator.iter_errors(dict(record)), key=lambda item: list(item.absolute_path))]
    for field in TIMESTAMP_FIELDS.intersection(record):
        value = record[field]
        if value is None:
            continue
        try:
            offset_aware = isinstance(value, str) and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
        except ValueError:
            offset_aware = False
        if not offset_aware:
            errors.append(("/" + field, "not RFC3339 offset-aware date-time"))
    return errors
