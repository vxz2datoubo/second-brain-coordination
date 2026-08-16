"""R136's public-safe intake, preflight, proof and closure mechanisms.

S0E has no second Signal store.  Its only durable mutations are validated
``SignalEvent`` and ``SignalLink`` appends through the accepted S0C ledger.
Everything else is a rebuildable view or a compact, evidence-bound receipt.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence

import yaml

S0C_SRC = Path(__file__).resolve().parents[3] / "S0-SYNTHETIC" / "src"
if str(S0C_SRC) not in sys.path:
    sys.path.insert(0, str(S0C_SRC))
from global_signal_plane.models import SignalEvent, SignalLink, SignalPlaneError  # noqa: E402


class GatewayError(ValueError):
    """Stable, public-safe remediation error; messages never contain source body."""
    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code, self.path = code, path


PERSISTENCE = ("EPHEMERAL", "TRACE_ONLY", "DURABLE_SIGNAL")
EXECUTION = ("DIRECT", "DOMAIN_WORKFLOW", "GOVERNED_MISSION")
MATERIALITY = ("LOW", "MATERIAL", "HIGH_RISK")
CLOSURES = ("PARTIALLY_SATISFIED", "SATISFIED", "BLOCKED", "NEEDS_REVALIDATION", "REVOKED", "SUPERSEDED")
REPOSITORY_STATE_FIELDS = frozenset({"main", "pr_heads", "reviews", "routes", "claims", "lanes", "leases", "domain_freshness"})
REQUIRED_ENVELOPE = frozenset({
    "envelope_id", "source_ref", "source_type", "source_project", "source_actor", "source_window_ref",
    "captured_at", "original_intent_ref", "public_safe_summary", "desired_effect", "problem_to_solve",
    "success_condition", "expected_problems", "risks", "assumptions", "unknowns", "dependencies",
    "evidence_refs", "counterevidence_refs", "privacy_scope_ref", "proposed_primary_domain",
    "proposed_related_domains", "epistemic_state",
})
SECRET_TOKENS = ("ghp_", "sk-", "password=", "-----begin private key", "api_key")
CAPTURE_ALIASES = ("\u5f55\u5165\u4fe1\u53f7\u5854", "\u767b\u5165\u4fe1\u53f7\u5854", "\u8bb0\u5230\u4fe1\u53f7\u5854", "\u653e\u8fdb\u4fe1\u53f7\u5854", "\u628a\u8fd9\u4e2a\u60f3\u6cd5\u5f55\u5165\u4fe1\u53f7\u5854", "\u628a\u8fd9\u4e2a\u9700\u6c42\u8bb0\u5230\u4fe1\u53f7\u5854", "capture this signal", "add this to signal tower")
NO_CAPTURE_ALIASES = ("\u4e0d\u5f55\u5165", "\u5148\u522b\u5f55", "\u53ea\u662f\u8ba8\u8bba", "\u6682\u65f6\u4e0d\u8981\u843d\u76d8", "\u4e0d\u8981\u8bb0\u5f55", "\u4e0d\u8bb0\u5f55", "\u65e0\u9700\u8bb0\u5f55", "do not capture", "don't capture", "no capture")
CANONICAL_SURFACES = (
    "coordination/PROPOSALS/PROGRAM-LANES/LANE-A-HARNESS-INTEGRATION/DEPARTMENT-CONTRACT-GRAPH.yaml",
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PROGRAM-INDEX.yaml",
    "coordination/CODEX-TASK-ROUTER.md", "coordination/TASK-BRIEFS/CODEX-GLOBAL-SIGNAL-TOWER-R136-ADAPTIVE-INTAKE-EXECUTION-GATEWAY.yaml",
    "coordination/ROUTES/CODEX-GLOBAL-SIGNAL-TOWER-R136-ADAPTIVE-INTAKE-EXECUTION-GATEWAY-R136.yaml",
    "coordination/ACTIVE-CODEX-TASK.yaml", "coordination/ACTIVE-QCLAW-TASK.yaml", "coordination/ACTIVE-WORKBUDDY-TASK.yaml",
    "coordination/ACTIVE-PROGRAM-LANES.yaml", "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
    "coordination/PROGRAM-CONTROL-TOWER.md", "coordination/PROPOSALS/PROGRAM-LANES/LANE-A-HARNESS-INTEGRATION/GLOBAL-SIGNAL-PLANE-CONTRACTS.yaml",
    "coordination/PROPOSALS/PROGRAM-LANES/LANE-A-HARNESS-INTEGRATION/GLOBAL-SIGNAL-PLANE-ENTERPRISE-GOVERNANCE.yaml",
    "coordination/PROPOSALS/PROGRAM-LANES/LANE-A-HARNESS-INTEGRATION/GLOBAL-SIGNAL-PLANE-REGRESSION-SPEC.yaml",
    "coordination/CONTROL-TOWER/R134-S0C-CLOSURE-RECONCILIATION.yaml",
)
AI_FILM_COMMIT = "44c383afd2207a97caf45b1b0da6ee1dece43a76"
AI_FILM_REPOSITORY = "vxz2datoubo/eustia-ai-film"
AI_FILM_AUTHORITY_BLOB = "a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19"
AI_FILM_DIRECTING_PATHS = (
    "PROJECT_INDEX.yaml", "10_\u8fd0\u884c\u65f6/read_sets.yaml", "10_\u8fd0\u884c\u65f6/director_route_index.yaml", "10_\u8fd0\u884c\u65f6/maturity_model.yaml",
    "01_AI\u7535\u5f71\u7cfb\u7edf/AI\u7535\u5f71\u7cfb\u7edf.md", "03_\u5267\u672c\u4e0e\u6539\u7f16/\u5f53\u524d\u6539\u7f16\u5267\u672c.md", "04_\u89d2\u8272\u4e0e\u8868\u6f14/\u89d2\u8272\u4e0e\u8868\u6f14\u8bbe\u5b9a\u5e93.md",
    "05_\u573a\u666f\u4e0e\u7a7a\u95f4/\u573a\u666f\u4e0e\u7a7a\u95f4\u8bbe\u5b9a\u5e93.md", "05_\u573a\u666f\u4e0e\u7a7a\u95f4/00_\u9879\u76ee\u5730\u56fe\u6587\u4ef6.md",
    "07_\u8fde\u7eed\u6027\u4e0e\u751f\u4ea7\u72b6\u6001/\u8fde\u7eed\u6027\u4e0e\u5f53\u524d\u751f\u4ea7\u72b6\u6001.md", "08_\u7cfb\u7edf\u5b66\u4e60/\u53cd\u9988\u53cd\u63a8\u4e0e\u7cfb\u7edf\u53cd\u54fa\u5f15\u64ce.md",
    "08_\u7cfb\u7edf\u5b66\u4e60/C-DANCE2.5\u771f\u5b9e\u751f\u6210\u53cd\u9988\u5e93.md", "10_\u8fd0\u884c\u65f6/proactive_execution_opportunity_router.yaml",
    "10_\u8fd0\u884c\u65f6/screen_observable_audible_ir_schema.yaml", "12_\u672a\u77e5\u9879/UNKNOWN_REGISTRY.yaml", "12_\u672a\u77e5\u9879/SOUND_UNKNOWN_REGISTRY.yaml",
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def instant(value: str, path: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise GatewayError("INVALID_TIMESTAMP", path) from exc
    if parsed.tzinfo is None:
        raise GatewayError("NAIVE_TIMESTAMP_FORBIDDEN", path)
    return parsed.astimezone(timezone.utc)


def public_safe(value: Any, path: str = "/") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in {"raw_source_body", "token", "password", "private_key", "secret"}:
                raise GatewayError("PRIVATE_OR_SECRET_FIELD_FORBIDDEN", f"{path}{key}")
            public_safe(child, f"{path}{key}/")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            public_safe(child, f"{path}{index}/")
    elif isinstance(value, str) and any(token in value.casefold() for token in SECRET_TOKENS):
        raise GatewayError("PRIVATE_OR_SECRET_VALUE_FORBIDDEN", path)


def semantic_capture(text: str) -> bool:
    normalized = " ".join(str(text).casefold().split())
    return not any(phrase in normalized for phrase in NO_CAPTURE_ALIASES) and any(phrase in normalized for phrase in CAPTURE_ALIASES)


def _has_any(text: str, terms: Sequence[str]) -> bool:
    normalized = str(text).casefold()
    return any(term.casefold() in normalized for term in terms)


def classify(envelope: Mapping[str, Any], request_text: str) -> dict[str, str]:
    """Derive three independent axes from request semantics; declarations only upgrade."""
    text = f"{request_text} {envelope.get('problem_to_solve', '')} {envelope.get('public_safe_summary', '')}"
    high = _has_any(text, ("high risk", "\u6743\u9650", "\u9690\u79c1", "\u751f\u4ea7", "production", "\u4ea4\u6613", "\u4e0d\u53ef\u9006", "credential"))
    governed = high or _has_any(text, ("\u7cfb\u7edf", "\u84dd\u56fe", "\u67b6\u6784", "\u6a21\u5757", "\u6b63\u5f0f\u4efb\u52a1", "system", "architecture", "module", "formal task", "skill", "rule", "cross-project"))
    film = _has_any(text, ("ai film", "\u5bfc\u6f14", "directing", "\u5267\u672c", "\u955c\u5934", "scene"))
    if governed:
        inferred = {"persistence_class": "DURABLE_SIGNAL", "execution_class": "GOVERNED_MISSION", "materiality_class": "HIGH_RISK" if high else "MATERIAL"}
    elif film:
        inferred = {"persistence_class": "TRACE_ONLY", "execution_class": "DOMAIN_WORKFLOW", "materiality_class": "LOW"}
    else:
        inferred = {"persistence_class": "EPHEMERAL", "execution_class": "DIRECT", "materiality_class": "LOW"}
    declared = {axis: envelope.get(axis) for axis in inferred}
    for axis, value in declared.items():
        choices = {"persistence_class": PERSISTENCE, "execution_class": EXECUTION, "materiality_class": MATERIALITY}[axis]
        if value is not None and value not in choices:
            raise GatewayError("INVALID_CLASSIFICATION_AXIS", f"/{axis}")
    # A user/system declaration may demand stricter handling, never downgrade the derived risk route.
    order = {"persistence_class": PERSISTENCE, "execution_class": EXECUTION, "materiality_class": MATERIALITY}
    result = dict(inferred)
    for axis, values in order.items():
        if declared[axis] is not None and values.index(str(declared[axis])) > values.index(result[axis]):
            result[axis] = str(declared[axis])
    if result["materiality_class"] == "HIGH_RISK":
        result["execution_class"], result["persistence_class"] = "GOVERNED_MISSION", "DURABLE_SIGNAL"
    if result["execution_class"] == "GOVERNED_MISSION":
        result["persistence_class"] = "DURABLE_SIGNAL"
    return result


def validate_envelope(envelope: Mapping[str, Any], request_text: str) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise GatewayError("ENVELOPE_NOT_OBJECT")
    public_safe(envelope)
    missing = sorted(REQUIRED_ENVELOPE - set(envelope))
    if missing:
        raise GatewayError("MISSING_REQUIRED_FIELD", f"/{missing[0]}")
    instant(str(envelope["captured_at"]), "/captured_at")
    for name in ("envelope_id", "source_ref", "source_project", "source_actor", "source_window_ref", "public_safe_summary", "problem_to_solve"):
        if not isinstance(envelope[name], str) or not envelope[name].strip():
            raise GatewayError("INVALID_STRING", f"/{name}")
    for name in ("expected_problems", "risks", "assumptions", "unknowns", "dependencies", "evidence_refs", "counterevidence_refs", "proposed_related_domains"):
        if not isinstance(envelope[name], list):
            raise GatewayError("INVALID_ARRAY", f"/{name}")
    result = dict(envelope); result.update(classify(envelope, request_text))
    if result["persistence_class"] == "DURABLE_SIGNAL":
        for name in ("desired_effect", "success_condition"):
            if not isinstance(result[name], str) or not result[name].strip():
                raise GatewayError("DURABLE_INTENT_FIELD_REQUIRED", f"/{name}")
    return result


def _git(root: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if result.returncode:
        raise GatewayError("EXACT_SOURCE_READ_FAILED")
    return result.stdout if binary else result.stdout.decode("utf-8", errors="strict").strip()


@dataclass(frozen=True)
class ExactReadProof:
    repository: str
    commit: str
    path: str
    blob_sha: str
    content_sha256: str
    execution_id: str
    _seal: object = field(repr=False, compare=False)

    def public_dict(self) -> dict[str, str]:
        return {"repository": self.repository, "commit": self.commit, "path": self.path,
                "blob_sha_or_equivalent_content_identity": self.blob_sha,
                "content_sha256_or_equivalent_digest": self.content_sha256, "execution_id": self.execution_id}


_PROOF_SEAL = object()
_SCAN_SEAL = object()


@dataclass(frozen=True)
class ExactScanProof:
    scan: str
    input_paths: tuple[str, ...]
    input_digest: str
    execution_id: str
    _seal: object = field(repr=False, compare=False)

    def public_dict(self) -> dict[str, Any]:
        return {"scan": self.scan, "input_paths": list(self.input_paths), "input_digest": self.input_digest, "execution_id": self.execution_id}


def execute_route_scans(*, mandatory_scans: Sequence[str], proofs: Sequence[ExactReadProof], execution_id: str) -> tuple[ExactScanProof, ...]:
    """Seal each route-required scan to the exact reads it consumed; no caller result is trusted."""
    paths = {proof.path for proof in proofs}
    scan_inputs = {
        "map_authority": {"05_场景与空间/00_项目地图文件.md"}, "world_cardinal_frame": {"05_场景与空间/00_项目地图文件.md"},
        "adjacency_and_height": {"05_场景与空间/00_项目地图文件.md"},
        "camera_anchor_resolution": {"10_运行时/scene_asset_identity_schema.yaml"}, "camera_orientation": {"10_运行时/scene_asset_identity_schema.yaml"},
        "view_resolution": {"10_运行时/scene_asset_identity_schema.yaml"}, "relation_resolution": {"10_运行时/scene_asset_identity_schema.yaml"},
        "asset_direction_tags": {"10_运行时/scene_asset_identity_schema.yaml"}, "no_legacy_id_direction_inference": {"10_运行时/scene_asset_identity_schema.yaml"},
        "current_media_version_resolution": {"10_运行时/scene_media_resolver_manifest.yaml"}, "pixel_verification_state": {"10_运行时/scene_media_resolver_manifest.yaml"},
    }
    sealed: list[ExactScanProof] = []
    for scan in mandatory_scans:
        required = scan_inputs.get(scan, set())
        if not required or not required <= paths:
            continue
        consumed = tuple(sorted(required))
        sealed.append(ExactScanProof(scan, consumed, digest([proof.public_dict() for proof in proofs if proof.path in required]), execution_id, _SCAN_SEAL))
    return tuple(sealed)


def exact_git_read_proofs(root: str | Path, *, repository: str, commit: str, paths: Sequence[str], execution_id: str) -> tuple[ExactReadProof, ...]:
    source = Path(root).resolve()
    if Path(str(_git(source, "rev-parse", "--show-toplevel"))).resolve() != source:
        raise GatewayError("SOURCE_ROOT_NOT_REPOSITORY_ROOT")
    if str(_git(source, "rev-parse", "HEAD")) != commit:
        raise GatewayError("SOURCE_REVISION_DRIFT")
    proofs: list[ExactReadProof] = []
    for path in paths:
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise GatewayError("FORBIDDEN_SOURCE_PATH")
        blob = str(_git(source, "rev-parse", f"{commit}:{path}"))
        committed = _git(source, "show", f"{commit}:{path}", binary=True)
        assert isinstance(committed, bytes)
        try:
            local = (source / path).read_bytes()
        except OSError as exc:
            raise GatewayError("SOURCE_PATH_UNREADABLE") from exc
        if local != committed:
            raise GatewayError("SOURCE_WORKTREE_PAYLOAD_MISMATCH")
        proofs.append(ExactReadProof(repository, commit, path, blob, hashlib.sha256(committed).hexdigest(), execution_id, _PROOF_SEAL))
    return tuple(proofs)


def exact_git_read_records(root: str | Path, **kwargs: Any) -> list[dict[str, str]]:
    """Compatibility projection; receipts refuse these plain dictionaries as proof."""
    return [proof.public_dict() for proof in exact_git_read_proofs(root, **kwargs)]


@dataclass(frozen=True)
class SystemAwarenessProjection:
    snapshot_ref: str
    source_revisions: tuple[tuple[str, str], ...]
    nodes: tuple[dict[str, Any], ...]
    ledger_checksum: str
    source_mode: str
    authority_granted: bool = False

    @classmethod
    def build(cls, sources: Mapping[str, Mapping[str, Any]], ledger_projection: Mapping[str, Any]) -> "SystemAwarenessProjection":
        nodes, revisions = [], []
        for ref, source in sorted(sources.items()):
            revision = source.get("revision")
            if not isinstance(revision, str) or not revision:
                raise GatewayError("AWARENESS_SOURCE_REVISION_MISSING", f"/sources/{ref}")
            revisions.append((ref, revision))
            nodes.append(_node(ref, source, revision))
        return cls._finish(nodes, revisions, ledger_projection, "SYNTHETIC_EXPLICIT_INPUT")

    @classmethod
    def from_canonical(cls, root: str | Path, ledger_projection: Mapping[str, Any], domain_observations: Sequence[Mapping[str, str]] = ()) -> "SystemAwarenessProjection":
        repo = Path(root).resolve(); nodes, revisions = [], []
        for ref in CANONICAL_SURFACES:
            payload = _git(repo, "show", f"HEAD:{ref}", binary=True); assert isinstance(payload, bytes)
            revision = str(_git(repo, "rev-parse", f"HEAD:{ref}")); revisions.append((ref, revision))
            document: Mapping[str, Any] = {}
            if ref.endswith(".yaml"):
                parsed = yaml.safe_load(payload.decode("utf-8"))
                if not isinstance(parsed, Mapping):
                    raise GatewayError("CANONICAL_SURFACE_NOT_MAPPING", f"/{ref}")
                document = parsed
            if ref.endswith("DEPARTMENT-CONTRACT-GRAPH.yaml"):
                for department in document.get("departments", []):
                    if isinstance(department, Mapping): nodes.append(_node(ref, department, revision))
            else:
                nodes.append(_node(ref, document, revision))
        for signal in ledger_projection.get("signals", []):
            if isinstance(signal, Mapping):
                nodes.append({"component_id": str(signal.get("signal_id")), "component_kind": "OPEN_SIGNAL", "source_authority_ref": "S0C_PROJECTION", "source_revision_or_commit": str(ledger_projection.get("checksum", "UNKNOWN")), "capability_refs": [], "authority_owner": "SIGNAL_TOWER", "canonical_entrypoints": [], "read_set_refs": [], "route_set_refs": [], "dependency_refs": [], "interface_refs": [], "maturity": "DERIVED", "current_phase": str(signal.get("planning_state", "UNKNOWN")), "current_route_or_claim_ref": "UNKNOWN", "read_boundary_refs": [], "write_boundary_refs": [], "regression_refs": [], "unknown_refs": [], "relevant_open_signal_refs": [str(signal.get("signal_id"))]})
        for observation in domain_observations:
            required = {"repository", "commit", "path", "blob_sha_or_equivalent_content_identity", "content_sha256_or_equivalent_digest"}
            if not required <= set(observation):
                raise GatewayError("DOMAIN_OBSERVATION_INCOMPLETE")
            ref = f"git://{observation['repository']}@{observation['commit']}/{observation['path']}"
            revisions.append((ref, observation["blob_sha_or_equivalent_content_identity"]))
            nodes.append({"component_id": observation["path"], "component_kind": "DOMAIN_READ_ONLY_SURFACE", "source_authority_ref": ref, "source_revision_or_commit": observation["commit"], "capability_refs": [], "authority_owner": "DOMAIN_OWNER", "canonical_entrypoints": [observation["path"]], "read_set_refs": [observation["path"]] if observation["path"].endswith("read_sets.yaml") else [], "route_set_refs": [observation["path"]] if observation["path"].endswith("route_index.yaml") else [], "dependency_refs": [], "interface_refs": [], "maturity": "EXACT_READ_ONLY", "current_phase": "OBSERVED", "current_route_or_claim_ref": "READ_ONLY", "read_boundary_refs": [ref], "write_boundary_refs": ["FORBIDDEN"], "regression_refs": [], "unknown_refs": [], "relevant_open_signal_refs": []})
        return cls._finish(nodes, revisions, ledger_projection, "CANONICAL_TARGETED_READ")

    @classmethod
    def _finish(cls, nodes: list[dict[str, Any]], revisions: list[tuple[str, str]], projection: Mapping[str, Any], mode: str) -> "SystemAwarenessProjection":
        checksum = str(projection.get("checksum", "UNKNOWN")); basis = {"revisions": revisions, "nodes": nodes, "ledger_checksum": checksum, "mode": mode}
        return cls(f"awareness:{digest(basis)}", tuple(revisions), tuple(nodes), checksum, mode)

    def is_current(self, root_or_sources: str | Path | Mapping[str, Mapping[str, Any]]) -> bool:
        if isinstance(root_or_sources, Mapping):
            return all(root_or_sources.get(ref, {}).get("revision") == revision for ref, revision in self.source_revisions)
        repo = Path(root_or_sources).resolve()
        try:
            return all(str(_git(repo, "rev-parse", f"HEAD:{ref}")) == revision for ref, revision in self.source_revisions)
        except GatewayError:
            return False


def _node(ref: str, source: Mapping[str, Any], revision: str) -> dict[str, Any]:
    identity = source.get("id") or source.get("component_id") or source.get("task_id") or source.get("registry_id") or source.get("program_id") or ref
    return {"component_id": str(identity), "component_kind": str(source.get("node_kind") or source.get("component_kind") or "CANONICAL_SURFACE"), "source_authority_ref": ref, "source_revision_or_commit": revision,
            "capability_refs": list(source.get("produces") or source.get("capability_refs") or []), "authority_owner": str(source.get("owner") or source.get("architecture_owner") or source.get("authority_owner") or "UNKNOWN"),
            "canonical_entrypoints": [ref], "read_set_refs": list(source.get("read_set_refs") or []), "route_set_refs": list(source.get("route_set_refs") or ([str(source.get("canonical_route"))] if source.get("canonical_route") else [])),
            "dependency_refs": list(source.get("dependencies") or source.get("requires") or []), "interface_refs": list(source.get("shared_interfaces") or []), "maturity": str(source.get("maturity") or source.get("status") or "UNKNOWN"), "current_phase": str(source.get("current_phase") or source.get("status") or "UNKNOWN"),
            "current_route_or_claim_ref": str(source.get("canonical_route") or source.get("claim_id") or "UNKNOWN"), "read_boundary_refs": list(source.get("canonical_inputs") or []), "write_boundary_refs": list(source.get("allowed_write_paths") or []), "regression_refs": list(source.get("regression_refs") or []), "unknown_refs": list(source.get("unknown_refs") or []), "relevant_open_signal_refs": []}


@dataclass(frozen=True)
class GlobalReconciliationProof:
    repository_state: Mapping[str, Any]
    awareness_snapshot_ref: str
    ledger_checksum: str
    evidence_refs: tuple[str, ...]
    receipt_ref: str
    _seal: object = field(repr=False, compare=False)


def seal_global_reconciliation(root: str | Path, awareness: SystemAwarenessProjection) -> GlobalReconciliationProof:
    """Build the only accepted preflight witness from exact canonical Git objects."""
    repo = Path(root).resolve(); commit = str(_git(repo, "rev-parse", "HEAD")); execution_id = f"r136-reconciliation:{commit[:16]}"
    proofs = exact_git_read_proofs(repo, repository="canonical/second-brain", commit=commit, paths=CANONICAL_SURFACES, execution_id=execution_id)
    by_path = {proof.path: proof for proof in proofs}
    def bound(*paths: str) -> list[str]: return [f"git://{proof.repository}@{proof.commit}/{proof.path}#blob={proof.blob_sha}" for path in paths for proof in [by_path[path]]]
    state = {
        "main": commit,
        "pr_heads": bound("coordination/ACTIVE-CODEX-TASK.yaml"),
        "reviews": bound("coordination/CONTROL-TOWER/R134-S0C-CLOSURE-RECONCILIATION.yaml"),
        "routes": bound("coordination/ROUTES/CODEX-GLOBAL-SIGNAL-TOWER-R136-ADAPTIVE-INTAKE-EXECUTION-GATEWAY-R136.yaml"),
        "claims": bound("coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml"),
        "lanes": bound("coordination/ACTIVE-PROGRAM-LANES.yaml"),
        "leases": bound("coordination/ACTIVE-CODEX-TASK.yaml"),
        "domain_freshness": [awareness.snapshot_ref],
    }
    return GlobalReconciliationProof(state, awareness.snapshot_ref, awareness.ledger_checksum, tuple(proof.public_dict()["path"] + "#blob=" + proof.blob_sha for proof in proofs), f"reconciliation:git:{commit}:{digest(state)[:16]}", _PROOF_SEAL)


@dataclass(frozen=True)
class RuntimeInvocationReceipt:
    data: Mapping[str, Any]

    @classmethod
    def build(cls, *, execution_id: str, task_class: str, domain_id: str, source_repository: str, source_commit: str,
              entry: Mapping[str, str], awareness: SystemAwarenessProjection, mandatory_reads: Sequence[str], actual_reads: Sequence[Any],
              started_at: str | None = None, completed_at: str | None = None, outcome_quality: str = "NOT_YET_OBSERVED", matched_route_refs: Sequence[str] = (), mandatory_scans: Sequence[str] = (), actual_scans: Sequence[Any] = ()) -> "RuntimeInvocationReceipt":
        started, completed = started_at or utc_now(), completed_at or utc_now(); instant(started, "/started_at"); instant(completed, "/completed_at")
        accepted: list[ExactReadProof] = [item for item in actual_reads if isinstance(item, ExactReadProof) and item._seal is _PROOF_SEAL and item.execution_id == execution_id and item.repository == source_repository and item.commit == source_commit]
        paths = {item.path for item in accepted}
        accepted_scans = [item for item in actual_scans if isinstance(item, ExactScanProof) and item._seal is _SCAN_SEAL and item.execution_id == execution_id]
        scan_names = {item.scan for item in accepted_scans}
        compliance = "PASS" if set(mandatory_reads) <= paths and set(mandatory_scans) <= scan_names else "UNVERIFIED"
        warnings = [] if compliance == "PASS" else ["MANDATORY_READ_OR_SCAN_UNPROVEN"]
        data = {"receipt_id": f"receipt:{digest([execution_id, source_commit, sorted(paths)])[:24]}", "execution_id": execution_id, "trace_id": f"trace:{digest(execution_id)[:24]}", "task_class": task_class, "domain_id": domain_id,
                "started_at": started, "completed_at": completed, "source_repository": source_repository, "source_commit": source_commit, "entry_contract_ref": entry["path"], "entry_contract_blob_or_content_digest": entry["blob_sha"], "system_awareness_snapshot_ref": awareness.snapshot_ref,
                "matched_route_refs": list(matched_route_refs), "mandatory_reads_resolved": list(mandatory_reads), "actual_reads": [item.public_dict() for item in accepted], "mandatory_scans": list(mandatory_scans), "actual_scans": [item.public_dict() for item in accepted_scans], "capability_invocations": [f"scan:{item.scan}" for item in accepted_scans],
                "ruleset_digest": digest({"entry": entry, "snapshot": awareness.snapshot_ref, "routes": list(matched_route_refs)}), "warnings": warnings, "unknowns": [] if compliance == "PASS" else ["self-declared or fabricated read metadata is not proof"], "result_ref": f"opaque://execution/{execution_id}", "validation_result": "VERIFIED" if compliance == "PASS" else "UNVERIFIED", "writeback_decision": "TRACE_ONLY", "process_compliance": compliance, "outcome_quality": outcome_quality, "evidence_refs": [f"git://{item.repository}@{item.commit}/{item.path}#blob={item.blob_sha}" for item in accepted], "privacy_scope_ref": "PUBLIC_SAFE_METADATA_ONLY"}
        return cls(data)


class SignalIntakeGateway:
    def __init__(self, ledger: Any) -> None:
        self.ledger = ledger

    def intake(self, envelope: Mapping[str, Any], *, request_text: str, explicit_capture: bool | None = None) -> dict[str, Any]:
        checked = validate_envelope(envelope, request_text)
        negative = _has_any(request_text, NO_CAPTURE_ALIASES)
        capture = False if negative else (semantic_capture(request_text) if explicit_capture is None else bool(explicit_capture))
        if not capture:
            return {"status": "NOT_CAPTURED", "reason": "EXPLICIT_NO_CAPTURE_OR_NO_EXPLICIT_SIGNAL_INTENT", "effective_state_changed": False}
        route = classify(checked, request_text)
        if route["persistence_class"] != "DURABLE_SIGNAL":
            return {"status": route["persistence_class"], "route": route, "effective_state_changed": False}
        event_id, signal_id = f"r136:{checked['envelope_id']}", f"signal:{checked['envelope_id']}"
        intent = {name: checked[name] for name in ("original_intent_ref", "public_safe_summary", "desired_effect", "problem_to_solve", "success_condition", "expected_problems", "risks", "assumptions", "unknowns", "dependencies", "evidence_refs", "counterevidence_refs", "source_window_ref", "source_project", "source_actor", "privacy_scope_ref")}
        event = SignalEvent.from_dict({"schema_version": "SignalEvent/v1", "signal_id": signal_id, "event_id": event_id, "event_source": "R136_EXPLICIT_INTAKE", "event_type": "EXPLICIT_SIGNAL_CAPTURE", "occurred_at": checked["captured_at"], "observed_at": checked["captured_at"], "source_type": checked["source_type"], "source_ref": checked["source_ref"], "source_project": checked["source_project"], "source_actor": checked["source_actor"], "primary_domain": checked["proposed_primary_domain"], "related_domains": checked["proposed_related_domains"], "signal_kind": "REQUIREMENT", "planning_state": "CAPTURED", "execution_state": "NOT_STARTED", "epistemic_state": checked["epistemic_state"], "privacy_scope_ref": checked["privacy_scope_ref"], "authority_targets": [], "touch_set": ["S0E_EXPLICIT_INTAKE"], "related_signal_refs": [], "supersedes_refs": [], "revokes_refs": [], "cross_domain_candidate": False, "summary_ref": checked["original_intent_ref"], "idempotency_key": f"r136-envelope:{checked['envelope_id']}", "payload_schema_ref": "SignalIntakeEnvelope/v1", "public_safe_metadata": {"intent_envelope": intent, "route": route}})
        receipt = self.ledger.ingest(event)
        return {"status": receipt["status"], "route": route, "event_id": event_id, "signal_id": signal_id, "ledger_receipt": receipt}

    def omission(self, signal_id: str) -> dict[str, Any]:
        return {"status": "OMISSION_NOOP", "signal_id": signal_id, "effective_state_changed": False, "revoked": False}

    def link_relation(self, left_signal_id: str, right_signal_id: str, relation_type: str, *, evidence_refs: Sequence[str], at: str) -> dict[str, Any]:
        """Append a canonical relation; it never mutates either accepted event."""
        instant(at, "/at")
        link = SignalLink.from_dict({"link_id": f"r136-link:{digest([left_signal_id, right_signal_id, relation_type, list(evidence_refs)])[:24]}", "from_signal_ref": left_signal_id, "to_signal_ref": right_signal_id, "relation_type": relation_type, "evidence_refs": list(evidence_refs), "created_at": at, "created_by": "CODEX"})
        return self.ledger.append_link(link)

    def revoke(self, signal_id: str, *, evidence_refs: Sequence[str], at: str) -> dict[str, Any]:
        instant(at, "/at")
        prior = next((item for item in reversed(self.ledger.history()) if item["signal_id"] == signal_id), None)
        if prior is None: raise GatewayError("REVOKE_TARGET_UNKNOWN")
        event_id = f"r136:revoke:{digest([signal_id, list(evidence_refs)])[:24]}"
        payload = {key: prior[key] for key in ("schema_version", "signal_id", "source_type", "source_ref", "source_project", "source_actor", "primary_domain", "related_domains", "privacy_scope_ref")}
        payload.update({"event_id": event_id, "event_source": "R136_EXPLICIT_INTAKE", "event_type": "EXPLICIT_SIGNAL_REVOKE", "occurred_at": at, "observed_at": at, "signal_kind": "REVOCATION", "planning_state": "SUPERSEDED", "execution_state": "CANCELLED", "epistemic_state": "USER_EXPLICIT", "authority_targets": [], "touch_set": ["S0E_EXPLICIT_INTAKE"], "related_signal_refs": [signal_id], "supersedes_refs": [], "revokes_refs": [signal_id], "cross_domain_candidate": False, "summary_ref": prior["summary_ref"], "source_sequence": len(self.ledger.history()) + 1, "idempotency_key": event_id, "public_safe_metadata": {"closure_state": "REVOKED", "evidence_refs": list(evidence_refs)}})
        return {"event": self.ledger.ingest(SignalEvent.from_dict(payload)), "revoked_signal": signal_id, "history_preserved": True}

    def preflight(self, *, awareness: SystemAwarenessProjection, canonical_root: str | Path | None, reconciliation_proof: Any) -> dict[str, Any]:
        if canonical_root is not None and not awareness.is_current(canonical_root): return {"status": "BLOCKED", "code": "STALE_SYSTEM_AWARENESS", "can_release": False}
        if not isinstance(reconciliation_proof, GlobalReconciliationProof) or reconciliation_proof._seal is not _PROOF_SEAL:
            return {"status": "BLOCKED", "code": "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT", "can_release": False}
        if reconciliation_proof.awareness_snapshot_ref != awareness.snapshot_ref or reconciliation_proof.ledger_checksum != awareness.ledger_checksum:
            return {"status": "BLOCKED", "code": "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT", "can_release": False}
        repository_state = reconciliation_proof.repository_state
        missing_state = sorted(REPOSITORY_STATE_FIELDS - set(repository_state))
        if missing_state:
            return {"status": "BLOCKED", "code": "REPOSITORY_STATE_SURFACE_MISSING", "path": f"/repository_state/{missing_state[0]}", "can_release": False}
        state_digest = digest(repository_state)
        events, links = self.ledger.history(), (self.ledger.current_projection() or {}).get("links", [])
        relations = _discover_relations(events, links)
        material = [item for item in relations if item["relation"] in {"CONTRADICTS", "BLOCKS", "AUTHORITY_COLLISION"}]
        decisions = _relation_decisions(relations)
        return {"status": "BLOCKED" if material else "PASS", "code": "MATERIAL_CONFLICT_UNRESOLVED" if material else None, "can_release": not material, "scan_strategy": "GLOBAL_SHALLOW + DELTA + TARGETED_DEEP + CONDITIONAL_RESEARCH", "global_shallow_surfaces": [ref for ref, _ in awareness.source_revisions], "delta": {"ledger_checksum": awareness.ledger_checksum, "repository_state": dict(repository_state)}, "targeted_deep_refs": sorted({ref for relation in relations for ref in relation["signals"]}), "conditional_research": ["UNKNOWN_CAPABILITY_REMAINS_UNKNOWN"], "relations": relations, "decisions": decisions, "reconciliation_receipt_ref": reconciliation_proof.receipt_ref, "repository_state_digest": state_digest, "exact_repository_state_refs": list(reconciliation_proof.evidence_refs), "authority_granted": False}

    def release(self, *, preflight: Mapping[str, Any], included_signal_refs: Sequence[str], awareness: SystemAwarenessProjection) -> dict[str, Any]:
        if not preflight.get("can_release"): raise GatewayError("FORMAL_RELEASE_PRECHECK_FAILED")
        latest: dict[str, Mapping[str, Any]] = {}
        for event in self.ledger.history(): latest[event["signal_id"]] = event
        selected = [latest[ref] for ref in included_signal_refs if ref in latest]
        if len(selected) != len(included_signal_refs): raise GatewayError("RELEASE_SIGNAL_REF_UNKNOWN")
        intent = [item.get("public_safe_metadata", {}).get("intent_envelope", {}) for item in selected]
        decisions = preflight.get("decisions", {})
        return {"packet_id": f"release:{digest([list(included_signal_refs), awareness.snapshot_ref, preflight['reconciliation_receipt_ref']])[:24]}", "mission_candidate_ref": f"mission-candidate:{digest(included_signal_refs)[:24]}", "included_signal_refs": list(included_signal_refs), "cluster_refs": [item["signal_id"] for item in selected], "desired_effects": [item.get("desired_effect") for item in intent], "success_conditions": [item.get("success_condition") for item in intent], "merge_keep_separate_rationale": decisions.get("merge_keep_separate_rationale", "no inferred merge"), "resolved_conflicts": [], "unresolved_conflicts": [item for item in preflight.get("relations", []) if item["relation"] in {"CONTRADICTS", "BLOCKS", "AUTHORITY_COLLISION"}], "dependencies": sorted({ref for item in intent for ref in item.get("dependencies", [])}), "can_parallel_refs": decisions.get("can_parallel_refs", []), "must_serialize_refs": decisions.get("must_serialize_refs", []), "reviewer_or_challenger_requirements": decisions.get("reviewer_or_challenger_requirements", []), "counterfactual_requirements": decisions.get("counterfactual_requirements", []), "expected_problems": [item.get("expected_problems") for item in intent], "risks": [item.get("risks") for item in intent], "unknowns": [item.get("unknowns") for item in intent] + ["CONTROL_TOWER_AUTHORIZATION_REQUIRED"], "required_capability_refs": sorted({cap for node in awareness.nodes for cap in node["capability_refs"]}), "required_read_set_refs": sorted({read for node in awareness.nodes for read in node["read_set_refs"]}), "authority_refs": sorted({node["source_authority_ref"] for node in awareness.nodes}), "exact_system_snapshot_ref": awareness.snapshot_ref, "exact_repository_state_refs": [f"{ref}#blob={revision}" for ref, revision in awareness.source_revisions], "route_claim_lane_refs": [node["source_authority_ref"] for node in awareness.nodes if "ACTIVE" in node["source_authority_ref"] or "CLAIM" in node["source_authority_ref"]], "reconciliation_receipt_ref": preflight["reconciliation_receipt_ref"], "control_tower_required": True, "execution_authorized": False}

    def assess_closure(self, *, signal_id: str, state: str, effect_evidence_refs: Sequence[str], task_done: bool, at: str) -> dict[str, Any]:
        if state not in CLOSURES: raise GatewayError("INVALID_CLOSURE_STATE", "/state")
        if state == "SATISFIED" and (not effect_evidence_refs or not task_done): raise GatewayError("SATISFACTION_EFFECT_EVIDENCE_REQUIRED")
        prior = next((item for item in reversed(self.ledger.history()) if item["signal_id"] == signal_id), None)
        if prior is None: raise GatewayError("CLOSURE_TARGET_UNKNOWN")
        payload = {key: prior[key] for key in ("schema_version", "signal_id", "source_type", "source_ref", "source_project", "source_actor", "primary_domain", "related_domains", "privacy_scope_ref")}
        event_id = f"r136:closure:{digest([signal_id, state, list(effect_evidence_refs)])[:24]}"
        payload.update({"event_id": event_id, "event_source": "R136_CLOSURE", "event_type": "SIGNAL_CLOSURE_ASSESSMENT", "occurred_at": at, "observed_at": at, "signal_kind": "STATUS", "planning_state": "CLOSED_NO_ACTION" if state == "SATISFIED" else "SUPERSEDED" if state in {"REVOKED", "SUPERSEDED"} else "CONFLICTED" if state == "BLOCKED" else "WATCH", "execution_state": "DONE" if task_done else "BLOCKED" if state == "BLOCKED" else "NOT_STARTED", "epistemic_state": "CONFIRMED_FACT" if effect_evidence_refs else "NEEDS_REVALIDATION", "authority_targets": [], "touch_set": ["S0E_CLOSURE"], "related_signal_refs": [signal_id], "supersedes_refs": [], "revokes_refs": [signal_id] if state == "REVOKED" else [], "cross_domain_candidate": False, "summary_ref": prior["summary_ref"], "source_sequence": len(self.ledger.history()) + 1, "idempotency_key": event_id, "public_safe_metadata": {"closure_state": state, "effect_evidence_refs": list(effect_evidence_refs), "task_done": task_done}})
        receipt = self.ledger.ingest(SignalEvent.from_dict(payload)); projection = self.ledger.current_projection() or {}
        return {"assessment_id": event_id, "state": state, "receipt": receipt, "active_projection_contains_signal": signal_id in (projection.get("views", {}).get("OPEN", [])), "history_retained": any(item["signal_id"] == signal_id for item in self.ledger.history()), "authorizes_promotion": False}


def _discover_relations(events: Sequence[Mapping[str, Any]], links: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for link in links:
        if isinstance(link, Mapping): found.append({"relation": str(link.get("relation_type")), "signals": [str(link.get("from_signal_ref")), str(link.get("to_signal_ref"))], "evidence_refs": list(link.get("evidence_refs", []))})
    for index, left in enumerate(events):
        for right in events[index + 1:]:
            if left["signal_id"] == right["signal_id"]: continue
            if left.get("summary_ref") == right.get("summary_ref"): found.append({"relation": "DUPLICATE", "signals": [left["signal_id"], right["signal_id"]], "evidence_refs": [left["summary_ref"]]})
            if set(left.get("touch_set", [])) & set(right.get("touch_set", [])): found.append({"relation": "SHARED_SURFACE", "signals": [left["signal_id"], right["signal_id"]], "evidence_refs": []})
            if set(left.get("authority_targets", [])) & set(right.get("authority_targets", [])): found.append({"relation": "AUTHORITY_COLLISION", "signals": [left["signal_id"], right["signal_id"]], "evidence_refs": []})
    return sorted(found, key=canonical)


def _relation_decisions(relations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    merge, serialize, parallel = [], [], []
    for relation in relations:
        pair = relation["signals"]
        if relation["relation"] == "DUPLICATE": merge.append(pair)
        elif relation["relation"] in {"CONTRADICTS", "BLOCKS", "AUTHORITY_COLLISION", "SHARED_SURFACE", "DEPENDS_ON"}: serialize.append(pair)
        else: parallel.append(pair)
    reviewers = ["REVIEWER_CANDIDATE"] if serialize else []
    return {"merge_keep_separate_rationale": "duplicate candidates require human review; conflicts serialize", "can_parallel_refs": parallel, "must_serialize_refs": serialize, "reviewer_or_challenger_requirements": reviewers, "counterfactual_requirements": ["COUNTERFACTUAL_PAIR"] if serialize else []}


@contextmanager
def temporary_exact_clone(repository_url: str, commit: str) -> Iterator[Path]:
    """Bound a child Git process and its temporary clone to one context."""
    with tempfile.TemporaryDirectory(prefix="r136-ai-film-") as temp:
        root = Path(temp) / "source"
        for args in (("clone", "--quiet", repository_url, str(root)), ("-C", str(root), "checkout", "--quiet", "--detach", commit)):
            if subprocess.run(["git", *args], capture_output=True, check=False).returncode:
                raise GatewayError("TEMPORARY_SOURCE_CLONE_FAILED")
        yield root
    if root.exists():
        raise GatewayError("BOUNDED_CLEANUP_FAILED")


DIRECTING_SELECTOR_PATHS = {
    "PROJECT_INDEX.yaml": "PROJECT_INDEX.yaml", "AI电影系统": "01_AI电影系统/AI电影系统.md", "当前改编剧本": "03_剧本与改编/当前改编剧本.md",
    "连续性与当前生产状态": "07_连续性与生产状态/连续性与当前生产状态.md", "proactive_execution_opportunity_router": "10_运行时/proactive_execution_opportunity_router.yaml",
    "角色与表演设定库": "04_角色与表演/角色与表演设定库.md", "场景与空间设定库": "05_场景与空间/场景与空间设定库.md",
    "00_项目地图文件": "05_场景与空间/00_项目地图文件.md", "scene_asset_identity_schema": "10_运行时/scene_asset_identity_schema.yaml",
    "scene_media_resolver_manifest": "10_运行时/scene_media_resolver_manifest.yaml", "反馈反推与系统反哺引擎": "08_系统学习/反馈反推与系统反哺引擎.md",
    "C-DANCE2.5真实生成反馈库": "08_系统学习/C-DANCE2.5真实生成反馈库.md",
}


def _selector_path(selector: str) -> str:
    key = selector.split("#", 1)[0]
    if "/" in key and key.endswith((".yaml", ".md")):
        return key
    if key not in DIRECTING_SELECTOR_PATHS: raise GatewayError("DIRECTING_SELECTOR_PATH_UNRESOLVED")
    return DIRECTING_SELECTOR_PATHS[key]


def _directing_requirements(read_sets: Mapping[str, Any], matched: Sequence[Mapping[str, Any]], fixture: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    directing = read_sets.get("read_sets", {}).get("directing")
    if not isinstance(directing, Mapping): raise GatewayError("DIRECTING_READ_SET_UNRESOLVED")
    selectors = list(directing.get("always", [])); conditional = directing.get("conditional", {})
    if not isinstance(conditional, Mapping): raise GatewayError("DIRECTING_READ_SET_UNRESOLVED")
    for flag, selector in conditional.items():
        if fixture.get(str(flag)) or (flag == "map" and fixture.get("spatial")) or (flag == "learning" and fixture.get("feedback")) or (flag == "model_real_generation_feedback" and fixture.get("feedback")):
            selectors.append(str(selector))
    scans: list[str] = []
    for route in matched:
        selectors.extend(map(str, route.get("mandatory_reads", [])))
        scans.extend(map(str, route.get("mandatory_scans", [])))
    return tuple(sorted({_selector_path(selector) for selector in selectors})), tuple(sorted(set(scans)))


def ai_film_directing_read_only_smoke(root: str | Path, *, awareness: SystemAwarenessProjection, fixture: Mapping[str, Any]) -> dict[str, Any]:
    execution_id = f"r136-ai-film:{digest(fixture)[:24]}"
    source = Path(root).resolve(); before = str(_git(source, "status", "--porcelain"))
    if before:
        raise GatewayError("AI_FILM_SOURCE_NOT_CLEAN")
    seed_paths = ("PROJECT_INDEX.yaml", "10_运行时/read_sets.yaml", "10_运行时/director_route_index.yaml")
    seed_proofs = exact_git_read_proofs(root, repository=AI_FILM_REPOSITORY, commit=AI_FILM_COMMIT, paths=seed_paths, execution_id=execution_id)
    if {proof.path: proof for proof in seed_proofs}["PROJECT_INDEX.yaml"].blob_sha != AI_FILM_AUTHORITY_BLOB: raise GatewayError("AI_FILM_AUTHORITY_BLOB_DRIFT")
    read_sets_bytes = _git(source, "show", f"{AI_FILM_COMMIT}:10_\u8fd0\u884c\u65f6/read_sets.yaml", binary=True); routes_bytes = _git(source, "show", f"{AI_FILM_COMMIT}:10_\u8fd0\u884c\u65f6/director_route_index.yaml", binary=True)
    assert isinstance(read_sets_bytes, bytes) and isinstance(routes_bytes, bytes)
    read_sets, route_index = yaml.safe_load(read_sets_bytes.decode("utf-8")), yaml.safe_load(routes_bytes.decode("utf-8"))
    directing = read_sets.get("read_sets", {}).get("directing") if isinstance(read_sets, Mapping) else None
    if not isinstance(directing, Mapping): raise GatewayError("DIRECTING_READ_SET_UNRESOLVED")
    symptoms = {str(item) for item in fixture.get("symptoms", [])}
    matched = [item for item in route_index.get("routes", []) if isinstance(item, Mapping) and symptoms & set(map(str, item.get("symptoms", [])))] if isinstance(route_index, Mapping) else []
    if not matched: raise GatewayError("DIRECTOR_ROUTE_UNRESOLVED")
    route_refs = [f"director-route:{item.get('id')}" for item in matched]
    mandatory_reads, mandatory_scans = _directing_requirements(read_sets, matched, fixture)
    withheld = set(map(str, fixture.get("withhold_derived_paths", [])))
    derived_proofs = exact_git_read_proofs(root, repository=AI_FILM_REPOSITORY, commit=AI_FILM_COMMIT, paths=[path for path in mandatory_reads if path not in withheld and path not in seed_paths], execution_id=execution_id)
    proofs = seed_proofs + derived_proofs
    scans = execute_route_scans(mandatory_scans=mandatory_scans, proofs=proofs, execution_id=execution_id)
    withheld_scans = set(map(str, fixture.get("withhold_scans", [])))
    scans = tuple(scan for scan in scans if scan.scan not in withheld_scans)
    receipt = RuntimeInvocationReceipt.build(execution_id=execution_id, task_class="DOMAIN_WORKFLOW", domain_id="EUSTIA_AI_FILM", source_repository=AI_FILM_REPOSITORY, source_commit=AI_FILM_COMMIT, entry={"path": "PROJECT_INDEX.yaml", "blob_sha": AI_FILM_AUTHORITY_BLOB}, awareness=awareness, mandatory_reads=mandatory_reads, actual_reads=proofs, matched_route_refs=route_refs, mandatory_scans=mandatory_scans, actual_scans=scans)
    after = str(_git(source, "status", "--porcelain"))
    if after != before: raise GatewayError("AI_FILM_ZERO_MUTATION_VIOLATION")
    return {"receipt": dict(receipt.data), "source_binding": {"repository": AI_FILM_REPOSITORY, "commit": AI_FILM_COMMIT, "authority_path": "PROJECT_INDEX.yaml", "authority_blob_sha": AI_FILM_AUTHORITY_BLOB}, "directing_read_set_resolved": True, "matched_routes": route_refs, "fixture_ref": f"opaque://ai-film-directing-fixture/{digest(fixture)}", "route": {"persistence_class": "TRACE_ONLY", "execution_class": "DOMAIN_WORKFLOW", "materiality_class": "LOW"}, "durable_signal_created": False, "domain_write_authorized": False, "raw_content_published": False, "source_status_before": "CLEAN", "source_status_after": "CLEAN"}
