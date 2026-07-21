"""Public-safe, deterministic offline A-share research demonstration."""

from .engine import OfflineResearchRunner, ValidationError

__all__ = ["OfflineResearchRunner", "ValidationError"]
