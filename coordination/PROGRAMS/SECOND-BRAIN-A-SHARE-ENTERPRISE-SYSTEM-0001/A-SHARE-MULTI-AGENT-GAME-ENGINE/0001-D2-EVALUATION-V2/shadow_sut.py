"""Source-derived, in-memory D2 mutation seams for Evaluation V2.

The accepted D2 module is never edited or imported as a mutant.  Each mutant
starts from the SHA-locked source text and changes a narrow callable seam in an
ephemeral module.  This makes the mutation exercise executable SUT behavior,
not a post-hoc replacement of an emitted record.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import sys
from types import ModuleType
from typing import Iterable

from evaluation_v2_contract import EXPECTED_D2_CORE_SHA256


ROOT = Path(__file__).resolve().parent
D2_CORE_PATH = ROOT.parent / "0001-D2" / "d2_game_core.py"


@dataclass(frozen=True)
class SourceReplacement:
    seam_id: str
    before: str
    after: str
    expected_count: int = 1


@dataclass(frozen=True)
class ShadowSut:
    mutant_id: str
    source_sha256: str
    mutant_source_sha256: str
    changed_seams: tuple[str, ...]
    module: ModuleType


def accepted_source() -> str:
    source = D2_CORE_PATH.read_text(encoding="utf-8")
    actual = sha256(source.encode("utf-8")).hexdigest()
    if actual != EXPECTED_D2_CORE_SHA256:
        raise RuntimeError("E23_ACCEPTED_D2_SOURCE_FINGERPRINT_MISMATCH:" + actual)
    return source


def _replace_exactly_once(source: str, replacement: SourceReplacement) -> str:
    actual_count = source.count(replacement.before)
    if actual_count != replacement.expected_count:
        raise RuntimeError(
            "E23_MUTATION_SEAM_COUNT_MISMATCH:"
            + replacement.seam_id + ":expected=" + str(replacement.expected_count) + ":actual=" + str(actual_count)
        )
    return source.replace(replacement.before, replacement.after, replacement.expected_count)


def load_shadow_sut(mutant_id: str, replacements: Iterable[SourceReplacement]) -> ShadowSut:
    """Compile an exact, source-derived mutant in memory without altering D2."""
    source = accepted_source()
    source_hash = sha256(source.encode("utf-8")).hexdigest()
    materialized = source
    seams: list[str] = []
    for replacement in replacements:
        materialized = _replace_exactly_once(materialized, replacement)
        seams.append(replacement.seam_id)
    mutant_hash = sha256(materialized.encode("utf-8")).hexdigest()
    module_name = "_evaluation_v2_shadow_" + "".join(character.lower() if character.isalnum() else "_" for character in mutant_id)
    if module_name in sys.modules:
        del sys.modules[module_name]
    module = ModuleType(module_name)
    # D2 derives its D1 import root from __file__; preserve that relationship.
    module.__file__ = str(D2_CORE_PATH)
    module.__package__ = ""
    sys.modules[module_name] = module
    try:
        exec(compile(materialized, str(D2_CORE_PATH), "exec"), module.__dict__)
    except Exception:
        del sys.modules[module_name]
        raise
    return ShadowSut(mutant_id, source_hash, mutant_hash, tuple(seams), module)
