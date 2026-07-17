from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import tomlkit


CODEX_HOME = Path.home() / ".codex"
CODEX_CONFIG_PATH = CODEX_HOME / "config.toml"
PROXY_ROOT = Path(r"F:\aidanao\codex_siliconflow_proxy")
STATE_DIR = PROXY_ROOT / "state"
STATE_PATH = STATE_DIR / "codex_config_state.json"

MODEL_NAME = "deepseek-v4-pro"
PROVIDER_NAME = "siliconflow_proxy"


def _load_config() -> Any:
    return tomlkit.parse(CODEX_CONFIG_PATH.read_text(encoding="utf-8"))


def _write_config(document: Any) -> None:
    CODEX_CONFIG_PATH.write_text(tomlkit.dumps(document), encoding="utf-8")


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _save_state(data: dict[str, Any]) -> None:
    _ensure_state_dir()
    STATE_PATH.write_text(
        json.dumps(data, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def enable() -> None:
    document = _load_config()
    state = {
        "model": document.get("model"),
        "model_provider": document.get("model_provider"),
        "provider": None,
    }

    provider_group = document.get("model_providers")
    if provider_group and PROVIDER_NAME in provider_group:
        state["provider"] = tomlkit.dumps(provider_group[PROVIDER_NAME])

    _save_state(state)

    document["model"] = MODEL_NAME
    document["model_provider"] = PROVIDER_NAME

    providers = document.get("model_providers")
    if providers is None:
        providers = tomlkit.table()
        document["model_providers"] = providers

    provider_table = tomlkit.table()
    provider_table["name"] = "SiliconFlow Proxy"
    provider_table["base_url"] = "http://127.0.0.1:4141/v1"
    provider_table["wire_api"] = "responses"
    provider_table["env_key"] = "CODEX_SILICONFLOW_PROXY_KEY"
    provider_table["env_key_instructions"] = "Set CODEX_SILICONFLOW_PROXY_KEY in your environment."
    providers[PROVIDER_NAME] = provider_table

    _write_config(document)
    print(f"Enabled Codex DeepSeek configuration: {CODEX_CONFIG_PATH}")


def disable() -> None:
    document = _load_config()
    state = _load_state()

    if state:
        previous_model = state.get("model")
        previous_provider = state.get("model_provider")

        if previous_model is None:
            document.pop("model", None)
        else:
            document["model"] = previous_model

        if previous_provider is None:
            document.pop("model_provider", None)
        else:
            document["model_provider"] = previous_provider

    providers = document.get("model_providers")
    if providers and PROVIDER_NAME in providers:
        providers.pop(PROVIDER_NAME)

    _write_config(document)
    print(f"Restored default Codex configuration: {CODEX_CONFIG_PATH}")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"enable", "disable"}:
        raise SystemExit("Usage: manage_codex_profile.py [enable|disable]")

    command = sys.argv[1]
    if command == "enable":
        enable()
        return

    disable()


if __name__ == "__main__":
    main()
