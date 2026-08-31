"""Repository-local, dependency-free public-safe capability verifier.

This verifier fails closed.  It does not depend on optional executables, does
not follow links, resolves Python import aliases through the AST, checks active
browser URL surfaces, and mechanically binds configured roots to PR triggers.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Iterable, Mapping


RULES_SCHEMA = "PublicSafeBoundaryRules/v1"
RECEIPT_SCHEMA = "PublicSafeBoundaryReceipt/v1"
DEFAULT_CONFIG = Path("tools/public_safe_boundary_rules.json")
DEFAULT_WORKFLOW = Path(".github/workflows/creative-runtime-offline.yml")
_REMOTE_URL = re.compile(r"(?is)^\s*(?:https?:)?//")
_CSS_REMOTE = re.compile(r"(?is)(?:url\s*\(\s*['\"]?|@import\s+(?:url\s*\(\s*)?['\"]?)((?:https?:)?//)")
_JS_REMOTE_CAPABILITY = re.compile(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|navigator\.sendBeacon)\s*(?:\(|\.)")
_JS_REMOTE_IMPORT = re.compile(r"(?is)\b(?:import\s*\(|import[^;\n]*?\bfrom\s*)['\"]\s*(?:https?:)?//")


class BoundaryViolation(ValueError):
    """Raised for an unsafe capability or unverifiable scan condition."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BoundaryViolation(f"Duplicate config key: {key}")
        result[key] = value
    return result


def _strict_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise BoundaryViolation(f"Config must be a regular non-symlink file: {path}")
    try:
        raw = path.read_bytes()
        if not raw:
            raise BoundaryViolation("Config is empty")
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, BoundaryViolation) as error:
        raise BoundaryViolation("Config must be strict UTF-8 JSON") from error
    if not isinstance(value, dict) or value.get("schema") != RULES_SCHEMA:
        raise BoundaryViolation("Unsupported rules schema")
    expected = {
        "schema", "scan_roots", "scanned_suffixes", "forbidden_python_imports",
        "forbidden_python_references", "required_pull_request_paths",
    }
    if set(value) != expected:
        raise BoundaryViolation("Rules fields differ from the closed schema")
    for key in expected - {"schema"}:
        items = value.get(key)
        if not isinstance(items, list) or not items or not all(isinstance(item, str) and item for item in items):
            raise BoundaryViolation(f"Rules field {key} must be a non-empty string list")
        if len(items) != len(set(items)):
            raise BoundaryViolation(f"Rules field {key} contains duplicates")
    return value


def _is_link(entry: os.DirEntry[str]) -> bool:
    if entry.is_symlink():
        return True
    details = entry.stat(follow_symlinks=False)
    attributes = getattr(details, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse and attributes & reparse)


