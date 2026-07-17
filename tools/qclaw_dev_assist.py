"""Development helper for routing heavy text-analysis tasks to QClaw.

Usage:
    python F:/ai/tools/qclaw_dev_assist.py "task prompt"
    python F:/ai/tools/qclaw_dev_assist.py "task prompt" output-name.md
"""

from __future__ import annotations

import sys

from core.qclaw import QClawBridge


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python F:/ai/tools/qclaw_dev_assist.py \"task prompt\" [save_as.md]")
        return 1

    prompt = sys.argv[1].strip()
    save_as = sys.argv[2].strip() if len(sys.argv) >= 3 and sys.argv[2].strip() else None
    bridge = QClawBridge()
    content, saved_path = bridge.ask(prompt, save_as=save_as)

    print(content)
    if saved_path:
        print(f"\n[SAVED] {saved_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
