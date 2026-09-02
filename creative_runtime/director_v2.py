"""Read-only DirectorBrief/v2 content compiler and multi-script switcher."""

from __future__ import annotations

from dataclasses import replace
import hashlib
from typing import Any

from .contracts import (
    DirectorBriefV2CompiledContent,
    DirectorBriefV2ContentSelection,
    DirectorScriptSelection,
    ScriptCatalogEntry,
    canonical_json,
)
from .script_catalog import PersistentScriptCatalog, ScriptCatalogViolation


class DirectorBriefV2Violation(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _compile_material(brief: DirectorBriefV2CompiledContent) -> dict[str, Any]:
    value = brief.to_dict()
    value.pop("brief_id", None)
    value.pop("compile_hash", None)
    return value


def compile_director_brief_v2(
    catalog: PersistentScriptCatalog,
    binding: DirectorBriefV2ContentSelection,
) -> DirectorBriefV2CompiledContent:
    """Compile content only after the R177 binding passes fresh validation."""

    if not isinstance(catalog, PersistentScriptCatalog):
        raise DirectorBriefV2Violation("DIRECTOR_CATALOG_INVALID", "a persistent validated catalog is required")
    if not isinstance(binding, DirectorBriefV2ContentSelection):
        raise DirectorBriefV2Violation("DIRECTOR_BINDING_INVALID", "a validated v2 content binding is required")
    try:
        package = catalog.consume_director_binding(binding)
    except ScriptCatalogViolation as error:
        raise DirectorBriefV2Violation(error.code, str(error)) from error
    profiles = {item.style_profile_id: item for item in package.style_profiles}
    style = profiles.get(binding.style_profile_id)
    if style is None:
        raise DirectorBriefV2Violation("DIRECTOR_STYLE_UNKNOWN", "bound style is absent from the package")

    placeholder = DirectorBriefV2CompiledContent(
        brief_id="",
        content_binding=binding,
        content_rating=package.content_rating,
        genre=package.genre,
        world_bible=package.world_bible,
        character_bibles=package.character_bibles,
        scene_bibles=package.scene_bibles,
        story_beats=package.story_beats,
        legal_choices=package.legal_choices,
        style_profile=style,
        asset_manifest=package.asset_manifest,
        compile_hash="",
    )
    compile_hash = _digest(_compile_material(placeholder))
    return replace(placeholder, brief_id=f"briefv2_{compile_hash[:24]}", compile_hash=compile_hash)


def inspect_director_brief_v2(
    catalog: PersistentScriptCatalog,
    brief: DirectorBriefV2CompiledContent,
) -> DirectorBriefV2CompiledContent:
    """Recompile and compare every field so relabeling cannot survive inspection."""

    if not isinstance(brief, DirectorBriefV2CompiledContent):
        raise DirectorBriefV2Violation("DIRECTOR_BRIEF_INVALID", "compiled content contract is required")
    if brief.schema_version != "DirectorBrief/v2.compiled-content":
        raise DirectorBriefV2Violation("DIRECTOR_BRIEF_SCHEMA", "compiled content schema is unsupported")
    if brief.compile_hash != _digest(_compile_material(brief)):
        raise DirectorBriefV2Violation("DIRECTOR_BRIEF_HASH_MISMATCH", "compiled content hash is stale or tampered")
    expected = compile_director_brief_v2(catalog, brief.content_binding)
    if brief != expected:
        raise DirectorBriefV2Violation("DIRECTOR_BRIEF_SUBSTITUTION", "compiled content differs from package truth")
    return brief


class MultiScriptDirectorCompiler:
    """Stateless facade for deterministic list/select/compile/inspect/switch."""

    def __init__(self, catalog: PersistentScriptCatalog) -> None:
        if not isinstance(catalog, PersistentScriptCatalog):
            raise DirectorBriefV2Violation("DIRECTOR_CATALOG_INVALID", "validated catalog is required")
        self._catalog = catalog

    def list_scripts(self) -> tuple[ScriptCatalogEntry, ...]:
        return self._catalog.list_entries()

    def select(
        self,
        *,
        script_id: str,
        script_revision: str,
        package_hash: str,
        style_profile_id: str,
    ) -> DirectorBriefV2ContentSelection:
        try:
            selection = self._catalog.select(
                script_id=script_id,
                script_revision=script_revision,
                package_hash=package_hash,
                style_profile_id=style_profile_id,
            )
            return self._catalog.bind_for_director(selection)
        except (ScriptCatalogViolation, ValueError) as error:
            code = getattr(error, "code", "DIRECTOR_SELECTION_INVALID")
            raise DirectorBriefV2Violation(code, str(error)) from error

    def compile(self, binding: DirectorBriefV2ContentSelection) -> DirectorBriefV2CompiledContent:
        return compile_director_brief_v2(self._catalog, binding)

    def inspect(self, brief: DirectorBriefV2CompiledContent) -> DirectorBriefV2CompiledContent:
        return inspect_director_brief_v2(self._catalog, brief)

    def switch(
        self,
        current: DirectorBriefV2CompiledContent,
        target: DirectorBriefV2ContentSelection,
    ) -> DirectorBriefV2CompiledContent:
        self.inspect(current)
        return self.compile(target)

    def compile_selection(self, selection: DirectorScriptSelection) -> DirectorBriefV2CompiledContent:
        if not isinstance(selection, DirectorScriptSelection):
            raise DirectorBriefV2Violation("DIRECTOR_SELECTION_INVALID", "DirectorScriptSelection is required")
        try:
            binding = self._catalog.bind_for_director(selection)
        except (ScriptCatalogViolation, ValueError) as error:
            code = getattr(error, "code", "DIRECTOR_SELECTION_INVALID")
            raise DirectorBriefV2Violation(code, str(error)) from error
        return self.compile(binding)
