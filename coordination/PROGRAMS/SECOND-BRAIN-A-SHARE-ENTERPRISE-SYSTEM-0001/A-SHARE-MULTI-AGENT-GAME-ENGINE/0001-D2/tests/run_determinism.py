"""Print a stable synthetic ledger hash for two clean-directory determinism checks."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d2_game_core import ActionLabel, AgentInformationSet, AgentState, CandidateAction, HiddenTypePosterior, ParticipantArchetypeHypothesis, ParticipantSubtype, arbitrate
from synthetic_engine.fixtures import INVENTORY, market, order

posterior = HiddenTypePosterior((ParticipantArchetypeHypothesis(ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, 1.0, ("synthetic:e",), ("synthetic:c",), "synthetic alternative"),))
agent = AgentState("agent-a", posterior, AgentInformationSet(100, ("synthetic:o",), ()), INVENTORY)
action = CandidateAction("action-a", "agent-a", ActionLabel.FEASIBLE, order("action-a"), ("assumption:one",), ("synthetic:e",))
result = arbitrate("d2-determinism", market(), (agent,), (action,))
print("D2_LEDGER_SHA256=" + result.ledger_hash)
