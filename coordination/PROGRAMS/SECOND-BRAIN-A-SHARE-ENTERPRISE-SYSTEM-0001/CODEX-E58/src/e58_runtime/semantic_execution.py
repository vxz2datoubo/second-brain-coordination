"""Execution-derived semantic records for E58 public-safe synthetic fixtures.

This is deliberately a task-local capability boundary, not a production trust
service. A trusted runtime owns an ephemeral signing key and an issuance ledger;
ordinary consumers receive only a verifier capability pinned to that runtime.
Callers can construct look-alike values, but they cannot make the pinned verifier
accept them without a matching execution and ledger entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import hmac
import json
import re
from secrets import token_bytes
from types import MappingProxyType
from typing import Any, Callable, Mapping


class SemanticExecutionError(ValueError):
    """A semantic record lacks the execution evidence required by E58."""


class JsonlOwnershipError(SemanticExecutionError):
    """A JSONL byte stream cannot be owned deterministically and completely."""

    def __init__(self, code: str, offset: int | None = None) -> None:
        self.code = code
        self.offset = offset
        suffix = "" if offset is None else f" at byte offset {offset}"
        super().__init__(f"{code}{suffix}")


def _normalise_public_json(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _normalise_public_json(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, tuple | list):
        return [_normalise_public_json(item) for item in value]
    raise SemanticExecutionError("canonical public JSON value is unsupported")


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(_normalise_public_json(value), ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise SemanticExecutionError("canonical public JSON encoding failed") from exc


def _digest(value: object) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _canonical_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise SemanticExecutionError(f"{field} must be a nonempty string")
    return normalized


class Polarity(str, Enum):
    AFFIRM = "AFFIRM"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class Proposition:
    subject: str
    predicate: str
    object_value: str
    polarity: Polarity
    scope: str
    time_window: str

    def __post_init__(self) -> None:
        for field in ("subject", "predicate", "object_value", "scope", "time_window"):
            object.__setattr__(self, field, _canonical_text(getattr(self, field), field))
        if not isinstance(self.polarity, Polarity):
            raise SemanticExecutionError("polarity must be a Polarity")

    @property
    def semantic_key(self) -> str:
        return _digest(
            {
                "subject": self.subject,
                "predicate": self.predicate,
                "object_value": self.object_value,
                "scope": self.scope,
                "time_window": self.time_window,
            }
        )

    @property
    def proposition_id(self) -> str:
        return _digest({"semantic_key": self.semantic_key, "polarity": self.polarity.value})

    def opposes(self, other: "Proposition") -> bool:
        return self.semantic_key == other.semantic_key and self.polarity is not other.polarity


@dataclass(frozen=True, slots=True)
class EvidenceStatement:
    source_id: str
    proposition: Proposition
    excerpt: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _canonical_text(self.source_id, "source_id"))
        object.__setattr__(self, "excerpt", _canonical_text(self.excerpt, "excerpt"))

    @property
    def evidence_id(self) -> str:
        return _digest(
            {
                "source_id": self.source_id,
                "proposition_id": self.proposition.proposition_id,
                "excerpt_sha256": sha256(self.excerpt.encode("utf-8")).hexdigest(),
            }
        )

    @property
    def input_digest(self) -> str:
        return _digest(
            {
                "evidence_id": self.evidence_id,
                "source_id": self.source_id,
                "proposition_id": self.proposition.proposition_id,
            }
        )


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    capability_id: str
    evaluator_id: str
    rule_id: str
    rule_version: str
    input_digest: str
    run_id: str
    outcome: str
    output_digest: str
    transcript_digest: str
    attestation: str

    @property
    def receipt_id(self) -> str:
        return _digest(self.claim())

    def claim(self) -> Mapping[str, str]:
        return MappingProxyType(
            {
                "capability_id": self.capability_id,
                "evaluator_id": self.evaluator_id,
                "rule_id": self.rule_id,
                "rule_version": self.rule_version,
                "input_digest": self.input_digest,
                "run_id": self.run_id,
                "outcome": self.outcome,
                "output_digest": self.output_digest,
                "transcript_digest": self.transcript_digest,
            }
        )


@dataclass(frozen=True, slots=True)
class IssuedPacket:
    capability_id: str
    packet_type: str
    packet_id: str
    payload_json: str
    attestation: str

    def payload(self) -> Mapping[str, Any]:
        try:
            decoded = json.loads(self.payload_json)
        except json.JSONDecodeError as exc:  # defensive; trusted kernel emits canonical JSON
            raise SemanticExecutionError("issued packet payload is malformed") from exc
        if not isinstance(decoded, dict):
            raise SemanticExecutionError("issued packet payload must be an object")
        return MappingProxyType(decoded)

    def claim(self) -> Mapping[str, str]:
        return MappingProxyType(
            {
                "capability_id": self.capability_id,
                "packet_type": self.packet_type,
                "packet_id": self.packet_id,
                "payload_json": self.payload_json,
            }
        )


@dataclass(frozen=True, slots=True)
class SemanticAtom:
    atom_id: str
    evidence: EvidenceStatement
    validation_receipt: ExecutionReceipt


@dataclass(frozen=True, slots=True)
class PolicyRef:
    policy_id: str
    version: str


@dataclass(frozen=True, slots=True)
class ByteRange:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise SemanticExecutionError("byte range must have nonempty nonnegative bounds")


class SegmentKind(str, Enum):
    JSON_RECORD = "JSON_RECORD"
    BLANK_LINE = "BLANK_LINE"
    LINE_TERMINATOR = "LINE_TERMINATOR"


@dataclass(frozen=True, slots=True)
class OwnedByteSegment:
    kind: SegmentKind
    raw: ByteRange
    line_index: int


@dataclass(frozen=True, slots=True)
class JsonlOwnership:
    source_sha256: str
    byte_length: int
    segments: tuple[OwnedByteSegment, ...]
    record_count: int
    status: str

    @property
    def digest(self) -> str:
        return _digest(
            {
                "source_sha256": self.source_sha256,
                "byte_length": self.byte_length,
                "record_count": self.record_count,
                "status": self.status,
                "segments": [
                    {"kind": segment.kind.value, "start": segment.raw.start, "end": segment.raw.end, "line": segment.line_index}
                    for segment in self.segments
                ],
            }
        )

    def assert_complete_partition(self) -> None:
        cursor = 0
        for segment in self.segments:
            if segment.raw.start != cursor:
                raise JsonlOwnershipError("JSONL_PARTITION_GAP_OR_OVERLAP", cursor)
            cursor = segment.raw.end
        if cursor != self.byte_length:
            raise JsonlOwnershipError("JSONL_PARTITION_INCOMPLETE", cursor)


class _AuthorityKernel:
    """Private in-memory issuance ledger, intentionally not exported as API."""

    def __init__(self) -> None:
        self.capability_id = "e58.semantic.execution.verifier.v1"
        self._key = token_bytes(32)
        self._receipts: dict[str, Mapping[str, str]] = {}
        self._packets: dict[str, Mapping[str, str]] = {}

    def _sign(self, claim: Mapping[str, str]) -> str:
        return hmac.new(self._key, _canonical_bytes(dict(claim)), "sha256").hexdigest()

    def issue_execution(
        self,
        *,
        evaluator_id: str,
        rule_id: str,
        rule_version: str,
        input_digest: str,
        outcome: str,
        output: Mapping[str, object],
    ) -> ExecutionReceipt:
        output_digest = _digest(dict(output))
        transcript = {
            "evaluator_id": evaluator_id,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "input_digest": input_digest,
            "outcome": outcome,
            "output_digest": output_digest,
        }
        transcript_digest = _digest(transcript)
        run_id = _digest({"execution": transcript_digest})
        claim = {
            "capability_id": self.capability_id,
            "evaluator_id": evaluator_id,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "input_digest": input_digest,
            "run_id": run_id,
            "outcome": outcome,
            "output_digest": output_digest,
            "transcript_digest": transcript_digest,
        }
        receipt = ExecutionReceipt(attestation=self._sign(claim), **claim)
        self._receipts[receipt.receipt_id] = dict(receipt.claim())
        return receipt

    def issue_packet(self, packet_type: str, payload: Mapping[str, object]) -> IssuedPacket:
        if not packet_type:
            raise SemanticExecutionError("packet_type is required")
        payload_json = _canonical_bytes(dict(payload)).decode("ascii")
        packet_id = _digest({"capability_id": self.capability_id, "packet_type": packet_type, "payload_json": payload_json})
        claim = {
            "capability_id": self.capability_id,
            "packet_type": packet_type,
            "packet_id": packet_id,
            "payload_json": payload_json,
        }
        packet = IssuedPacket(attestation=self._sign(claim), **claim)
        self._packets[packet.packet_id] = dict(packet.claim())
        return packet

    def verify_receipt(self, receipt: object) -> bool:
        if not isinstance(receipt, ExecutionReceipt) or receipt.capability_id != self.capability_id:
            return False
        expected = self._receipts.get(receipt.receipt_id)
        return bool(expected and hmac.compare_digest(_canonical_bytes(expected), _canonical_bytes(dict(receipt.claim()))) and hmac.compare_digest(self._sign(receipt.claim()), receipt.attestation))

    def verify_packet(self, packet: object) -> bool:
        if not isinstance(packet, IssuedPacket) or packet.capability_id != self.capability_id:
            return False
        expected = self._packets.get(packet.packet_id)
        return bool(expected and hmac.compare_digest(_canonical_bytes(expected), _canonical_bytes(dict(packet.claim()))) and hmac.compare_digest(self._sign(packet.claim()), packet.attestation))


class VerifierCapability:
    """Read-only consumer capability; it exposes no issuance or registry API."""

    __slots__ = ("_kernel",)

    def __init__(self, kernel: _AuthorityKernel) -> None:
        self._kernel = kernel

    @property
    def capability_id(self) -> str:
        return self._kernel.capability_id

    def verify_execution(self, receipt: object) -> bool:
        return self._kernel.verify_receipt(receipt)

    def verify_packet(self, packet: object) -> bool:
        return self._kernel.verify_packet(packet)


class _RedactionPolicyRegistry:
    _EMAIL = PolicyRef("e58.public-safe.email-redaction", "1.0.0")
    _EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

    def resolve(self, policy: PolicyRef) -> Callable[[str], tuple[ByteRange, ...]]:
        if policy != self._EMAIL:
            raise SemanticExecutionError("redaction policy is not registered at the requested version")

        def classify(text: str) -> tuple[ByteRange, ...]:
            ranges: list[ByteRange] = []
            for match in self._EMAIL_PATTERN.finditer(text):
                start = len(text[: match.start()].encode("utf-8"))
                end = len(text[: match.end()].encode("utf-8"))
                ranges.append(ByteRange(start, end))
            return tuple(ranges)

        return classify


class TrustedSemanticExecutor:
    """Trusted command channel used by the local synthetic evaluator only."""

    _EVALUATOR = "e58.semantic.synthetic-evaluator.v1"
    _PROPOSITION_RULE = ("proposition.validation", "1.0.0")
    _RELATION_RULE = ("relation.relevance", "1.0.0")
    _POLICY_RULE = ("redaction.classification", "1.0.0")

    def __init__(self, kernel: _AuthorityKernel) -> None:
        self._kernel = kernel
        self._verifier = VerifierCapability(kernel)
        self._policies = _RedactionPolicyRegistry()

    @property
    def verifier(self) -> VerifierCapability:
        return self._verifier

    def validate_evidence(self, evidence: EvidenceStatement) -> tuple[SemanticAtom, ExecutionReceipt, IssuedPacket]:
        if not isinstance(evidence, EvidenceStatement):
            raise SemanticExecutionError("evidence must be an EvidenceStatement")
        proposition = evidence.proposition
        receipt = self._kernel.issue_execution(
            evaluator_id=self._EVALUATOR,
            rule_id=self._PROPOSITION_RULE[0],
            rule_version=self._PROPOSITION_RULE[1],
            input_digest=evidence.input_digest,
            outcome="PASS",
            output={"evidence_id": evidence.evidence_id, "proposition_id": proposition.proposition_id, "semantic_key": proposition.semantic_key},
        )
        atom = SemanticAtom(
            atom_id=_digest({"evidence_id": evidence.evidence_id, "receipt_id": receipt.receipt_id}),
            evidence=evidence,
            validation_receipt=receipt,
        )
        packet = self._kernel.issue_packet(
            "VALIDATION",
            {
                "atom_id": atom.atom_id,
                "evidence_id": evidence.evidence_id,
                "receipt_id": receipt.receipt_id,
                "input_digest": evidence.input_digest,
                "outcome": receipt.outcome,
            },
        )
        return atom, receipt, packet

    def issue_conflict(self, left: SemanticAtom, right: SemanticAtom) -> IssuedPacket:
        self._require_validated_atom(left)
        self._require_validated_atom(right)
        if left.evidence.source_id == right.evidence.source_id:
            raise SemanticExecutionError("conflict requires independently sourced validated evidence")
        if not left.evidence.proposition.opposes(right.evidence.proposition):
            raise SemanticExecutionError("conflict requires identical proposition identity with opposite polarity, scope, and time")
        return self._kernel.issue_packet(
            "CONFLICT",
            {
                "left_atom_id": left.atom_id,
                "right_atom_id": right.atom_id,
                "proposition_semantic_key": left.evidence.proposition.semantic_key,
                "left_polarity": left.evidence.proposition.polarity.value,
                "right_polarity": right.evidence.proposition.polarity.value,
                "left_receipt_id": left.validation_receipt.receipt_id,
                "right_receipt_id": right.validation_receipt.receipt_id,
            },
        )

    def issue_relation(self, left: SemanticAtom, right: SemanticAtom, *, relation_type: str) -> IssuedPacket:
        self._require_validated_atom(left)
        self._require_validated_atom(right)
        relation_type = _canonical_text(relation_type, "relation_type")
        if left.atom_id == right.atom_id:
            raise SemanticExecutionError("relation requires two distinct validated atoms")
        if left.evidence.proposition.subject != right.evidence.proposition.subject:
            raise SemanticExecutionError("relation relevance is not derivable: validated subjects differ")
        execution_input = _digest(
            {"left_atom_id": left.atom_id, "right_atom_id": right.atom_id, "relation_type": relation_type, "shared_subject": left.evidence.proposition.subject}
        )
        receipt = self._kernel.issue_execution(
            evaluator_id=self._EVALUATOR,
            rule_id=self._RELATION_RULE[0],
            rule_version=self._RELATION_RULE[1],
            input_digest=execution_input,
            outcome="PASS",
            output={"left_atom_id": left.atom_id, "right_atom_id": right.atom_id, "shared_subject": left.evidence.proposition.subject},
        )
        return self._kernel.issue_packet(
            "RELATION",
            {
                "relation_type": relation_type,
                "left_atom_id": left.atom_id,
                "right_atom_id": right.atom_id,
                "derived_basis": "validated_shared_subject",
                "relevance_receipt_id": receipt.receipt_id,
                "input_digest": execution_input,
            },
        )

    def issue_redaction(self, source: bytes, policy: PolicyRef) -> IssuedPacket:
        try:
            text = source.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise SemanticExecutionError("redaction source must be strict UTF-8") from exc
        classifier = self._policies.resolve(policy)
        ranges = classifier(text)
        source_sha256 = sha256(source).hexdigest()
        policy_input = _digest({"source_sha256": source_sha256, "policy_id": policy.policy_id, "version": policy.version})
        receipt = self._kernel.issue_execution(
            evaluator_id=self._EVALUATOR,
            rule_id=self._POLICY_RULE[0],
            rule_version=self._POLICY_RULE[1],
            input_digest=policy_input,
            outcome="PASS",
            output={"source_sha256": source_sha256, "policy_id": policy.policy_id, "policy_version": policy.version, "ranges": [[item.start, item.end] for item in ranges]},
        )
        return self._kernel.issue_packet(
            "REDACTION",
            {
                "source_sha256": source_sha256,
                "policy_id": policy.policy_id,
                "policy_version": policy.version,
                "classification_receipt_id": receipt.receipt_id,
                "classification_input_digest": policy_input,
                "raw_ranges": [[item.start, item.end] for item in ranges],
                "lineage": {"source_sha256": source_sha256, "policy_execution_receipt": receipt.receipt_id},
            },
        )

    def _require_validated_atom(self, atom: object) -> None:
        if not isinstance(atom, SemanticAtom):
            raise SemanticExecutionError("semantic operation requires a SemanticAtom")
        if not self._verifier.verify_execution(atom.validation_receipt):
            raise SemanticExecutionError("atom validation receipt was not issued by this trusted executor")
        expected_atom_id = _digest({"evidence_id": atom.evidence.evidence_id, "receipt_id": atom.validation_receipt.receipt_id})
        if atom.atom_id != expected_atom_id:
            raise SemanticExecutionError("atom identity is not derived from its validated evidence and receipt")


def bootstrap_trusted_runtime() -> TrustedSemanticExecutor:
    """Create an ephemeral synthetic authority; consumers should retain only `.verifier`.

    A separately bootstrapped runtime cannot substitute for a consumer's pinned
    verifier because its private issuance ledger and signing key differ.
    """

    return TrustedSemanticExecutor(_AuthorityKernel())


def _assert_no_isolated_surrogate(text: str, global_offset: int) -> None:
    index = 0
    while index < len(text):
        if text[index] != "\\":
            index += 1
            continue
        if index + 1 >= len(text):
            return
        marker = text[index + 1]
        if marker == "\\":
            index += 2
            continue
        if marker != "u" or index + 6 > len(text) or not re.fullmatch(r"[0-9A-Fa-f]{4}", text[index + 2 : index + 6]):
            index += 2
            continue
        codepoint = int(text[index + 2 : index + 6], 16)
        byte_offset = global_offset + len(text[:index].encode("utf-8"))
        if 0xD800 <= codepoint <= 0xDBFF:
            if index + 12 <= len(text) and text[index + 6 : index + 8] == "\\u" and re.fullmatch(r"[0-9A-Fa-f]{4}", text[index + 8 : index + 12]):
                low = int(text[index + 8 : index + 12], 16)
                if 0xDC00 <= low <= 0xDFFF:
                    index += 12
                    continue
            raise JsonlOwnershipError("ISOLATED_HIGH_SURROGATE", byte_offset)
        if 0xDC00 <= codepoint <= 0xDFFF:
            raise JsonlOwnershipError("ISOLATED_LOW_SURROGATE", byte_offset)
        index += 6


def _validate_json_record(content: bytes, global_offset: int) -> None:
    try:
        text = content.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise JsonlOwnershipError("NON_UTF8_JSONL_RECORD", global_offset + exc.start) from exc
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        raise JsonlOwnershipError("INVALID_JSONL_RECORD", global_offset + len(text[: exc.pos].encode("utf-8"))) from exc
    _assert_no_isolated_surrogate(text, global_offset)


def parse_jsonl_whole_source(data: bytes) -> JsonlOwnership:
    """Own every byte of a JSONL source, including blank lines and CR/LF bytes."""

    segments: list[OwnedByteSegment] = []
    record_count = 0
    line_index = 0
    line_start = 0
    cursor = 0
    while cursor < len(data):
        byte = data[cursor]
        if byte not in (10, 13):
            cursor += 1
            continue
        content_end = cursor
        terminator_end = cursor + 1
        if byte == 13 and cursor + 1 < len(data) and data[cursor + 1] == 10:
            terminator_end = cursor + 2
        content = data[line_start:content_end]
        if content:
            content_range = ByteRange(line_start, content_end)
            if content.strip(b" \t"):
                _validate_json_record(content, line_start)
                segments.append(OwnedByteSegment(SegmentKind.JSON_RECORD, content_range, line_index))
                record_count += 1
            else:
                segments.append(OwnedByteSegment(SegmentKind.BLANK_LINE, content_range, line_index))
        segments.append(OwnedByteSegment(SegmentKind.LINE_TERMINATOR, ByteRange(content_end, terminator_end), line_index))
        line_index += 1
        line_start = terminator_end
        cursor = terminator_end
    if line_start < len(data):
        content_range = ByteRange(line_start, len(data))
        content = data[line_start:]
        if content.strip(b" \t"):
            _validate_json_record(content, line_start)
            segments.append(OwnedByteSegment(SegmentKind.JSON_RECORD, content_range, line_index))
            record_count += 1
        else:
            segments.append(OwnedByteSegment(SegmentKind.BLANK_LINE, content_range, line_index))
    status = "EMPTY_SOURCE" if not data else ("NO_JSON_RECORDS" if record_count == 0 else "PARSED")
    result = JsonlOwnership(sha256(data).hexdigest(), len(data), tuple(segments), record_count, status)
    result.assert_complete_partition()
    return result
