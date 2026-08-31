"""Fail-closed, repository-local public-safety boundary verifier.

The verifier has no dependency on ripgrep or another optional executable.  It
reads a versioned JSON rule file, validates every declared scan surface, and
returns a deterministic receipt.  Missing/unreadable surfaces, malformed
configuration, invalid UTF-8, symlink indirection, unexpected scanner errors,
or forbidden matches are all failures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Mapping, NamedTuple, Sequence


CONFIG_SCHEMA = "CreativeRuntimePublicSafeBoundaryConfig/v1"
RECEIPT_SCHEMA = "CreativeRuntimePublicSafeBoundaryReceipt/v1"


class PublicSafeBoundaryError(RuntimeError):
    """Fail-closed verification error safe to report in CI."""


class Rule(NamedTuple):
    rule_id: str
    expression: re.Pattern[str]


class Surface(NamedTuple):
    name: str
    roots: tuple[str, ...]
    extensions: tuple[str, ...]
    rules: tuple[Rule, ...]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_utf8(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise PublicSafeBoundaryError(f"{label} is missing, unreadable, or not valid UTF-8: {path}") from error


def _strict_keys(record: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(record)
    if actual != expected:
        raise PublicSafeBoundaryError(
            f"Malformed {label}: expected keys {sorted(expected)}, found {sorted(actual)}"
        )


def _nonempty_strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise PublicSafeBoundaryError(f"Malformed {label}: expected a non-empty string list")
    if len(set(value)) != len(value):
        raise PublicSafeBoundaryError(f"Malformed {label}: duplicate values are forbidden")
    return tuple(value)


def _load_config(config_path: Path) -> tuple[tuple[Surface, ...], str]:
    raw = _read_utf8(config_path, "boundary configuration")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise PublicSafeBoundaryError(f"Malformed boundary configuration JSON: {error.msg}") from error
    if not isinstance(payload, Mapping):
        raise PublicSafeBoundaryError("Malformed boundary configuration: root must be an object")
    _strict_keys(payload, {"schema", "surfaces"}, "boundary configuration")
    if payload["schema"] != CONFIG_SCHEMA:
        raise PublicSafeBoundaryError("Unsupported boundary configuration schema")
    surfaces_raw = payload["surfaces"]
    if not isinstance(surfaces_raw, list) or not surfaces_raw:
        raise PublicSafeBoundaryError("Malformed boundary configuration: surfaces must be non-empty")

    surfaces: list[Surface] = []
    surface_names: set[str] = set()
    all_rule_ids: set[str] = set()
    for index, record in enumerate(surfaces_raw):
        label = f"surface[{index}]"
        if not isinstance(record, Mapping):
            raise PublicSafeBoundaryError(f"Malformed {label}: expected an object")
        _strict_keys(record, {"name", "roots", "extensions", "forbidden_patterns"}, label)
        name = record["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", name):
            raise PublicSafeBoundaryError(f"Malformed {label}.name")
        if name in surface_names:
            raise PublicSafeBoundaryError(f"Duplicate surface name: {name}")
        surface_names.add(name)
        roots = _nonempty_strings(record["roots"], f"{label}.roots")
        for root in roots:
            parsed = PurePosixPath(root)
            if parsed.is_absolute() or ".." in parsed.parts or "." in parsed.parts or "\\" in root:
                raise PublicSafeBoundaryError(f"Unsafe repository-relative root in {label}: {root}")
        extensions = _nonempty_strings(record["extensions"], f"{label}.extensions")
        if not all(re.fullmatch(r"\.[a-z0-9]+", extension) for extension in extensions):
            raise PublicSafeBoundaryError(f"Malformed {label}.extensions")
        patterns = record["forbidden_patterns"]
        if not isinstance(patterns, list) or not patterns:
            raise PublicSafeBoundaryError(f"Malformed {label}.forbidden_patterns")
        rules: list[Rule] = []
        for rule_index, rule_record in enumerate(patterns):
            rule_label = f"{label}.forbidden_patterns[{rule_index}]"
            if not isinstance(rule_record, Mapping):
                raise PublicSafeBoundaryError(f"Malformed {rule_label}")
            _strict_keys(rule_record, {"id", "regex"}, rule_label)
            rule_id = rule_record["id"]
            expression = rule_record["regex"]
            if not isinstance(rule_id, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", rule_id):
                raise PublicSafeBoundaryError(f"Malformed {rule_label}.id")
            if rule_id in all_rule_ids:
                raise PublicSafeBoundaryError(f"Duplicate boundary rule id: {rule_id}")
            if not isinstance(expression, str) or not expression:
                raise PublicSafeBoundaryError(f"Malformed {rule_label}.regex")
            try:
                compiled = re.compile(expression, re.IGNORECASE | re.MULTILINE)
            except re.error as error:
                raise PublicSafeBoundaryError(f"Malformed regex for {rule_id}: {error.msg}") from error
            all_rule_ids.add(rule_id)
            rules.append(Rule(rule_id, compiled))
        surfaces.append(Surface(name, roots, extensions, tuple(rules)))
    return tuple(surfaces), _sha256_text(_canonical_json(payload))


def _repository_path(repository_root: Path, relative: str) -> Path:
    candidate = repository_root.joinpath(*PurePosixPath(relative).parts)
    try:
        candidate.resolve(strict=False).relative_to(repository_root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise PublicSafeBoundaryError(f"Scan root escapes repository: {relative}") from error
    return candidate


def _scan_surface(repository_root: Path, surface: Surface) -> tuple[list[dict[str, Any]], int]:
    findings: list[dict[str, Any]] = []
    scanned_files = 0
    for relative_root in surface.roots:
        root = _repository_path(repository_root, relative_root)
        if not root.exists() or not root.is_dir() or root.is_symlink():
            raise PublicSafeBoundaryError(f"Required scan surface is missing, unreadable, or indirect: {relative_root}")
        files = sorted(
            path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in surface.extensions
        )
        if not files:
            raise PublicSafeBoundaryError(f"Required scan surface contains no declared files: {relative_root}")
        for path in files:
            if path.is_symlink():
                raise PublicSafeBoundaryError(f"Symlinked scan file is forbidden: {path.relative_to(repository_root)}")
            content = _read_utf8(path, "scan file")
            scanned_files += 1
            for rule in surface.rules:
                for match in rule.expression.finditer(content):
                    findings.append(
                        {
                            "rule_id": rule.rule_id,
                            "path": path.relative_to(repository_root).as_posix(),
                            "line": content.count("\n", 0, match.start()) + 1,
                        }
                    )
    return findings, scanned_files


def verify(repository_root: Path, config_path: Path) -> dict[str, Any]:
    root = repository_root.resolve(strict=True)
    if not root.is_dir():
        raise PublicSafeBoundaryError("Repository root is not a directory")
    surfaces, config_hash = _load_config(config_path.resolve(strict=False))
    findings: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for surface in surfaces:
        surface_findings, count = _scan_surface(root, surface)
        counts[surface.name] = count
        findings.extend(surface_findings)
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": "FAIL" if findings else "PASS",
        "configuration_sha256": config_hash,
        "surface_file_counts": counts,
        "finding_count": len(findings),
        "findings": findings,
        "external_scanner_required": False,
    }
    if findings:
        details = ", ".join(f"{item['rule_id']}@{item['path']}:{item['line']}" for item in findings)
        raise PublicSafeBoundaryError("Forbidden public-safety boundary indicators detected: " + details)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("public_safe_boundary_rules.json"),
    )
    args = parser.parse_args(argv)
    try:
        receipt = verify(args.root, args.config)
    except Exception as error:  # The CLI boundary must fail closed even on an unexpected verifier defect.
        failure = {
            "schema": RECEIPT_SCHEMA,
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        print(_canonical_json(failure), file=sys.stderr)
        return 2
    print(_canonical_json(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
