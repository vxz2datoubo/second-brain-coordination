"""Hash-bound, read-only local knowledge adapters for public-safe or local bodies."""

from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .canonical import content_hash, normalize_text
from .knowledge_contracts import (
    KnowledgeAccessDecision,
    KnowledgeGatewayPolicy,
    KnowledgeSourceManifest,
    evaluate_knowledge_access,
)
from .learning_packet import build_learning_packet
from .security import assert_no_credential_value


@dataclass(frozen=True)
class LocalKnowledgeDocument:
    document_id: str
    manifest_id: str
    source_reference: str
    ordinal: int
    content_format: str
    content: str

    def semantic_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LocalKnowledgeLoadResult:
    decision: KnowledgeAccessDecision
    documents: tuple[LocalKnowledgeDocument, ...]
    file_count: int
    document_count: int
    content_bytes: int
    document_core_hash: str
    source_modified: bool = False

    def public_receipt(self) -> dict[str, Any]:
        payload = {
            "access_decision": self.decision.to_public_receipt(),
            "file_count": self.file_count,
            "document_count": self.document_count,
            "content_bytes": self.content_bytes,
            "document_core_hash": self.document_core_hash,
            "source_modified": self.source_modified,
            "private_body_included": False,
            "credential_value_included": False,
            "authority_write": False,
            "no_trade_gate": True,
        }
        assert_no_credential_value(payload)
        return payload


class LocalKnowledgeAdapter(abc.ABC):
    @abc.abstractmethod
    def load(
        self,
        manifest: KnowledgeSourceManifest,
        policy: KnowledgeGatewayPolicy,
    ) -> LocalKnowledgeLoadResult: ...


class ExistingServiceKnowledgeAdapter(LocalKnowledgeAdapter):
    """Interface only: service lifecycle or network access is outside Issue #38."""

    def load(
        self,
        manifest: KnowledgeSourceManifest,
        policy: KnowledgeGatewayPolicy,
    ) -> LocalKnowledgeLoadResult:
        decision = evaluate_knowledge_access(manifest, policy)
        if decision.status == "GRANTED":
            decision = KnowledgeAccessDecision(
                **{
                    **asdict(decision),
                    "status": "WAITING_LOCAL_EVIDENCE",
                    "reason_codes": ("existing_service_interface_not_bound",),
                }
            )
        return LocalKnowledgeLoadResult(decision, (), 0, 0, 0, content_hash([]))


class LocalFileKnowledgeAdapter(LocalKnowledgeAdapter):
    def __init__(self, local_path: Path) -> None:
        self.local_path = local_path

    def load(
        self,
        manifest: KnowledgeSourceManifest,
        policy: KnowledgeGatewayPolicy,
    ) -> LocalKnowledgeLoadResult:
        decision = evaluate_knowledge_access(manifest, policy)
        if decision.status != "GRANTED":
            return LocalKnowledgeLoadResult(decision, (), 0, 0, 0, content_hash([]))
        if manifest.source_kind != "FILE":
            return _denied_result(decision, "knowledge_source_kind_not_file")
        try:
            path = self.local_path.resolve(strict=True)
        except OSError:
            return _denied_result(decision, "knowledge_source_not_found")
        if not path.is_file():
            return _denied_result(decision, "knowledge_source_not_file")
        suffix = _format_for_path(path)
        if suffix not in set(manifest.allowed_formats) or suffix != manifest.local_reference.content_format:
            return _denied_result(decision, "knowledge_source_format_mismatch")
        before = _file_fingerprint(path)
        if before[0] != manifest.local_reference.size_bytes or before[1] != manifest.local_reference.sha256:
            return _denied_result(decision, "knowledge_source_size_or_hash_mismatch")
        try:
            text = path.read_text(encoding="utf-8")
            assert_no_credential_value(text)
            documents = tuple(_documents_from_text(text, suffix, manifest.manifest_id, path.name))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            return _denied_result(decision, str(error))
        after = _file_fingerprint(path)
        modified = before != after
        if modified:
            return _denied_result(decision, "knowledge_source_changed_during_read")
        if not documents:
            return _denied_result(decision, "knowledge_source_empty")
        return LocalKnowledgeLoadResult(
            decision=decision,
            documents=documents,
            file_count=1,
            document_count=len(documents),
            content_bytes=before[0],
            document_core_hash=_document_core_hash(documents),
            source_modified=False,
        )


