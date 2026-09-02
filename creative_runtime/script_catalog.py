"""Deterministic persistent read-only ScriptPackage catalog.

The only write is one atomic materialization of approved offline content. A
loaded catalog exposes immutable list/get/select/bind operations and has no
campaign, session, director-job, media-job, provider, or canonical-knowledge
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from .contracts import (
    DirectorBriefV2ContentSelection,
    DirectorScriptSelection,
    ScriptCatalogEntry,
    ScriptPackage,
    canonical_json,
)
from .script_registry import ScriptPackageRegistry, ScriptRegistryViolation, parse_script_package_json


CATALOG_SCHEMA = "ScriptPackageCatalog/v1"


class ScriptCatalogViolation(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _strict_json(text: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ScriptCatalogViolation("CATALOG_DUPLICATE_KEY", f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=reject_duplicates)
    except ScriptCatalogViolation:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ScriptCatalogViolation("CATALOG_CORRUPT", "catalog is not valid strict JSON") from error


def _catalog_material(packages: Iterable[ScriptPackage]) -> dict[str, Any]:
    ordered = sorted(packages, key=lambda item: (item.script_id, item.script_revision, item.package_hash))
    if not ordered:
        raise ScriptCatalogViolation("CATALOG_EMPTY", "at least one approved package is required")
    registry = ScriptPackageRegistry()
    seen: set[tuple[str, str, str]] = set()
    try:
        for package in ordered:
            exact_identity = (package.script_id, package.script_revision, package.package_hash)
            if exact_identity in seen:
                raise ScriptCatalogViolation("CATALOG_DUPLICATE_PACKAGE", "exact package appears more than once")
            seen.add(exact_identity)
            registry.register(package)
    except ScriptRegistryViolation as error:
        raise ScriptCatalogViolation(error.code, str(error)) from error
    return {"schema_version": CATALOG_SCHEMA, "packages": [item.to_dict() for item in ordered]}


def serialize_catalog(packages: Iterable[ScriptPackage]) -> str:
    material = _catalog_material(packages)
    document = {**material, "catalog_hash": _hash(material)}
    return canonical_json(document) + "\n"


def _confined_path(root: Path, relative_path: str | Path) -> Path:
    root = root.resolve()
    relative = Path(relative_path)
    if relative.is_absolute():
        raise ScriptCatalogViolation("CATALOG_PATH_ESCAPE", "catalog path must be repository-relative")
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ScriptCatalogViolation("CATALOG_PATH_ESCAPE", "catalog path escapes its declared root") from error
    return target


def materialize_catalog(
    root: Path,
    relative_path: str | Path,
    packages: Iterable[ScriptPackage],
) -> Path:
    """Atomically create an immutable-by-contract catalog artifact.

    Repeating the exact operation is idempotent. Replacing different content at
    the same path fails closed.
    """

    target = _confined_path(root, relative_path)
    payload = serialize_catalog(packages).encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)

    def existing_matches() -> bool:
        try:
            existing = target.read_bytes()
        except OSError as error:
            raise ScriptCatalogViolation("CATALOG_READ_FAILED", "existing catalog cannot be read") from error
        if existing == payload:
            return True
        raise ScriptCatalogViolation("CATALOG_IMMUTABLE_CONFLICT", "existing catalog content cannot be replaced")

    if target.exists() and existing_matches():
        return target

    lock = target.with_name(f".{target.name}.lock")
    try:
        lock_descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as error:
        raise ScriptCatalogViolation("CATALOG_WRITE_BUSY", "another materialization owns the catalog lock") from error
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        if target.exists() and existing_matches():
            return target
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ScriptCatalogViolation("CATALOG_WRITE_FAILED", "atomic catalog materialization failed") from error
    finally:
        os.close(lock_descriptor)
        try:
            lock.unlink(missing_ok=True)
        except OSError:
            pass
    return target


@dataclass(frozen=True)
class PersistentScriptCatalog:
    catalog_hash: str
    _packages: tuple[ScriptPackage, ...]

    def list_entries(self) -> tuple[ScriptCatalogEntry, ...]:
        return tuple(
            ScriptCatalogEntry(
                script_id=package.script_id,
                script_revision=package.script_revision,
                package_hash=package.package_hash,
                approval_status=package.approval_status,
                style_profile_ids=tuple(profile.style_profile_id for profile in package.style_profiles),
            )
            for package in self._packages
        )

    def get(self, script_id: str, script_revision: str, package_hash: str) -> ScriptPackage:
        return self._registry().resolve(script_id, script_revision, package_hash)

    def select(
        self,
        *,
        script_id: str,
        script_revision: str,
        package_hash: str,
        style_profile_id: str,
    ) -> DirectorScriptSelection:
        return self._registry().select_for_director(
            script_id=script_id,
            script_revision=script_revision,
            package_hash=package_hash,
            style_profile_id=style_profile_id,
        )

    def bind_for_director(self, selection: DirectorScriptSelection) -> DirectorBriefV2ContentSelection:
        if not isinstance(selection, DirectorScriptSelection):
            raise ScriptCatalogViolation("DIRECTOR_SELECTION_INVALID", "binding requires DirectorScriptSelection")
        package = self.get(selection.script_id, selection.script_revision, selection.package_hash)
        validated = self.select(**selection.to_dict())
        return DirectorBriefV2ContentSelection(
            catalog_hash=self.catalog_hash,
            script_id=validated.script_id,
            script_revision=validated.script_revision,
            package_hash=validated.package_hash,
            style_profile_id=validated.style_profile_id,
            asset_manifest_hash=_hash(package.asset_manifest),
            source_provenance_hash=_hash(package.source_provenance),
        )

    def consume_director_binding(self, binding: DirectorBriefV2ContentSelection) -> ScriptPackage:
        if not isinstance(binding, DirectorBriefV2ContentSelection):
            raise ScriptCatalogViolation("DIRECTOR_BINDING_INVALID", "consumer requires a v2 content binding")
        if binding.schema_version != "DirectorBrief/v2.content-selection":
            raise ScriptCatalogViolation("DIRECTOR_BINDING_SCHEMA", "director selection schema is unsupported")
        if binding.catalog_hash != self.catalog_hash:
            raise ScriptCatalogViolation("DIRECTOR_CATALOG_SUBSTITUTION", "binding belongs to another catalog")
        selection = DirectorScriptSelection(
            script_id=binding.script_id,
            script_revision=binding.script_revision,
            package_hash=binding.package_hash,
            style_profile_id=binding.style_profile_id,
        )
        try:
            package = self.get(selection.script_id, selection.script_revision, selection.package_hash)
            self.select(**selection.to_dict())
        except ScriptRegistryViolation as error:
            raise ScriptCatalogViolation("DIRECTOR_SELECTION_SUBSTITUTION", str(error)) from error
        if binding.asset_manifest_hash != _hash(package.asset_manifest):
            raise ScriptCatalogViolation("DIRECTOR_ASSET_SUBSTITUTION", "asset manifest changed after validation")
        if binding.source_provenance_hash != _hash(package.source_provenance):
            raise ScriptCatalogViolation("DIRECTOR_PROVENANCE_SUBSTITUTION", "source provenance changed after validation")
        return package

    def _registry(self) -> ScriptPackageRegistry:
        registry = ScriptPackageRegistry()
        for package in self._packages:
            registry.register(package)
        return registry


def load_catalog(root: Path, relative_path: str | Path) -> PersistentScriptCatalog:
    path = _confined_path(root, relative_path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScriptCatalogViolation("CATALOG_READ_FAILED", "catalog cannot be read as UTF-8") from error
    document = _strict_json(text)
    if not isinstance(document, Mapping):
        raise ScriptCatalogViolation("CATALOG_SCHEMA_INVALID", "catalog root must be an object")
    if set(document) != {"schema_version", "catalog_hash", "packages"}:
        raise ScriptCatalogViolation("CATALOG_SCHEMA_INVALID", "catalog fields are missing or ambiguous")
    if document.get("schema_version") != CATALOG_SCHEMA:
        raise ScriptCatalogViolation("CATALOG_SCHEMA_INVALID", "unsupported catalog schema")
    package_values = document.get("packages")
    if not isinstance(package_values, list) or not package_values:
        raise ScriptCatalogViolation("CATALOG_PARTIAL", "catalog package list is missing or empty")

    material = {"schema_version": CATALOG_SCHEMA, "packages": package_values}
    if document.get("catalog_hash") != _hash(material):
        raise ScriptCatalogViolation("CATALOG_HASH_MISMATCH", "catalog content is stale or tampered")
    packages: list[ScriptPackage] = []
    try:
        for value in package_values:
            packages.append(parse_script_package_json(canonical_json(value)))
        validated_material = _catalog_material(packages)
    except (ScriptRegistryViolation, ScriptCatalogViolation) as error:
        if isinstance(error, ScriptCatalogViolation):
            raise
        raise ScriptCatalogViolation(error.code, str(error)) from error
    if canonical_json(validated_material) != canonical_json(material):
        raise ScriptCatalogViolation("CATALOG_NONCANONICAL", "catalog order or representation is noncanonical")
    return PersistentScriptCatalog(catalog_hash=str(document["catalog_hash"]), _packages=tuple(packages))
