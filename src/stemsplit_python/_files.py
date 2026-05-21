"""Helpers for normalizing the many ways callers pass us audio data.

The public ``client.jobs.create(audio=...)`` accepts:

* ``str`` or ``pathlib.Path`` — read from disk
* ``bytes`` / ``bytearray`` — already in memory
* file-like with ``.read()`` — read once into memory

Everything is reduced to a ``(filename, content_type, raw_bytes)`` tuple.
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import IO, Any

AudioInput = str | Path | bytes | bytearray | IO[bytes]

_DEFAULT_CONTENT_TYPE = "audio/mpeg"

_EXT_TO_MIME = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".webm": "audio/webm",
}


def normalize_audio_input(
    audio: AudioInput,
    *,
    file_name: str | None = None,
    content_type: str | None = None,
) -> tuple[str, str, bytes]:
    """Return ``(filename, content_type, raw_bytes)`` for any supported input.

    Raises :class:`TypeError` for unsupported argument types and
    :class:`FileNotFoundError` for missing paths.
    """

    if isinstance(audio, (bytes, bytearray)):
        if not file_name:
            raise ValueError(
                "file_name is required when audio is raw bytes; the server "
                "needs a filename to derive the upload key."
            )
        return file_name, content_type or _guess_mime(file_name), bytes(audio)

    if isinstance(audio, (str, Path)):
        path = Path(audio)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        return (
            file_name or path.name,
            content_type or _guess_mime(path.name),
            path.read_bytes(),
        )

    read = getattr(audio, "read", None)
    if callable(read):
        data = read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError(
                f"file-like object's .read() must return bytes, got {type(data).__name__}"
            )
        derived_name = file_name or _name_from_filelike(audio)
        if not derived_name:
            raise ValueError(
                "file_name is required when audio is a file-like object without a .name attribute."
            )
        return (
            derived_name,
            content_type or _guess_mime(derived_name),
            bytes(data),
        )

    raise TypeError(
        f"Unsupported audio input type: {type(audio).__name__}. "
        "Pass a Path, str, bytes, or file-like object."
    )


def _guess_mime(name: str) -> str:
    suffix = os.path.splitext(name)[1].lower()
    return _EXT_TO_MIME.get(suffix) or mimetypes.guess_type(name)[0] or _DEFAULT_CONTENT_TYPE


def _name_from_filelike(obj: Any) -> str | None:
    name = getattr(obj, "name", None)
    if isinstance(name, str) and name:
        return os.path.basename(name)
    return None


__all__ = ["AudioInput", "normalize_audio_input"]
