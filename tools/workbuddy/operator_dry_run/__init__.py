"""WorkBuddy-owned offline operator dry run (WB-S3).

Simulates a fully offline operator working the interactive-film session lifecycle
-- intake, duplicate input, resume, replay, failure recovery and handoff
receipts -- against the checkpoint's runtime contracts (ledger, knowledge,
generation, governance, provenance) without adding platform access, private
media, credentials or provider calls. Everything is synthetic and deterministic.
"""

from __future__ import annotations

SCHEMA = "WorkBuddyOperatorDryRun/v1"

__all__ = ["SCHEMA"]
