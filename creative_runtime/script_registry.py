"""Immutable ScriptPackage/v1 registry and read-only director selection.

This module performs no file, network, campaign, session, or media writes.  It
only validates approved synthetic content and returns a hash-bound selection.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from .contracts import DirectorScriptSelection, ScriptPackage, StyleProfile, canonical_json


SCRIPT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
REVISION_PATTERN = re.compile(r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$")
ALLOWED_CONTENT_RATINGS = frozenset({"non_explicit"})
REQUIRED_STYLE_IDS = frozenset(
    {"cinematic_live_action", "stylized_3d", "japanese_animation", "ink_animation"}
)
FORBIDDEN_METADATA_KEYS = frozenset(
    {"token", "access_token", "credential_secret", "password", "cookie", "raw_photo", "comment_text"}
)


class ScriptRegistryViolation(ValueError):
    """A fail-closed registry or package validation result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _package_material(package: ScriptPackage) -> dict[str, Any]:
    value = package.to_dict()
    value.pop("package_hash", None)
    return value


def compute_package_hash(package: ScriptPackage) -> str:
    return hashlib.sha256(canonical_json(_package_material(package)).encode("utf-8")).hexdigest()


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key).lower()
            yield from _walk_keys(item)
    elif isinstance(value, tuple | list):
        for item in value:
            yield from _walk_keys(item)


def _validate_package(package: ScriptPackage) -> None:
    if package.schema_version != "ScriptPackage/v1":
        raise ScriptRegistryViolation("PACKAGE_SCHEMA_VERSION", "only ScriptPackage/v1 is supported")
    if not SCRIPT_ID_PATTERN.fullmatch(package.script_id):
        raise ScriptRegistryViolation("SCRIPT_ID_INVALID", "script_id must be stable lower snake case")
    if not REVISION_PATTERN.fullmatch(package.script_revision):
        raise ScriptRegistryViolation("SCRIPT_REVISION_INVALID", "script_revision must be exact semver")
    if package.content_rating not in ALLOWED_CONTENT_RATINGS:
        raise ScriptRegistryViolation("CONTENT_RATING_FORBIDDEN", "only non_explicit fixtures are allowed")
    if package.approval_status != "approved":
        raise ScriptRegistryViolation("SCRIPT_NOT_APPROVED", "registration requires explicit approval")

    if any(not isinstance(profile, StyleProfile) for profile in package.style_profiles):
        raise ScriptRegistryViolation("STYLE_PROFILE_INVALID", "style profiles must match StyleProfile/v1")
    style_ids = [profile.style_profile_id for profile in package.style_profiles]
    if len(style_ids) != len(set(style_ids)):
        raise ScriptRegistryViolation("STYLE_PROFILE_DUPLICATE", "style profile IDs must be unique")
    if not REQUIRED_STYLE_IDS.issubset(style_ids):
        raise ScriptRegistryViolation("STYLE_PROFILE_INCOMPLETE", "all four presentation styles are required")
    if any(not profile.presentation_only for profile in package.style_profiles):
        raise ScriptRegistryViolation("STYLE_MUTATES_STORY", "style profiles must be presentation-only")

    if any(not isinstance(beat, Mapping) for beat in package.story_beats):
        raise ScriptRegistryViolation("STORY_BEAT_INVALID", "story beats must be objects")
    beat_ids = [str(beat.get("beat_id", "")) for beat in package.story_beats]
    if not beat_ids or len(beat_ids) != len(set(beat_ids)) or any(not item for item in beat_ids):
        raise ScriptRegistryViolation("STORY_BEAT_INVALID", "story beat IDs must be present and unique")
    if set(package.legal_choices) != set(beat_ids):
        raise ScriptRegistryViolation("LEGAL_CHOICE_COVERAGE", "every and only story beats need choices")
    if any(not choices or len(choices) != len(set(choices)) for choices in package.legal_choices.values()):
        raise ScriptRegistryViolation("LEGAL_CHOICE_INVALID", "each beat needs unique legal choices")

    if any(not isinstance(asset, Mapping) for asset in package.asset_manifest):
        raise ScriptRegistryViolation("ASSET_MANIFEST_INVALID", "asset records must be objects")
    asset_ids = [str(asset.get("asset_id", "")) for asset in package.asset_manifest]
    if not asset_ids or len(asset_ids) != len(set(asset_ids)) or any(not item for item in asset_ids):
        raise ScriptRegistryViolation("ASSET_MANIFEST_INVALID", "synthetic asset IDs must be present and unique")
    provenance = package.source_provenance
    if not isinstance(provenance, Mapping):
        raise ScriptRegistryViolation("SOURCE_PROVENANCE_INVALID", "source provenance must be an object")
    if provenance.get("classification") != "SYNTHETIC" or provenance.get("approved_for_reuse") is not True:
        raise ScriptRegistryViolation("SOURCE_PROVENANCE_INVALID", "only approved synthetic sources may register")
    if not str(provenance.get("approval_record", "")):
        raise ScriptRegistryViolation("SOURCE_APPROVAL_MISSING", "source approval record is required")
    if FORBIDDEN_METADATA_KEYS.intersection(_walk_keys(package.to_dict())):
        raise ScriptRegistryViolation("PRIVATE_METADATA_FORBIDDEN", "private or credential metadata is forbidden")

    expected_hash = compute_package_hash(package)
    if package.package_hash != expected_hash:
        raise ScriptRegistryViolation("PACKAGE_HASH_MISMATCH", "package content does not match its hash")


