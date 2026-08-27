from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from idle_signal_scheduler import _load_r137_provider, _queue_field


EVIDENCE_SCHEMA = "ExplicitUserValueEvidence/v1"
DECLARATION_SCHEMA = "SIGNAL_USER_VALUE_DECLARATION/v1"
POLICY_VERSION = "R155/v1"
COORDINATOR_REPOSITORY = "vxz2datoubo/second-brain-coordination"
CONTROL_ISSUE = 456
REPOSITORY_OWNER = "vxz1datoubo"
MAX_COMMENT_PAGES = 20
NEUTRAL_SCORE = 50
VALUE_SCORES = {"LOW": 25, "NORMAL": 50, "HIGH": 75}
_SIGNAL_REF = re.compile(r"^signal:[A-Za-z0-9_.:-]+$")
_COMMENT_ENDPOINT = re.compile(
    rf"^/repos/{re.escape(COORDINATOR_REPOSITORY)}/issues/{CONTROL_ISSUE}/comments"
    r"\?per_page=100&page=[1-9][0-9]*$"
)


class ExplicitUserValueError(ValueError):
    """Stable fail-closed R155 declaration/evidence error."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExplicitUserValueError("INVALID_STRING", path)
    return value.strip()


def _signal(value: Any) -> str:
    signal_ref = _nonempty(value, "/signal_ref")
    if not _SIGNAL_REF.fullmatch(signal_ref):
        raise ExplicitUserValueError("SIGNAL_REF_INVALID", "/signal_ref")
    return signal_ref


def _make_observer(root: Path) -> tuple[Any, type[BaseException]]:
    provider_base, gateway_error = _load_r137_provider(root)

    class _UserValueObserver(provider_base):
        def _dynamic_domain_endpoint_allowed(self, path: str) -> bool:
            if path == f"/repos/{COORDINATOR_REPOSITORY}/issues/{CONTROL_ISSUE}":
                return True
            if _COMMENT_ENDPOINT.fullmatch(path):
                return True
            return super()._dynamic_domain_endpoint_allowed(path)

    return _UserValueObserver(), gateway_error


def _trusted_repository_owner(raw: Mapping[str, Any]) -> bool:
    user = raw.get("user")
    login = user.get("login") if isinstance(user, Mapping) else None
    association = str(raw.get("author_association", "")).upper()
    return login == REPOSITORY_OWNER and association == "OWNER"


def _evidence(
    *,
    signal_ref: str,
    status: str,
    value_class: str | None,
    declaration_ref: str | None,
    declaration_id: str | None,
    source_evidence_refs: list[str],
) -> dict[str, Any]:
    score = VALUE_SCORES[value_class] if value_class is not None else NEUTRAL_SCORE
    value: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA,
        "policy_version": POLICY_VERSION,
        "signal_ref": signal_ref,
        "status": status,
        "value_class": value_class,
        "user_value_score": score,
        "declaration_id": declaration_id,
        "declaration_ref": declaration_ref,
        "source_evidence_refs": sorted(set(source_evidence_refs)),
        "authority_boundary": {
            "creates_signal_truth": False,
            "creates_task": False,
            "selects_opportunity": False,
            "releases_task": False,
            "creates_issue": False,
            "creates_route": False,
            "creates_work_claim": False,
            "creates_worker_slot": False,
            "grants_execution_authority": False,
            "grants_domain_write": False,
            "grants_w3_write": False,
            "grants_merge_authority": False,
        },
    }
    value["evidence_digest"] = _digest(value)
    return value


def _neutral(signal_ref: str, status: str, issue_ref: str) -> dict[str, Any]:
    return _evidence(
        signal_ref=signal_ref,
        status=status,
        value_class=None,
        declaration_ref=None,
        declaration_id=None,
        source_evidence_refs=[issue_ref],
    )


def observe_explicit_user_value(
    repo_root: str | Path,
    signal_ref: str,
    *,
    observer: Any = None,
) -> dict[str, Any]:
    """Observe explicit repository-owner declarations on the fixed #456 control issue.

    The GitHub declaration is user-value attestation only. It never creates or
    replaces Signal truth. The R155 current materializer consumes this function
    only after the retained R153 path has already replay-verified canonical S0C.
    """
    signal = _signal(signal_ref)
    root = Path(repo_root).resolve()
    if observer is None:
        observer, gateway_error = _make_observer(root)
    else:
        gateway_error = Exception

    issue_path = f"/repos/{COORDINATOR_REPOSITORY}/issues/{CONTROL_ISSUE}"
    issue_ref = f"https://github.com/{COORDINATOR_REPOSITORY}/issues/{CONTROL_ISSUE}"
    try:
        _headers, issue, _meta = observer._get_json(issue_path)
    except gateway_error:
        return _neutral(signal, "PROVIDER_UNAVAILABLE_NEUTRAL", issue_ref)

    if (
        not isinstance(issue, Mapping)
        or issue.get("number") != CONTROL_ISSUE
        or issue.get("state") != "open"
    ):
        return _neutral(signal, "CONTROL_ISSUE_UNAVAILABLE_NEUTRAL", issue_ref)

    matches: list[tuple[int, str, str, str]] = []
    for page in range(1, MAX_COMMENT_PAGES + 1):
        path = (
            f"/repos/{COORDINATOR_REPOSITORY}/issues/{CONTROL_ISSUE}/comments"
            f"?per_page=100&page={page}"
        )
        try:
            _headers, payload, _meta = observer._get_json(path)
        except gateway_error:
            return _neutral(signal, "PROVIDER_UNAVAILABLE_NEUTRAL", issue_ref)
        if not isinstance(payload, list):
            raise ExplicitUserValueError("COMMENTS_PAYLOAD_INVALID")
        for raw in payload:
            if not isinstance(raw, Mapping):
                raise ExplicitUserValueError("COMMENT_INVALID")
            body = raw.get("body")
            comment_id = raw.get("id")
            if not isinstance(body, str) or not isinstance(comment_id, int):
                raise ExplicitUserValueError("COMMENT_INVALID")
            if _queue_field(body, "schema") != DECLARATION_SCHEMA:
                continue
            if _queue_field(body, "signal_id") != signal:
                continue
            if not _trusted_repository_owner(raw):
                continue
            declaration_id = _queue_field(body, "declaration_id")
            source = _queue_field(body, "source")
            value_class = _queue_field(body, "value_class")
            if (
                not declaration_id
                or source != "USER_EXPLICIT"
                or value_class not in VALUE_SCORES
            ):
                raise ExplicitUserValueError(
                    "TRUSTED_EXACT_SIGNAL_DECLARATION_INVALID",
                    f"/comments/{comment_id}",
                )
            ref = str(
                raw.get("html_url")
                or f"{issue_ref}#issuecomment-{comment_id}"
            )
            matches.append((comment_id, declaration_id, value_class, ref))
        if len(payload) < 100:
            break
    else:
        raise ExplicitUserValueError("COMMENT_PAGINATION_INCOMPLETE")

    if not matches:
        return _neutral(signal, "NO_TRUSTED_DECLARATION_NEUTRAL", issue_ref)

    comment_id, declaration_id, value_class, declaration_ref = sorted(matches)[-1]
    return _evidence(
        signal_ref=signal,
        status="VERIFIED_EXPLICIT_DECLARATION",
        value_class=value_class,
        declaration_ref=declaration_ref,
        declaration_id=declaration_id,
        source_evidence_refs=[issue_ref, declaration_ref],
    )


def explicit_user_value_ref(value: Mapping[str, Any]) -> str:
    if value.get("schema_version") != EVIDENCE_SCHEMA:
        raise ExplicitUserValueError("EVIDENCE_SCHEMA_INVALID")
    digest = value.get("evidence_digest")
    score = value.get("user_value_score")
    status = value.get("status")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ExplicitUserValueError("EVIDENCE_DIGEST_INVALID")
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise ExplicitUserValueError("EVIDENCE_SCORE_INVALID")
    if not isinstance(status, str) or not status:
        raise ExplicitUserValueError("EVIDENCE_STATUS_INVALID")
    value_class = value.get("value_class") or "NEUTRAL"
    return (
        f"r155://user-value/{digest}#policy={POLICY_VERSION};"
        f"class={value_class};score={score};status={status}"
    )
