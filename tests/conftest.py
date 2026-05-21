"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from stemsplit_python import StemSplit


@pytest.fixture
def api_key() -> str:
    return "sk_live_test_1234567890"


@pytest.fixture
def base_url() -> str:
    return "https://stemsplit.io/api/v1"


@pytest.fixture
def client(api_key: str, base_url: str) -> StemSplit:
    return StemSplit(api_key=api_key, base_url=base_url, max_retries=0)


@pytest.fixture
def now_iso() -> str:
    return "2026-05-21T12:00:00Z"
