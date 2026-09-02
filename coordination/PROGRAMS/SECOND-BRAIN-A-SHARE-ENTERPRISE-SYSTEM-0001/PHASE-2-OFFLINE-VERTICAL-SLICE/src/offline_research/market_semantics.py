from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Sequence


MARKET_SEMANTIC_FIELD_SCHEMA_DIGEST_V1 = "c765ea43c6c147462b34771e29162de777d2ce9ba7d904bda675ea3b06673ae7"
PROVIDER_CAPABILITY_SCHEMA_DIGEST_V1 = "33dc4bf5683bb62720b23c90e2dc3864f43a232f3e0b5f415cf4dc34b8377851"

# This is the governed semantic identity registry for the bounded R182 v1 slice.
# A caller may reconstruct an identical record, but cannot change its meaning and
# recompute a fresh digest to create a new governed identity. New/changed bindings
# require a governed code/fixture change plus independent review.
GOVERNED_SEMANTIC_DIGESTS_V1 = MappingProxyType({
    ("TDXQUANT_OFFICIAL_DOC", "OFFICIAL_DOC_CURRENT_AT_2026_09_01", "Price", "TDXQUANT.TICK.PRICE.DOCREF.V1"):
        "d6ac91f54bf0f990aa79bb0e250a5dada33dfe2f2e04555f3dfd8201c7fe3f2a",
    ("TDXQUANT_OFFICIAL_DOC", "OFFICIAL_DOC_CURRENT_AT_2026_09_01", "Volume", "TDXQUANT.TICK.VOLUME.DOCREF.V1"):
        "e5410ea49963e7aa79bea690a60309e32eca5fc4678691b56d9e5bb91d38c3d9",
    ("TDXQUANT_OFFICIAL_DOC", "OFFICIAL_DOC_CURRENT_AT_2026_09_01", "BSFlag", "TDXQUANT.TICK.BSFLAG.DOCREF.V1"):
        "ba5c6e8d7b008ae795f8b1600a34899cd34168ef05b170c070cdbfcf27d76a1f",
    ("TDXQUANT_OFFICIAL_DOC", "OFFICIAL_DOC_CURRENT_AT_2026_09_01", "Time", "TDXQUANT.TICK.TIME.DOCREF.V1"):
        "926b3cd8d2797f6b2a2cc7ddb3b9b495dce3005d5b21683bca7b5185c45a9b42",
})

_SEMANTIC_IDENTITY_FIELDS = (
    "semantic_field_id", "semantic_version", "source_system", "source_version",
    "source_field_name", "canonical_field_ref", "primitive_type", "unit_kind",
    "unit_symbol", "unit_scale", "fixed_scale", "tick_size", "tick_size_ref",
    "rounding_policy", "price_semantic", "time_semantic", "adjustment_state",
    "source_enum_map", "allowed_missing_states", "canonical_persistable",
    "valid_from", "valid_until", "source_ref", "evidence_ref", "schema_digest",
    "observed_at", "last_verified_at",
)


class SemanticValidationError(ValueError):
    """Stable fail-closed error for W2 market-semantic validation."""

    def __init__(self, code: str, path: str = "/", detail: str | None = None) -> None:
        self.code = code
        self.path = path
        self.detail = detail
        message = f"{code} at {path}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


class CanonicalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


class MissingState(str, Enum):
    PRESENT = "PRESENT"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    SOURCE_MISSING = "SOURCE_MISSING"
    PERMISSION_OR_ENTITLEMENT_UNVERIFIED = "PERMISSION_OR_ENTITLEMENT_UNVERIFIED"
    MARKET_NOT_OPEN = "MARKET_NOT_OPEN"
    STALE = "STALE"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"


class CapabilityEvidenceClass(str, Enum):
    OFFICIAL_DOCUMENTED = "OFFICIAL_DOCUMENTED"
    LOCAL_RUNTIME_VERIFIED = "LOCAL_RUNTIME_VERIFIED"
    LOCAL_RUNTIME_NOT_VERIFIED = "LOCAL_RUNTIME_NOT_VERIFIED"
    ENTITLEMENT_UNVERIFIED = "ENTITLEMENT_UNVERIFIED"
    OBSERVED_UNSUPPORTED = "OBSERVED_UNSUPPORTED"
    STALE_REVALIDATION_REQUIRED = "STALE_REVALIDATION_REQUIRED"
    UNKNOWN = "UNKNOWN"


