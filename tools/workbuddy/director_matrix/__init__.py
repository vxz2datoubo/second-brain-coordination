"""WorkBuddy-owned director coverage matrix probe (WB-S2).

Implements the discovery plan for ``M-REACHABLE-STATE-DIRECTOR-COMPILABILITY-v1``
without touching the director contract, its quality oracle, or any Codex-retained
surface. Everything is synthetic and offline: no credentials, no network, no real
player data, no generated media.

The metric this probe measures is a FIXED_CONTRACT with a hard gate:

    ratio = states_with_legal_brief_or_declared_missing_asset / reachable_states
    target = 1.0
    failure = ratio < 1.0
"""

from __future__ import annotations

SCHEMA = "WorkBuddyDirectorMatrixProbe/v1"
METRIC_ID = "M-REACHABLE-STATE-DIRECTOR-COMPILABILITY-v1"
FORMULA_REVISION = "states_with_legal_brief_or_declared_missing_asset/reachable_states/v1"

__all__ = ["SCHEMA", "METRIC_ID", "FORMULA_REVISION"]
