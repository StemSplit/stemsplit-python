"""Internal `_files.normalize_audio_input` helper."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from stemsplit_python._files import normalize_audio_input


def test_path_input_reads_bytes(tmp_path: Path) -> None:
    p = tmp_path / "song.mp3"
    p.write_bytes(b"\x00\x01\x02")
    name, ctype, raw = normalize_audio_input(p)
    assert name == "song.mp3"
    assert ctype == "audio/mpeg"
    assert raw == b"\x00\x01\x02"


def test_str_input(tmp_path: Path) -> None:
    p = tmp_path / "song.flac"
    p.write_bytes(b"\xab")
    name, ctype, _ = normalize_audio_input(str(p))
    assert ctype == "audio/flac"
    assert name == "song.flac"


def test_bytes_input_requires_filename() -> None:
    with pytest.raises(ValueError, match="file_name is required"):
        normalize_audio_input(b"raw-audio-bytes")


def test_bytes_input_with_filename_and_explicit_content_type() -> None:
    name, ctype, raw = normalize_audio_input(b"raw", file_name="x.wav", content_type="audio/wav")
    assert name == "x.wav"
    assert ctype == "audio/wav"
    assert raw == b"raw"


def test_filelike_input_with_name_attribute() -> None:
    buf = io.BytesIO(b"audio-bytes")
    buf.name = "song.opus"
    name, ctype, raw = normalize_audio_input(buf)
    assert name == "song.opus"
    assert ctype == "audio/opus"
    assert raw == b"audio-bytes"


def test_filelike_input_without_name_requires_file_name() -> None:
    with pytest.raises(ValueError, match="file_name is required"):
        normalize_audio_input(io.BytesIO(b"abc"))


def test_unsupported_type_raises() -> None:
    with pytest.raises(TypeError):
        normalize_audio_input(12345)  # type: ignore[arg-type]


def test_missing_path_raises() -> None:
    with pytest.raises(FileNotFoundError):
        normalize_audio_input(Path("/tmp/does-not-exist-stemsplit-test.mp3"))


def test_unknown_extension_falls_back_to_default() -> None:
    name, ctype, _ = normalize_audio_input(b"raw", file_name="weird.totallyunknown42")
    assert ctype == "audio/mpeg"
    assert name == "weird.totallyunknown42"
