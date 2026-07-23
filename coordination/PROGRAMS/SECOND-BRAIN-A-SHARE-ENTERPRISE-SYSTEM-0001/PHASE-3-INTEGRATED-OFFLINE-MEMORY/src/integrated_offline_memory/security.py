"""Credential-value and private-body guards shared by the Phase 4 gateway."""

from __future__ import annotations

import re
from typing import Any


_SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}"),
)
_SECRET_VALUE_KEYS = {
    "credential_value",
    "secret_value",
    "access_token_value",
    "token_value",
    "api_key_value",
    "password_value",
    "private_key_value",
    "cookie_value",
    "session_value",
    "broker_credential_value",
    "bank_credential_value",
}
_SECRET_SUBJECTS = (
    "token",
    "api key",
    "password",
    "cookie",
    "private key",
    "session secret",
    "broker credential",
    "bank credential",
    "令牌",
    "密钥",
    "密码",
    "私钥",
    "券商凭证",
    "银行凭证",
)
_REVEAL_ACTIONS = (
    "show my",
    "reveal",
    "print",
    "give me",
    "what is my",
    "display",
    "读取我的",
    "显示",
    "打印",
    "告诉我",
    "给我",
)


class CredentialValueDenied(ValueError):
    """Raised without echoing the value that triggered the gate."""


def contains_credential_value(value: Any) -> bool:
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in _SECRET_PATTERNS)
    if isinstance(value, (list, tuple, set)):
        return any(contains_credential_value(item) for item in value)
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold().replace(" ", "_") in _SECRET_VALUE_KEYS and item not in (None, ""):
                return True
            if contains_credential_value(item):
                return True
    return False


def assert_no_credential_value(value: Any) -> None:
    if contains_credential_value(value):
        raise CredentialValueDenied("credential_value_denied")


def query_requests_credential_value(query_text: str) -> bool:
    normalized = " ".join((query_text or "").casefold().split())
    return any(subject in normalized for subject in _SECRET_SUBJECTS) and any(
        action in normalized for action in _REVEAL_ACTIONS
    )

