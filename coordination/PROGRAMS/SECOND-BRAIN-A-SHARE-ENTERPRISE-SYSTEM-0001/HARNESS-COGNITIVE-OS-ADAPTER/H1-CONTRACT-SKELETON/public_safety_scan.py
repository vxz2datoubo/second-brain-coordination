"""Static H1 scope/resource audit; deliberately creates no child process."""
"""Static, public-safe H1 audit; this program never creates a child process."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
IMPORT_OR_PROCESS = re.compile(r"^\s*(?:from\s+deepseek\b|import\s+deepseek\b|import\s+subprocess\b|from\s+subprocess\b|import\s+multiprocessing\b|from\s+multiprocessing\b|.*taskkill\b)", re.IGNORECASE | re.MULTILINE)
SECRET_LITERAL = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{20,})")
issues = []
for path in ROOT.rglob("*"):
    if path == Path(__file__).resolve():
        continue  # The static checker contains its own detector expressions.
    if path.is_file() and path.suffix in {".py", ".json", ".yaml", ".md"}:
        content = path.read_text(encoding="utf-8")
        if IMPORT_OR_PROCESS.search(content) or SECRET_LITERAL.search(content):
            issues.append(path.relative_to(ROOT).as_posix())
assert not issues, "PUBLIC_SAFETY_ISSUES:" + ",".join(issues)
print("PUBLIC_SAFE_PASS files_scanned=" + str(sum(1 for item in ROOT.rglob("*") if item.is_file())) + " NO_CHILD_PROCESS_CREATED")
