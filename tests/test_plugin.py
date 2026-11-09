"""Tests for the Picard 3 plugin: manifest sanity and the real FLAC conversion."""

import hashlib
import importlib.util
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vorbis_to_id3_plugin", ROOT / "__init__.py")
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


class Log:
    def __init__(self):
        self.messages = []

    def __getattr__(self, level):
        return lambda msg, *a, **k: self.messages.append((level, str(msg)))


def test_manifest_has_required_fields():
    data = tomllib.loads((ROOT / "MANIFEST.toml").read_text(encoding="utf-8"))
    for key in ("uuid", "name", "description", "api"):
        assert data.get(key), key
    assert data["api"] == ["3.0"]
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", data["uuid"])


def _flac_bytes_md5(path):
    return FLAC(path).info.md5_signature


@pytest.fixture
def flac(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg required to create a FLAC")
    p = tmp_path / "track.flac"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-nostdin", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(p)],
        check=True,
    )
    audio = FLAC(p)
    audio["TITLE"] = "Chameleon"
    audio["ARTIST"] = ["Herbie Hancock", "Second Artist"]
    audio["ALBUM"] = "Head Hunters"
    audio["TRACKNUMBER"] = "1/4"
    audio["DISCNUMBER"] = "1/1"
    audio["DATE"] = "2012-05-01"
    audio["COMMENT"] = "a comment"
    audio["MUSICBRAINZ_ALBUMID"] = "b353f3d7-9eaa-4372-bda6-3963a042a15d"
    jpg = tmp_path / "cover.jpg"  # a real (tiny) JPEG so ffmpeg can parse the picture streams
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-nostdin", "-f", "lavfi", "-i", "color=c=red:s=32x32", "-frames:v", "1", str(jpg)],
        check=True,
    )
    pic = Picture()
    pic.type, pic.mime, pic.desc, pic.data = 3, "image/jpeg", "cover.jpg", jpg.read_bytes()
    audio.add_picture(pic)
    audio.save()
    return p


def test_copies_tags_cover_and_custom_tags(flac):
    md5_before = _flac_bytes_md5(flac)
    log = Log()
    plugin.copy_vorbis_to_id3(flac, log)
    id3 = ID3(flac)
    assert str(id3["TIT2"]) == "Chameleon"
    # ID3v2.3 has no multi-value frames: mutagen joins them with "/" (same as the Picard 2 release)
    assert str(id3["TPE1"]) == "Herbie Hancock/Second Artist"
    assert str(id3["TALB"]) == "Head Hunters"
    assert str(id3["TRCK"]) == "1"        # "1/4" -> "1", as in the Picard 2 release
    assert str(id3["TPOS"]) == "1"
    assert str(id3["TDRC"]) == "2012"     # year only
    assert id3.getall("COMM")[0].text == ["a comment"]
    apic = id3.getall("APIC")[0]
    assert apic.data.startswith(b"\xff\xd8\xff") and apic.type == 3
    assert any(f.desc.lower() == "musicbrainz_albumid" for f in id3.getall("TXXX"))
    assert id3.version == (2, 3, 0)
    # the audio and the Vorbis comments are untouched
    assert _flac_bytes_md5(flac) == md5_before
    assert FLAC(flac)["TITLE"] == ["Chameleon"]
    assert any(level == "info" and "Successfully copied" in m for level, m in log.messages)


def test_flac_stays_decodable(flac):
    plugin.copy_vorbis_to_id3(flac, Log())
    if shutil.which("ffmpeg"):
        out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(flac), "-map", "0:a", "-f", "null", "-"], capture_output=True, text=True)
        assert out.returncode == 0 and not out.stderr.strip()


def test_ignores_non_flac_and_missing(tmp_path):
    log = Log()
    plugin.copy_vorbis_to_id3(tmp_path / "x.mp3", log)
    plugin.copy_vorbis_to_id3(None, log)
    plugin.copy_vorbis_to_id3(tmp_path / "does-not-exist.flac", log)  # logged, never raises
    assert not any(level == "info" for level, _ in log.messages)


def test_picard3_hooks(flac):
    calls = {}
    api = SimpleNamespace(
        logger=Log(),
        register_file_post_save_processor=lambda fn, priority=0: calls.setdefault("fn", fn),
    )
    plugin.enable(api)
    assert calls["fn"] is plugin.on_file_saved
    plugin.on_file_saved(api, SimpleNamespace(filename=str(flac)))   # what Picard calls after Save
    assert str(ID3(flac)["TIT2"]) == "Chameleon"