def build_script_package(**values: Any) -> ScriptPackage:
    """Build and hash a package once, then return its immutable representation."""

    try:
        values = dict(values)
        values["style_profiles"] = tuple(
            item if isinstance(item, StyleProfile) else StyleProfile(**item)
            for item in values.get("style_profiles", ())
        )
        placeholder = ScriptPackage(package_hash="", **values)
        package = replace(placeholder, package_hash=compute_package_hash(placeholder))
    except (KeyError, TypeError, ValueError) as error:
        raise ScriptRegistryViolation("PACKAGE_SCHEMA_INVALID", "package fields do not match ScriptPackage/v1") from error
    _validate_package(package)
    return package


def parse_script_package_json(text: str) -> ScriptPackage:
    """Parse a package with duplicate-key rejection and full hash validation."""

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ScriptRegistryViolation("DUPLICATE_METADATA_KEY", f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        values = json.loads(text, object_pairs_hook=strict_object)
    except ScriptRegistryViolation:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ScriptRegistryViolation("PACKAGE_JSON_INVALID", "package JSON is malformed") from error
    if not isinstance(values, dict):
        raise ScriptRegistryViolation("PACKAGE_JSON_INVALID", "package JSON root must be an object")
    try:
        styles = tuple(
            item if isinstance(item, StyleProfile) else StyleProfile(**item)
            for item in values.get("style_profiles", ())
        )
        package = ScriptPackage(**{**values, "style_profiles": styles})
    except (KeyError, TypeError, ValueError) as error:
        raise ScriptRegistryViolation("PACKAGE_SCHEMA_INVALID", "package fields do not match ScriptPackage/v1") from error
    _validate_package(package)
    return package


class ScriptPackageRegistry:
    """In-memory registry keyed by exact script ID, revision and package hash."""

    def __init__(self) -> None:
        self._packages: dict[tuple[str, str, str], ScriptPackage] = {}
        self._revision_hashes: dict[tuple[str, str], str] = {}

    def register(self, package: ScriptPackage) -> ScriptPackage:
        _validate_package(package)
        identity = (package.script_id, package.script_revision)
        existing_hash = self._revision_hashes.get(identity)
        if existing_hash is not None and existing_hash != package.package_hash:
            raise ScriptRegistryViolation(
                "IMMUTABLE_REVISION_CONFLICT", "an approved script revision cannot be replaced"
            )
        exact_identity = (*identity, package.package_hash)
        if exact_identity not in self._packages:
            self._packages[exact_identity] = package
            self._revision_hashes[identity] = package.package_hash
        return self._packages[exact_identity]

    def resolve(self, script_id: str, script_revision: str, package_hash: str) -> ScriptPackage:
        exact_identity = (script_id, script_revision, package_hash)
        package = self._packages.get(exact_identity)
        if package is None:
            revisions = {key[1] for key in self._revision_hashes if key[0] == script_id}
            if not revisions:
                raise ScriptRegistryViolation("SCRIPT_UNKNOWN", "script ID is not registered")
            if script_revision not in revisions:
                raise ScriptRegistryViolation("SCRIPT_REVISION_UNKNOWN", "script revision is not registered")
            raise ScriptRegistryViolation("PACKAGE_HASH_MISMATCH", "selection requires the exact package hash")
        _validate_package(package)
        return package

    def select_for_director(
        self,
        *,
        script_id: str,
        script_revision: str,
        package_hash: str,
        style_profile_id: str,
    ) -> DirectorScriptSelection:
        package = self.resolve(script_id, script_revision, package_hash)
        style_ids = {profile.style_profile_id for profile in package.style_profiles}
        if style_profile_id not in style_ids:
            raise ScriptRegistryViolation("STYLE_PROFILE_UNKNOWN", "style is not approved for this package")
        return DirectorScriptSelection(
            script_id=script_id,
            script_revision=script_revision,
            package_hash=package_hash,
            style_profile_id=style_profile_id,
        )

    def list_identities(self) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            (item.script_id, item.script_revision, item.package_hash)
            for item in sorted(self._packages.values(), key=lambda value: (value.script_id, value.script_revision))
        )


def style_profiles_v1() -> tuple[StyleProfile, ...]:
    return (
        StyleProfile("cinematic_live_action", "电影真人", "restrained cinematic realism", "diegetic score"),
        StyleProfile("stylized_3d", "风格化 3D", "expressive authored 3D", "spatial cinematic mix"),
        StyleProfile("japanese_animation", "日式动画", "hand-authored anime language", "dramatic animation mix"),
        StyleProfile("ink_animation", "水墨动画", "ink-wash movement and negative space", "minimal acoustic score"),
    )
