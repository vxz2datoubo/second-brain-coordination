"""Fail-closed public-safe verifier anchored to a canonical policy floor.

Only Python's standard library is used. Candidate configuration may widen the
canonical floor but cannot shrink it. In CI the floor is read from the immutable
pull-request base commit rather than from candidate-controlled working files.
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


RULES_SCHEMA = "PublicSafeBoundaryRules/v2"
FLOOR_SCHEMA = "CREATIVE_RUNTIME_PUBLIC_SAFE_POLICY_FLOOR/v1"
RECEIPT_SCHEMA = "PublicSafeBoundaryReceipt/v2"
CONFIG_PATH = Path("tools/public_safe_boundary_rules.json")
WORKFLOW_PATH = Path(".github/workflows/creative-runtime-offline.yml")
FLOOR_PATH = Path("coordination/GOVERNANCE/CREATIVE-RUNTIME-PUBLIC-SAFE-POLICY-FLOOR-v1.yaml")
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
_ASCII_EDGE = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x7f"
_CSS_ESCAPE = re.compile(r"\\(?:([0-9a-fA-F]{1,6})[ \t\r\n\f]?|(.))", re.DOTALL)
_JS_ESCAPE = re.compile(r"\\(?:x([0-9a-fA-F]{2})|u\{([0-9a-fA-F]{1,6})\}|u([0-9a-fA-F]{4}))")
_DANGEROUS_JS_NAMES = ("fetch", "xmlhttprequest", "websocket", "eventsource", "sendbeacon")
_MINIMUM_FORBIDDEN_IMPORTS = frozenset({
    "aiohttp", "anthropic", "builtins", "ftplib", "http.client", "httpx",
    "imaplib", "importlib", "openai", "operator", "poplib", "requests",
    "smtplib", "socket", "telnetlib", "urllib.request", "urllib3",
    "websockets", "xmlrpc.client",
})
_MINIMUM_FORBIDDEN_REFS = frozenset({"os.environ", "os.environb", "os.getenv", "os.getenvb"})


class BoundaryViolation(ValueError):
    """The repository cannot prove the configured public-safe boundary."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BoundaryViolation(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_rules(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise BoundaryViolation("Rules must be a regular non-link file")
    try:
        raw = path.read_bytes()
        if not raw:
            raise BoundaryViolation("Rules file is empty")
        rules = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, BoundaryViolation) as error:
        raise BoundaryViolation("Rules must be strict duplicate-free UTF-8 JSON") from error
    fields = {
        "schema", "scan_roots", "scanned_suffixes", "forbidden_python_imports",
        "forbidden_python_references", "forbidden_capability_classes",
        "required_pull_request_paths",
    }
    if not isinstance(rules, dict) or rules.get("schema") != RULES_SCHEMA or set(rules) != fields:
        raise BoundaryViolation("Rules differ from the closed v2 schema")
    for field in fields - {"schema"}:
        values = rules.get(field)
        if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
            raise BoundaryViolation(f"Rules field {field} must be a non-empty string list")
        if len(values) != len(set(values)):
            raise BoundaryViolation(f"Rules field {field} contains duplicates")
    if not _MINIMUM_FORBIDDEN_IMPORTS.issubset(rules["forbidden_python_imports"]):
        raise BoundaryViolation("Rules shrink the verifier's minimum forbidden import capabilities")
    if not _MINIMUM_FORBIDDEN_REFS.issubset(rules["forbidden_python_references"]):
        raise BoundaryViolation("Rules shrink the verifier's minimum environment-read capabilities")
    relative_component = re.compile(r"[A-Za-z0-9_.-]+")
    for root in rules["scan_roots"]:
        parts = root.split("/")
        if (
            "\\" in root or root.startswith("/") or ":" in root
            or any(part in {"", ".", ".."} or not relative_component.fullmatch(part) for part in parts)
        ):
            raise BoundaryViolation(f"Scan root is not a canonical repository-relative path: {root}")
    for suffix in rules["scanned_suffixes"]:
        if not re.fullmatch(r"\.[a-z0-9]+", suffix):
            raise BoundaryViolation(f"Unsafe source suffix rule: {suffix}")
    for field in ("forbidden_python_imports", "forbidden_python_references"):
        for reference in rules[field]:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", reference):
                raise BoundaryViolation(f"Unsafe Python capability reference in {field}: {reference}")
    for capability in rules["forbidden_capability_classes"]:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", capability):
            raise BoundaryViolation(f"Unsafe capability class: {capability}")
    for trigger in rules["required_pull_request_paths"]:
        plain = trigger[:-3] if trigger.endswith("/**") else trigger
        parts = plain.split("/")
        if (
            "\\" in trigger or trigger.startswith("/") or ":" in trigger
            or any(part in {"", ".", ".."} or not relative_component.fullmatch(part) for part in parts)
        ):
            raise BoundaryViolation(f"Unsafe pull-request trigger path: {trigger}")
    return rules