class DriftKind(str, Enum):
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    SEMANTIC_DRIFT = "SEMANTIC_DRIFT"
    UNIT_DRIFT = "UNIT_DRIFT"
    DIRECTION_DRIFT = "DIRECTION_DRIFT"
    PRECISION_DRIFT = "PRECISION_DRIFT"
    ENUM_DRIFT = "ENUM_DRIFT"
    TIME_SEMANTIC_DRIFT = "TIME_SEMANTIC_DRIFT"
    ADJUSTMENT_DRIFT = "ADJUSTMENT_DRIFT"
    MISSINGNESS_DRIFT = "MISSINGNESS_DRIFT"
    VENDOR_VERSION_DRIFT = "VENDOR_VERSION_DRIFT"
    ENTITLEMENT_OR_CAPABILITY_DRIFT = "ENTITLEMENT_OR_CAPABILITY_DRIFT"


class TimeSemantic(str, Enum):
    EVENT_TIME = "EVENT_TIME"
    EXCHANGE_TIME = "EXCHANGE_TIME"
    PUBLISHED_AT = "PUBLISHED_AT"
    AVAILABLE_AT = "AVAILABLE_AT"
    INGESTED_AT = "INGESTED_AT"


class PriceSemantic(str, Enum):
    RAW_TRADE_PRICE = "RAW_TRADE_PRICE"
    QUOTE_PRICE = "QUOTE_PRICE"
    REFERENCE_PRICE = "REFERENCE_PRICE"
    ADJUSTED_PRICE = "ADJUSTED_PRICE"
    DISPLAY_PRICE = "DISPLAY_PRICE"


def parse_fixed_decimal(value: Any, *, path: str = "/value") -> Decimal:
    """Parse a canonical decimal without silently accepting binary floats."""
    if isinstance(value, bool) or isinstance(value, float):
        raise SemanticValidationError("BINARY_FLOAT_FORBIDDEN", path)
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        if not value.strip():
            raise SemanticValidationError("DECIMAL_STRING_EMPTY", path)
        try:
            result = Decimal(value)
        except InvalidOperation as exc:
            raise SemanticValidationError("DECIMAL_INVALID", path) from exc
    else:
        raise SemanticValidationError("DECIMAL_TYPE_UNSUPPORTED", path)
    if not result.is_finite():
        raise SemanticValidationError("DECIMAL_NON_FINITE", path)
    return result


def _parse_optional_decimal(value: Any, path: str) -> Decimal | None:
    if value is None:
        return None
    return parse_fixed_decimal(value, path=path)


