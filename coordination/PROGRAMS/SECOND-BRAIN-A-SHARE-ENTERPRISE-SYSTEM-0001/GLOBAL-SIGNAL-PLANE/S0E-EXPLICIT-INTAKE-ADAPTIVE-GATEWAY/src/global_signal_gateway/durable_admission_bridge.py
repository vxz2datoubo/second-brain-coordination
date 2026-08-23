"""R146 public-safe durable admission bridge over the existing S0E/S0C/R145 seams.

The bridge owns no Signal truth. It requires an already-authorized caller context,
resolves owner-domain canonical authority through the existing R145 resolver,
delegates durable intake to the existing S0E gateway, and verifies the admitted
event by reading it back from the same existing S0C ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from global_signal_plane.ledger import DurableSignalLedger, REDUCER_VERSION

from .domain_authority import DomainAuthorityResolver
from .gateway import GatewayError, SignalIntakeGateway, digest, validate_envelope


LEDGER_IDENTITY = f"S0C_DURABLE_SIGNAL_LEDGER/{REDUCER_VERSION}"
RECEIPT_SCHEMA = "DurableAdmissionReceipt/v1"


@dataclass(frozen=True)
class DurableAdmissionReceipt:
    """Compact public-safe proof of one S0C durable admission and read-back."""

    data: Mapping[str, Any]

    def public_dict(self) -> dict[str, Any]:
        return dict(self.data)


class DurableAdmissionBridge:
    """Thin one-shot admission wrapper; it never constructs a ledger or resolver."""

    def __init__(
        self,
        *,
        gateway: SignalIntakeGateway,
        domain_authority_resolver: DomainAuthorityResolver,
        expected_canonical_main: str,
        coordinator_repository: str,
    ) -> None:
        if not isinstance(gateway, SignalIntakeGateway):
            raise GatewayError("S0E_SIGNAL_INTAKE_GATEWAY_REQUIRED", "/gateway")
        if not isinstance(gateway.ledger, DurableSignalLedger):
            raise GatewayError("S0C_DURABLE_LEDGER_REQUIRED", "/gateway/ledger")
        if not isinstance(domain_authority_resolver, DomainAuthorityResolver):
            raise GatewayError("R145_DOMAIN_AUTHORITY_RESOLVER_REQUIRED", "/domain_authority_resolver")
        if not isinstance(expected_canonical_main, str) or not expected_canonical_main:
            raise GatewayError("CANONICAL_MAIN_REQUIRED", "/expected_canonical_main")
        if not isinstance(coordinator_repository, str) or not coordinator_repository:
            raise GatewayError("COORDINATOR_REPOSITORY_REQUIRED", "/coordinator_repository")
        self.gateway = gateway
        self.domain_authority_resolver = domain_authority_resolver
        self.expected_canonical_main = expected_canonical_main
        self.coordinator_repository = coordinator_repository

    @staticmethod
    def _require_public_scope(scope: Any) -> str:
        if not isinstance(scope, str) or not scope.startswith("PUBLIC_SAFE"):
            raise GatewayError("PUBLIC_SAFE_PRIVACY_SCOPE_REQUIRED", "/privacy_scope_ref")
        return scope

    @staticmethod
    def _require_authorized_caller(caller_authorization_ref: Any) -> str:
        if not isinstance(caller_authorization_ref, str) or not caller_authorization_ref.strip():
            raise GatewayError("AUTHORIZED_CALLER_REQUIRED", "/caller_authorization_ref")
        return caller_authorization_ref.strip()

    def admit(
        self,
        envelope: Mapping[str, Any],
        *,
        request_text: str,
        caller_authorization_ref: str,
        authority_observations: Sequence[Mapping[str, Any]],
        exact_read_proofs: Sequence[Any] = (),
        live_observation_proof: Any = None,
        signal_kind: str | None = None,
    ) -> DurableAdmissionReceipt:
        """Resolve authority, append once through S0E, then verify S0C read-back."""

        caller_ref = self._require_authorized_caller(caller_authorization_ref)
        checked = validate_envelope(envelope, request_text)
        privacy_scope = self._require_public_scope(checked.get("privacy_scope_ref"))
        primary_domain = str(checked["proposed_primary_domain"])

        authority = self.domain_authority_resolver.resolve(
            primary_domain,
            authority_observations,
            exact_read_proofs=exact_read_proofs,
            live_observation_proof=live_observation_proof,
            expected_canonical_main=self.expected_canonical_main,
            coordinator_repository=self.coordinator_repository,
        )
        if not authority.get("valid"):
            raise GatewayError(str(authority.get("reason") or "DOMAIN_AUTHORITY_UNVERIFIED"), "/proposed_primary_domain")
        authority_refs = authority.get("authority_refs")
        binding_digest = authority.get("binding_digest")
        if (
            not isinstance(authority_refs, list)
            or not authority_refs
            or not isinstance(binding_digest, str)
            or len(binding_digest) != 64
            or any(character not in "0123456789abcdef" for character in binding_digest)
        ):
            raise GatewayError("DOMAIN_AUTHORITY_BINDING_INCOMPLETE", "/proposed_primary_domain")

        intake = self.gateway.intake(
            envelope,
            request_text=request_text,
            explicit_capture=True,
            signal_kind=signal_kind,
        )
        if intake.get("status") not in {"ADMITTED", "IDEMPOTENT_DUPLICATE"}:
            raise GatewayError("DURABLE_ADMISSION_REQUIRED", "/persistence_class")

        ledger_receipt = intake.get("ledger_receipt")
        if not isinstance(ledger_receipt, Mapping):
            raise GatewayError("S0C_LEDGER_RECEIPT_REQUIRED", "/ledger_receipt")
        offset = ledger_receipt.get("receipt_offset")
        if not isinstance(offset, int) or offset < 1:
            raise GatewayError("S0C_LEDGER_OFFSET_INVALID", "/ledger_receipt/receipt_offset")

        rows = [row for row in self.gateway.ledger.history() if row.get("ledger_offset") == offset]
        if len(rows) != 1:
            raise GatewayError("DURABLE_ADMISSION_READBACK_FAILED", "/readback")
        row = rows[0]
        if (
            row.get("event_id") != intake.get("event_id")
            or row.get("signal_id") != intake.get("signal_id")
            or row.get("primary_domain") != primary_domain
            or row.get("privacy_scope_ref") != privacy_scope
        ):
            raise GatewayError("DURABLE_ADMISSION_READBACK_MISMATCH", "/readback")

        event_record = {key: value for key, value in row.items() if key != "ledger_offset"}
        event_digest = digest(event_record)
        intent_digest = digest(event_record.get("public_safe_metadata", {}).get("intent_envelope", {}))
        receipt_id = f"durable-admission:{digest([intake['event_id'], offset, binding_digest, event_digest])[:24]}"
        input_revision = ledger_receipt.get("input_revision")
        if input_revision is None:
            input_revision = self.gateway.ledger.input_revision()

        return DurableAdmissionReceipt(
            {
                "schema_version": RECEIPT_SCHEMA,
                "receipt_id": receipt_id,
                "signal_id": intake["signal_id"],
                "event_id": intake["event_id"],
                "admission_status": intake["status"],
                "effective_state_changed": bool(ledger_receipt.get("effective_state_changed")),
                "ledger_identity": LEDGER_IDENTITY,
                "receipt_offset": offset,
                "input_revision": input_revision,
                "primary_domain": primary_domain,
                "authority_refs": sorted(map(str, authority_refs)),
                "authority_binding_digest": binding_digest,
                "caller_authorization_digest": digest(caller_ref),
                "readback_verification_status": "VERIFIED_SAME_LEDGER",
                "event_digest": event_digest,
                "content_digest": intent_digest,
                "privacy_scope": privacy_scope,
                "task_created": False,
                "route_created": False,
                "work_claim_created": False,
                "write_permission_created": False,
            }
        )


def admit_durable_signal(
    envelope: Mapping[str, Any],
    *,
    gateway: SignalIntakeGateway,
    domain_authority_resolver: DomainAuthorityResolver,
    expected_canonical_main: str,
    coordinator_repository: str,
    request_text: str,
    caller_authorization_ref: str,
    authority_observations: Sequence[Mapping[str, Any]],
    exact_read_proofs: Sequence[Any] = (),
    live_observation_proof: Any = None,
    signal_kind: str | None = None,
) -> dict[str, Any]:
    """Caller-neutral one-shot entrypoint; returns only the compact receipt."""

    return DurableAdmissionBridge(
        gateway=gateway,
        domain_authority_resolver=domain_authority_resolver,
        expected_canonical_main=expected_canonical_main,
        coordinator_repository=coordinator_repository,
    ).admit(
        envelope,
        request_text=request_text,
        caller_authorization_ref=caller_authorization_ref,
        authority_observations=authority_observations,
        exact_read_proofs=exact_read_proofs,
        live_observation_proof=live_observation_proof,
        signal_kind=signal_kind,
    ).public_dict()
