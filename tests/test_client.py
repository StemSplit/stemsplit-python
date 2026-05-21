"""Top-level client behaviour: env-var defaults, key validation, ctx manager."""

from __future__ import annotations

import warnings

import pytest

from stemsplit_python import AsyncStemSplit, StemSplit


def test_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STEMSPLIT_API_KEY", raising=False)
    with pytest.raises(ValueError, match="Missing API key"):
        StemSplit()


def test_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STEMSPLIT_API_KEY", "sk_live_from_env")
    client = StemSplit()
    assert client._transport.api_key == "sk_live_from_env"
    client.close()


def test_warns_on_unrecognised_prefix() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        StemSplit(api_key="random-not-a-real-key").close()
    assert any("does not begin with" in str(w.message) for w in captured)


def test_default_base_url() -> None:
    client = StemSplit(api_key="sk_live_test")
    assert client.base_url == "https://stemsplit.io/api/v1"
    client.close()


def test_custom_base_url() -> None:
    client = StemSplit(api_key="sk_live_test", base_url="https://staging.stemsplit.io/api/v1/")
    assert client.base_url == "https://staging.stemsplit.io/api/v1"
    client.close()


def test_async_client_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match=r"v0\.2"):
        AsyncStemSplit(api_key="sk_live_test")


def test_context_manager_closes() -> None:
    with StemSplit(api_key="sk_live_test") as client:
        assert client.base_url
