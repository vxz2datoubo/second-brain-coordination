"""Backward-compatible call-shape adapter for non-Codex process starts.

Codex lanes pass a fourth verified compute-authorization argument. Existing GPT/WorkBuddy
lanes retain the historical validator call shape so R175/R184 and existing callers do not
need a meaningless trailing None.
"""


def validate_dispatch(
    repo_path: str | Path,
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
    compute_authorization_ref: str | None = None,
    claimed_compute_authorization: base.VerifiedComputeLaneAuthorization | None = None,
) -> base.VerifiedCanonicalAuthority:
    fresh = validate_canonical_authority(repo_path, claimed_snapshot)
    fresh_compute = _resolve_fresh_compute_for_dispatch(
        repo_path,
        dispatch,
        fresh,
        compute_authorization_ref,
        claimed_compute_authorization,
    )
    if fresh_compute is None:
        base.validate_dispatch(dispatch, fresh)
    else:
        base.validate_dispatch(dispatch, fresh, fresh_compute)
    return fresh


def validate_local_admission(
    repo_path: str | Path,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
    compute_authorization_ref: str | None = None,
    claimed_compute_authorization: base.VerifiedComputeLaneAuthorization | None = None,
) -> base.VerifiedCanonicalAuthority:
    fresh = validate_canonical_authority(repo_path, claimed_snapshot)
    fresh_compute = _resolve_fresh_compute_for_dispatch(
        repo_path,
        dispatch,
        fresh,
        compute_authorization_ref,
        claimed_compute_authorization,
    )
    if fresh_compute is None:
        base.validate_local_admission(admission, dispatch, fresh)
    else:
        base.validate_local_admission(admission, dispatch, fresh, fresh_compute)
    return fresh
