"""Fail closed unless six canonical artifacts are byte-identical."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--expected-count", type=int, default=6)
    args = parser.parse_args()
    if len(args.artifacts) != args.expected_count:
        raise SystemExit("canonical artifact count is not exact")
    payloads = [path.read_bytes() for path in args.artifacts]
    if any(payload != payloads[0] for payload in payloads[1:]):
        raise SystemExit("canonical artifacts are not byte-identical")
    print(sha256(payloads[0]).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