def _yaml_list_map(text: str) -> tuple[str, dict[tuple[str, ...], list[str]]]:
    if "\t" in text:
        raise BoundaryViolation("Canonical policy floor must not contain tabs")
    schema = ""
    stack: list[tuple[int, str]] = []
    lists: dict[tuple[str, ...], list[str]] = {}
    declared: set[tuple[str, ...]] = set()
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()
        if content.startswith("- "):
            path = tuple(key for level, key in stack if level < indent)
            if not path:
                raise BoundaryViolation(f"Unscoped policy-floor list at line {number}")
            value = content[2:].strip().strip("'\"")
            if not value or value.startswith(("&", "*", "!", "{" , "[")):
                raise BoundaryViolation(f"Unsupported policy-floor list value at line {number}")
            lists.setdefault(path, []).append(value)
            continue
        match = re.fullmatch(r"([A-Za-z0-9_]+):(?:\s*(.*))?", content)
        if not match:
            # Multiline prose is not used by the minimum lists; ignore its text
            # only when it is visibly indented beneath a scalar block.
            if stack and indent > stack[-1][0]:
                continue
            raise BoundaryViolation(f"Unsupported policy-floor syntax at line {number}")
        key, value = match.group(1), (match.group(2) or "").strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        path = tuple(item for _level, item in stack) + (key,)
        if path in declared:
            raise BoundaryViolation(f"Duplicate policy-floor key: {'.'.join(path)}")
        declared.add(path)
        if key == "schema" and indent == 0:
            schema = value.strip("'\"")
        if not value or value in {">-", "|", ">", "|-"}:
            stack.append((indent, key))
    return schema, lists


