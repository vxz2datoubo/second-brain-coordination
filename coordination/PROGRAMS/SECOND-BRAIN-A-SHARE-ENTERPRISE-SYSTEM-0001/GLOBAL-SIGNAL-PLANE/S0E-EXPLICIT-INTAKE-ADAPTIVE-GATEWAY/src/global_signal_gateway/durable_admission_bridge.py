"""R146 public-safe durable admission bridge over the existing S0E/S0C/R145 seams.

Trusted dependency composition is deliberately separated from the caller-facing
entrypoint. The authorized caller can supply only the public-safe envelope and
R145 proof material; it cannot choose or replace the SignalIntakeGateway,
DurableSignalLedger, or DomainAuthorityResolver used for admission.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from global_signal_plane.ledger import DurableSignalLedger, REDUCER_VERSION

from .domain_authority import DomainAuthorityDescriptor, DomainAuthorityResolver
from .gateway import GatewayError, SignalIntakeGateway, digest, validate_envelope


LEDGER_IDENTITY = f"S0C_DURABLE_SIGNAL_LEDGER/{REDUCER_VERSION}"
RECEIPT_SCHEMA = "DurableAdmissionReceipt/v1"

_CANONICAL_GATEWAY_INTAKE = SignalIntakeGateway.intake
_CANONICAL_RESOLVER_RESOLVE = DomainAuthorityResolver.resolve
_CANONICAL_LEDGER_INGEST = DurableSignalLedger.ingest
_CANONICAL_LEDGER_HISTORY = DurableSignalLedger.history
_CANONICAL_LEDGER_INPUT_REVISION = DurableSignalLedger.input_revision
_COMPOSITION_TOKEN = object()


@dataclass(frozen=True)
class DurableAdmissionReceipt:
    """Compact public-safe proof of one S0C durable admission and read-back."""

    data: Mapping[str, Any]

    def public_dict(self) -> dict[str, Any]:
        return dict(self.data)


def _bound_method_is(instance: Any, name: str, canonical: Any) -> bool:
    bound = getattr(instance, name, None)
    return (
        getattr(bound, "__self__", None) is instance
        and getattr(bound, "__func__", None) is canonical
    )


def _resolver_state_digest(resolver: DomainAuthorityResolver) -> str:
    by_domain = getattr(resolver, "_by_domain", None)
    if not isinstance(by_domain, dict):
        raise GatewayError(
            "R145_CANONICAL_RESOLVER_STATE_REQUIRED",
            "/trusted_composition/domain_authority_resolver",
        )
    serialized: list[dict[str, str]] = []
    for domain_id, descriptor in sorted(by_domain.items()):
        if (
            not isinstance(domain_id, str)
            or type(descriptor) is not DomainAuthorityDescriptor
            or descriptor.domain_id != domain_id
        ):
            raise GatewayError(
                "R145_CANONICAL_RESOLVER_STATE_REQUIRED",
                "/trusted_composition/domain_authority_resolver",
            )
        serialized.append(descriptor.public_dict())
    return digest(serialized)


def _validate_composition_inputs(
    *,
    gateway: SignalIntakeGateway,
    domain_authority_resolver: DomainAuthorityResolver,
    expected_canonical_main: str,
    coordinator_repository: str,
) -> tuple[DurableSignalLedger, str]:
    if type(gateway) is not SignalIntakeGateway:
        raise GatewayError(
            "S0E_CANONICAL_SIGNAL_INTAKE_GATEWAY_REQUIRED",
            "/trusted_composition/gateway",
        )
    ledger = getattr(gateway, "ledger", None)
    if type(ledger) is not DurableSignalLedger:
        raise GatewayError(
            "S0C_CANONICAL_DURABLE_LEDGER_REQUIRED",
            "/trusted_composition/gateway/ledger",
        )
    if type(domain_authority_resolver) is not DomainAuthorityResolver:
        raise GatewayError(
            "R145_CANONICAL_DOMAIN_AUTHORITY_RESOLVER_REQUIRED",
            "/trusted_composition/domain_authority_resolver",
        )
    if not _bound_method_is(gateway, "intake", _CANONICAL_GATEWAY_INTAKE):
        raise GatewayError(
            "S0E_CANONICAL_GATEWAY_METHOD_REQUIRED",
            "/trusted_composition/gateway/intake",
        )
    if not _bound_method_is(
        domain_authority_resolver,
        "resolve",
        _CANONICAL_RESOLVER_RESOLVE,
    ):
        raise GatewayError(
            "R145_CANONICAL_RESOLVER_METHOD_REQUIRED",
            "/trusted_composition/domain_authority_resolver/resolve",
        )
    if not _bound_method_is(ledger, "ingest", _CANONICAL_LEDGER_INGEST):
        raise GatewayError(
            "S0C_CANONICAL_LEDGER_INGEST_REQUIRED",
            "/trusted_composition/gateway/ledger/ingest",
        )
    if not isinstance(expected_canonical_main, str) or not expected_canonical_main:
        raise GatewayError("CANONICAL_MAIN_REQUIRED", "/expected_canonical_main")
    if not isinstance(coordinator_repository, str) or not coordinator_repository:
        raise GatewayError("COORDINATOR_REPOSITORY_REQUIRED", "/coordinator_repository")
    return ledger, _resolver_state_digest(domain_authority_resolver)


class _DurableAdmissionBridge:
    """Pre-composed trusted bridge. Caller input never selects trust engines."""

    __slots__ = (
        "_gateway",
        "_ledger",
        "_resolver",
        "_resolver_state",
        "_expected_canonical_main",
        "_coordinator_repository",
    )

    def __init__(
        self,
        *,
        token: object,
        gateway: SignalIntakeGateway,
        ledger: DurableSignalLedger,
        domain_authority_resolver: DomainAuthorityResolver,
        resolver_state: str,
        expected_canonical_main: str,
        coordinator_repository: str,
    ) -> None:
        if token is not _COMPOSITION_TOKEN:
            raise GatewayError("TRUSTED_COMPOSITION_REQUIRED", "/trusted_composition")
        self._gateway = gateway
        self._ledger = ledger
        self._resolver = domain_authority_resolver
        self._resolver_state = resolver_state
        self._expected_canonical_main = expected_canonical_main
        self._coordinator_repository = coordinator_repository

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

    def _assert_pre_append_trust(self) -> None:
        if (
            type(self._gateway) is not SignalIntakeGateway
            or type(self._ledger) is not DurableSignalLedger
            or self._gateway.ledger is not self._ledger
        ):
            raise GatewayError(
                "TRUSTED_ADMISSION_COMPOSITION_TAMPERED",
                "/trusted_composition",
            )
        if not _bound_method_is(self._gateway, "intake", _CANONICAL_GATEWAY_INTAKE):
            raise GatewayError(
                "S0E_CANONICAL_GATEWAY_METHOD_TAMPERED",
                "/trusted_composition/gateway/intake",
            )
        if not _bound_method_is(self._ledger, "ingest", _CANONICAL_LEDGER_INGEST):
            raise GatewayError(
                "S0C_CANONICAL_LEDGER_INGEST_TAMPERED",
                "/trusted_composition/gateway/ledger/ingest",
            )
        if (
            type(self._resolver) is not DomainAuthorityResolver
            or not _bound_method_is(
                self._resolver,
                "resolve",
                _CANONICAL_RESOLVER_RESOLVE,
            )
        ):
            raise GatewayError(
                "R145_CANONICAL_RESOLVER_TAMPERED",
                "/trusted_composition/domain_authority_resolver",
            )
        if _resolver_state_digest(self._resolver) != self._resolver_state:
            raise GatewayError(
                "R145_CANONICAL_RESOLVER_STATE_TAMPERED",
                "/trusted_composition/domain_authority_resolver",
            )

    def _assert_readback_trust(self) -> None:
        if self._gateway.ledger is not self._ledger or type(self._ledger) is not DurableSignalLedger:
            raise GatewayError(
                "S0C_DURABLE_LEDGER_SUBSTITUTED",
                "/readback",
            )
        if not _bound_method_is(self._ledger, "history", _CANONICAL_LEDGER_HISTORY):
            raise GatewayError(
                "S0C_DURABLE_LEDGER_READBACK_TAMPERED",
                "/readback",
            )
        if not _bound_method_is(
            self._ledger,
            "input_revision",
            _CANONICAL_LEDGER_INPUT_REVISION,
        ):
            raise GatewayError(
                "S0C_DURABLE_LEDGER_REVISION_TAMPERED",
                "/readback",
            )

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
        """Resolve canonical authority, append via S0E, then verify S0C read-back."""

        self._assert_pre_append_trust()
        caller_ref = self._require_authorized_caller(caller_authorization_ref)
        checked = validate_envelope(envelope, request_text)
        privacy_scope = self._require_public_scope(checked.get("privacy_scope_ref"))
        primary_domain = str(checked["proposed_primary_domain"])

        authority = self._resolver.resolve(
            primary_domain,
            authority_observations,
            exact_read_proofs=exact_read_proofs,
            live_observation_proof=live_observation_proof,
            expected_canonical_main=self._expected_canonical_main,
            coordinator_repository=self._coordinator_repository,
        )
        if not authority.get("valid"):
            raise GatewayError(
                str(authority.get("reason") or "DOMAIN_AUTHORITY_UNVERIFIED"),
                "/proposed_primary_domain",
            )
        authority_refs = authority.get("authority_refs")
        binding_digest = authority.get("binding_digest")
        if (
            not isinstance(authority_refs, list)
            or not authority_refs
            or not isinstance(binding_digest, str)
            or len(binding_digest) != 64
            or any(character not in "0123456789abcdef" for character in binding_digest)
        ):
            raise GatewayError(
                "DOMAIN_AUTHORITY_BINDING_INCOMPLETE",
                "/proposed_primary_domain",
            )

        self._assert_pre_append_trust()
        intake = self._gateway.intake(
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
            raise GatewayError(
                "S0C_LEDGER_OFFSET_INVALID",
                "/ledger_receipt/receipt_offset",
            )

        self._assert_readback_trust()
        rows = [
            row
            for row in self._ledger.history()
            if row.get("ledger_offset") == offset
        ]
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
        intent_digest = digest(
            event_record.get("public_safe_metadata", {}).get("intent_envelope", {})
        )
        receipt_id = (
            "durable-admission:"
            + digest([intake["event_id"], offset, binding_digest, event_digest])[:24]
        )
        input_revision = ledger_receipt.get("input_revision")
        if input_revision is None:
            input_revision = self._ledger.input_revision()

        return DurableAdmissionReceipt(
            {
                "schema_version": RECEIPT_SCHEMA,
                "receipt_id": receipt_id,
                "signal_id": intake["signal_id"],
                "event_id": intake["event_id"],
                "admission_status": intake["status"],
                "effective_state_changed": bool(
                    ledger_receipt.get("effective_state_changed")
                ),
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


class DurableAdmissionEntrypoint:
    """Caller-facing one-shot entrypoint with no dependency-selection surface."""

    __slots__ = ("_bridge",)

    def __init__(self, bridge: _DurableAdmissionBridge, *, token: object) -> None:
        if token is not _COMPOSITION_TOKEN or type(bridge) is not _DurableAdmissionBridge:
            raise GatewayError("TRUSTED_COMPOSITION_REQUIRED", "/trusted_composition")
        self._bridge = bridge

    def admit_durable_signal(
        self,
        envelope: Mapping[str, Any],
        *,
        request_text: str,
        caller_authorization_ref: str,
        authority_observations: Sequence[Mapping[str, Any]],
        exact_read_proofs: Sequence[Any] = (),
        live_observation_proof: Any = None,
        signal_kind: str | None = None,
    ) -> dict[str, Any]:
        """Caller-facing one-shot admission; trust engines are already sealed."""
        return self._bridge.admit(
            envelope,
            request_text=request_text,
            caller_authorization_ref=caller_authorization_ref,
            authority_observations=authority_observations,
            exact_read_proofs=exact_read_proofs,
            live_observation_proof=live_observation_proof,
            signal_kind=signal_kind,
        ).public_dict()

    __call__ = admit_durable_signal


def _bind_trusted_durable_admission_entrypoint(
    *,
    gateway: SignalIntakeGateway,
    domain_authority_resolver: DomainAuthorityResolver,
    expected_canonical_main: str,
    coordinator_repository: str,
) -> DurableAdmissionEntrypoint:
    """Trusted host composition seam; never expose these dependencies to callers."""

    ledger, resolver_state = _validate_composition_inputs(
        gateway=gateway,
        domain_authority_resolver=domain_authority_resolver,
        expected_canonical_main=expected_canonical_main,
        coordinator_repository=coordinator_repository,
    )
    bridge = _DurableAdmissionBridge(
        token=_COMPOSITION_TOKEN,
        gateway=gateway,
        ledger=ledger,
        domain_authority_resolver=domain_authority_resolver,
        resolver_state=resolver_state,
        expected_canonical_main=expected_canonical_main,
        coordinator_repository=coordinator_repository,
    )
    return DurableAdmissionEntrypoint(bridge, token=_COMPOSITION_TOKEN)
