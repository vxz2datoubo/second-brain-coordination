"""Generation adapters that are deterministic offline by default and by policy."""

from __future__ import annotations

import hashlib
from typing import Any

from .contracts import GenerationRequest, GenerationResult, canonical_json
from .director import QualityReport


class GenerationViolation(ValueError):
    """Raised before a request can cross an external-provider authority boundary."""


def _require_quality(request: GenerationRequest, report: QualityReport) -> None:
    if not report.can_generate:
        raise GenerationViolation("Generation blocked: director quality gate did not pass")
    if request.content_rating != "non_explicit":
        raise GenerationViolation("Generation blocked: only non_explicit content is permitted")


class OfflineGenerationAdapter:
    """Produce a stable reference, never a media file or network request."""

    provider = "offline"

    def generate(self, request: GenerationRequest, report: QualityReport) -> GenerationResult:
        _require_quality(request, report)
        if request.provider != self.provider:
            raise GenerationViolation("Offline adapter accepts provider=offline only")
        request_hash = hashlib.sha256(canonical_json(request.to_dict()).encode("utf-8")).hexdigest()
        return GenerationResult(
            request_id=request.request_id,
            provider=self.provider,
            status="simulated",
            output_ref="offline://creative-runtime/" + request_hash[:24],
            request_hash=request_hash,
            simulated=True,
        )


class ExternalGenerationGuard:
    """Represents Dreamina/command integrations without implementing a call path."""

    def preview(self, request: GenerationRequest, report: QualityReport) -> GenerationResult:
        """Return an auditable denial. This method never reads environment variables."""

        _require_quality(request, report)
        request_hash = hashlib.sha256(canonical_json(request.to_dict()).encode("utf-8")).hexdigest()
        if not request.confirm_generate:
            status = "blocked_confirmation_required"
        else:
            status = "blocked_route_authority"
        return GenerationResult(
            request_id=request.request_id,
            provider=request.provider,
            status=status,
            output_ref=None,
            request_hash=request_hash,
            simulated=True,
        )


def adapter_for(provider: str) -> OfflineGenerationAdapter | ExternalGenerationGuard:
    if provider == "offline":
        return OfflineGenerationAdapter()
    if provider in {"dreamina", "command"}:
        return ExternalGenerationGuard()
    raise GenerationViolation("Unknown generation provider: " + provider)
