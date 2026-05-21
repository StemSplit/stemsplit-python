"""Top-level :class:`StemSplit` client and the placeholder
:class:`AsyncStemSplit` that points at the v0.2 milestone.
"""

from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING

from stemsplit_python._transport import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    RateLimit,
    Transport,
)
from stemsplit_python.resources.account import AccountResource
from stemsplit_python.resources.jobs import JobsResource
from stemsplit_python.resources.uploads import UploadsResource
from stemsplit_python.resources.webhooks import WebhooksResource
from stemsplit_python.resources.youtube_jobs import YouTubeJobsResource

if TYPE_CHECKING:
    import httpx


class StemSplit:
    """Synchronous client for the StemSplit API.

    Args:
        api_key: The API key. Defaults to the ``STEMSPLIT_API_KEY`` environment
            variable. Strings beginning with anything other than ``sk_live_``
            or ``sk_test_`` produce a warning, not an error.
        base_url: API base URL. Defaults to ``https://stemsplit.io/api/v1``.
        timeout: Per-request timeout. Defaults to a sane mix (10s connect,
            30s read for normal calls; 10min for uploads).
        max_retries: Number of retries on idempotent verbs and ``429``/``5xx``.
            Honors ``Retry-After``. Defaults to ``3``.
        http_client: Optional pre-built :class:`httpx.Client`. The client
            takes ownership of the underlying client only when it constructs
            it itself; user-supplied clients are not closed.

    Example::

        from pathlib import Path
        from stemsplit_python import StemSplit

        client = StemSplit(api_key="sk_live_...")
        job = client.jobs.create(audio=Path("song.mp3"), output_type="BOTH").wait()
        job.download_all("./out/")
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.Client | None = None,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get("STEMSPLIT_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Missing API key. Pass api_key= or set the STEMSPLIT_API_KEY "
                "environment variable. Get one at https://stemsplit.io/app/settings/api"
            )
        if not (resolved_key.startswith("sk_live_") or resolved_key.startswith("sk_test_")):
            warnings.warn(
                "API key does not begin with 'sk_live_' or 'sk_test_'. The server "
                "may reject requests — check your key in the dashboard.",
                stacklevel=2,
            )

        self._transport = Transport(
            api_key=resolved_key,
            base_url=base_url or DEFAULT_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
            http_client=http_client,
        )

        self.uploads = UploadsResource(self._transport)
        self.jobs = JobsResource(self._transport, self.uploads)
        self.youtube_jobs = YouTubeJobsResource(self._transport)
        self.account = AccountResource(self._transport)
        self.webhooks = WebhooksResource(self._transport)

    @property
    def base_url(self) -> str:
        return self._transport.base_url

    @property
    def last_rate_limit(self) -> RateLimit | None:
        """Latest ``X-RateLimit-*`` headers parsed from the most recent response."""

        return self._transport.last_rate_limit

    def close(self) -> None:
        """Close the underlying HTTP client (only if the SDK created it)."""

        self._transport.close()

    def __enter__(self) -> StemSplit:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncStemSplit:
    """Placeholder for the async client.

    The async surface ships in v0.2 — track progress on
    `https://github.com/StemSplit/stemsplit-python/issues`. Constructing
    this class today raises :class:`NotImplementedError`; use the sync
    :class:`StemSplit` in the meantime.
    """

    def __init__(self, *_: object, **__: object) -> None:
        raise NotImplementedError(
            "AsyncStemSplit lands in v0.2. Track the milestone at "
            "https://github.com/StemSplit/stemsplit-python/issues — for now use "
            "the sync StemSplit client."
        )


__all__ = ["AsyncStemSplit", "StemSplit"]
