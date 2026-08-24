"""R147 automatic ChatGPT -> canonical R146/S0C durable Signal ingress.

This module owns only transport/orchestration. It does not define Signal truth,
domain truth, a second gateway, a second resolver, or a second ledger. Git-backed
state is an append-oriented replay transport: every effective event is replayed
through the canonical S0C ``DurableSignalLedger`` before it is trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping, Sequence

import yaml

from global_signal_gateway.domain_authority import DomainAuthorityResolver
from global_signal_gateway.durable_admission_bridge import _bind_trusted_durable_admission_entrypoint
from global_signal_gateway.gateway import (
    GatewayError,
    NO_CAPTURE_ALIASES,
    SignalIntakeGateway,
    digest,
    public_safe,
    semantic_capture,
    temporary_exact_clone,
)
from global_signal_gateway.live_observation_provider import (
    ACTIVE_TASK_PATH,
    CONTROL_PATHS,
    CONTRACT_REVISION,
    TARGET_REPOSITORY,
    DomainFreshnessTarget,
    LiveObservationProvider,
    LiveObservationRequest,
)
from global_signal_gateway.semantic_authority import (
    exact_semantic_authority_proof,
    native_semantic_authority_identity,
)
from global_signal_plane.ledger import DurableSignalLedger
from global_signal_plane.models import SignalPlaneError


REQUEST_SCHEMA = "R147ChatGPTCaptureRequest/v1"
RECEIPT_SCHEMA = "R147AutomaticIngressReceipt/v1"
TRANSPORT_SCHEMA = "R147GitReplayTransport/v1"
R145_AUTHORITY_CONTRACT = (
    "coordination/TASK-BRIEFS/"
    "GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145.yaml"
)
ALLOWED_REQUEST_FIELDS = frozenset({
    "schema_version", "attempt_id", "capture_identity", "capture_command",
    "source_project", "source_window_ref", "public_safe_summary", "desired_effect",
    "problem_to_solve", "success_condition", "expected_problems", "risks",
    "assumptions", "unknowns", "dependencies", "evidence_refs",
    "counterevidence_refs", "proposed_primary_domain", "proposed_related_domains",
    "epistemic_state", "signal_kind",
})
_CALLER_FORBIDDEN_FRAGMENTS = (
    "authority", "resolver", "gateway", "ledger", "proof", "raw", "private",
    "body", "secret", "token", "credential",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GatewayError("R147_INVALID_STRING", path)
    return value.strip()


def _string_list(value: Any, path: str, *, default_unknown: bool = False) -> list[str]:
    if value is None:
        return ["UNKNOWN"] if default_unknown else []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise GatewayError("R147_INVALID_STRING_ARRAY", path)
    return [item.strip() for item in value]


def validate_transport_request(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the bounded public-safe transport object.

    Envelope boilerplate, trust engines and authority proof material are deliberately
    absent from this caller surface.
    """
    if not isinstance(value, Mapping):
        raise GatewayError("R147_REQUEST_NOT_OBJECT", "/")
    for key in value:
        folded = str(key).casefold()
        if any(fragment in folded for fragment in _CALLER_FORBIDDEN_FRAGMENTS):
            raise GatewayError("R147_CALLER_TRUST_OR_PRIVATE_FIELD_FORBIDDEN", f"/{key}")
    extra = sorted(set(value) - ALLOWED_REQUEST_FIELDS)
    if extra:
        raise GatewayError("R147_UNRECOGNIZED_REQUEST_FIELD", f"/{extra[0]}")
    public_safe(value)
    if value.get("schema_version") != REQUEST_SCHEMA:
        raise GatewayError("R147_REQUEST_SCHEMA_INVALID", "/schema_version")

    attempt_id = _require_string(value.get("attempt_id"), "/attempt_id")
    command = _require_string(value.get("capture_command"), "/capture_command")
    summary = _require_string(value.get("public_safe_summary"), "/public_safe_summary")
    domain = _require_string(value.get("proposed_primary_domain"), "/proposed_primary_domain")
    capture_identity = value.get("capture_identity")
    if capture_identity is not None:
        capture_identity = _require_string(capture_identity, "/capture_identity")
    source_project = value.get("source_project")
    source_project = "UNKNOWN" if source_project is None else _require_string(source_project, "/source_project")
    source_window_ref = value.get("source_window_ref")
    source_window_ref = (
        "window://authorized-chatgpt/r147"
        if source_window_ref is None
        else _require_string(source_window_ref, "/source_window_ref")
    )
    desired_effect = value.get("desired_effect")
    desired_effect = (
        "Preserve this public-safe intent as a durable Signal for governed follow-up."
        if desired_effect is None
        else _require_string(desired_effect, "/desired_effect")
    )
    problem = value.get("problem_to_solve")
    problem = summary if problem is None else _require_string(problem, "/problem_to_solve")
    success = value.get("success_condition")
    success = (
        "The Signal is durably admitted and verified by canonical same-ledger read-back."
        if success is None
        else _require_string(success, "/success_condition")
    )
    epistemic = value.get("epistemic_state")
    epistemic = "USER_EXPLICIT" if epistemic is None else _require_string(epistemic, "/epistemic_state")
    signal_kind = value.get("signal_kind")
    if signal_kind is not None:
        signal_kind = _require_string(signal_kind, "/signal_kind")

    return {
        "schema_version": REQUEST_SCHEMA,
        "attempt_id": attempt_id,
        "capture_identity": capture_identity,
        "capture_command": command,
        "source_project": source_project,
        "source_window_ref": source_window_ref,
        "public_safe_summary": summary,
        "desired_effect": desired_effect,
        "problem_to_solve": problem,
        "success_condition": success,
        "expected_problems": _string_list(value.get("expected_problems"), "/expected_problems", default_unknown=True),
        "risks": _string_list(value.get("risks"), "/risks", default_unknown=True),
        "assumptions": _string_list(value.get("assumptions"), "/assumptions", default_unknown=True),
        "unknowns": _string_list(value.get("unknowns"), "/unknowns", default_unknown=True),
        "dependencies": _string_list(value.get("dependencies"), "/dependencies"),
        "evidence_refs": _string_list(value.get("evidence_refs"), "/evidence_refs"),
        "counterevidence_refs": _string_list(value.get("counterevidence_refs"), "/counterevidence_refs"),
        "proposed_primary_domain": domain,
        "proposed_related_domains": _string_list(value.get("proposed_related_domains"), "/proposed_related_domains"),
        "epistemic_state": epistemic,
        "signal_kind": signal_kind,
    }


