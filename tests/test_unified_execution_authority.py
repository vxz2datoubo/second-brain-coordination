"""Canonical test entrypoint with compute-lane regressions layered over prior authority tests."""
from pathlib import Path as _BootstrapPath

_extension_path = _BootstrapPath(__file__).with_name("test_unified_execution_authority_compute_extension.py")
exec(compile(_extension_path.read_text(encoding="utf-8"), str(_extension_path), "exec"), globals(), globals())
del _extension_path, _BootstrapPath


def _valid_handoff_with_explicit_compute_carriers(self):
    old_auth = _verified_authority(MAIN_OLD, "old")
    new_auth = _verified_authority(MAIN_NEW, "new")
    old_dispatch = _dispatch(old_auth, carrier="WORKBUDDY_CLI_HEADLESS")
    new_dispatch = _dispatch(new_auth, carrier="WORKBUDDY_DESKTOP_INTERACTIVE")
    new_admission = _admission(new_auth, new_dispatch)
    witness = self._verified_release(old_auth)
    old = old_auth.as_mapping()
    handoff = {
        **{key: old[key] for key in mod.COMMON_IDENTITY_FIELDS},
        "from_carrier": "WORKBUDDY_CLI_HEADLESS",
        "to_carrier": "WORKBUDDY_DESKTOP_INTERACTIVE",
        "checkpoint_head_sha": "d" * 40,
        "old_writer_lease_identity": old["writer_lease_identity"],
        "new_writer_admission_required": True,
    }
    mod.validate_carrier_handoff(
        handoff,
        old_dispatch,
        old_auth,
        witness,
        new_dispatch,
        new_admission,
        new_auth,
    )


CarrierReleaseTrustBoundaryTests.test_valid_handoff_uses_verified_release_and_canonical_new_writer_identity = (
    _valid_handoff_with_explicit_compute_carriers
)