class LocalDirectoryKnowledgeAdapter(LocalKnowledgeAdapter):
    def __init__(self, local_path: Path) -> None:
        self.local_path = local_path

    def load(
        self,
        manifest: KnowledgeSourceManifest,
        policy: KnowledgeGatewayPolicy,
    ) -> LocalKnowledgeLoadResult:
        decision = evaluate_knowledge_access(manifest, policy)
        if decision.status != "GRANTED":
            return LocalKnowledgeLoadResult(decision, (), 0, 0, 0, content_hash([]))
        if manifest.source_kind != "DIRECTORY":
            return _denied_result(decision, "knowledge_source_kind_not_directory")
        try:
            root = self.local_path.resolve(strict=True)
        except OSError:
            return _denied_result(decision, "knowledge_source_not_found")
        if not root.is_dir():
            return _denied_result(decision, "knowledge_source_not_directory")
        files = tuple(
            path for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
            if path.is_file() and _format_for_path(path) in set(manifest.allowed_formats)
        )
        before = _directory_fingerprint(root, files)
        if before[0] != manifest.local_reference.size_bytes or before[1] != manifest.local_reference.sha256:
            return _denied_result(decision, "knowledge_source_size_or_hash_mismatch")
        documents: list[LocalKnowledgeDocument] = []
        try:
            for path in files:
                text = path.read_text(encoding="utf-8")
                assert_no_credential_value(text)
                relative = path.relative_to(root).as_posix()
                documents.extend(_documents_from_text(text, _format_for_path(path), manifest.manifest_id, relative))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            return _denied_result(decision, str(error))
        after_files = tuple(
            path for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
            if path.is_file() and _format_for_path(path) in set(manifest.allowed_formats)
        )
        if before != _directory_fingerprint(root, after_files):
            return _denied_result(decision, "knowledge_source_changed_during_read")
        normalized = tuple(sorted(documents, key=lambda item: item.document_id))
        if not normalized:
            return _denied_result(decision, "knowledge_source_empty")
        return LocalKnowledgeLoadResult(
            decision=decision,
            documents=normalized,
            file_count=len(files),
            document_count=len(normalized),
            content_bytes=before[0],
            document_core_hash=_document_core_hash(normalized),
            source_modified=False,
        )


def build_local_knowledge_packet(
    result: LocalKnowledgeLoadResult,
    manifest: KnowledgeSourceManifest,
    *,
    base_knowledge_version: str = "candidate-r0",
) -> dict[str, Any]:
    if result.decision.status != "GRANTED":
        raise ValueError("knowledge_source_access_not_granted")
    grouped_documents: dict[str, list[LocalKnowledgeDocument]] = {}
    for document in result.documents:
        semantic_key = content_hash({
            "atom_type": "knowledge_fragment",
            "scope": manifest.content_category,
            "statement": normalize_text(document.content),
        })
        grouped_documents.setdefault(semantic_key, []).append(document)
    atoms = []
    for semantic_key in sorted(grouped_documents):
        documents = grouped_documents[semantic_key]
        primary = documents[0]
        atoms.append({
            "atom_type": "knowledge_fragment",
            "statement": primary.content,
            "scope": manifest.content_category,
            "confidence": 0.6,
            "verification_status": "USER_AUTHORIZED_SOURCE",
            "evidence_quality": manifest.license_status,
            "knowledge_status": "candidate",
            "gpt_access": "FULL_SEMANTIC_ACCESS",
            "transport_visibility": manifest.transport_visibility,
            "source_refs": [
                f"manifest:{manifest.manifest_id}",
                f"local-reference:{manifest.local_reference.reference_id}",
                *[f"document:{document.document_id}" for document in documents],
            ],
            "premises": ["hash_bound_readonly_source"],
            "failure_conditions": ["source_hash_changes", "authorization_revoked"],
        })
    return build_learning_packet(
        source_manifest_ids=[manifest.manifest_id],
        source_hash=manifest.local_reference.sha256,
        validation_report={
            "status": "LOCAL_READONLY_HASH_BOUND",
            "access_decision_id": result.decision.decision_id,
            "file_count": result.file_count,
            "document_count": result.document_count,
            "document_core_hash": result.document_core_hash,
            "private_body_exported": False,
            "credential_value_included": False,
            "authority_write": False,
            "no_trade_gate": True,
        },
        evidence_refs=[
            f"manifest:{manifest.manifest_id}",
            f"artifact-sha256:{manifest.local_reference.sha256}",
        ],
        atoms=atoms,
        base_knowledge_version=base_knowledge_version,
    )