def _negative_capture(command: str) -> bool:
    normalized = " ".join(command.casefold().split())
    return any(alias in normalized for alias in NO_CAPTURE_ALIASES)


def _semantic_identity_basis(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_project": request["source_project"],
        "public_safe_summary": request["public_safe_summary"],
        "desired_effect": request["desired_effect"],
        "problem_to_solve": request["problem_to_solve"],
        "success_condition": request["success_condition"],
        "expected_problems": request["expected_problems"],
        "risks": request["risks"],
        "assumptions": request["assumptions"],
        "unknowns": request["unknowns"],
        "dependencies": request["dependencies"],
        "evidence_refs": request["evidence_refs"],
        "counterevidence_refs": request["counterevidence_refs"],
        "proposed_primary_domain": request["proposed_primary_domain"],
        "proposed_related_domains": request["proposed_related_domains"],
        "epistemic_state": request["epistemic_state"],
        "signal_kind": request["signal_kind"],
    }


def derive_envelope(
    request: Mapping[str, Any],
    *,
    existing_event: Mapping[str, Any] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Derive the full R136 envelope without exposing boilerplate to callers."""
    explicit_identity = request.get("capture_identity")
    identity_basis: Any = (
        {"capture_identity": explicit_identity, "source_project": request["source_project"]}
        if explicit_identity
        else _semantic_identity_basis(request)
    )
    envelope_id = f"r147-{digest(identity_basis)[:32]}"
    first_seen = captured_at or _utc_now()
    source_ref = f"r147-transport://capture/{envelope_id}"
    source_project = str(request["source_project"])
    source_window = str(request["source_window_ref"])
    if existing_event is not None:
        if existing_event.get("event_id") != f"r136:{envelope_id}":
            raise GatewayError("R147_EXISTING_IDENTITY_MISMATCH", "/existing_event")
        first_seen = str(existing_event.get("occurred_at") or first_seen)
        source_ref = str(existing_event.get("source_ref") or source_ref)
        source_project = str(existing_event.get("source_project") or source_project)
        prior_intent = existing_event.get("public_safe_metadata", {}).get("intent_envelope", {})
        if isinstance(prior_intent, Mapping):
            source_window = str(prior_intent.get("source_window_ref") or source_window)

    return {
        "envelope_id": envelope_id,
        "source_ref": source_ref,
        "source_type": "CHATGPT_PUBLIC_SAFE_GITHUB_TRANSPORT",
        "source_project": source_project,
        "source_actor": "AUTHORIZED_CHATGPT_WINDOW",
        "source_window_ref": source_window,
        "captured_at": first_seen,
        "original_intent_ref": f"intent://r147/{envelope_id}",
        "public_safe_summary": request["public_safe_summary"],
        "desired_effect": request["desired_effect"],
        "problem_to_solve": request["problem_to_solve"],
        "success_condition": request["success_condition"],
        "expected_problems": list(request["expected_problems"]),
        "risks": list(request["risks"]),
        "assumptions": list(request["assumptions"]),
        "unknowns": list(request["unknowns"]),
        "dependencies": list(request["dependencies"]),
        "evidence_refs": list(request["evidence_refs"]),
        "counterevidence_refs": list(request["counterevidence_refs"]),
        "privacy_scope_ref": "PUBLIC_SAFE_METADATA_ONLY",
        "proposed_primary_domain": request["proposed_primary_domain"],
        "proposed_related_domains": list(request["proposed_related_domains"]),
        "epistemic_state": request["epistemic_state"],
        "persistence_class": "DURABLE_SIGNAL",
        "execution_class": "GOVERNED_MISSION",
        "materiality_class": "MATERIAL",
    }


@dataclass(frozen=True)
class TrustedAuthorityMaterial:
    resolver: DomainAuthorityResolver
    observations: tuple[Mapping[str, Any], ...]
    exact_read_proofs: tuple[Any, ...]
    live_observation_proof: Any
    expected_canonical_main: str
    coordinator_repository: str


class GitReplayTransport:
    """Append-oriented replay transport. S0C remains the only Signal truth."""

    def __init__(self, journal_path: str | Path) -> None:
        self.journal_path = Path(journal_path)

    def load_events(self) -> list[dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line_number, line in enumerate(self.journal_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GatewayError("R147_TRANSPORT_JOURNAL_JSON_INVALID", f"/journal/{line_number}") from exc
            if not isinstance(item, dict) or "ledger_offset" in item:
                raise GatewayError("R147_TRANSPORT_JOURNAL_RECORD_INVALID", f"/journal/{line_number}")
            public_safe(item, f"/journal/{line_number}/")
            events.append(item)
        return events

    @staticmethod
    def replay(events: Sequence[Mapping[str, Any]]) -> tuple[DurableSignalLedger, dict[str, Any]]:
        ledger = DurableSignalLedger()
        for expected_offset, event in enumerate(events, start=1):
            receipt = ledger.ingest_raw(event)
            if receipt.get("status") != "ADMITTED" or receipt.get("receipt_offset") != expected_offset:
                ledger.close()
                raise GatewayError("R147_TRANSPORT_REPLAY_NOT_EXACT", f"/journal/{expected_offset}")
        projection = ledger.current_projection()
        if projection is None:
            projection = ledger.rebuild_projection(expected_version=ledger.current_projection_version())
        rows = ledger.history()
        evidence = {
            "schema_version": TRANSPORT_SCHEMA,
            "event_count": len(rows),
            "input_revision": ledger.input_revision(),
            "history_digest": digest([
                {key: value for key, value in row.items() if key != "ledger_offset"}
                for row in rows
            ]),
            "projection_checksum": projection.get("checksum"),
            "journal_digest": digest(list(events)),
        }
        return ledger, evidence

    def write_events(self, events: Sequence[Mapping[str, Any]]) -> None:
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(_canonical(dict(event)) + "\n" for event in events)
        temporary = self.journal_path.with_suffix(self.journal_path.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.journal_path)


class AutomaticSignalTowerIngress:
    """Trusted host. Normal callers supply no envelope/proof/engine internals."""

    def __init__(
        self,
        *,
        transport: GitReplayTransport,
        authority_materializer: Callable[[Mapping[str, Any]], TrustedAuthorityMaterial],
        caller_authorization_ref: str,
        clock: Callable[[], str] = _utc_now,
    ) -> None:
        self.transport = transport
        self.authority_materializer = authority_materializer
        self.caller_authorization_ref = caller_authorization_ref
        self.clock = clock

    @staticmethod
    def _find_existing(ledger: DurableSignalLedger, envelope_id: str) -> Mapping[str, Any] | None:
        event_id = f"r136:{envelope_id}"
        rows = [row for row in ledger.history() if row.get("event_id") == event_id]
        if len(rows) > 1:
            raise GatewayError("R147_EXISTING_EVENT_AMBIGUOUS", "/journal")
        return rows[0] if rows else None

    @staticmethod
    def _failure_receipt(
        request: Mapping[str, Any] | None,
        *,
        code: str,
        path: str,
        replay: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": RECEIPT_SCHEMA,
            "attempt_id": None if request is None else request.get("attempt_id"),
            "status": "NEEDS_REVALIDATION",
            "durable_success": False,
            "code": code,
            "path": path,
            "readback_verification_status": "NOT_VERIFIED",
            "transport_replay_before": dict(replay or {}),
            "task_created": False,
            "route_created": False,
            "work_claim_created": False,
            "write_permission_created": False,
        }

    def process(self, raw_request: Mapping[str, Any]) -> dict[str, Any]:
        request: dict[str, Any] | None = None
        ledger: DurableSignalLedger | None = None
        before: dict[str, Any] | None = None
        try:
            request = validate_transport_request(raw_request)
            events = self.transport.load_events()
            ledger, before = self.transport.replay(events)

            if _negative_capture(request["capture_command"]) or not semantic_capture(request["capture_command"]):
                return {
                    "schema_version": RECEIPT_SCHEMA,
                    "attempt_id": request["attempt_id"],
                    "status": "NOT_CAPTURED",
                    "durable_success": False,
                    "code": "EXPLICIT_NO_CAPTURE_OR_NO_EXPLICIT_SIGNAL_INTENT",
                    "transport_replay_before": before,
                    "transport_replay_after": before,
                    "task_created": False,
                    "route_created": False,
                    "work_claim_created": False,
                    "write_permission_created": False,
                }

            provisional = derive_envelope(request, captured_at=self.clock())
            existing = self._find_existing(ledger, provisional["envelope_id"])
            envelope = derive_envelope(request, existing_event=existing, captured_at=provisional["captured_at"])

            material = self.authority_materializer(request)
            gateway = SignalIntakeGateway(ledger)
            entrypoint = _bind_trusted_durable_admission_entrypoint(
                gateway=gateway,
                domain_authority_resolver=material.resolver,
                expected_canonical_main=material.expected_canonical_main,
                coordinator_repository=material.coordinator_repository,
            )
            durable = entrypoint(
                envelope,
                request_text=request["capture_command"],
                caller_authorization_ref=self.caller_authorization_ref,
                authority_observations=material.observations,
                exact_read_proofs=material.exact_read_proofs,
                live_observation_proof=material.live_observation_proof,
                signal_kind=request.get("signal_kind"),
            )

            candidate_events = list(events)
            if durable["admission_status"] == "ADMITTED":
                rows = [row for row in ledger.history() if row.get("ledger_offset") == durable["receipt_offset"]]
                if len(rows) != 1:
                    raise GatewayError("R147_POST_ADMISSION_EVENT_UNAVAILABLE", "/readback")
                candidate_events.append({key: value for key, value in rows[0].items() if key != "ledger_offset"})
            elif durable["admission_status"] != "IDEMPOTENT_DUPLICATE":
                raise GatewayError("R147_UNEXPECTED_DURABLE_STATUS", "/admission_status")

            verify_ledger, after = self.transport.replay(candidate_events)
            try:
                live_history_digest = digest([
                    {key: value for key, value in row.items() if key != "ledger_offset"}
                    for row in ledger.history()
                ])
                if (
                    after["history_digest"] != live_history_digest
                    or after["projection_checksum"] != (ledger.current_projection() or {}).get("checksum")
                    or after["input_revision"] != ledger.input_revision()
                ):
                    raise GatewayError("R147_FRESH_REPLAY_DIVERGENCE", "/transport")
                verify_rows = [row for row in verify_ledger.history() if row.get("event_id") == durable["event_id"]]
                if (
                    len(verify_rows) != 1
                    or verify_rows[0].get("signal_id") != durable["signal_id"]
                    or verify_rows[0].get("ledger_offset") != durable["receipt_offset"]
                ):
                    raise GatewayError("R147_FRESH_REPLAY_READBACK_MISMATCH", "/transport")
            finally:
                verify_ledger.close()

            if durable["admission_status"] == "ADMITTED":
                self.transport.write_events(candidate_events)

            return {
                "schema_version": RECEIPT_SCHEMA,
                "attempt_id": request["attempt_id"],
                "status": durable["admission_status"],
                "durable_success": True,
                "signal_id": durable["signal_id"],
                "event_id": durable["event_id"],
                "receipt_id": durable["receipt_id"],
                "receipt_offset": durable["receipt_offset"],
                "input_revision": durable["input_revision"],
                "primary_domain": durable["primary_domain"],
                "authority_binding_digest": durable["authority_binding_digest"],
                "authority_refs": durable["authority_refs"],
                "content_digest": durable["content_digest"],
                "event_digest": durable["event_digest"],
                "readback_verification_status": durable["readback_verification_status"],
                "fresh_replay_verification_status": "VERIFIED_FRESH_S0C_REPLAY",
                "transport_replay_before": before,
                "transport_replay_after": after,
                "task_created": False,
                "route_created": False,
                "work_claim_created": False,
                "write_permission_created": False,
            }
        except (GatewayError, SignalPlaneError) as exc:
            code = getattr(exc, "code", type(exc).__name__)
            path = getattr(exc, "path", "/")
            return self._failure_receipt(request, code=str(code), path=str(path), replay=before)
        finally:
            if ledger is not None:
                ledger.close()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise GatewayError("R147_RUNTIME_GIT_READ_FAILED", "/runtime")
    return result.stdout.strip()


class GithubR145AuthorityMaterializer:
    """Production public-GitHub materializer over existing R137/R145 seams."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        observation_pr: int,
        authority_contract_path: str = R145_AUTHORITY_CONTRACT,
    ) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self.observation_pr = observation_pr
        self.authority_contract_path = authority_contract_path

    def __call__(self, request: Mapping[str, Any]) -> TrustedAuthorityMaterial:
        main = _git(self.runtime_root, "rev-parse", "HEAD")
        contract_file = self.runtime_root / self.authority_contract_path
        active_file = self.runtime_root / ACTIVE_TASK_PATH
        try:
            contract = yaml.safe_load(contract_file.read_text(encoding="utf-8"))
            active = yaml.safe_load(active_file.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise GatewayError("R147_CANONICAL_AUTHORITY_CONFIG_UNAVAILABLE", "/authority") from exc
        if not isinstance(contract, Mapping) or not isinstance(active, Mapping):
            raise GatewayError("R147_CANONICAL_AUTHORITY_CONFIG_INVALID", "/authority")
        if contract.get("repository") != TARGET_REPOSITORY:
            raise GatewayError("R147_CANONICAL_AUTHORITY_REPOSITORY_MISMATCH", "/authority")

        domain_id = str(request["proposed_primary_domain"])
        domains = contract.get("mandatory_domain_regressions")
        if not isinstance(domains, Mapping):
            raise GatewayError("R147_R145_DOMAIN_CONFIG_INVALID", "/authority")
        spec = domains.get(domain_id)
        if not isinstance(spec, Mapping):
            raise GatewayError("DOMAIN_ROUTE_UNRESOLVED", "/proposed_primary_domain")
        repository = spec.get("repository")
        if not isinstance(repository, str) or not repository:
            raise GatewayError("DOMAIN_AUTHORITY_UNAVAILABLE", "/proposed_primary_domain")

        task_id = active.get("task_id")
        route_epoch = active.get("route_epoch")
        if not isinstance(task_id, str) or not isinstance(route_epoch, int):
            raise GatewayError("R147_ACTIVE_CONTROL_BINDING_INVALID", "/authority")

        live_request = LiveObservationRequest(
            request_id=f"r147-ingress-{digest([request['attempt_id'], domain_id, main])[:24]}",
            provider_contract_revision=CONTRACT_REVISION,
            target_repository=TARGET_REPOSITORY,
            target_branch="main",
            pull_request_number=self.observation_pr,
            expected_task_id=task_id,
            expected_route_epoch=route_epoch,
            required_control_plane_paths=CONTROL_PATHS,
            required_domain_freshness_targets=(
                DomainFreshnessTarget(
                    repository,
                    domain_id=domain_id,
                    authority_contract_path=self.authority_contract_path,
                ),
            ),
            required_review_scope="ALL_RAW_REVIEWS",
            requested_max_age_seconds=240,
            requested_at=_utc_now(),
        )
        bundle, live = LiveObservationProvider().observe(live_request)

        hints = [
            value
            for value in (spec.get("authority_hint"), spec.get("architecture_hint"))
            if isinstance(value, str) and value.strip()
        ]
        if len(hints) != 1:
            raise GatewayError("DOMAIN_AUTHORITY_PATH_UNRESOLVED", "/proposed_primary_domain")
        source_records = [
            record
            for record in bundle.exact_objects
            if record.repository == repository and record.path == hints[0]
        ]
        if len(source_records) != 1:
            raise GatewayError("DOMAIN_AUTHORITY_SOURCE_UNAVAILABLE", "/proposed_primary_domain")
        source = source_records[0]

        with temporary_exact_clone(f"https://github.com/{repository}.git", source.commit_sha) as source_root:
            try:
                payload = (source_root / source.path).read_bytes()
            except OSError as exc:
                raise GatewayError("DOMAIN_AUTHORITY_SOURCE_UNAVAILABLE", "/authority") from exc
            native = native_semantic_authority_identity(payload, path=source.path)
            project_id = native.get("project_id")
            schema = native.get("authority_schema_version")
            if not isinstance(project_id, str) or not isinstance(schema, str):
                raise GatewayError("SEMANTIC_AUTHORITY_IDENTITY_INCOMPLETE", "/authority")
            expected_identity = {
                "domain_id": domain_id,
                "project_id": project_id,
                "authority_schema_version": schema,
                "writeback_owner": domain_id,
                "observation_mode": "READ_ONLY",
            }
            exact = exact_semantic_authority_proof(
                source_root,
                repository=repository,
                commit=source.commit_sha,
                path=source.path,
                execution_id=f"r147-authority-{digest([request['attempt_id'], domain_id])[:24]}",
                governed_source_proof=live,
                expected_identity=expected_identity,
            )

        visibility = "PUBLIC_OR_METADATA_ONLY"
        descriptor = {
            "domain_id": domain_id,
            "project_id": project_id,
            "repository": repository,
            "canonical_ref_kind": "CANONICAL_MAIN",
            "canonical_commit": source.commit_sha,
            "authority_path_or_contract_ref": source.path,
            "authority_schema_version": schema,
            "writeback_owner": domain_id,
            "observation_mode": "READ_ONLY",
            "repository_visibility": visibility,
        }
        observation = {
            "domain_id": domain_id,
            "project_id": project_id,
            "repository": repository,
            "canonical_ref_kind": "CANONICAL_MAIN",
            "canonical_commit": source.commit_sha,
            "authority_path_or_contract_ref": source.path,
            "authority_blob_sha": source.blob_sha,
            "authority_content_sha256": source.content_sha256,
            "authority_schema_version": schema,
            "observation_mode": "READ_ONLY",
            "source_kind": "CANONICAL_MAIN",
            "observed_at": live.observed_at,
            "evidence_refs": [bundle.identity_ref(), source.ref()],
            "repository_visibility": visibility,
        }
        return TrustedAuthorityMaterial(
            resolver=DomainAuthorityResolver([descriptor]),
            observations=(observation,),
            exact_read_proofs=(exact,),
            live_observation_proof=live,
            expected_canonical_main=main,
            coordinator_repository=TARGET_REPOSITORY,
        )


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GatewayError("R147_REQUEST_FILE_INVALID", "/request") from exc
    if not isinstance(value, Mapping):
        raise GatewayError("R147_REQUEST_FILE_INVALID", "/request")
    return value


def _write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    public_safe(receipt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def process_github_request(
    *,
    runtime_root: Path,
    transport_root: Path,
    request_path: Path,
    observation_pr: int,
) -> dict[str, Any]:
    state_root = transport_root / (
        "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
        "GLOBAL-SIGNAL-PLANE/R147-AUTOMATIC-INGRESS/transport"
    )
    resolved_request = request_path.resolve()
    resolved_transport = transport_root.resolve()
    if not resolved_request.is_relative_to(resolved_transport):
        raise GatewayError("R147_REQUEST_PATH_OUTSIDE_TRANSPORT_ROOT", "/request")
    relative = resolved_request.relative_to(resolved_transport)
    if "requests" not in relative.parts or request_path.suffix != ".json":
        raise GatewayError("R147_REQUEST_PATH_INVALID", "/request")
    raw = _load_json(request_path)
    attempt = raw.get("attempt_id")
    if not isinstance(attempt, str) or request_path.stem != attempt:
        raise GatewayError("R147_REQUEST_FILENAME_ID_MISMATCH", "/attempt_id")

    ingress = AutomaticSignalTowerIngress(
        transport=GitReplayTransport(state_root / "admitted_events.jsonl"),
        authority_materializer=GithubR145AuthorityMaterializer(
            runtime_root=runtime_root,
            observation_pr=observation_pr,
        ),
        caller_authorization_ref="authorization://github-actions/r147-authorized-chatgpt-ingress",
    )
    receipt = ingress.process(raw)
    _write_receipt(state_root / "receipts" / f"{attempt}.json", receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    process = sub.add_parser("process-github")
    process.add_argument("--runtime-root", required=True)
    process.add_argument("--transport-root", required=True)
    process.add_argument("--request", required=True)
    process.add_argument("--observation-pr", required=True, type=int)
    args = parser.parse_args(argv)
    if args.command == "process-github":
        try:
            receipt = process_github_request(
                runtime_root=Path(args.runtime_root),
                transport_root=Path(args.transport_root),
                request_path=Path(args.request),
                observation_pr=args.observation_pr,
            )
        except GatewayError as exc:
            print(json.dumps({"status": "INFRASTRUCTURE_FAILURE", "code": exc.code, "path": exc.path}))
            return 2
        print(json.dumps(receipt, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
