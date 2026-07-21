"""Strict, read-only TDX .day structural parser and manifest-bound adapter."""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from local_adapter.contracts import (
    AdapterResult,
    AdapterStatus,
    ContractError,
    ManifestValidator,
    SourceManifest,
    canonical_hash,
)

from .contracts import (
    ParseIssue,
    ParseReport,
    SourceActivationPolicy,
    TdxDayRawRecord,
    field_semantic_decisions,
)


RECORD_WIDTH = 32
_RECORD = struct.Struct("<IIIII4sII")


@dataclass(frozen=True)
class ParsedDayDataset:
    records: tuple[TdxDayRawRecord, ...]
    report: ParseReport


class TdxDayParser:
    """Parses bytes without assigning authority to ambiguous vendor fields."""

    def parse_bytes(
        self,
        payload: bytes,
        *,
        manifest_id: str,
        policy_id: str,
        artifact_sha256: str,
        requested_as_of_date: date,
        field_semantics_version: str = "tdx-day-partial-v1",
    ) -> ParsedDayDataset:
        issues: list[ParseIssue] = []
        if len(payload) % RECORD_WIDTH:
            issues.append(ParseIssue("TRUNCATED_RECORD", None, f"size={len(payload)}", "REJECTED"))
            return ParsedDayDataset((), self._report(
                payload, manifest_id, policy_id, artifact_sha256, (), issues,
                field_semantics_version, source_record_count=len(payload) // RECORD_WIDTH,
            ))

        accepted: list[TdxDayRawRecord] = []
        all_dates: list[str] = []
        duplicate_dates = 0
        out_of_order = 0
        nonzero_reserved = 0
        amount_float_candidates = 0
        amount_float_invalid = 0
        zero_volume = 0
        seen_dates: set[str] = set()
        previous_date: str | None = None

        for index in range(len(payload) // RECORD_WIDTH):
            offset = index * RECORD_WIDTH
            chunk = payload[offset:offset + RECORD_WIDTH]
            date_raw, open_raw, high_raw, low_raw, close_raw, amount_raw, volume_raw, reserved_raw = _RECORD.unpack(chunk)
            trade_date = self._parse_date(date_raw)
            if trade_date is None:
                issues.append(ParseIssue("INVALID_DATE", index, str(date_raw)))
                continue
            if trade_date > requested_as_of_date:
                issues.append(ParseIssue("FUTURE_DATE", index, trade_date.isoformat()))
                continue

            day_text = trade_date.isoformat()
            all_dates.append(day_text)
            if day_text in seen_dates:
                duplicate_dates += 1
                issues.append(ParseIssue("DUPLICATE_DATE", index, day_text))
                continue
            if previous_date is not None and day_text < previous_date:
                out_of_order += 1
                issues.append(ParseIssue("OUT_OF_ORDER_DATE", index, day_text))
            seen_dates.add(day_text)
            previous_date = day_text

            prices = tuple(value / 100.0 for value in (open_raw, high_raw, low_raw, close_raw))
            if any(value <= 0 for value in prices):
                issues.append(ParseIssue("NON_POSITIVE_PRICE", index, repr(prices)))
                continue
            open_price, high_price, low_price, close_price = prices
            if not (low_price <= open_price <= high_price and low_price <= close_price <= high_price):
                issues.append(ParseIssue("INVALID_OHLC", index, repr(prices)))
                continue

            amount_float = struct.unpack("<f", amount_raw)[0]
            amount_float_candidate = amount_float if math.isfinite(amount_float) and amount_float >= 0 else None
            if amount_float_candidate is None:
                amount_float_invalid += 1
            else:
                amount_float_candidates += 1
            amount_uint = struct.unpack("<I", amount_raw)[0]
            if reserved_raw:
                nonzero_reserved += 1
            if volume_raw == 0:
                zero_volume += 1
            accepted.append(TdxDayRawRecord(
                record_index=index,
                byte_offset=offset,
                trade_date=day_text,
                date_raw=date_raw,
                open_raw=open_raw,
                high_raw=high_raw,
                low_raw=low_raw,
                close_raw=close_raw,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                amount_raw_hex=amount_raw.hex(),
                amount_float32_candidate=amount_float_candidate,
                amount_uint32_candidate=amount_uint,
                volume_vendor_raw=volume_raw,
                reserved_vendor_raw=reserved_raw,
            ))

        report = self._report(
            payload, manifest_id, policy_id, artifact_sha256, tuple(accepted), issues,
            field_semantics_version, source_record_count=len(payload) // RECORD_WIDTH,
            duplicate_date_count=duplicate_dates, out_of_order_count=out_of_order,
            nonzero_reserved_count=nonzero_reserved,
            amount_float_candidate_count=amount_float_candidates,
            amount_float_invalid_count=amount_float_invalid,
            zero_volume_count=zero_volume,
        )
        return ParsedDayDataset(tuple(accepted), report)

    @staticmethod
    def _parse_date(raw: int) -> date | None:
        text = str(raw)
        if len(text) != 8:
            return None
        try:
            return datetime.strptime(text, "%Y%m%d").date()
        except ValueError:
            return None

    @staticmethod
    def _report(
        payload: bytes,
        manifest_id: str,
        policy_id: str,
        artifact_sha256: str,
        records: tuple[TdxDayRawRecord, ...],
        issues: list[ParseIssue],
        field_semantics_version: str,
        *,
        source_record_count: int,
        duplicate_date_count: int = 0,
        out_of_order_count: int = 0,
        nonzero_reserved_count: int = 0,
        amount_float_candidate_count: int = 0,
        amount_float_invalid_count: int = 0,
        zero_volume_count: int = 0,
    ) -> ParseReport:
        hard_reject = any(item.disposition == "REJECTED" for item in issues)
        stable_records = [item.stable_payload() for item in records]
        report = ParseReport(
            schema_version="1.0.0",
            status="REJECTED" if hard_reject else "PARTIALLY_VERIFIED",
            source_manifest_id=manifest_id,
            activation_policy_id=policy_id,
            artifact_sha256=artifact_sha256,
            artifact_size=len(payload),
            record_width=RECORD_WIDTH,
            source_record_count=source_record_count,
            accepted_record_count=len(records),
            quarantined_record_count=len(issues),
            first_date=min((record.trade_date for record in records), default=None),
            last_date=max((record.trade_date for record in records), default=None),
            duplicate_date_count=duplicate_date_count,
            out_of_order_count=out_of_order_count,
            nonzero_reserved_count=nonzero_reserved_count,
            amount_float_candidate_count=amount_float_candidate_count,
            amount_float_invalid_count=amount_float_invalid_count,
            zero_volume_count=zero_volume_count,
            parse_core_hash=canonical_hash(stable_records),
            field_semantics_version=field_semantics_version,
            field_decisions=field_semantic_decisions(),
            issues=tuple(issues),
        )
        report.validate()
        return report


class TdxDaySourceAdapter:
    """Allows one hash-bound local file to pass the narrower research gate."""

    _OVERRIDABLE_GATE_STATUSES = {
        AdapterStatus.BLOCKED_BY_POLICY,
        AdapterStatus.LEGACY_UNKNOWN,
        AdapterStatus.PARTIALLY_VERIFIED,
    }

    def __init__(self, artifact_path: Path, policy: SourceActivationPolicy) -> None:
        self.artifact_path = artifact_path
        self.policy = policy
        self.parser = TdxDayParser()

    def load_parsed(self, manifest: SourceManifest, requested_as_of: str) -> ParsedDayDataset:
        self.policy.validate()
        if self.policy.manifest_id != manifest.manifest_id:
            raise ContractError("activation_manifest_mismatch")
        if self.policy.artifact_sha256 != manifest.artifact.sha256:
            raise ContractError("activation_manifest_hash_mismatch")
        if manifest.synthetic:
            raise ContractError("real_local_activation_cannot_target_synthetic")
        if manifest.capability.capability_level != "HISTORICAL_BAR":
            raise ContractError("activation_capability_not_historical_bar")
        gate = ManifestValidator().validate(manifest, requested_as_of)
        if gate.status not in self._OVERRIDABLE_GATE_STATUSES:
            raise ContractError(f"manifest_gate_not_eligible:{gate.status.value}")
        if not self.artifact_path.is_file() or self.artifact_path.suffix.lower() != ".day":
            raise ContractError("day_artifact_not_found_or_wrong_suffix")
        payload = self.artifact_path.read_bytes()
        actual_hash = hashlib.sha256(payload).hexdigest()
        if actual_hash != self.policy.artifact_sha256:
            raise ContractError("artifact_hash_mismatch")
        requested = datetime.fromisoformat(requested_as_of.replace("Z", "+00:00")).date()
        return self.parser.parse_bytes(
            payload,
            manifest_id=manifest.manifest_id,
            policy_id=self.policy.policy_id,
            artifact_sha256=actual_hash,
            requested_as_of_date=requested,
            field_semantics_version=manifest.field_semantics_version,
        )

    def load(self, manifest: SourceManifest, requested_as_of: str) -> AdapterResult:
        try:
            parsed = self.load_parsed(manifest, requested_as_of)
        except (ContractError, OSError, ValueError) as error:
            return AdapterResult(AdapterStatus.REJECTED, (str(error),))
        status = AdapterStatus.PARTIALLY_VERIFIED if parsed.report.status == "PARTIALLY_VERIFIED" else AdapterStatus.REJECTED
        return AdapterResult(
            status,
            reason_codes=("partial_field_evidence",),
            remediation_hints=("do_not_promote_ambiguous_fields_or_source_authority",),
            payload=parsed.report.public_receipt(),
        )


def aggregate_record_hash(records: Iterable[TdxDayRawRecord]) -> str:
    return canonical_hash([asdict(record) for record in records])