def hash_local_file(path: Path) -> tuple[int, str]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError("knowledge_source_not_file")
    return _file_fingerprint(resolved)


def hash_local_directory(path: Path, allowed_formats: Iterable[str]) -> tuple[int, str, int]:
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("knowledge_source_not_directory")
    allowed = set(allowed_formats)
    files = tuple(
        item for item in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix())
        if item.is_file() and _format_for_path(item) in allowed
    )
    size, digest = _directory_fingerprint(root, files)
    return size, digest, len(files)


def _documents_from_text(
    text: str,
    content_format: str,
    manifest_id: str,
    source_name: str,
) -> list[LocalKnowledgeDocument]:
    pieces: list[str]
    if content_format in {"markdown", "txt"}:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        pieces = [normalize_text(block) for block in normalized.split("\n\n") if normalize_text(block)]
    elif content_format == "json":
        value = json.loads(text)
        records = value if isinstance(value, list) else value.get("records", [value]) if isinstance(value, dict) else [value]
        pieces = [json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in records]
    elif content_format == "jsonl":
        pieces = [json.dumps(json.loads(line), ensure_ascii=False, sort_keys=True, separators=(",", ":")) for line in text.splitlines() if line.strip()]
    else:
        raise ValueError("knowledge_source_format_unsupported")
    documents: list[LocalKnowledgeDocument] = []
    for ordinal, piece in enumerate(pieces):
        assert_no_credential_value(piece)
        identity = content_hash({"manifest_id": manifest_id, "source": source_name, "ordinal": ordinal, "content": piece})
        documents.append(
            LocalKnowledgeDocument(
                document_id="doc-" + identity[:20],
                manifest_id=manifest_id,
                source_reference=source_name,
                ordinal=ordinal,
                content_format=content_format,
                content=piece,
            )
        )
    return documents


def _format_for_path(path: Path) -> str:
    return {".md": "markdown", ".txt": "txt", ".json": "json", ".jsonl": "jsonl"}.get(path.suffix.casefold(), "unsupported")


def _file_fingerprint(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _directory_fingerprint(root: Path, files: tuple[Path, ...]) -> tuple[int, str]:
    entries: list[dict[str, Any]] = []
    total = 0
    for path in files:
        size, digest = _file_fingerprint(path)
        total += size
        entries.append({"path": path.relative_to(root).as_posix(), "size": size, "sha256": digest})
    return total, content_hash(entries)


def _document_core_hash(documents: Iterable[LocalKnowledgeDocument]) -> str:
    return content_hash([document.semantic_payload() for document in documents])


def _denied_result(decision: KnowledgeAccessDecision, reason: str) -> LocalKnowledgeLoadResult:
    denied = KnowledgeAccessDecision(
        **{
            **asdict(decision),
            "decision_id": "kad-" + content_hash({"prior": decision.decision_id, "reason": reason})[:20],
            "status": "DENIED",
            "reason_codes": (reason,),
        }
    )
    return LocalKnowledgeLoadResult(denied, (), 0, 0, 0, content_hash([]))
