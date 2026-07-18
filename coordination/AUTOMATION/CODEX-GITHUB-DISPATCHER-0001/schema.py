"""
CODEX-GITHUB-DISPATCHER-0001 — Schema Validator
Phase 1: Strict YAML dispatch protocol parser.
Zero external dependencies — uses regex for the flat key:value subset we accept.
"""
import re

ALLOWED_ACTIONS = {"START"}
UNSUPPORTED_ACTIONS = {"REVIEW", "CONTINUE", "CANCEL"}

# Patterns that indicate automated dispatcher receipts — skip these
AUTO_RECEIPT_PREFIXES = (
    "CodexDispatchReceipt:",
    "CODEX_TASK_STARTED",
    "CODEX_TASK_PROGRESS",
    "CODEX_TASK_BLOCKED",
    "CODEX_TASK_COMPLETED",
    "WBDispatcherHeartbeat:",
)
ALLOWED_MODES = {"goal", "direct"}
ALLOWED_RISK_CLASSES = {"low"}
ALLOWED_APPROVAL_POLICIES = {"automatic"}
ALLOWED_WORKSPACES = {"AIDANAO_ROOT"}

REQUIRED_KEYS = {
    "schema_version",
    "issuer_agent",
    "target_agent",
    "task_id",
    "action",
    "mode",
    "repository",
    "source_issue_or_pr",
    "workspace_alias",
    "risk_class",
    "approval_policy",
    "idempotency_key",
}

OPTIONAL_KEYS = {
    "expected_base_head",
    "instruction_location",
}

# All known keys — reject anything else
ALL_KNOWN_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS

TARGET_REPO = "vxz2datoubo/second-brain-coordination"


class SchemaError(Exception):
    pass


class DispatchBlock:
    def __init__(self, raw: str, comment_id: int, comment_url: str):
        self.raw = raw
        self.comment_id = comment_id
        self.comment_url = comment_url
        self.parsed = None
        self.errors = []
        self.is_unsupported_action = False

    def parse(self) -> bool:
        block = _extract_fenced_yaml(self.raw)
        if block is None:
            self.errors.append("No fenced YAML code block found")
            return False
        data = _parse_flat_yaml(block)
        if data is None:
            self.errors.append("YAML parse error: invalid format")
            return False
        if not isinstance(data, dict):
            self.errors.append("YAML root is not a dictionary")
            return False
        if "CodexDispatch" not in data:
            self.errors.append("Missing top-level key: CodexDispatch")
            return False
        inner = data["CodexDispatch"]
        if not isinstance(inner, dict):
            self.errors.append("CodexDispatch value is not a dictionary")
            return False
        for key in inner:
            if key not in ALL_KNOWN_KEYS:
                self.errors.append(f"Unknown key: {key}")
        for key in REQUIRED_KEYS:
            if key not in inner:
                self.errors.append(f"Missing required key: {key}")
        if self.errors:
            return False
        self.parsed = inner
        return True

    def validate(self) -> bool:
        if self.parsed is None:
            return False
        p = self.parsed

        # Check for unsupported action FIRST — flag it clearly
        action = p.get("action", "")
        if action in UNSUPPORTED_ACTIONS:
            self.is_unsupported_action = True
            self.errors.append(f"action '{action}' is not supported in Phase 1 (only START)")
            return False

        checks = [
            (p.get("schema_version") == "1.0", "schema_version must be 1.0"),
            (p.get("issuer_agent") == "GPT", "issuer_agent must be GPT"),
            (p.get("target_agent") == "CODEX", "target_agent must be CODEX"),
            (action in ALLOWED_ACTIONS, f"action must be one of {ALLOWED_ACTIONS}"),
            (p.get("mode") in ALLOWED_MODES, f"mode must be one of {ALLOWED_MODES}"),
            (p.get("repository") == TARGET_REPO, f"repository must be {TARGET_REPO}"),
            (p.get("workspace_alias") in ALLOWED_WORKSPACES, f"workspace_alias must be one of {ALLOWED_WORKSPACES}"),
            (p.get("risk_class") in ALLOWED_RISK_CLASSES, f"risk_class must be {ALLOWED_RISK_CLASSES}"),
            (p.get("approval_policy") in ALLOWED_APPROVAL_POLICIES, f"approval_policy must be one of {ALLOWED_APPROVAL_POLICIES}"),
            (_valid_id(p.get("task_id", "")), "task_id invalid format"),
            (_valid_id(p.get("idempotency_key", "")), "idempotency_key invalid format"),
            (isinstance(p.get("source_issue_or_pr"), int) or str(p.get("source_issue_or_pr", "")).isdigit(),
             "source_issue_or_pr must be a number"),
        ]
        for ok, msg in checks:
            if not ok:
                self.errors.append(msg)
        if self.errors:
            return False
        if p.get("instruction_location"):
            loc = p["instruction_location"]
            if not str(loc).startswith("https://github.com/" + TARGET_REPO):
                self.errors.append("instruction_location must point to this repository")
                return False
        return True


