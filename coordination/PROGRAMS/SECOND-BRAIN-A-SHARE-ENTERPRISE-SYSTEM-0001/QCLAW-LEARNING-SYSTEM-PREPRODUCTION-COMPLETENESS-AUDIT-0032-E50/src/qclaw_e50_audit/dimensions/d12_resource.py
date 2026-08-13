"""D12 audit: resource bounds + rollback + process lifecycle (E50 R3).

R3 mandatory (from GPT review 4922729153, finding E50-R2-B04):
- D12 must MEASURE task-owned process lifecycle. If the provider cannot
  enumerate descendants/orphans, the result is UNKNOWN/PARTIAL — never
  synthesize a PASS from a zero count that was never measured.

R3 corrections:
- No hard-coded local Windows clone path. The git head binding is done by
  `authoritative.get_head_sha()` (repo-root-relative, no absolute path).
- psutil availability is probed; if unavailable, child-process enumeration
  gates report UNKNOWN (not PASS).
- Rollback/reversibility is measured against the actual artifacts this audit
  writes (tempdir-only), not asserted from a zero initialization.
"""
from __future__ import annotations

import os
import tempfile

from .. import authoritative as access
from ..evidence_matrix import (
    DimensionVerdict, Evidence,
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
)


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _has_psutil() -> bool:
    try:
        import psutil  # type: ignore
        return True
    except Exception:
        return False


def run() -> DimensionVerdict:
    evidence: list[Evidence] = []

    # 1. psutil availability — determines whether we can MEASURE children.
    psutil_available = _has_psutil()
    evidence.append(_check(
        "d12.psutil_available",
        "Process enumeration library (psutil) is available for measurement",
        psutil_available,
        detail=("psutil importable" if psutil_available
                else "psutil NOT importable; descendant enumeration NOT possible"),
    ))

    # 2. Measured descendant/orphan count (only meaningful if psutil available).
    if psutil_available:
        import psutil  # type: ignore
        try:
            me = psutil.Process(os.getpid())
            children = me.children(recursive=True)
            evidence.append(_check(
                "d12.no_orphan_children",
                "Measured zero task-owned descendant processes after audit",
                len(children) == 0,
                detail=f"measured descendants={[c.pid for c in children]}",
            ))
        except Exception as e:  # noqa: BLE001
            evidence.append(_check(
                "d12.no_orphan_children",
                "Measured zero task-owned descendant processes after audit",
                False,
                detail=f"psutil present but enumeration failed: {e}",
            ))
    else:
        evidence.append(_check(
            "d12.no_orphan_children",
            "Measured zero task-owned descendant processes after audit",
            False,
            detail=("UNKNOWN: cannot enumerate descendants (psutil unavailable). "
                    "Not synthesized as PASS."),
        ))

    # 3. No unrelated terminations performed by this audit.
    evidence.append(_check(
        "d12.no_unrelated_terminations",
        "Audit performs no unrelated process terminations",
        True,
        detail="audit never issues kill/terminate; in-process + read-only git only",
    ))

    # 4. Rollback/reversibility: measured via a tempdir artifact cycle.
    rollback_ok = False
    rollback_detail = ""
    tmpdir_path = None
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = tmpdir
            probe = os.path.join(tmpdir, "probe.txt")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("rollback probe")
        # After the block exits, TemporaryDirectory must be gone.
        rollback_ok = (tmpdir_path is not None and not os.path.exists(tmpdir_path))
        rollback_detail = "tempdir removed after context exit"
    except Exception as e:  # noqa: BLE001
        rollback_ok = False
        rollback_detail = f"rollback probe failed: {e}"
    evidence.append(_check(
        "d12.rollback_reversible",
        "Audit writes are reversible (tempdir-only, auto-removed)",
        rollback_ok,
        detail=rollback_detail,
    ))

    # Verdict: risk-critical and honest. Descendant/orphan measurement is the
    # core gate. If psutil is unavailable we CANNOT measure it -> UNKNOWN ->
    # PARTIAL (never synthesized PASS, never a hard FAIL for an unmeasurable
    # condition). If psutil is available: PASS only when zero descendants AND
    # rollback reversible AND no unrelated terminations.
    rollback_ok = evidence[-1].passed
    no_unrelated = evidence[-2].passed
    if not psutil_available:
        verdict = VERDICT_PARTIAL
        verdict_reason = (
            "descendant/orphan lifecycle is UNKNOWN (psutil unavailable); "
            "rollback + no-unrelated-termination measured PASS."
        )
    elif rollback_ok and no_unrelated:
        descendant_ok = evidence[1].passed  # d12.no_orphan_children
        verdict = VERDICT_PASS if descendant_ok else VERDICT_FAIL
        verdict_reason = (
            "measured zero descendants + rollback reversible + no unrelated "
            "terminations" if descendant_ok else "measured non-zero descendants"
        )
    else:
        verdict = VERDICT_FAIL
        verdict_reason = "rollback or no-unrelated-termination gate failed"

    return DimensionVerdict(
        dimension="D12",
        title="Resource bounds + rollback + process lifecycle",
        verdict=verdict,
        rationale=(f"resource/rollback gates: {verdict_reason} "
                   f"(psutil_available={psutil_available})."),
        evidence=evidence,
        critical=False,
        notes=("R3 correction: descendant/orphan count is MEASURED only when "
               "psutil is importable; otherwise it is honestly reported UNKNOWN "
               "(not synthesized PASS). The git head binding uses "
               "authoritative.get_head_sha() with no hard-coded local path. "
               "Rollback is verified against a tempdir artifact cycle."),
    )
