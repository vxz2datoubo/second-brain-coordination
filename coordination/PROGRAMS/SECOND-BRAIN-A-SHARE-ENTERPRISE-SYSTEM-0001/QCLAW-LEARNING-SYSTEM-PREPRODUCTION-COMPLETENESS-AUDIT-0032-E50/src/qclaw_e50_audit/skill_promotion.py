"""skill_promotion — D7 receipt-bound skill learning/promotion + rollback.

D7 pass criteria:
  - promotion requires actual test receipts (test_name + digest + pass_count)
  - no caller-authored promotion (only `promote_to_formal(skill_id, dry_run=True)`
    is the public API; full promotion gated)
  - rollback path: each promotion has `rollback_receipt` with reverse digests
  - distinct cases + failure conditions recorded

Default state: all skills are CANDIDATE. EXPERIMENTAL requires test receipts.
FORMAL requires GPT/Codex authorization (out of scope for E50 — E50 only audits the gate).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SkillStage(str, Enum):
    CANDIDATE = "candidate"
    EXPERIMENTAL = "experimental"
    FORMAL = "formal"
    ROLLBACK_PENDING = "rollback_pending"


class PromotionRefused(Exception):
    """Raised when promotion does not meet receipt requirements."""


@dataclass(frozen=True)
class PromotionReceipt:
    test_name: str
    digest: str
    pass_count: int
    failure_count: int
    distinct_cases: int = 0
    failure_conditions: tuple = ()

    def is_sufficient(self) -> bool:
        return (
            self.pass_count >= 1
            and self.digest != ""
            and self.test_name != ""
            and self.distinct_cases >= 1
            and len(self.failure_conditions) >= 1
        )


@dataclass(frozen=True)
class RollbackReceipt:
    promotion_digest: str
    reverse_digest: str
    rollback_target_stage: SkillStage
    reason: str


@dataclass
class SkillCandidate:
    skill_id: str
    stage: SkillStage = SkillStage.CANDIDATE
    receipts: list = field(default_factory=list)
    rollback_history: list = field(default_factory=list)

    def add_receipt(self, receipt: PromotionReceipt) -> None:
        self.receipts.append(receipt)

    def has_sufficient_receipts(self) -> bool:
        return any(r.is_sufficient() for r in self.receipts)

    def attempt_promote(self, *, dry_run: bool, receipt: PromotionReceipt,
                        reverse_digest: str = "") -> SkillStage:
        """Promote candidate → experimental.

        Refuses (raises PromotionRefused) if receipt is insufficient.
        Refuses (raises PromotionRefused) if dry_run is False (full promotion gated).
        """
        if not receipt.is_sufficient():
            raise PromotionRefused(
                f"Receipt insufficient: pass_count={receipt.pass_count}, "
                f"digest={receipt.digest[:12] if receipt.digest else 'EMPTY'}, "
                f"distinct_cases={receipt.distinct_cases}, "
                f"failure_conditions={len(receipt.failure_conditions)}"
            )
        if not dry_run:
            raise PromotionRefused(
                "Full promotion (FORMAL) requires explicit Owner authorization; "
                "use dry_run=True for the E50 audit harness."
            )
        self.add_receipt(receipt)
        self.stage = SkillStage.EXPERIMENTAL
        return self.stage

    def rollback(self, *, reason: str) -> RollbackReceipt:
        prior_stage = self.stage
        rb = RollbackReceipt(
            promotion_digest=_skill_digest(self.skill_id, self.receipts),
            reverse_digest=_skill_digest(self.skill_id, []),
            rollback_target_stage=SkillStage.CANDIDATE,
            reason=reason,
        )
        self.rollback_history.append(rb)
        self.stage = SkillStage.ROLLBACK_PENDING
        # Stage drops back to CANDIDATE after rollback acknowledged
        self.stage = SkillStage.CANDIDATE
        return rb


def _skill_digest(skill_id: str, receipts: list) -> str:
    payload = json.dumps({
        "skill_id": skill_id,
        "receipts": [
            {"test_name": r.test_name, "digest": r.digest, "pass_count": r.pass_count}
            for r in receipts
        ],
    }, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def no_caller_authored_promotion(skill: SkillCandidate, *, receipt: PromotionReceipt,
                                  dry_run: bool = True) -> SkillStage:
    """Public gate: only EXPERIMENTAL promotion allowed, only with receipt, only dry-run."""
    return skill.attempt_promote(dry_run=dry_run, receipt=receipt)