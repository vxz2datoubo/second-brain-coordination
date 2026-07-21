"""Public-safe, synthetic-first local adapter contracts for Phase 3."""

from .contracts import (
    AdapterCapability,
    AdapterResult,
    AdapterStatus,
    CapabilityProbeAdapter,
    CredentialReference,
    InMemoryKnowledgeGateway,
    InMemoryCapabilityProbe,
    InMemoryLearningPacketAdapter,
    LocalArtifactReference,
    ManifestValidator,
    SourceManifest,
    SyntheticOfflineDatasetAdapter,
    canonical_hash,
    deserialize_contract,
    serialize_contract,
)

__all__ = [
    "AdapterCapability", "AdapterResult", "AdapterStatus", "CapabilityProbeAdapter", "InMemoryCapabilityProbe",
    "CredentialReference", "InMemoryKnowledgeGateway", "InMemoryLearningPacketAdapter",
    "LocalArtifactReference", "ManifestValidator", "SourceManifest",
    "SyntheticOfflineDatasetAdapter", "canonical_hash",
    "deserialize_contract", "serialize_contract",
]
