# stemsplit-python

[![PyPI version](https://img.shields.io/pypi/v/stemsplit-python.svg?label=pypi&color=blue)](https://pypi.org/project/stemsplit-python/)
[![Python versions](https://img.shields.io/pypi/pyversions/stemsplit-python.svg)](https://pypi.org/project/stemsplit-python/)
[![License: MIT](https://img.shields.io/pypi/l/stemsplit-python.svg?color=green)](https://github.com/StemSplit/stemsplit-python/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/stemsplit-python.svg?color=informational)](https://pypistats.org/packages/stemsplit-python)
[![Tests](https://github.com/StemSplit/stemsplit-python/actions/workflows/test.yml/badge.svg)](https://github.com/StemSplit/stemsplit-python/actions/workflows/test.yml)
[![GitHub stars](https://img.shields.io/github/stars/StemSplit/stemsplit-python?style=social)](https://github.com/StemSplit/stemsplit-python)

**Official Python SDK for the [StemSplit](https://stemsplit.io)
stem-separation API.** Synchronous client, typed pydantic v2 models,
automatic file uploads, job-completion polling, YouTube jobs, BPM / key
detection, and a Stripe-style error hierarchy. Three runtime
dependencies. No PyTorch, no numpy, no native code.

```bash
pip install stemsplit-python
```

```python
from pathlib import Path
from stemsplit_python import StemSplit

client = StemSplit(api_key="sk_live_...")          # or set STEMSPLIT_API_KEY
job = client.jobs.create(audio=Path("song.mp3"), output_type="BOTH").wait()
job.download_all("./out/")                         # vocals.mp3 + instrumental.mp3
```

## Quick links

- **API key:** [stemsplit.io/app/settings/api](https://stemsplit.io/app/settings/api) — new accounts get [5 free minutes](https://stemsplit.io/free-trial)
- **Developer guide:** [stemsplit.io/developers/docs](https://stemsplit.io/developers/docs)
- **API reference:** [stemsplit.io/developers/reference](https://stemsplit.io/developers/reference)
- **GitHub:** [github.com/StemSplit/stemsplit-python](https://github.com/StemSplit/stemsplit-python) — source, issues, discussions
- **Changelog:** [`CHANGELOG.md`](https://github.com/StemSplit/stemsplit-python/blob/main/CHANGELOG.md)
- **Companion package:** [`demucs-onnx`](https://pypi.org/project/demucs-onnx/) — run inference locally without an API key

## Features

- **Sync client `StemSplit`** with sub-resources for every public endpoint
- **Automatic file uploads** — pass a `Path`, `bytes`, or file-like object and the SDK handles the presigned-URL dance for you
- **`job.wait()` / `job.iter_progress()` / `job.download_all()`** ergonomic helpers — no more polling loops in your code
- **YouTube jobs** — kick off a separation directly from a YouTube URL, no download step required
- **BPM and key detection** typed and surfaced on `Job.audio_metadata`
- **Webhook signature verification** in two lines, Stripe-style: `webhooks.verify_and_parse(...)`
- **Stripe-style error hierarchy** with documented error codes, `.retry_after`, `.required_seconds`, `.purchase_url` where the API exposes them
- **Retries with `Retry-After`-aware backoff** on `429` / `5xx` for safe-to-replay verbs
- **Rate-limit introspection** — every response's `X-RateLimit-*` headers parsed and exposed via `client.last_rate_limit`
- **`Idempotency-Key` passthrough** so adopters can opt-in once the server lights up support
- **Forward-compatible models** (`extra="allow"`) — server adds a new field, your code keeps running
- **Fully typed** — `py.typed` shipped, `mypy --strict` clean

## When to use this SDK vs the alternatives

| You want to … | Use |
| --- | --- |
| Call the [hosted StemSplit API](https://stemsplit.io/developers) from Python | **`stemsplit-python`** *(this package)* |
| Run HT-Demucs locally with no API key, no GPU pool, no per-minute pricing | [`demucs-onnx`](https://pypi.org/project/demucs-onnx/) — same model family, runs in pure ONNX Runtime |
| Use the API from `curl` / your own HTTP client | The [API reference](https://stemsplit.io/developers/reference) — every endpoint is straightforward JSON |
| Wire StemSplit into n8n / Zapier / Make | The [n8n node](https://stemsplit.io/developers/guides/n8n) and [no-code guides](https://stemsplit.io/developers/guides) |

## Quick start

### Install

```bash
pip install stemsplit-python                  # everything you need
pip install "stemsplit-python[dev]"           # adds pytest, ruff, mypy, respx for contributors
```

Python 3.10 / 3.11 / 3.12 / 3.13 supported on macOS, Linux, and Windows.

### Authenticate

Get an API key from [Settings → API Keys](https://stemsplit.io/app/settings/api) and either pass it explicitly or set the `STEMSPLIT_API_KEY` environment variable:

```python
from stemsplit_python import StemSplit

client = StemSplit(api_key="sk_live_...")     # explicit
client = StemSplit()                          # reads STEMSPLIT_API_KEY
```

### Separate stems from a local file

```python
from pathlib import Path
from stemsplit_python import StemSplit

client = StemSplit()

job = client.jobs.create(
    audio=Path("song.mp3"),                   # Path | str | bytes | file-like
    stems=["vocals", "instrumental"],         # subset shorthand
    quality="BEST",                           # FAST | BALANCED | BEST
    output_format="MP3",                      # MP3 | WAV | FLAC
    output_type=None,                         # …or pass output_type directly
    metadata={"customer_id": 42},             # echoed back in webhooks
    idempotency_key=None,                     # passthrough
)

print(job.id, job.status)                     # job_abc123  PENDING
final = job.wait(timeout=300, poll_interval=5)
print(final.audio_metadata.bpm, final.audio_metadata.key)
job.download_all("./out/")                    # writes vocals.mp3 + instrumental.mp3
```

### Stream progress instead of blocking

```python
for snapshot in job.iter_progress(poll_interval=2.0, timeout=300):
    print(snapshot.status, snapshot.progress)
```

### Separate from a public URL (no upload step)

```python
job = client.jobs.create(
    source_url="https://example.com/song.mp3",
    output_type="FOUR_STEMS",
).wait()
```

### Per-stem downloads

```python
job.outputs.vocals.url           # presigned URL, valid ~1h
job.outputs.vocals.expires_at    # datetime
# downloaded one-by-one if you want different paths:
client = StemSplit()
job = client.jobs.get("job_abc123").wait()
for stem, output in job.outputs.as_dict().items():
    print(stem, output.url, output.expires_at)
```

### YouTube jobs

```python
yt = client.youtube_jobs.create(
    url="https://youtube.com/watch?v=dQw4w9WgXcQ",
).wait(timeout=900)

print(yt.video_title, yt.video_duration)
print(yt.audio_metadata.bpm, yt.audio_metadata.key)
yt.download_all("./out/")        # full_audio + vocals + instrumental
```

### List + iterate jobs

```python
client.jobs.list(limit=20, status="COMPLETED")    # one page
for job in client.jobs.iter_all(status="COMPLETED"):
    print(job.id, job.progress)
```

### Account balance + rate limits

```python
balance = client.account.get()
print(balance.balance_formatted)                  # "5 minutes"

client.jobs.list(limit=1)                         # any call updates this
print(client.last_rate_limit.remaining)           # 59
```

## Webhooks

Register a subscription, capture the secret (only shown once), and verify
deliveries on your endpoint.

### Register

```python
from stemsplit_python import StemSplit

client = StemSplit()
hook = client.webhooks.create(
    url="https://your-server.com/stemsplit-webhook",
    events=["job.completed", "job.failed"],       # default if omitted
)
print(hook.secret)                                # whsec_… — save this now
client.webhooks.list()
client.webhooks.delete(hook.id)
```

### FastAPI handler

```python
import os
from fastapi import FastAPI, Request, Response
from stemsplit_python import SignatureVerificationError, webhooks

app = FastAPI()
SECRET = os.environ["STEMSPLIT_WEBHOOK_SECRET"]

@app.post("/stemsplit-webhook")
async def handle(request: Request) -> Response:
    raw = await request.body()
    try:
        event = webhooks.verify_and_parse(
            payload=raw,
            signature=request.headers["X-Webhook-Signature"],
            secret=SECRET,
        )
    except SignatureVerificationError:
        return Response(status_code=401)

    if event.event == "job.completed":
        outputs = event.data.outputs
        # download outputs.vocals.url etc. here, ideally in a background task —
        # webhook delivery has a 10-second budget.
    return Response(status_code=200)
```

### Flask handler

```python
import os
from flask import Flask, request, abort
from stemsplit_python import SignatureVerificationError, webhooks

app = Flask(__name__)
SECRET = os.environ["STEMSPLIT_WEBHOOK_SECRET"]

@app.post("/stemsplit-webhook")
def handle():
    try:
        event = webhooks.verify_and_parse(
            payload=request.data,
            signature=request.headers["X-Webhook-Signature"],
            secret=SECRET,
        )
    except SignatureVerificationError:
        abort(401)
    print(event.event, event.data.job_id)
    return ("", 200)
```

The signing scheme is HMAC-SHA256 of the raw request body. The library
takes care of constant-time comparison and accepts both `sha256=<hex>`
and bare-hex signatures.

## Error handling

Every non-2xx response from the API maps to a typed exception. The base
class is `StemSplitError` so a single `except` is enough for callers
that don't care about the distinction.

```python
from stemsplit_python import (
    StemSplit,
    AuthenticationError,
    InsufficientCreditsError,
    JobFailedError,
    RateLimitError,
)

client = StemSplit()
try:
    job = client.jobs.create(source_url="https://example.com/song.mp3").wait()
except AuthenticationError:
    raise SystemExit("API key invalid or missing — check STEMSPLIT_API_KEY")
except InsufficientCreditsError as e:
    print(f"Need {e.required_seconds}s of credit. Buy more at {e.purchase_url}")
except RateLimitError as e:
    print(f"Slow down — retry after {e.retry_after}s")
except JobFailedError as e:
    print(f"Job {e.job_id} failed: {e.error_message}")
```

| Exception | HTTP | Documented codes |
| --- | --- | --- |
| `BadRequestError` | 400 | `FILE_TOO_LARGE`, `AUDIO_TOO_LONG`, `AUDIO_TOO_SHORT`, `UNSUPPORTED_FORMAT` |
| `AuthenticationError` | 401 | `MISSING_API_KEY`, `INVALID_API_KEY` |
| `InsufficientCreditsError` | 402 | `INSUFFICIENT_CREDITS` (exposes `.required_seconds`, `.purchase_url`) |
| `PermissionDeniedError` | 403 | `API_KEY_REVOKED` |
| `NotFoundError` | 404 | `JOB_NOT_FOUND` |
| `ConflictError` | 409 | reserved |
| `UnprocessableEntityError` | 422 | reserved |
| `RateLimitError` | 429 | `RATE_LIMIT_EXCEEDED` (exposes `.retry_after`, `.limit`, `.remaining`, `.reset_at`) |
| `InternalServerError` | 5xx | server bugs / outages |
| `JobFailedError` | — | logical: surfaced by `.wait()` when status is `FAILED` |
| `JobExpiredError` | — | logical: surfaced by `.wait()` when status is `EXPIRED` |
| `SignatureVerificationError` | — | webhook signature mismatch |
| `APITimeoutError` | — | client-side timeout |
| `APIError` | — | transport-level failure (DNS, parse, …) |

## Async support

The async surface ships in **v0.2**. Tracking issue:
[github.com/StemSplit/stemsplit-python/issues](https://github.com/StemSplit/stemsplit-python/issues).
Until then, `AsyncStemSplit` is exported as a placeholder that raises
`NotImplementedError`; use the sync `StemSplit` client and offload to a
thread if you're inside an async app.

## Configuration reference

```python
StemSplit(
    api_key=None,                            # str | None — env STEMSPLIT_API_KEY
    base_url=None,                           # str | None — defaults to https://stemsplit.io/api/v1
    timeout=None,                            # float | None — read 30s, connect 10s defaults
    max_retries=3,                           # int — 429 + 5xx + safe-to-replay verbs only
    http_client=None,                        # httpx.Client | None — bring your own transport
)
```

The SDK always sends `User-Agent: stemsplit-python/<version> python/<v> httpx/<v> (<os>)`.

## Companion package — run separation locally

Want to run inference without an API key (no quotas, no per-minute
pricing, no network)? Install
[`demucs-onnx`](https://pypi.org/project/demucs-onnx/) — same model
family that powers the StemSplit production stack, exported to ONNX,
runs on CPU / CoreML / CUDA / DirectML.

```bash
pip install demucs-onnx
demucs-onnx separate song.mp3 stems/ --karaoke --mp3
```

The two packages are designed to coexist: prototype against the
local-inference path with `demucs-onnx`, then swap in `stemsplit-python`
when you need shared GPU capacity, the YouTube ingest, BPM / key
detection, or webhook delivery.

## Limits, billing, and supported formats

The hosted API caps audio at 60 minutes and 50 MB per upload, with a
60 req/min rate limit. Pricing is per second of audio processed; new
accounts get [5 free minutes](https://stemsplit.io/free-trial). See
[stemsplit.io/pricing](https://stemsplit.io/pricing) for current rates
and [the developer docs](https://stemsplit.io/developers/docs#7-limits--errors)
for the full limits table.

Supported input formats: MP3, WAV, FLAC, M4A, AAC, OGG, Opus, WebM.
Output formats: MP3, WAV, FLAC.

## Contributing

```bash
git clone https://github.com/StemSplit/stemsplit-python
cd stemsplit-python
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

ruff check src tests && ruff format --check src tests
mypy src/stemsplit_python
pytest
```

Issues, PRs, and questions are welcome at
[github.com/StemSplit/stemsplit-python](https://github.com/StemSplit/stemsplit-python).

## License

MIT — see [`LICENSE`](https://github.com/StemSplit/stemsplit-python/blob/main/LICENSE).
