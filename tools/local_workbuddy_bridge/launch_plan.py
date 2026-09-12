"""Launch planning — the fail-closed decision core of the local bridge.

This module TURNS an authority view into a PLAN. It launches nothing.

Design rule (NO_SECOND_CONTROL_TOWER_OR_SECOND_TRUST_GATE): this module does
not decide whether authority exists. It CONSUMES a decision produced by the
existing governance layers:
  - unified_active_task_registry  -> which tasks are registered
  - unified_execution_trust_gate  -> whether canonical authority is valid
  - HostExecutionBroker           -> which lease/reservation is held

Every check below is a *composition* of those verdicts. The bridge never
re-derives authority from strings, numbers or GitHub free text.

Fail-closed matrix (TASK-BRIEF.yaml adversarial tests):
  1.  stale canonical main                       -> REFUSED_STALE_MAIN
  2.  task not in registered index               -> REFUSED_UNREGISTERED_TASK
  3.  wrong/expired lease or reservation         -> REFUSED_AUTHORITY_MISMATCH
  4.  duplicate launch, same immutable identity  -> REFUSED_DUPLICATE
  5.  branch does not match canonical branch     -> REFUSED_BASE_MISMATCH
  6.  collision domain overlap with a live writer-> REFUSED_COLLISION_CONFLICT
  7.  candidate-only task (not canonical)        -> REFUSED_CANDIDATE_ONLY
  8.  required model mismatch/unavailable        -> REFUSED_MODEL_UNAVAILABLE
  9.  unknown/undeclared process adapter         -> REFUSED_UNKNOWN_ADAPTER
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping, Sequence

from .contracts import BridgeDecision, LaunchPlan, ModelPreflightResult
from .model_preflight import preflight_model

# The only adapters that may ever be named. The real adapter is present but
# disabled until independent review + canonicalization.
_ALLOWED_ADAPTERS = ("FAKE_PROCESS_ADAPTER", "CODEBUDDY_CLI_SUBPROCESS")

# Structural shape of a legitimate fencing token. A malformed token is a
# forgery attempt, not merely an empty field, so it gets its own check.
_FENCING_TOKEN_RE = re.compile(r"^F-[0-9a-f]{8,64}$")
_LEASE_ID_RE = re.compile(r"^HL-[0-9a-f]{8,64}$")


def normalize_domain(domain: str) -> str:
    """Canonical identity for a collision domain.

    Two paths that the OS would treat as the same location MUST hash to the
    same collision identity, or parallel writers could collide undetected:

      - Windows is case-insensitive      -> lower-case
      - Windows accepts both separators  -> forward slashes
      - Unicode has multiple encodings   -> NFC
      - trailing separators are noise    -> strip

    This mirrors the "Windows case/Unicode path equivalence keeps collision
    semantics" adversarial requirement from TASK-BRIEF.yaml.
    """
    text = unicodedata.normalize("NFC", str(domain or ""))
    text = text.replace("\\", "/").strip()
    while text.endswith("/") and len(text) > 1:
        text = text[:-1]
    return text.lower()



@dataclass(frozen=True)
class AuthorityView:
    """A read-only SNAPSHOT of authority owned by other layers.

    The bridge never constructs this from free text. It is assembled by
    `watcher.LocalWorkBuddyBridge` from the canonical registry + trust gate +
    broker. Fields are intentionally strings/bools only, so no layer can smuggle
    an object that later mutates.
    """

    task_id: str = ""
    route_epoch: int | None = None

    # -- registry layer (unified_active_task_registry) -------------------
    is_registered: bool = False
    is_canonical: bool = True          # False => candidate-only

    # -- trust-gate layer ------------------------------------------------
    canonical_authority_valid: bool = False
    authority_state: str = ""          # e.g. "VERIFIED_CANONICAL"
    lease_id: str = ""
    fencing_token: str = ""
    reservation_id: str = ""
    lease_valid: bool = False

    # -- broker layer ----------------------------------------------------
    broker_admission: str = ""         # ADMIT / WAIT / JOIN_EXISTING / BLOCK_CONFLICT / REROUTE
    active_writer_present: bool = False

    # -- base/epoch layer ------------------------------------------------
    canonical_main_sha: str = ""
    expected_main_sha: str = ""
    branch: str = ""
    expected_branch: str = ""
    route_epoch_valid: bool = True

    # -- isolation layer (one worktree/clone per write task) -------------
    isolation_required: bool = True
    isolated_worktree: str = ""
    active_worktree_holders: Mapping[str, str] | None = None

    # -- dispatch layer (validated structured fields only) ---------------
    carrier: str = ""
    execution_identity: str = ""
    model: str = ""
    required_model: str = ""
    collision_domain: str = ""
    declared_collision_domain: str = ""
    cli_path: str = ""
    adapter: str = "FAKE_PROCESS_ADAPTER"

    # -- idempotency layer ----------------------------------------------
    duplicate_receipt_present: bool = False

    def with_duplicate_receipt(self) -> "AuthorityView":
        """Return a copy flagged as already-receipted.

        Declared explicitly rather than via dict reflection so the public-safe
        boundary guard (which fails closed on reflective namespace access) is
        satisfied, and so the set of mutable fields stays auditable.
        """
        return AuthorityView(
            task_id=self.task_id,
            route_epoch=self.route_epoch,
            is_registered=self.is_registered,
            is_canonical=self.is_canonical,
            canonical_authority_valid=self.canonical_authority_valid,
            authority_state=self.authority_state,
            lease_id=self.lease_id,
            fencing_token=self.fencing_token,
            reservation_id=self.reservation_id,
            lease_valid=self.lease_valid,
            broker_admission=self.broker_admission,
            active_writer_present=self.active_writer_present,
            canonical_main_sha=self.canonical_main_sha,
            expected_main_sha=self.expected_main_sha,
            branch=self.branch,
            expected_branch=self.expected_branch,
            route_epoch_valid=self.route_epoch_valid,
            isolation_required=self.isolation_required,
            isolated_worktree=self.isolated_worktree,
            active_worktree_holders=self.active_worktree_holders,
            carrier=self.carrier,
            execution_identity=self.execution_identity,
            model=self.model,
            required_model=self.required_model,
            collision_domain=self.collision_domain,
            declared_collision_domain=self.declared_collision_domain,
            cli_path=self.cli_path,
            adapter=self.adapter,
            duplicate_receipt_present=True,
        )


def _refuse(decision: BridgeDecision, reason: str, view: AuthorityView) -> LaunchPlan:    return LaunchPlan(
        decision=decision,
        reason=reason,
        task_id=view.task_id,
        route_epoch=view.route_epoch,
        branch=view.branch or view.expected_branch,
        collision_domain=view.collision_domain or view.declared_collision_domain,
        carrier=view.carrier,
        model=view.model,
        canonical_main_sha=view.canonical_main_sha,
        cli_path="",
        argv=(),
        dry_run=True,
        launches_real_process=False,
    )


def _model_gate(view: AuthorityView) -> ModelPreflightResult:
    return preflight_model(
        view.model or None,
        required_model=view.required_model or None,
    )


def plan_launch(
    view: AuthorityView,
    *,
    allowed_collision_domains: Sequence[str] | None = None,
    active_collision_domains: Mapping[str, str] | None = None,
) -> LaunchPlan:
    """Compose an authority snapshot into a fail-closed plan.

    Order matters: cheapest/most-fundamental refusals first, so the reported
    reason is the *root* cause rather than a downstream symptom.
    """
    # (2) Registry — an unregistered task cannot be scheduled at all.
    if not view.is_registered:
        return _refuse(
            BridgeDecision.REFUSED_UNREGISTERED_TASK,
            "task is not present in the registered active-task index",
            view,
        )

    # (7) Candidate-only — legible but not yet canonical.
    if not view.is_canonical:
        return _refuse(
            BridgeDecision.REFUSED_CANDIDATE_ONLY,
            "task is candidate-only; canonicalization has not completed",
            view,
        )

    # (1) Stale base — dispatched against a main that has since moved.
    if (
        view.expected_main_sha
        and view.canonical_main_sha
        and view.canonical_main_sha != view.expected_main_sha
    ):
        return _refuse(
            BridgeDecision.REFUSED_STALE_MAIN,
            "canonical main has moved past the dispatched base commit",
            view,
        )

    # (1b) Route epoch — a stale epoch routes to a retired placement.
    if not view.route_epoch_valid:
        return _refuse(
            BridgeDecision.REFUSED_STALE_MAIN,
            "route epoch is stale relative to the canonical task registry",
            view,
        )

    # (5) Branch mismatch.
    if view.expected_branch and view.branch and view.branch != view.expected_branch:
        return _refuse(
            BridgeDecision.REFUSED_BASE_MISMATCH,
            "declared branch does not match the canonical task branch",
            view,
        )

    # (5b) Worktree isolation — every write task gets its own worktree/clone.
    # Sharing a worktree across two write tasks IS a collision, even if their
    # declared collision domains differ.
    if view.isolation_required and view.isolated_worktree in ("", "."):
        return _refuse(
            BridgeDecision.REFUSED_BASE_MISMATCH,
            "write task has no dedicated isolated worktree/clone from execution_repository",
            view,
        )
    if view.active_worktree_holders and view.isolated_worktree:
        norm = normalize_domain(view.isolated_worktree)
        holder = {normalize_domain(k): v for k, v in view.active_worktree_holders.items()}.get(norm)
        if holder:
            return _refuse(
                BridgeDecision.REFUSED_COLLISION_CONFLICT,
                f"worktree {view.isolated_worktree!r} is already held by {holder}",
                view,
            )

    # (3) Authority — trust gate + lease/reservation must both be valid.
    if not view.canonical_authority_valid:
        return _refuse(
            BridgeDecision.REFUSED_AUTHORITY_MISMATCH,
            "canonical authority did not validate (trust gate refused)",
            view,
        )
    if not view.lease_valid or not (view.lease_id and view.fencing_token):
        return _refuse(
            BridgeDecision.REFUSED_AUTHORITY_MISMATCH,
            "writer lease/fencing token is missing, expired or not holder of record",
            view,
        )
    # Structural check: a malformed lease/fencing token is a forgery attempt.
    # Truthiness alone is insufficient — "F-" is non-empty but not a token.
    if not _LEASE_ID_RE.match(view.lease_id):
        return _refuse(
            BridgeDecision.REFUSED_AUTHORITY_MISMATCH,
            f"lease id {view.lease_id!r} is not a well-formed lease identity",
            view,
        )
    if not _FENCING_TOKEN_RE.match(view.fencing_token):
        return _refuse(
            BridgeDecision.REFUSED_AUTHORITY_MISMATCH,
            f"fencing token {view.fencing_token!r} is not a well-formed fencing token",
            view,
        )
    if view.reservation_id == "":
        return _refuse(
            BridgeDecision.REFUSED_AUTHORITY_MISMATCH,
            "no live resource reservation is held for this execution identity",
            view,
        )

    # (6) Collision — parallel writers only in non-overlapping domains.
    if view.broker_admission == "BLOCK_CONFLICT":
        return _refuse(
            BridgeDecision.REFUSED_COLLISION_CONFLICT,
            "host broker refused admission: collision domain is already held",
            view,
        )
    domain = normalize_domain(view.collision_domain or view.declared_collision_domain)
    if view.active_writer_present and active_collision_domains:
        normalized_active = {
            normalize_domain(k): v for k, v in active_collision_domains.items()
        }
        holder = normalized_active.get(domain)
        if holder:
            return _refuse(
                BridgeDecision.REFUSED_COLLISION_CONFLICT,
                f"collision domain {domain!r} is held by another live writer",
                view,
            )
    if allowed_collision_domains is not None:
        allowed = {normalize_domain(d) for d in allowed_collision_domains}
        if domain not in allowed:
            return _refuse(
                BridgeDecision.REFUSED_COLLISION_CONFLICT,
                f"collision domain {domain!r} is not in the authorized domain set",
                view,
            )

    # (4) Idempotency — a prior receipt for the SAME immutable identity wins.
    if view.duplicate_receipt_present:
        return _refuse(
            BridgeDecision.REFUSED_DUPLICATE,
            "a launch receipt already exists for this immutable authority identity",
            view,
        )

    # (8) Model preflight.
    model_result = _model_gate(view)
    if not model_result.ok:
        return _refuse(
            BridgeDecision.REFUSED_MODEL_UNAVAILABLE,
            f"model preflight failed: {model_result.reason}",
            view,
        )

    # (9) Adapter must be one of the declared, reviewed adapters.
    if view.adapter not in _ALLOWED_ADAPTERS:
        return _refuse(
            BridgeDecision.REFUSED_UNKNOWN_ADAPTER,
            f"process adapter {view.adapter!r} is not declared/validated",
            view,
        )

    # -- All gates passed. Emit a PLAN (never a launch). -----------------
    argv = _compose_argv(view)
    return LaunchPlan(
        decision=BridgeDecision.PLANNED,
        reason="all authority, base, collision, idempotency and model gates passed",
        task_id=view.task_id,
        route_epoch=view.route_epoch,
        branch=view.branch,
        collision_domain=domain,
        carrier=view.carrier,
        model=model_result.model,
        canonical_main_sha=view.canonical_main_sha,
        cli_path=view.cli_path,
        argv=argv,
        env_allowlist=(("WB_BRIDGE_DRY_RUN", "1"),),
        dry_run=True,
        launches_real_process=False,
    )


def _compose_argv(view: AuthorityView) -> tuple[str, ...]:
    """Compose argv from VALIDATED structured fields only.

    No free text, no shell interpolation, no untrusted GitHub body content.
    argv is descriptive metadata for the receipt; it is never executed in 2B.
    """
    parts = [
        "--task",
        view.task_id,
        "--route-epoch",
        str(view.route_epoch),
        "--model",
        view.model,
        "--branch",
        view.branch,
    ]
    if view.collision_domain:
        parts += ["--collision-domain", view.collision_domain]
    if view.execution_identity:
        parts += ["--execution-identity", view.execution_identity]
    return tuple(parts)