def _walk_no_links(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise BoundaryViolation(f"Scan root must be a regular directory: {root}")
    files: list[Path] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as error:
            raise BoundaryViolation(f"Cannot enumerate scan directory: {directory}") from error
        for entry in entries:
            try:
                if _is_link(entry):
                    raise BoundaryViolation(f"Symlink or reparse point is forbidden: {entry.path}")
                if entry.is_dir(follow_symlinks=False):
                    visit(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    files.append(Path(entry.path))
                else:
                    raise BoundaryViolation(f"Unsupported filesystem entry: {entry.path}")
            except OSError as error:
                raise BoundaryViolation(f"Cannot inspect filesystem entry: {entry.path}") from error

    visit(root)
    return files


def _dotted_name(node: ast.AST, aliases: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value, aliases)
        return f"{base}.{node.attr}" if base else None
    return None


def verify_python_source(text: str, label: str, rules: Mapping[str, Any]) -> None:
    try:
        tree = ast.parse(text, filename=label)
    except SyntaxError as error:
        raise BoundaryViolation(f"Python cannot be parsed: {label}: {error.msg}") from error
    aliases: dict[str, str] = {}
    forbidden_imports = tuple(rules["forbidden_python_imports"])
    forbidden_refs = tuple(rules["forbidden_python_references"])

    def import_forbidden(name: str) -> bool:
        return any(name == item or name.startswith(item + ".") for item in forbidden_imports)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                local = item.asname or item.name.split(".")[0]
                aliases[local] = item.name if item.asname else item.name.split(".")[0]
                if import_forbidden(item.name):
                    raise BoundaryViolation(f"Forbidden Python capability import {item.name}: {label}:{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for item in node.names:
                resolved = f"{module}.{item.name}" if module else item.name
                aliases[item.asname or item.name] = resolved
                if import_forbidden(module) or import_forbidden(resolved):
                    raise BoundaryViolation(f"Forbidden Python capability import {resolved}: {label}:{node.lineno}")

    for node in ast.walk(tree):
        reference: str | None = None
        if isinstance(node, ast.Call):
            reference = _dotted_name(node.func, aliases)
            if reference in {"__import__", "importlib.import_module"} and node.args:
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str) and import_forbidden(argument.value):
                    raise BoundaryViolation(
                        f"Forbidden dynamic Python capability import {argument.value}: {label}:{node.lineno}"
                    )
        elif isinstance(node, ast.Subscript | ast.Attribute):
            reference = _dotted_name(node, aliases)
        if reference and any(reference == item or reference.startswith(item + ".") for item in forbidden_refs):
            raise BoundaryViolation(f"Forbidden environment capability {reference}: {label}:{node.lineno}")


class _ActiveURLParser(HTMLParser):
    ACTIVE: dict[str, frozenset[str]] = {
        "audio": frozenset({"src"}), "base": frozenset({"href"}), "button": frozenset({"formaction"}),
        "embed": frozenset({"src"}), "form": frozenset({"action"}),
        "iframe": frozenset({"src"}), "img": frozenset({"src", "srcset"}),
        "input": frozenset({"src", "formaction"}), "link": frozenset({"href"}),
        "object": frozenset({"data"}), "script": frozenset({"src"}),
        "source": frozenset({"src", "srcset"}), "track": frozenset({"src"}),
        "use": frozenset({"href", "xlink:href"}), "image": frozenset({"href", "xlink:href"}),
        "video": frozenset({"src", "poster"}),
    }

    def __init__(self, label: str) -> None:
        super().__init__(convert_charrefs=True)
        self.label = label

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        active = self.ACTIVE.get(tag.lower(), frozenset())
        normalized = {name.lower(): value or "" for name, value in attrs}
        if tag.lower() == "meta" and normalized.get("http-equiv", "").lower() == "refresh":
            content = normalized.get("content", "")
            match = re.search(r"(?is)\burl\s*=\s*['\"]?\s*((?:https?:)?//)", content)
            if match:
                raise BoundaryViolation(f"Remote meta refresh in {self.label}")
        for name, value in attrs:
            if name.lower() == "style" and value and _CSS_REMOTE.search(value):
                raise BoundaryViolation(f"Remote CSS load in {self.label}")
            if name.lower() not in active or value is None:
                continue
            candidates = [part.strip().split()[0] for part in value.split(",") if part.strip()]
            if any(_REMOTE_URL.match(candidate) for candidate in candidates):
                raise BoundaryViolation(f"Remote browser load {tag}.{name} in {self.label}")

    handle_startendtag = handle_starttag


def verify_browser_source(text: str, label: str, suffix: str) -> None:
    if _CSS_REMOTE.search(text):
        raise BoundaryViolation(f"Remote CSS resource in {label}")
    if suffix in {".html", ".htm"}:
        parser = _ActiveURLParser(label)
        try:
            parser.feed(text)
            parser.close()
        except BoundaryViolation:
            raise
        except Exception as error:
            raise BoundaryViolation(f"HTML cannot be safely parsed: {label}") from error
    if suffix in {".html", ".htm", ".js"} and _JS_REMOTE_CAPABILITY.search(text):
        raise BoundaryViolation(f"Browser network capability in {label}")
    if suffix in {".html", ".htm", ".js"} and _JS_REMOTE_IMPORT.search(text):
        raise BoundaryViolation(f"Remote JavaScript import in {label}")


def _workflow_pr_paths(workflow: Path) -> list[str]:
    if workflow.is_symlink() or not workflow.is_file():
        raise BoundaryViolation("Creative workflow is missing or linked")
    try:
        lines = workflow.read_text(encoding="utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as error:
        raise BoundaryViolation("Creative workflow is not strict UTF-8") from error
    pull_indent: int | None = None
    paths_indent: int | None = None
    values: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if stripped == "pull_request:":
            pull_indent, paths_indent = indent, None
            continue
        if pull_indent is None:
            continue
        if indent <= pull_indent and not stripped.startswith("-"):
            if paths_indent is not None:
                break
            pull_indent = None
            continue
        if stripped == "paths:":
            paths_indent = indent
            continue
        if paths_indent is not None and indent > paths_indent and stripped.startswith("-"):
            values.append(stripped[1:].strip().strip("'\""))
        elif paths_indent is not None and indent <= paths_indent:
            break
    if not values:
        raise BoundaryViolation("pull_request.paths is missing or empty")
    return values


def verify_workflow_congruence(repo: Path, rules: Mapping[str, Any], workflow: Path = DEFAULT_WORKFLOW) -> None:
    actual = _workflow_pr_paths(repo / workflow)
    expected = list(rules["required_pull_request_paths"])
    if set(actual) != set(expected) or len(actual) != len(expected):
        raise BoundaryViolation(f"Workflow PR paths drifted: expected={sorted(expected)} actual={sorted(actual)}")
    root_patterns = {f"{root.rstrip('/')}/**" for root in rules["scan_roots"]}
    if not root_patterns.issubset(set(actual)):
        raise BoundaryViolation("Every configured scan root must have an exact recursive PR trigger")


def verify_repository(repo: Path, config: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    repo = repo.resolve()
    rules = _strict_json(repo / config)
    verify_workflow_congruence(repo, rules)
    suffixes = set(rules["scanned_suffixes"])
    scanned: list[dict[str, str]] = []
    for raw_root in rules["scan_roots"]:
        root = repo / raw_root
        for path in _walk_no_links(root):
            if path.suffix.lower() not in suffixes:
                continue
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="strict")
            except (OSError, UnicodeDecodeError) as error:
                raise BoundaryViolation(f"Scanned source is unreadable or non-UTF8: {path}") from error
            relative = path.relative_to(repo).as_posix()
            if path.suffix.lower() == ".py":
                verify_python_source(text, relative, rules)
            else:
                verify_browser_source(text, relative, path.suffix.lower())
            scanned.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
    if not scanned:
        raise BoundaryViolation("Public-safe scan selected no source files")
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "scan_roots": list(rules["scan_roots"]),
        "file_count": len(scanned),
        "files": sorted(scanned, key=lambda item: item["path"]),
    }


def _git_head(repo: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise BoundaryViolation("Cannot resolve repository HEAD") from error


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--expected-head")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt = verify_repository(args.repo, args.config)
        head = _git_head(args.repo)
        if args.expected_head and head != args.expected_head:
            raise BoundaryViolation(f"Exact HEAD mismatch: expected={args.expected_head} actual={head}")
        receipt["exact_head"] = head
        rendered = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(rendered, encoding="utf-8")
        sys.stdout.write(rendered)
        return 0
    except Exception as error:
        failure = {"schema": RECEIPT_SCHEMA, "status": "FAIL", "error": str(error)}
        sys.stderr.write(json.dumps(failure, ensure_ascii=False, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
