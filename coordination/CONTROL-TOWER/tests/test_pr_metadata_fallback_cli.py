import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py"
spec = importlib.util.spec_from_file_location("pr_metadata_fallback_cli", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_cli_rejects_invalid_exact_head_without_calling_github(monkeypatch, capsys):
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("GitHub transport must not be called")

    monkeypatch.setattr(mod, "_run_gh", forbidden)
    rc = mod.main([
        "--repo", "o/r",
        "--pr", "96",
        "--expected-head", "bad",
        "--operation", "mark_ready_for_review",
    ])
    assert rc == 2
    assert called is False
    assert '"status": "FAIL_CLOSED"' in capsys.readouterr().out