def _valid_id(s: str) -> bool:
    return bool(re.match(r'^[A-Za-z0-9_\-\.]+$', s))


def _parse_flat_yaml(text: str) -> dict | None:
    """
    Parse a strict subset of YAML: only flat key: value lines with 2-space indent.
    Supports nested dicts with 2 spaces per level.
    Rejects: tags, anchors, complex types, lists, multiline strings.
    """
    lines = text.split("\n")
    result = {}
    stack = [(0, result)]  # (indent, dict)

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Reject YAML features we don't need
        if "!!" in line or "&" in line or "\\*" in stripped:
            return None
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            return None  # Must be 2-space increments

        # Parse key: value
        kv_match = re.match(r'^([\w_]+):\s*(.*)', stripped)
        if not kv_match:
            return None
        key = kv_match.group(1)
        value = kv_match.group(2).strip()

        # Pop stack to current indent level
        while stack and stack[-1][0] > indent:
            stack.pop()

        if not stack:
            return None

        current = stack[-1][1]

        # Check if value starts a nested block (empty value = next lines at higher indent)
        if value == "":
            nested = {}
            current[key] = nested
            stack.append((indent, nested))
        else:
            # Unquote if needed
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            # Convert integer
            if value.isdigit():
                current[key] = int(value)
            else:
                current[key] = value

    return result


def _extract_fenced_yaml(text: str) -> str | None:
    """Extract the first fenced ```yaml ... ``` block."""
    pattern = r'```yaml[ \t]*\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        block = match.group(1).strip()
        # Reject YAML tags, anchors, aliases
        if re.search(r'!!|&\w+|\\*\\w+', block):
            return None
        if len(block) > 4096:
            return None  # reject oversized
        return block
    return None


def should_skip_comment(body: str) -> tuple[bool, str]:
    """
    Pre-filter: return (True, reason) if this comment should be skipped silently.
    Returns (False, "") if it might contain a dispatch block and should be parsed.
    """
    if not body or not body.strip():
        return (True, "empty")

    first_line = body.strip().split("\n")[0].strip() if body.strip() else ""

    # Skip automated receipt comments from dispatcher itself
    for prefix in AUTO_RECEIPT_PREFIXES:
        if first_line.startswith(prefix):
            return (True, f"auto_receipt:{prefix}")

    # Skip if no CodexDispatch keyword AND no fenced YAML
    if "CodexDispatch" not in body:
        return (True, "no_dispatch_keyword")
    if "```yaml" not in body:
        return (True, "no_fenced_yaml")

    return (False, "")


def find_dispatch_blocks(body: str, comment_id: int, comment_url: str) -> list[DispatchBlock]:
    """Find all potential dispatch blocks in a comment body. Use should_skip_comment first."""
    skip, reason = should_skip_comment(body)
    if skip:
        return []  # Silent skip — caller should NOT log this as WARNING

    pattern = r'```yaml[ \t]*\n.*?CodexDispatch.*?```'
    matches = re.finditer(pattern, body, re.DOTALL)
    blocks = []
    for m in matches:
        blocks.append(DispatchBlock(m.group(0), comment_id, comment_url))
    return blocks