def _git_show(repo: Path, revision: str, path: Path) -> bytes:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
        raise BoundaryViolation("Policy-floor revision must be an exact 40-hex commit")
    try:
        return subprocess.run(
            ["git", "show", f"{revision}:{path.as_posix()}"], cwd=repo, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise BoundaryViolation("Cannot read the canonical policy floor from the immutable base") from error


def _load_floor(repo: Path, revision: str) -> tuple[dict[str, set[str]], str]:
    raw = _git_show(repo, revision, FLOOR_PATH)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise BoundaryViolation("Canonical policy floor is not strict UTF-8") from error
    schema, lists = _yaml_list_map(text)
    if schema != FLOOR_SCHEMA:
        raise BoundaryViolation("Unsupported canonical policy-floor schema")
    required_paths = {
        "scan_roots": (("minimum_scan_roots",),),
        "suffixes": (("minimum_source_suffixes", "python"), ("minimum_source_suffixes", "web")),
        "triggers": (("minimum_pull_request_trigger_paths",),),
        "classes": (
            ("minimum_forbidden_capability_classes", "python"),
            ("minimum_forbidden_capability_classes", "browser"),
        ),
    }
    floor: dict[str, set[str]] = {}
    for name, paths in required_paths.items():
        values: set[str] = set()
        for path in paths:
            items = lists.get(path)
            if not items:
                raise BoundaryViolation(f"Canonical floor is missing {'.'.join(path)}")
            values.update(items)
        floor[name] = values
    return floor, hashlib.sha256(raw).hexdigest()


def _require_floor(rules: Mapping[str, Any], floor: Mapping[str, set[str]]) -> None:
    candidate = {
        "scan_roots": set(rules["scan_roots"]),
        "suffixes": set(rules["scanned_suffixes"]),
        "triggers": set(rules["required_pull_request_paths"]),
        "classes": set(rules["forbidden_capability_classes"]),
    }
    for field, minimum in floor.items():
        missing = sorted(minimum - candidate[field])
        if missing:
            raise BoundaryViolation(f"Candidate rules shrink canonical {field}: {missing}")


def _entry_is_indirect(entry: os.DirEntry[str]) -> bool:
    if entry.is_symlink():
        return True
    details = entry.stat(follow_symlinks=False)
    return bool(_REPARSE and getattr(details, "st_file_attributes", 0) & _REPARSE)


def _walk_no_indirection(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise BoundaryViolation(f"Scan root is absent or linked: {root}")
    files: list[Path] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda value: value.name)
        except OSError as error:
            raise BoundaryViolation(f"Cannot enumerate scan directory: {directory}") from error
        for entry in entries:
            try:
                if _entry_is_indirect(entry):
                    raise BoundaryViolation(f"Linked or reparse descendant is forbidden: {entry.path}")
                if entry.is_dir(follow_symlinks=False):
                    visit(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    files.append(Path(entry.path))
                else:
                    raise BoundaryViolation(f"Unsupported filesystem entry: {entry.path}")
            except OSError as error:
                raise BoundaryViolation(f"Cannot inspect scan entry: {entry.path}") from error

    visit(root)
    return files


def _constant_string(node: ast.AST, bindings: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return bindings.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _constant_string(node.left, bindings)
        right = _constant_string(node.right, bindings)
        return left + right if left is not None and right is not None else None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return None
            parts.append(value.value)
        return "".join(parts)
    return None


def _dotted(
    node: ast.AST,
    aliases: Mapping[str, str],
    strings: Mapping[str, str] | None = None,
) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value, aliases, strings)
        return f"{base}.{node.attr}" if base else None
    if isinstance(node, ast.Call):
        caller = _dotted(node.func, aliases, strings)
        if caller in {"__import__", "__import__.__call__", "importlib.import_module", "importlib.import_module.__call__"} and node.args:
            return _constant_string(node.args[0], strings or {})
    return None


def verify_python_source(text: str, label: str, rules: Mapping[str, Any]) -> None:
    try:
        tree = ast.parse(text, filename=label)
    except SyntaxError as error:
        raise BoundaryViolation(f"Python syntax cannot be verified: {label}:{error.lineno}") from error
    aliases: dict[str, str] = {}
    strings: dict[str, str] = {}
    forbidden_imports = tuple(rules["forbidden_python_imports"])
    forbidden_refs = tuple(rules["forbidden_python_references"])

    def forbidden_import(name: str) -> bool:
        return any(name == item or name.startswith(item + ".") for item in forbidden_imports)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                resolved = item.name
                aliases[item.asname or item.name.split(".")[0]] = resolved if item.asname else item.name.split(".")[0]
                if forbidden_import(resolved):
                    raise BoundaryViolation(f"Forbidden capability import {resolved}: {label}:{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for item in node.names:
                resolved = f"{module}.{item.name}" if module else item.name
                aliases[item.asname or item.name] = resolved
                if forbidden_import(module) or forbidden_import(resolved):
                    raise BoundaryViolation(f"Forbidden capability import {resolved}: {label}:{node.lineno}")

    # Resolve simple module aliases and bounded constant strings to a fixed point.
    assignments = [node for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.AnnAssign))]
    for _round in range(len(assignments) + 1):
        changed = False
        for node in assignments:
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Name) or value is None:
                    continue
                dotted = _dotted(value, aliases, strings)
                if dotted and aliases.get(target.id) != dotted:
                    aliases[target.id] = dotted
                    changed = True
                constant = _constant_string(value, strings)
                if constant is not None and strings.get(target.id) != constant:
                    strings[target.id] = constant
                    changed = True
        if not changed:
            break

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            reference = _dotted(node.func, aliases, strings)
            if reference in {"eval", "exec", "compile"}:
                raise BoundaryViolation(f"Dynamic code execution fails closed: {label}:{node.lineno}")
            if reference in {"__import__", "__import__.__call__", "importlib.import_module", "importlib.import_module.__call__"}:
                if not node.args:
                    raise BoundaryViolation(f"Unverifiable dynamic import: {label}:{node.lineno}")
                target = _constant_string(node.args[0], strings)
                if target is None:
                    raise BoundaryViolation(f"Unresolved dynamic import fails closed: {label}:{node.lineno}")
                if forbidden_import(target):
                    raise BoundaryViolation(f"Forbidden dynamic import {target}: {label}:{node.lineno}")
            if reference in {"vars", "globals", "locals"}:
                raise BoundaryViolation(f"Reflective namespace access fails closed: {label}:{node.lineno}")
            if reference and (reference.endswith(".__getattribute__") or ".__dict__." in reference):
                raise BoundaryViolation(f"Reflective capability access fails closed: {label}:{node.lineno}")
            if reference == "getattr":
                if len(node.args) < 2:
                    raise BoundaryViolation(f"Unverifiable getattr fails closed: {label}:{node.lineno}")
                attribute = _constant_string(node.args[1], strings)
                if attribute is None:
                    raise BoundaryViolation(f"Computed reflective attribute fails closed: {label}:{node.lineno}")
                if attribute in {"getenv", "getenvb", "environ", "environb", "__dict__"}:
                    raise BoundaryViolation(f"Reflective environment capability {attribute}: {label}:{node.lineno}")
                target = _dotted(node.args[0], aliases, strings)
                if target == "__builtins__" or (target and target.startswith("__builtins__.")):
                    raise BoundaryViolation(f"Reflective builtins access fails closed: {label}:{node.lineno}")
            if reference and any(reference == item or reference.startswith(item + ".") for item in forbidden_refs):
                raise BoundaryViolation(f"Forbidden environment capability {reference}: {label}:{node.lineno}")
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            reference = _dotted(node, aliases, strings)
            if reference and (
                reference == "__builtins__"
                or reference.startswith("__builtins__.")
                or ".__dict__" in reference
            ):
                raise BoundaryViolation(f"Reflective namespace capability fails closed: {label}:{node.lineno}")
            if reference and any(reference == item or reference.startswith(item + ".") for item in forbidden_refs):
                raise BoundaryViolation(f"Forbidden environment capability {reference}: {label}:{node.lineno}")
        if isinstance(node, ast.Subscript):
            base = _dotted(node.value, aliases, strings)
            if base == "__builtins__":
                raise BoundaryViolation(f"Reflective builtins capability fails closed: {label}:{node.lineno}")
            if base and any(base == item or base.startswith(item + ".") for item in forbidden_refs):
                raise BoundaryViolation(f"Forbidden environment capability {base}: {label}:{node.lineno}")
            if base and base.endswith(".__dict__"):
                key = _constant_string(node.slice, strings)
                if key is None or key in {"getenv", "getenvb", "environ", "environb", "__dict__"}:
                    raise BoundaryViolation(f"Reflective dictionary capability fails closed: {label}:{node.lineno}")


