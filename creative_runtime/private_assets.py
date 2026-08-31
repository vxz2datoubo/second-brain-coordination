"""Private-asset reference contracts; never opens images, media, or credentials."""
from __future__ import annotations
import hashlib, re
from typing import Any
from .contracts import AvatarIdentity, AvatarRevision, AppearanceContinuityRecord, canonical_json

class PrivateAssetViolation(ValueError): pass
_REF = re.compile(r"^private://[a-z0-9][a-z0-9/_-]{7,120}$")
_EVENT = re.compile(r"^evt_[a-f0-9]{20}$")

def _id(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(canonical_json(value).encode()).hexdigest()[:20]

def _private_ref(value: str) -> None:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise PrivateAssetViolation("private asset references must be opaque private:// identifiers, never paths or image bytes")

def create_avatar_identity(owner_ref: str, consent_revision: str, asset_ref: str) -> AvatarIdentity:
    _private_ref(owner_ref); _private_ref(asset_ref)
    if not consent_revision: raise PrivateAssetViolation("consent revision is required")
    avatar_id = _id("avatar_", {"owner": owner_ref, "consent": consent_revision, "asset": asset_ref})
    return AvatarIdentity(avatar_id, owner_ref, consent_revision, asset_ref, "approved_private_reference")

def create_appearance_change(identity: AvatarIdentity, command: str, role: str, asset_ref: str, approval_ref: str, effective_from_event_id: str) -> AvatarRevision:
    _private_ref(asset_ref); _private_ref(approval_ref)
    if command != "整容" or not role.strip(): raise PrivateAssetViolation("appearance revision requires explicit 整容 command and specified role")
    if not _EVENT.fullmatch(effective_from_event_id): raise PrivateAssetViolation("appearance revision needs a verified future event id")
    revision_id = _id("avatarrev_", {"avatar": identity.avatar_id, "asset": asset_ref, "event": effective_from_event_id})
    return AvatarRevision(revision_id, identity.avatar_id, asset_ref, approval_ref, effective_from_event_id, "appearance_change:" + role.strip())

def continuity_record(segment_id: str, campaign_id: str, revisions: tuple[str, ...], timeline_hash: str) -> AppearanceContinuityRecord:
    if not segment_id or not campaign_id or not revisions or not re.fullmatch(r"[a-f0-9]{64}", timeline_hash):
        raise PrivateAssetViolation("continuity record requires identifiers, cast revisions, and exact timeline hash")
    return AppearanceContinuityRecord(segment_id, campaign_id, revisions, timeline_hash, "references_verified_no_media_read")
