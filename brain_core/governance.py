"""Governance, approval and research-mode safety gates."""

from __future__ import annotations

from typing import Any

from .contracts import RiskApproval


HIGH_RISK_ACTIONS = {"live_trade", "place_order", "delete_legacy_data", "external_write"}


class GovernancePolicy:
    version = "v0.1"

    def __init__(self, research_mode: bool = True, live_trading_enabled: bool = False):
        self.research_mode = research_mode
        self.live_trading_enabled = live_trading_enabled

    def assess_action(self, action_type: str, context: dict[str, Any] | None = None) -> RiskApproval:
        context = context or {}
        risk_level = "low"
        requires = False
        reason = "low-risk local research action"
        if action_type in HIGH_RISK_ACTIONS:
            risk_level = "high"
            requires = True
            reason = f"{action_type} is a high-risk action"
        if action_type in {"trade", "buy", "sell"}:
            risk_level = "medium"
            reason = "trading output is research-only in v0.1"
            if not self.research_mode or self.live_trading_enabled:
                risk_level = "high"
                requires = True
                reason = "live trading must remain disabled unless manually approved"
        return RiskApproval(
            action_type=action_type,
            risk_level=risk_level,
            requires_approval=requires,
            approved=False,
            reason=reason,
            policy_version=self.version,
            metadata={
                "research_mode": self.research_mode,
                "live_trading_enabled": self.live_trading_enabled,
                "context": context,
            },
        )

    def trading_gate(self, context: dict[str, Any]) -> dict[str, Any]:
        approval = self.assess_action("trade", context)
        warnings: list[str] = []
        action = "wait"
        confidence = float(context.get("confidence", 0.5))
        cost_pct = float(context.get("cost_pct", context.get("transaction_cost_pct", 0.0015)))
        expected_edge_pct = float(context.get("expected_edge_pct", 0.0))
        max_loss_pct = float(context.get("max_loss_pct", 0.02))
        position_pct = float(context.get("position_pct", 0.05))
        if cost_pct <= 0:
            warnings.append("missing_or_zero_transaction_cost")
        if position_pct > 0.1:
            warnings.append("position_exceeds_v0_1_research_limit")
        if max_loss_pct > 0.03:
            warnings.append("max_loss_exceeds_default_guardrail")
        net_edge = expected_edge_pct - cost_pct
        if warnings:
            action = "no_trade"
        elif confidence >= 0.65 and net_edge > 0:
            action = "trade"
        elif confidence >= 0.45:
            action = "wait"
        else:
            action = "no_trade"
        return {
            "action": action,
            "research_mode": True,
            "live_trading_enabled": False,
            "approval": approval,
            "warnings": warnings,
            "net_edge_pct": round(net_edge, 6),
        }
