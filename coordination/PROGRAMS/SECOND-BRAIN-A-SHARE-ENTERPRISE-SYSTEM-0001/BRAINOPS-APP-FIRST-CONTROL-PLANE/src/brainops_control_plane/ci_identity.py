"""Exact Git head assertion used by the E38 pull-request workflow."""

from __future__ import annotations

import subprocess
import sys

from .models import ValidationError, require_sha1


def assert_exact_head(expected_head: str, observed_head: str) -> str:
    require_sha1(expected_head, "expected PR head")
    require_sha1(observed_head, "checked out head")
    if observed_head != expected_head:
        raise ValidationError("ci_checkout_sha_differs_from_expected_pr_head")
    return observed_head


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise ValidationError("ci expected exactly one PR head SHA")
    observed = subprocess.check_output(("git", "rev-parse", "HEAD"), text=True).strip()
    verified = assert_exact_head(args[0], observed)
    print(f"verified_head={verified}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
