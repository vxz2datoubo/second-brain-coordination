"""Dependency-free validator for the JSON Schema subset used by this package."""

from __future__ import annotations

import re
from typing import Any


class SchemaValidationError(ValueError):
    pass


def validate_schema_subset(schema: dict[str, Any], value: Any) -> None:
    _validate(schema, value, "$")


def _validate(schema: dict[str, Any], value: Any, path: str) -> None:
    expected = schema.get("type")
    if expected is not None and not _matches_type(expected, value):
        raise SchemaValidationError(f"{path}:type")
    if "const" in schema and value != schema["const"]:
        raise SchemaValidationError(f"{path}:const")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaValidationError(f"{path}:enum")
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            raise SchemaValidationError(f"{path}:minLength")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise SchemaValidationError(f"{path}:pattern")
    if isinstance(value, int) and not isinstance(value, bool) and "minimum" in schema and value < schema["minimum"]:
        raise SchemaValidationError(f"{path}:minimum")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            raise SchemaValidationError(f"{path}:minItems")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate(item_schema, item, f"{path}[{index}]")
    if isinstance(value, dict):
        missing = set(schema.get("required", ())) - set(value)
        if missing:
            raise SchemaValidationError(f"{path}:required:{sorted(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise SchemaValidationError(f"{path}:additionalProperties:{sorted(unknown)}")
        for key, item in value.items():
            if key in properties:
                _validate(properties[key], item, f"{path}.{key}")


def _matches_type(expected: str | list[str], value: Any) -> bool:
    names = [expected] if isinstance(expected, str) else expected
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return any(name in checks and checks[name](value) for name in names)
