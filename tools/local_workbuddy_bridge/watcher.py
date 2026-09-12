"""LocalWorkBuddyBridge — the composition layer (Phase 2B shadow mode).

This class is the single entry point for the RDC launch path. It performs:

    read authority snapshot
      -> compose AuthorityView (from EXISTING governance layers)
      -> plan_launch()  (fail-closed)
      -> record durable idempotency receipt
      -> hand the plan to a ProcessAdapter (FakeProcessAdapter in 2B)
      -> build a redacted ReturnPackage

It NEVER reimplements the trust gate, the active-task registry, or the host
broker. It reads them. If any of them is unavailable or disagrees, the bridge
fails closed with OUTCOME_UNKNOWN-equivalent refusal — it does not guess.

Hard boundary kept here: `LocalWorkBuddyBridge.launch()` asserts the adapter is
not a real one unless an explicit, independently-granted activation flag is
present. That flag does not exist yet by design.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .contracts import (
    BridgeBoundaryError,
    BridgeDecision,
    LaunchPlan,
    ProcessAdapter,
    ReturnPackage,
)
from .fake_process_adapter import FakeProcessAdapter
from .launch_plan import AuthorityView, plan_launch
from .receipt_store import LaunchReceiptStore
from .return_package import build_return_package

# Bridge-wide activation switch. It is intentionally hard-coded False and there
# is no supported way to set it True from a test, a CI run, or GitHub text.
# Flipping it is an Owner action performed ONLY after independent review +
# canonicalization of this bridge (R184 boundary).
_ACTIVATION_GRANTED = False


@dataclass
class BridgeResult:
    plan: LaunchPlan
    adapter_note: dict
    receipt_id: str | None


class LocalWorkBuddyBridge:
    """Shadow-mode bridge. Dry-run by default. Real launch is impossible."""

    def __init__(
        self,
        *,
        receipt_root: str | Path,
        adapter: ProcessAdapter | None = None,
        project_id: str = "",
    ) -> None:
        self.project_id = project_id
        self.receipts = LaunchReceiptStore(receipt_root)
        self.adapter: ProcessAdapter = adapter or FakeProcessAdapter()

    # -- composition ----------------------------------------------------
    @staticmethod
    def _as_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def compose_view(
        self,
        authority_inputs: Mapping[str, object],
        *,
        trusted_main_sha: str | None = None,
    ) -> AuthorityView:
        """Assemble an AuthorityView from read-only governance outputs.

        `authority_inputs` is the union of the registry / trust-gate / broker
        outputs. Unknown keys are IGNORED (never inherited into the plan).
        """
        src = dict(authority_inputs)

        task_id = str(src.get("task_id", "") or "")
        route_epoch_raw = src.get("route_epoch")
        try:
            route_epoch = int(route_epoch_raw) if route_epoch_raw is not None else None
        except (TypeError, ValueError):
            route_epoch = None

        canonical_main = str(src.get("canonical_main_sha", "") or "")
        # A trusted main sha observed locally (from git) is authoritative for
        # staleness. If absent we fall back to the dispatched expectation only
        # when the caller supplied it; otherwise we cannot judge, and the
        # registered/authority gates still protect us.
        expected_main = str(
            src.get("expected_main_sha", trusted_main_sha or canonical_main) or ""
        )

        return AuthorityView(
            task_id=task_id,
            route_epoch=route_epoch,
            is_registered=self._as_bool(src.get("is_registered", False)),
            is_canonical=self._as_bool(src.get("is_canonical", True)),
            canonical_authority_valid=self._as_bool(
                src.get("canonical_authority_valid", False)
            ),
            authority_state=str(src.get("authority_state", "") or ""),
            lease_id=str(src.get("lease_id", "") or ""),
            fencing_token=str(src.get("fencing_token", "") or ""),
            reservation_id=str(src.get("reservation_id", "") or ""),
            lease_valid=self._as_bool(src.get("lease_valid", False)),
            broker_admission=str(src.get("broker_admission", "") or ""),
            active_writer_present=self._as_bool(src.get("active_writer_present", False)),
            canonical_main_sha=canonical_main,
            expected_main_sha=expected_main,
            branch=str(src.get("branch", "") or ""),
            expected_branch=str(src.get("expected_branch", "") or ""),
            route_epoch_valid=self._as_bool(src.get("route_epoch_valid", True)),
            isolation_required=self._as_bool(src.get("isolation_required", True)),
            isolated_worktree=str(
                src.get("isolated_worktree", src.get("worktree", "")) or ""
            ),
            active_worktree_holders=src.get("active_worktree_holders") or None,
            carrier=str(src.get("carrier", "") or ""),
            execution_identity=str(src.get("execution_identity", "") or ""),
            model=str(src.get("model", "") or ""),
            required_model=str(src.get("required_model", "") or ""),
            collision_domain=str(src.get("collision_domain", "") or ""),
            declared_collision_domain=str(
                src.get("declared_collision_domain", "") or ""
            ),
            cli_path=str(src.get("cli_path", "") or ""),
            adapter=str(src.get("adapter", "FAKE_PROCESS_ADAPTER") or ""),
            duplicate_receipt_present=self._as_bool(
                src.get("duplicate_receipt_present", False)
            ),
        )

    # -- idempotency ----------------------------------------------------
    def _idempotency_key(self, view: AuthorityView) -> str:
        return LaunchReceiptStore.idempotency_key(
            view.task_id,
            int(view.route_epoch or 0),
            view.execution_identity,
        )

    def _mark_duplicate(self, view: AuthorityView) -> AuthorityView:
        key = self._idempotency_key(view)
        if self.receipts.find(key) is not None:
            return view.with_duplicate_receipt()
        return view

    # -- main entry -----------------------------------------------------
    def evaluate(
        self,
        authority_inputs: Mapping[str, object],
        *,
        trusted_main_sha: str | None = None,
        allowed_collision_domains: Sequence[str] | None = None,
        active_collision_domains: Mapping[str, str] | None = None,
    ) -> BridgeResult:
        """Compose -> plan -> record receipt -> adapter. Never launches for real."""
        view = self.compose_view(authority_inputs, trusted_main_sha=trusted_main_sha)

        # Idempotency check happens against the DURABLE store, keyed to the
        # immutable (task, route_epoch, execution_identity) triple.
        view = self._mark_duplicate(view)

        plan = plan_launch(
            view,
            allowed_collision_domains=allowed_collision_domains,
            active_collision_domains=active_collision_domains,
        )

        receipt_id: str | None = None
        # Only PLANNED plans mint a receipt; refusals are not reservations.
        if plan.decision is BridgeDecision.PLANNED:
            receipt = self.receipts.record(
                task_id=view.task_id,
                route_epoch=int(view.route_epoch or 0),
                execution_identity=view.execution_identity,
                decision=plan.decision,
            )
            receipt_id = receipt.receipt_id

        adapter_note = self._hand_off(plan)
        return BridgeResult(plan=plan, adapter_note=adapter_note, receipt_id=receipt_id)

    def _hand_off(self, plan: LaunchPlan) -> dict:
        """Give the plan to the adapter, enforcing the activation boundary."""
        if plan.decision is not BridgeDecision.PLANNED:
            return {"adapter": self.adapter.identity(), "handoff": False,
                    "reason": "plan was refused; nothing to hand off"}

        is_fake = isinstance(self.adapter, FakeProcessAdapter) or (
            self.adapter.identity() == "FAKE_PROCESS_ADAPTER"
        )
        if not is_fake and not _ACTIVATION_GRANTED:
            raise BridgeBoundaryError(
                "real process adapter handoff requires activation grant "
                "(independent review + canonicalization); refusing to launch"
            )
        return self.adapter.launch(plan)

    # -- return package -------------------------------------------------
    def report(
        self,
        plan: LaunchPlan,
        *,
        head_sha: str | None,
        tests: Sequence[str] = (),
        findings: Sequence[str] = (),
        unknowns: Sequence[str] = (),
        changed_files: Sequence[str] = (),
        telemetry: Mapping[str, object] | None = None,
    ) -> ReturnPackage:
        return build_return_package(
            task_id=plan.task_id,
            route_epoch=plan.route_epoch,
            branch=plan.branch,
            head_sha=head_sha or (plan.canonical_main_sha or None),
            tests=tests,
            findings=findings,
            unknowns=unknowns,
            changed_files=changed_files,
            telemetry=telemetry,
        )