def _parse_timestamp(value: str, path: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SemanticValidationError("TIMESTAMP_REQUIRED", path)
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise SemanticValidationError("TIMESTAMP_INVALID", path) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SemanticValidationError("TIMEZONE_REQUIRED", path)
    return parsed


def _require_digest(value: str, *, path: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise SemanticValidationError("DIGEST_REQUIRED", path)
    try:
        int(value, 16)
    except ValueError as exc:
        raise SemanticValidationError("DIGEST_INVALID", path) from exc
    if value.lower() != value:
        raise SemanticValidationError("DIGEST_NOT_CANONICAL_LOWERCASE", path)
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    return value


def semantic_identity_digest_from_mapping(values: Mapping[str, Any]) -> str:
    """Integrity digest only. It is not authority until registry-bound."""
    payload = {name: _jsonable(values.get(name)) for name in _SEMANTIC_IDENTITY_FIELDS}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MarketSemanticFieldSpec:
    semantic_field_id: str
    semantic_version: str
    source_system: str
    source_version: str
    source_field_name: str
    canonical_field_ref: str
    primitive_type: str
    unit_kind: str
    unit_symbol: str
    unit_scale: Decimal | str | int = Decimal("1")
    fixed_scale: Decimal | str | int | None = None
    tick_size: Decimal | str | int | None = None
    tick_size_ref: str | None = None
    rounding_policy: str = "EXACT_NO_IMPLICIT_ROUNDING"
    price_semantic: PriceSemantic | None = None
    time_semantic: TimeSemantic | None = None
    adjustment_state: str = "NOT_APPLICABLE"
    source_enum_map: Mapping[str, str] = field(default_factory=dict)
    allowed_missing_states: tuple[MissingState, ...] = tuple(MissingState)
    canonical_persistable: bool = True
    valid_from: str | None = None
    valid_until: str | None = None
    source_ref: str = ""
    evidence_ref: str = ""
    schema_digest: str = ""
    semantic_digest: str = ""
    observed_at: str = ""
    last_verified_at: str = ""

    def __post_init__(self) -> None:
        required = {
            "semantic_field_id": self.semantic_field_id,
            "semantic_version": self.semantic_version,
            "source_system": self.source_system,
            "source_version": self.source_version,
            "source_field_name": self.source_field_name,
            "canonical_field_ref": self.canonical_field_ref,
            "primitive_type": self.primitive_type,
            "unit_kind": self.unit_kind,
            "unit_symbol": self.unit_symbol,
            "source_ref": self.source_ref,
            "evidence_ref": self.evidence_ref,
        }
        for name, value in required.items():
            if not isinstance(value, str) or not value.strip():
                raise SemanticValidationError("FIELD_IDENTITY_REQUIRED", f"/{name}")

        if self.schema_digest != MARKET_SEMANTIC_FIELD_SCHEMA_DIGEST_V1:
            raise SemanticValidationError("SCHEMA_DIGEST_MISMATCH", "/schema_digest")
        _require_digest(self.semantic_digest, path="/semantic_digest")
        _parse_timestamp(self.observed_at, "/observed_at")
        _parse_timestamp(self.last_verified_at, "/last_verified_at")

        unit_scale = parse_fixed_decimal(self.unit_scale, path="/unit_scale")
        fixed_scale = _parse_optional_decimal(self.fixed_scale, "/fixed_scale")
        tick_size = _parse_optional_decimal(self.tick_size, "/tick_size")
        if unit_scale <= 0:
            raise SemanticValidationError("UNIT_SCALE_MUST_BE_POSITIVE", "/unit_scale")
        if fixed_scale is not None and fixed_scale <= 0:
            raise SemanticValidationError("FIXED_SCALE_MUST_BE_POSITIVE", "/fixed_scale")
        if tick_size is not None and tick_size <= 0:
            raise SemanticValidationError("TICK_SIZE_MUST_BE_POSITIVE", "/tick_size")
        if tick_size is None and self.tick_size_ref is not None and not self.tick_size_ref.strip():
            raise SemanticValidationError("TICK_SIZE_REF_INVALID", "/tick_size_ref")
        object.__setattr__(self, "unit_scale", unit_scale)
        object.__setattr__(self, "fixed_scale", fixed_scale)
        object.__setattr__(self, "tick_size", tick_size)

        enum_map: dict[str, str] = {}
        for raw, canonical in dict(self.source_enum_map).items():
            if not isinstance(raw, str):
                raise SemanticValidationError("ENUM_RAW_KEY_MUST_BE_STRING", "/source_enum_map")
            try:
                enum_map[raw] = CanonicalDirection(canonical).value
            except ValueError as exc:
                raise SemanticValidationError(
                    "CANONICAL_DIRECTION_INVALID", f"/source_enum_map/{raw}"
                ) from exc
        object.__setattr__(self, "source_enum_map", MappingProxyType(enum_map))

        missing_states: list[MissingState] = []
        for item in self.allowed_missing_states:
            try:
                missing_states.append(item if isinstance(item, MissingState) else MissingState(item))
            except ValueError as exc:
                raise SemanticValidationError("MISSING_STATE_INVALID", "/allowed_missing_states") from exc
        if not missing_states:
            raise SemanticValidationError("MISSING_STATES_EMPTY", "/allowed_missing_states")
        object.__setattr__(self, "allowed_missing_states", tuple(missing_states))

        if self.price_semantic is not None and not isinstance(self.price_semantic, PriceSemantic):
            object.__setattr__(self, "price_semantic", PriceSemantic(self.price_semantic))
        if self.time_semantic is not None and not isinstance(self.time_semantic, TimeSemantic):
            object.__setattr__(self, "time_semantic", TimeSemantic(self.time_semantic))
        if self.price_semantic == PriceSemantic.DISPLAY_PRICE and self.canonical_persistable:
            raise SemanticValidationError(
                "DISPLAY_PRICE_CANNOT_BE_CANONICAL", "/canonical_persistable"
            )
        if self.price_semantic is not None and self.time_semantic is not None:
            raise SemanticValidationError("FIELD_ROLE_AMBIGUOUS", "/")
        for path, value in (("/valid_from", self.valid_from), ("/valid_until", self.valid_until)):
            if value is not None:
                _parse_timestamp(value, path)

        actual_digest = semantic_digest(self)
        if self.semantic_digest != actual_digest:
            raise SemanticValidationError(
                "SEMANTIC_DIGEST_CONTENT_MISMATCH", "/semantic_digest"
            )


def semantic_digest(spec: MarketSemanticFieldSpec) -> str:
    payload = {name: getattr(spec, name) for name in _SEMANTIC_IDENTITY_FIELDS}
    return semantic_identity_digest_from_mapping(payload)


def semantic_registry_key(spec: MarketSemanticFieldSpec) -> tuple[str, str, str, str]:
    return (
        spec.source_system,
        spec.source_version,
        spec.source_field_name,
        spec.semantic_field_id,
    )


def require_governed_semantic_spec(spec: MarketSemanticFieldSpec) -> MarketSemanticFieldSpec:
    """Prove that the spec is the exact governed semantic identity for v1."""
    expected = GOVERNED_SEMANTIC_DIGESTS_V1.get(semantic_registry_key(spec))
    if expected is None:
        raise SemanticValidationError(
            "SEMANTIC_REGISTRY_BINDING_REQUIRED", "/semantic_registry"
        )
    if spec.semantic_digest != expected:
        raise SemanticValidationError(
            "SEMANTIC_REGISTRY_DIGEST_MISMATCH", "/semantic_digest"
        )
    if semantic_digest(spec) != expected:
        raise SemanticValidationError(
            "SEMANTIC_REGISTRY_CONTENT_MISMATCH", "/semantic_digest"
        )
    return spec


@dataclass(frozen=True)
class ProviderCapabilityObservation:
    observation_id: str
    provider: str
    product: str
    capability_id: str
    method: str
    evidence_class: CapabilityEvidenceClass
    observed_at: str
    local_runtime_observed: bool
    documented_fields: tuple[str, ...] = ()
    observed_fields: tuple[str, ...] = ()
    documentation_version: str | None = None
    runtime_version: str | None = None
    entitlement_state: str = "UNKNOWN"
    semantic_field_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    next_verification_action: str = ""

    def __post_init__(self) -> None:
        for name in ("observation_id", "provider", "product", "capability_id", "method"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise SemanticValidationError("CAPABILITY_IDENTITY_REQUIRED", f"/{name}")
        evidence_class = (
            self.evidence_class
            if isinstance(self.evidence_class, CapabilityEvidenceClass)
            else CapabilityEvidenceClass(self.evidence_class)
        )
        object.__setattr__(self, "evidence_class", evidence_class)
        _parse_timestamp(self.observed_at, "/observed_at")

        # R182 is GitHub-only and is not a local runtime/entitlement observer.
        # LOCAL_RUNTIME_VERIFIED is reserved in the taxonomy for a future separately
        # governed external verifier/receipt contract. No caller-authored fields or
        # string prefixes can mint that state here.
        if evidence_class == CapabilityEvidenceClass.LOCAL_RUNTIME_VERIFIED:
            raise SemanticValidationError(
                "EXTERNAL_LOCAL_RUNTIME_AUTHORITY_REQUIRED", "/evidence_class"
            )

        if evidence_class == CapabilityEvidenceClass.OFFICIAL_DOCUMENTED:
            if self.local_runtime_observed:
                raise SemanticValidationError(
                    "DOCUMENTATION_OBSERVATION_CANNOT_CLAIM_LOCAL_RUNTIME",
                    "/local_runtime_observed",
                )
            if not self.documentation_version:
                raise SemanticValidationError(
                    "DOCUMENTATION_VERSION_REQUIRED", "/documentation_version"
                )
            if not self.documented_fields:
                raise SemanticValidationError(
                    "DOCUMENTED_FIELDS_REQUIRED", "/documented_fields"
                )


def map_direction(raw_value: Any, spec: MarketSemanticFieldSpec) -> CanonicalDirection:
    # Direction semantics are authority-bearing. The normal consuming path always
    # proves registry identity before using the enum map.
    require_governed_semantic_spec(spec)
    if spec.primitive_type != "ENUM_STRING":
        raise SemanticValidationError("DIRECTION_SPEC_TYPE_INVALID", "/primitive_type")
    if raw_value is None:
        raise SemanticValidationError("DIRECTION_MISSING", "/direction")
    raw = str(raw_value)
    if raw not in spec.source_enum_map:
        raise SemanticValidationError("ENUM_VALUE_UNMAPPED", f"/source_enum_map/{raw}")
    return CanonicalDirection(spec.source_enum_map[raw])


def assert_direction_contract(
    spec: MarketSemanticFieldSpec,
    expected_map: Mapping[str, CanonicalDirection | str] | None = None,
) -> None:
    # Retained compatibility helper. The caller-supplied expected map is never the
    # authority: governed registry identity is checked first.
    require_governed_semantic_spec(spec)
    if expected_map is None:
        return
    expected = {
        str(key): (
            value.value if isinstance(value, CanonicalDirection)
            else CanonicalDirection(value).value
        )
        for key, value in expected_map.items()
    }
    if dict(spec.source_enum_map) != expected:
        raise SemanticValidationError("DIRECTION_CONTRACT_MISMATCH", "/source_enum_map")


def classify_value(value: Any, state: MissingState | str) -> tuple[Any, MissingState]:
    state = state if isinstance(state, MissingState) else MissingState(state)
    if state == MissingState.PRESENT:
        if value is None:
            raise SemanticValidationError("PRESENT_VALUE_REQUIRED", "/value")
        return value, state
    if value is not None:
        raise SemanticValidationError("MISSING_STATE_REQUIRES_NULL_VALUE", "/value")
    return None, state


def require_point_in_time(values: Mapping[str, Any]) -> datetime:
    if "available_at" not in values or values["available_at"] in (None, ""):
        raise SemanticValidationError("AVAILABLE_AT_REQUIRED", "/available_at")
    return _parse_timestamp(values["available_at"], "/available_at")


def validate_tick_aligned(value: Any, spec: MarketSemanticFieldSpec) -> Decimal:
    if spec.price_semantic == PriceSemantic.DISPLAY_PRICE or not spec.canonical_persistable:
        raise SemanticValidationError("NON_CANONICAL_PRICE_SEMANTIC", "/price_semantic")
    price = parse_fixed_decimal(value, path="/price")
    if spec.tick_size is None:
        if spec.tick_size_ref:
            raise SemanticValidationError("TICK_SIZE_RULE_RESOLUTION_REQUIRED", "/tick_size_ref")
        return price
    quotient = price / spec.tick_size
    if quotient != quotient.to_integral_value():
        raise SemanticValidationError("PRICE_NOT_TICK_ALIGNED", "/price")
    return price


def validate_governed_tick_aligned(value: Any, spec: MarketSemanticFieldSpec) -> Decimal:
    require_governed_semantic_spec(spec)
    return validate_tick_aligned(value, spec)


@dataclass(frozen=True)
class TickNormalization:
    original: Decimal
    normalized: Decimal
    tick_size: Decimal
    policy: str


def normalize_to_tick(
    value: Any, tick_size: Any, *, policy: str = "ROUND_HALF_EVEN_EXPLICIT"
) -> TickNormalization:
    original = parse_fixed_decimal(value, path="/price")
    tick = parse_fixed_decimal(tick_size, path="/tick_size")
    if tick <= 0:
        raise SemanticValidationError("TICK_SIZE_MUST_BE_POSITIVE", "/tick_size")
    if policy != "ROUND_HALF_EVEN_EXPLICIT":
        raise SemanticValidationError("NORMALIZATION_POLICY_UNSUPPORTED", "/policy")
    normalized = (original / tick).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN) * tick
    return TickNormalization(original, normalized, tick, policy)


def explicit_unit_convert(
    value: Any, *, from_unit: str, to_unit: str, factor: Any | None
) -> Decimal:
    if not from_unit or not to_unit:
        raise SemanticValidationError("UNIT_REQUIRED", "/unit")
    amount = parse_fixed_decimal(value, path="/value")
    if from_unit == to_unit:
        if factor not in (None, "1", 1, Decimal("1")):
            raise SemanticValidationError("IDENTICAL_UNIT_FACTOR_INVALID", "/factor")
        return amount
    if factor is None:
        raise SemanticValidationError("EXPLICIT_CONVERSION_FACTOR_REQUIRED", "/factor")
    conversion = parse_fixed_decimal(factor, path="/factor")
    if conversion <= 0:
        raise SemanticValidationError("CONVERSION_FACTOR_MUST_BE_POSITIVE", "/factor")
    return amount * conversion


def capability_digest(observation: ProviderCapabilityObservation) -> str:
    payload = _jsonable(asdict(observation))
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def append_capability_observation(
    history: Sequence[ProviderCapabilityObservation],
    observation: ProviderCapabilityObservation,
) -> tuple[ProviderCapabilityObservation, ...]:
    out = list(history)
    for existing in out:
        if existing.observation_id == observation.observation_id:
            if capability_digest(existing) == capability_digest(observation):
                return tuple(out)
            raise SemanticValidationError(
                "CAPABILITY_OBSERVATION_IMMUTABLE", f"/history/{observation.observation_id}"
            )
    out.append(observation)
    return tuple(out)


def require_capability(
    observation: ProviderCapabilityObservation, *, require_local_runtime: bool
) -> ProviderCapabilityObservation:
    if require_local_runtime:
        # v1 cannot create LOCAL_RUNTIME_VERIFIED at all. This branch remains
        # explicit so callers cannot confuse documentation/unverified evidence
        # with a local capability.
        if observation.evidence_class != CapabilityEvidenceClass.LOCAL_RUNTIME_VERIFIED:
            raise SemanticValidationError(
                "LOCAL_RUNTIME_CAPABILITY_NOT_VERIFIED", "/evidence_class"
            )
        raise SemanticValidationError(
            "EXTERNAL_LOCAL_RUNTIME_AUTHORITY_REQUIRED", "/evidence_class"
        )
    return observation


def detect_field_drift(
    old: MarketSemanticFieldSpec, new: MarketSemanticFieldSpec
) -> tuple[DriftKind, ...]:
    drift: set[DriftKind] = set()
    if old.source_field_name != new.source_field_name:
        drift.add(DriftKind.SCHEMA_DRIFT)
    if old.source_version != new.source_version:
        drift.add(DriftKind.VENDOR_VERSION_DRIFT)
    if (
        old.semantic_field_id != new.semantic_field_id
        or old.canonical_field_ref != new.canonical_field_ref
        or old.primitive_type != new.primitive_type
        or old.price_semantic != new.price_semantic
        or old.canonical_persistable != new.canonical_persistable
        or old.source_ref != new.source_ref
        or old.schema_digest != new.schema_digest
        or old.semantic_digest != new.semantic_digest
    ):
        drift.add(DriftKind.SEMANTIC_DRIFT)
    if (
        old.unit_kind != new.unit_kind
        or old.unit_symbol != new.unit_symbol
        or old.unit_scale != new.unit_scale
    ):
        drift.add(DriftKind.UNIT_DRIFT)
    if old.source_enum_map != new.source_enum_map:
        drift.add(DriftKind.ENUM_DRIFT)
        drift.add(DriftKind.DIRECTION_DRIFT)
    if (
        old.fixed_scale != new.fixed_scale
        or old.tick_size != new.tick_size
        or old.tick_size_ref != new.tick_size_ref
        or old.rounding_policy != new.rounding_policy
    ):
        drift.add(DriftKind.PRECISION_DRIFT)
    if old.time_semantic != new.time_semantic:
        drift.add(DriftKind.TIME_SEMANTIC_DRIFT)
    if old.adjustment_state != new.adjustment_state:
        drift.add(DriftKind.ADJUSTMENT_DRIFT)
    if old.allowed_missing_states != new.allowed_missing_states:
        drift.add(DriftKind.MISSINGNESS_DRIFT)
    return tuple(sorted(drift, key=lambda item: item.value))


def detect_capability_drift(
    old: ProviderCapabilityObservation, new: ProviderCapabilityObservation
) -> tuple[DriftKind, ...]:
    drift: set[DriftKind] = set()
    if old.provider != new.provider or old.product != new.product or old.capability_id != new.capability_id:
        drift.add(DriftKind.SEMANTIC_DRIFT)
    if old.method != new.method:
        drift.add(DriftKind.SCHEMA_DRIFT)
    if old.documentation_version != new.documentation_version or old.runtime_version != new.runtime_version:
        drift.add(DriftKind.VENDOR_VERSION_DRIFT)
    if (
        old.evidence_class != new.evidence_class
        or old.entitlement_state != new.entitlement_state
        or old.local_runtime_observed != new.local_runtime_observed
        or old.observed_fields != new.observed_fields
    ):
        drift.add(DriftKind.ENTITLEMENT_OR_CAPABILITY_DRIFT)
    return tuple(sorted(drift, key=lambda item: item.value))