def _decode_css_escapes(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1):
            value = int(match.group(1), 16)
            return chr(value) if value and value <= 0x10FFFF else "\ufffd"
        return match.group(2) or ""

    return _CSS_ESCAPE.sub(replace, text)


def _decode_js_escapes(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        raw = match.group(1) or match.group(2) or match.group(3)
        return chr(int(raw, 16))

    return _JS_ESCAPE.sub(replace, text)


def _normalized_url(value: str) -> str:
    value = _decode_css_escapes(value)
    value = _decode_js_escapes(value)
    value = value.strip(_ASCII_EDGE).replace("\\", "/")
    value = "".join(character for character in value if ord(character) > 0x20 or character == " ")
    return value.lstrip()


def _remote_url(value: str) -> bool:
    normalized = _normalized_url(value).lower()
    # WHATWG special schemes treat backslashes as path separators and repair a
    # single slash after the scheme into an authority URL. Conservatively treat
    # every http(s):/ spelling as remote after slash normalization.
    return bool(re.match(r"^https?:/+", normalized)) or normalized.startswith("//")


def _js_compact(text: str) -> str:
    decoded = _decode_js_escapes(_decode_css_escapes(text)).lower().replace("\\", "/")
    # Joining quoted string fragments makes "fe" + "tch" and bracket forms
    # visible without claiming to be a general JavaScript interpreter.
    return re.sub(r"[\s'\"+`]", "", decoded)


def _verify_js(text: str, label: str) -> None:
    decoded = _decode_js_escapes(_decode_css_escapes(text))
    compact = _js_compact(decoded)
    if any(name in compact for name in _DANGEROUS_JS_NAMES):
        raise BoundaryViolation(f"Browser network API capability in {label}")
    # A computed property on a browser-global object cannot be proven offline
    # with a repository-local lexical verifier. Reject both direct and simply
    # aliased forms instead of guessing whether the runtime key is harmless.
    global_names = {"window", "globalthis", "self", "navigator"}
    global_names.update(
        match.group(1).lower()
        for match in re.finditer(
            r"(?i)\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:window|globalThis|self|navigator)\b",
            decoded,
        )
    )
    if any(re.search(rf"(?i)\b{re.escape(name)}\s*\[", decoded) for name in global_names):
        raise BoundaryViolation(f"Computed browser-global capability fails closed in {label}")
    if re.search(r"\bimport\s*\(", decoded, re.IGNORECASE):
        raise BoundaryViolation(f"Dynamic JavaScript import fails closed in {label}")
    if "http://" in compact or "https://" in compact or re.search(r"(^|[=(,:])//", compact):
        raise BoundaryViolation(f"Remote JavaScript URL in {label}")


class _MarkupVerifier(HTMLParser):
    ACTIVE: dict[str, frozenset[str]] = {
        "audio": frozenset({"src"}), "base": frozenset({"href"}),
        "button": frozenset({"formaction"}), "embed": frozenset({"src"}),
        "feimage": frozenset({"href", "xlink:href"}), "form": frozenset({"action"}),
        "iframe": frozenset({"src"}), "image": frozenset({"href", "xlink:href"}),
        "img": frozenset({"src", "srcset"}), "input": frozenset({"src", "formaction"}),
        "link": frozenset({"href"}), "object": frozenset({"data"}),
        "script": frozenset({"src", "href", "xlink:href"}), "source": frozenset({"src", "srcset"}),
        "animatemotion": frozenset({"href", "xlink:href"}),
        "mpath": frozenset({"href", "xlink:href"}),
        "track": frozenset({"src"}), "use": frozenset({"href", "xlink:href"}),
        "video": frozenset({"src", "poster"}),
    }

    def __init__(self, label: str) -> None:
        super().__init__(convert_charrefs=True)
        self.label = label
        self.script_parts: list[str] = []
        self.in_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        normalized = {name.lower(): value or "" for name, value in attrs}
        if tag == "script":
            self.in_script = True
        if tag == "meta" and normalized.get("http-equiv", "").lower() == "refresh":
            content = normalized.get("content", "")
            match = re.search(r"(?is)\burl\s*=\s*['\"]?\s*(.+)$", content)
            if match and _remote_url(match.group(1)):
                raise BoundaryViolation(f"Remote meta refresh in {self.label}")
        for name, value in normalized.items():
            if name == "style" and re.search(r"(?is)(?:url\s*\(|@import)", _decode_css_escapes(value)):
                if _remote_url(value[value.find("(") + 1:].strip(" )'\"")) or "//" in _normalized_url(value):
                    raise BoundaryViolation(f"Remote inline CSS in {self.label}")
            if name not in self.ACTIVE.get(tag, frozenset()):
                continue
            candidates = [part.strip().split()[0] for part in value.split(",") if part.strip()]
            if any(_remote_url(candidate) for candidate in candidates):
                raise BoundaryViolation(f"Remote active load {tag}.{name} in {self.label}")

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self.in_script = False

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.script_parts.append(data)


def verify_browser_source(text: str, label: str, suffix: str) -> None:
    decoded_css = _decode_css_escapes(text)
    for match in re.finditer(r"(?is)(?:url\s*\(\s*|@import\s+(?:url\s*\(\s*)?)([^);\n]+)", decoded_css):
        if _remote_url(match.group(1).strip(" ' \"")):
            raise BoundaryViolation(f"Remote CSS resource in {label}")
    if suffix in {".html", ".htm", ".svg"}:
        parser = _MarkupVerifier(label)
        try:
            parser.feed(text)
            parser.close()
        except BoundaryViolation:
            raise
        except Exception as error:
            raise BoundaryViolation(f"Markup cannot be safely parsed: {label}") from error
        if parser.script_parts:
            _verify_js("\n".join(parser.script_parts), label)
    if suffix in {".js", ".mjs"}:
        _verify_js(text, label)


def _workflow_paths(path: Path) -> list[str]:
    if path.is_symlink() or not path.is_file():
        raise BoundaryViolation("Creative workflow is absent or linked")
    try:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as error:
        raise BoundaryViolation("Creative workflow is not strict UTF-8") from error
    on_count = 0
    pull_count = 0
    paths_count = 0
    in_paths = False
    inside_on = False
    values: list[str] = []
    for raw in lines:
        content = raw.strip()
        if not content or content.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if content == "on:":
            if indent != 0:
                raise BoundaryViolation("Workflow on key must be top-level")
            on_count += 1
            inside_on = True
            continue
        if indent == 0:
            inside_on = False
            in_paths = False
        if content == "pull_request:":
            if not inside_on or indent != 2:
                raise BoundaryViolation("pull_request must be a direct child of top-level on")
            pull_count += 1
            in_paths = False
            continue
        if content == "paths:":
            if pull_count != 1 or indent != 4:
                raise BoundaryViolation("paths must be a direct child of pull_request")
            paths_count += 1
            in_paths = True
            continue
        if in_paths and indent == 6 and content.startswith("-"):
            values.append(content[1:].strip().strip("'\""))
        elif in_paths and indent <= 4:
            in_paths = False
    if on_count != 1 or pull_count != 1 or paths_count != 1:
        raise BoundaryViolation("Workflow needs exactly one top-level on.pull_request.paths chain")
    if not values or len(values) != len(set(values)):
        raise BoundaryViolation("pull_request.paths is missing, empty, or duplicated")
    return values


def verify_workflow(repo: Path, rules: Mapping[str, Any], floor: Mapping[str, set[str]]) -> None:
    actual = set(_workflow_paths(repo / WORKFLOW_PATH))
    configured = set(rules["required_pull_request_paths"])
    if actual != configured:
        raise BoundaryViolation(f"Workflow/config trigger drift: actual={sorted(actual)} configured={sorted(configured)}")
    if not floor["triggers"].issubset(actual):
        raise BoundaryViolation("Workflow and config jointly shrink the canonical trigger floor")
    root_patterns = {f"{root.rstrip('/')}/**" for root in rules["scan_roots"]}
    if not root_patterns.issubset(actual):
        raise BoundaryViolation("Each candidate scan root needs an exact recursive trigger")


def verify_repository(repo: Path, *, policy_floor_ref: str) -> dict[str, Any]:
    repo = repo.resolve()
    rules = _load_rules(repo / CONFIG_PATH)
    floor, floor_sha256 = _load_floor(repo, policy_floor_ref)
    _require_floor(rules, floor)
    verify_workflow(repo, rules, floor)
    suffixes = set(rules["scanned_suffixes"])
    files: list[dict[str, str]] = []
    for root_name in rules["scan_roots"]:
        for path in _walk_no_indirection(repo / root_name):
            suffix = path.suffix.lower()
            if suffix not in suffixes:
                continue
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="strict")
            except (OSError, UnicodeDecodeError) as error:
                raise BoundaryViolation(f"Scanned source is unreadable or non-UTF8: {path}") from error
            relative = path.relative_to(repo).as_posix()
            if suffix == ".py":
                verify_python_source(text, relative, rules)
            else:
                verify_browser_source(text, relative, suffix)
            files.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
    if not files:
        raise BoundaryViolation("No source files were selected")
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "policy_floor_ref": policy_floor_ref,
        "policy_floor_sha256": floor_sha256,
        "scan_roots": list(rules["scan_roots"]),
        "file_count": len(files),
        "files": sorted(files, key=lambda item: item["path"]),
    }


def _head(repo: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise BoundaryViolation("Cannot resolve exact repository HEAD") from error


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--policy-floor-ref", required=True)
    parser.add_argument("--expected-head")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt = verify_repository(args.repo, policy_floor_ref=args.policy_floor_ref)
        head = _head(args.repo)
        if args.expected_head and head != args.expected_head:
            raise BoundaryViolation(f"Exact-head mismatch: expected={args.expected_head} actual={head}")
        receipt["exact_head"] = head
        rendered = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(rendered, encoding="utf-8")
        sys.stdout.write(rendered)
        return 0
    except Exception as error:
        sys.stderr.write(json.dumps({"schema": RECEIPT_SCHEMA, "status": "FAIL", "error": str(error)}, ensure_ascii=False) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
