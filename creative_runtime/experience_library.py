"""Strict multi-scenario, offline experience-library artifacts.

The existing single-scenario artifact is useful for focused replay.  This
module adds a bounded library for a reviewer or a local static player without
giving that player story authority: every entry is a complete, independently
rebuildable synthetic artifact, and the library is rejected as a whole if one
entry differs from the exact source reconstruction.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from .continuity import graph_for_initial_state
from .contracts import canonical_json
from .coverage import coverage_for_scenario, ledger_for_route
from .demo_routes import GITHUB_DEMO_ROUTES, github_demo_actions
from .experience import build_verified_experience, build_verified_scenario_catalog
from .sequence import build_verified_sequence


SYNTHETIC_ARTIFACT_SCHEMA = "CreativeRuntimeExperienceArtifact/v1"
LIBRARY_SCHEMA = "CreativeRuntimeExperienceLibrary/v1"
DEMO_SLOT = "github_demo"


class ExperienceLibraryViolation(ValueError):
    """Raised when a synthetic library cannot be reproduced exactly."""


def _require_head(head_sha: str) -> str:
    if not isinstance(head_sha, str) or len(head_sha) != 40 or any(character not in "0123456789abcdef" for character in head_sha):
        raise ExperienceLibraryViolation("Experience library requires a lowercase full 40-character git SHA")
    return head_sha


def artifact_sha256(artifact: Mapping[str, Any]) -> str:
    """Return a content identity for a canonical synthetic artifact object."""

    return hashlib.sha256(canonical_json(dict(artifact)).encode("utf-8")).hexdigest()


def build_synthetic_experience_artifact(head_sha: str, scenario: str) -> dict[str, Any]:
    """Build one exact-head demonstration artifact without touching a workspace.

    The route ledger is created through the production event contract and the
    catalogue still comes from exhaustive route coverage.  This helper owns
    the public-safe artifact schema so the library builder and its verifier do
    not have subtly different reconstruction rules.
    """

    head = _require_head(head_sha)
    try:
        actions = github_demo_actions(scenario)
    except ValueError as error:
        raise ExperienceLibraryViolation("Artifact declares an unsupported GitHub demo scenario") from error
    report = coverage_for_scenario(scenario)
    graph = graph_for_initial_state(report.initial_state)
    ledger = ledger_for_route(graph, report.initial_state, actions)
    return {
        "schema": SYNTHETIC_ARTIFACT_SCHEMA,
        "status": "experience_artifact_verified",
        "head_sha": head,
        "scenario": scenario,
        "actions": list(actions),
        "experience": build_verified_experience(ledger, slot=DEMO_SLOT).to_dict(),
        "sequence": build_verified_sequence(ledger, slot=DEMO_SLOT).to_dict(),
        "catalog": build_verified_scenario_catalog(scenario).to_dict(),
        "boundary": {
            "synthetic_only": True,
            "customer_data_present": False,
            "external_provider_called": False,
            "publication_authorized": False,
        },
    }


def _normalized_scenarios(scenarios: Iterable[str] | None) -> tuple[str, ...]:
    requested = tuple(sorted(GITHUB_DEMO_ROUTES) if scenarios is None else scenarios)
    if not requested:
        raise ExperienceLibraryViolation("Experience library must contain at least one synthetic scenario")
    if len(set(requested)) != len(requested):
        raise ExperienceLibraryViolation("Experience library scenario names must be unique")
    for scenario in requested:
        if not isinstance(scenario, str) or scenario not in GITHUB_DEMO_ROUTES:
            raise ExperienceLibraryViolation("Experience library contains an unsupported synthetic scenario")
    return requested


@dataclass(frozen=True)
class VerifiedExperienceLibrary:
    """A complete local navigation library made only of verified artifacts."""

    library_id: str
    head_sha: str
    entries: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": LIBRARY_SCHEMA,
            "status": "experience_library_verified",
            "library_id": self.library_id,
            "head_sha": self.head_sha,
            "entry_count": len(self.entries),
            "scenario_ids": [entry["scenario"] for entry in self.entries],
            "entries": [dict(entry) for entry in self.entries],
            "boundary": {
                "synthetic_only": True,
                "customer_data_present": False,
                "external_provider_called": False,
                "publication_authorized": False,
                "client_story_authority": False,
            },
            "authority_note": "Render-only synthetic library. The browser may select a precomputed scenario but cannot calculate, persist, or authorize story transitions.",
        }


def build_verified_experience_library(head_sha: str, scenarios: Iterable[str] | None = None) -> VerifiedExperienceLibrary:
    """Create a deterministic multi-scenario library at one exact Git head."""

    head = _require_head(head_sha)
    normalized = _normalized_scenarios(scenarios)
    entries: list[Mapping[str, Any]] = []
    for scenario in normalized:
        artifact = build_synthetic_experience_artifact(head, scenario)
        catalog = artifact["catalog"]
        entries.append(
            {
                "scenario": scenario,
                "graph_revision": catalog["graph_revision"],
                "catalog_id": catalog["catalog_id"],
                "artifact_sha256": artifact_sha256(artifact),
                "artifact": artifact,
            }
        )
    material = {
        "schema": LIBRARY_SCHEMA,
        "head_sha": head,
        "entries": entries,
    }
    library_id = "experience_library_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20]
    return VerifiedExperienceLibrary(library_id=library_id, head_sha=head, entries=tuple(entries))


def verify_verified_experience_library(head_sha: str, library: Mapping[str, Any]) -> VerifiedExperienceLibrary:
    """Fail closed unless a library exactly equals its clean source rebuild."""

    head = _require_head(head_sha)
    try:
        supplied = dict(library)
        entries = supplied.get("entries")
        scenarios = tuple(entry["scenario"] for entry in entries) if isinstance(entries, list) else ()
    except (KeyError, TypeError, ValueError) as error:
        raise ExperienceLibraryViolation("Experience library has malformed scenario entries") from error
    if scenarios != tuple(sorted(GITHUB_DEMO_ROUTES)):
        raise ExperienceLibraryViolation("Experience library must contain the complete registered synthetic scenario set in stable order")
    expected = build_verified_experience_library(head)
    if canonical_json(supplied) != canonical_json(expected.to_dict()):
        raise ExperienceLibraryViolation("Experience library does not exactly match the clean exact-head synthetic rebuild")
    return expected
