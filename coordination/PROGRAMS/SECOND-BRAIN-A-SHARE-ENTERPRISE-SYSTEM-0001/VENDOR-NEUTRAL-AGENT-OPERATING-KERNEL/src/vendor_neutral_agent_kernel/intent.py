"""Structured intent compilation for the reference kernel."""

from __future__ import annotations

from .canonical import seal_contract
from .contracts import ContractMeta, SideEffectClass, TaskIntent


def compile_intent(
    meta: ContractMeta,
    *,
    objective: str,
    explicit_requirements: tuple[str, ...],
    success_criteria: tuple[str, ...],
    non_goals: tuple[str, ...] = (),
    unknowns: tuple[str, ...] = (),
    reversibility: str = "REVERSIBLE",
    side_effect_class: SideEffectClass = SideEffectClass.READ_ONLY,
    evidence_budget: int = 1,
    time_budget_seconds: int | None = None,
    autonomy_boundary: tuple[str, ...] = (),
) -> TaskIntent:
    intent = TaskIntent(
        meta=meta,
        objective=objective,
        explicit_requirements=explicit_requirements,
        success_criteria=success_criteria,
        non_goals=non_goals,
        unknowns=unknowns,
        reversibility=reversibility,
        side_effect_class=side_effect_class,
        evidence_budget=evidence_budget,
        time_budget_seconds=time_budget_seconds,
        autonomy_boundary=autonomy_boundary,
    )
    return seal_contract(intent)
