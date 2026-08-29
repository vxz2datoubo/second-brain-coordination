import importlib.util
from pathlib import Path
import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py"
spec = importlib.util.spec_from_file_location("pr_metadata_fallback_exact_head", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_uppercase_or_mixed_hex_is_accepted_but_length_is_exact():
    class NeverCalled:
        def __call__(self, *args, **kwargs):
            raise mod.FallbackError("stop after SHA validation")

    with pytest.raises(mod.FallbackError, match="stop after SHA validation"):
        mod.mark_ready_for_review("o/r", 1, "A" * 40, runner=NeverCalled())
