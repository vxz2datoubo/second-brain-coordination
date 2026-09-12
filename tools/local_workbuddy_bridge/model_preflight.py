"""Model availability/identity preflight abstraction.

Rules (TASK-BRIEF.yaml):
  - "required model mismatch/unavailability fails closed"
  - "Commands and model identifiers may come only from validated structured
     authority/dispatch fields, never arbitrary GitHub free text."
  - COMPUTE-LANE-AUTHORIZATION: no silent tier upgrade.
"""
from __future__ import annotations

import re

from .contracts import ModelPreflightResult

# Model identifiers must be simple, structured tokens. Free text is rejected.
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-/:]{1,80}$")

# The set the bridge can currently resolve locally. Anything else fails closed.
# NOTE: this is a resolution *catalogue*, not an authority. The authority for
# which model may run is COMPUTE-LANE-AUTHORIZATION + the canonical dispatch.
_LOCALLY_RESOLVABLE = (
    "deepseek-v4-pro",
    "deepseek-v4.1-flash",
    "deepseek-v4-flash",
    "glm-5",
    "kimi-k2",
)

# A model identifier that demands a higher compute tier must never be silently
# granted. Escalation is an Owner decision, not a bridge decision.
_TIER_UPGRADE_MARKERS = ("gpt-6", "frontier", "gpt-5", "o3", "o4")


def preflight_model(
    declared_model: str | None,
    *,
    required_model: str | None = None,
) -> ModelPreflightResult:
    """Verify the model can be resolved. Never upgrades a tier silently."""
    model = (declared_model or "").strip()
    if not model:
        return ModelPreflightResult(
            ok=False, model="", reason="no model declared on the canonical task"
        )
    if not _MODEL_ID_RE.match(model):
        return ModelPreflightResult(
            ok=False, model=model,
            reason="model identifier is not a structured token (free text rejected)",
        )
    lowered = model.lower()
    if any(marker in lowered for marker in _TIER_UPGRADE_MARKERS):
        return ModelPreflightResult(
            ok=False, model=model,
            reason="model requires a higher compute tier; silent upgrade is forbidden "
                   "(OWNER decision required)",
        )
    if required_model and model != required_model:
        return ModelPreflightResult(
            ok=False, model=model,
            reason=f"declared model does not match required model {required_model}",
        )
    if model not in _LOCALLY_RESOLVABLE:
        return ModelPreflightResult(
            ok=False, model=model,
            reason="required model is unavailable or resolves ambiguously",
        )
    return ModelPreflightResult(
        ok=True, model=model,
        reason="model resolved unambiguously", resolved_from="LOCAL_CATALOGUE",
    )
