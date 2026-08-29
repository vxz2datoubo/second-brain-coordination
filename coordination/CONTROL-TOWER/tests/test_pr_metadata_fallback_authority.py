import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py"
spec = importlib.util.spec_from_file_location("pr_metadata_fallback_authority", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_authority_vector_is_all_false():
    assert mod.AUTHORITY
    assert all(value is False for value in mod.AUTHORITY.values())
