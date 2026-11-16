"""pytest：collect / durations / rpp（契约 §8）。"""
import os
import re
import wave
from pathlib import Path

import pytest

from app.collect import collect_from_files, collect_from_folder, natural_key
from app.durations import get_duration, get_sample_rate
from app.rpp import RppItem, build_rpp, write_rpp


def make_wav(path, seconds=1.0, rate=44100):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(round(seconds * rate))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)
    return path


# ---------- collect ----------

def test_natural_key():
    assert sorted(["10", "2", "01"], key=natural_key) == ["01", "2", "10"]
    assert sorted(["B.wav", "a.wav", "C.wav"], key=natural_key) == ["a.wav", "B.wav", "C.wav"]


def test_collect_from_folder(tmp_path):
    root = tmp_path / "Project"
    root.mkdir()
    for name in ["10 Outro.wav", "2 Main.wav", "01 Intro.wav"]:
        (root / name).write_bytes(b"")
    (root / "notes.txt").write_text("x")

    sub = root / "Session 1"
    sub.mkdir()
    for name in ["take10.wav", "take2.wav", "take1.wav"]:
        (sub / name).write_bytes(b"")

    empty = root / "Empty"
    empty.mkdir()
    (empty / "readme.txt").write_text("x")

    nested = root / "Nested"
    nested.mkdir()
    (nested / "deep").mkdir()
    (nested / "deep" / "x.wav").write_bytes(b"")

    result = collect_from_folder(root)
    by_name = {g.name: g.files for g in result.groups}
    assert set(by_name) == {"Project", "Session 1"}
    assert [p.name for p in by_name["Project"]] == ["01 Intro.wav", "2 Main.wav", "10 Outro.wav"]
    assert [p.name for p in by_name["Session 1"]] == ["take1.wav", "take2.wav", "take10.wav"]


@pytest.mark.skipif(os.name == "nt", reason="Windows 文件名不允许双引号")
def test_collect_skips_quote_filename(tmp_path):
    root = tmp_path / "Q"
    root.mkdir()
    (root / 'bad"name.wav').write_bytes(b"")
    (root / "good.wav").write_bytes(b"")
    result = collect_from_folder(root)
    assert len(result.groups) == 1
    assert [p.name for p in result.groups[0].files] == ["good.wav"]
    assert any('bad"name.wav' in msg for msg in result.logs)


def test_collect_from_files_common_parent(tmp_path):
    album = tmp_path / "Album"
    album.mkdir()
    a = album / "a.wav"
    b = album / "b.mp3"
    a.write_bytes(b"")
    b.write_bytes(b"")
    result = collect_from_files([str(a), str(b)])
    assert len(result.groups) == 1
    assert result.groups[0].name == "Album"
    assert [p.name for p in result.groups[0].files] == ["a.wav", "b.mp3"]


def test_collect_from_files_no_common_parent():
    result = collect_from_files(["/tmp/x.wav", "/var/y.wav"])
    assert len(result.groups) == 1
    assert result.groups[0].name == "新工程"


def test_collect_from_files_skips_non_audio(tmp_path):
    mix = tmp_path / "Mix"
    mix.mkdir()
    a = mix / "a.wav"
    txt = mix / "b.txt"
    a.write_bytes(b"")
    txt.write_text("x")
    result = collect_from_files([str(a), str(txt)])
    assert [p.name for p in result.groups[0].files] == ["a.wav"]
    assert any("b.txt" in msg for msg in result.logs)


# ---------- durations ----------

def test_wav_duration_about_one_second(tmp_path):
    path = make_wav(tmp_path / "one.wav", seconds=1.0)
    assert abs(get_duration(path) - 1.0) < 0.05


# ---------- rpp ----------

def test_build_rpp_structure(tmp_path):
    items = [
        RppItem(path=tmp_path / "audio" / "song a.wav", length=3.5),
        RppItem(path=tmp_path / "audio" / "beat2.mp3", length=2.25),
    ]
    content = build_rpp(items, rpp_dir=tmp_path, timestamp=1234567890)

    assert "\r" not in content
    assert content.startswith('<REAPER_PROJECT 0.1 "7.0" 1234567890')
    assert content.count("<TRACK ") == 1
    assert content.count("<ITEM") == 2

    assert 'MARKER 1 0.0 "song a" 1 0 1 B {' in content
    assert 'MARKER 1 3.5 "" 1' in content
    assert 'MARKER 2 3.5 "beat2" 1 0 1 B {' in content
    assert 'MARKER 2 5.75 "" 1' in content

    assert "NAME PGM" in content
    assert "NCHAN 2" in content
    assert "FX 0" in content
    assert "TRACKID {" in content

    assert "POSITION 0.0" in content
    assert "LENGTH 3.5" in content
    assert 'NAME "song a.wav"' in content
    assert "POSITION 3.5" in content
    assert "LENGTH 2.25" in content
    assert "NAME beat2.mp3" in content

    assert 'FILE "audio/song a.wav"' in content
    assert 'FILE "audio/beat2.mp3"' in content

    guids = re.findall(r"\{[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\}", content)
    assert len(guids) == 8
    assert len(set(guids)) == 8


def test_write_rpp_lf(tmp_path):
    target = tmp_path / "out.rpp"
    write_rpp(target, "line1\nline2\n")
    data = target.read_bytes()
    assert b"\r\n" not in data
    assert data.endswith(b"\n")


def test_write_group_rpp_handles_cross_drive_value_error(tmp_path, monkeypatch):
    from app import gui

    class FakeGroup:
        name = "跨盘组"
        files = [Path("a.wav")]

    class FakeSelf:
        def __init__(self):
            self.messages = []

        def _log(self, message):
            self.messages.append(message)

    fake = FakeSelf()
    monkeypatch.setattr(gui, "get_duration", lambda path: 1.0)

    def boom(items, rpp_dir, track_name="PGM", timestamp=None, sample_rate=44100):
        raise ValueError("无法生成相对路径：音频与保存位置不在同一磁盘")

    monkeypatch.setattr(gui, "build_rpp", boom)

    result = gui.App._write_group_rpp(fake, FakeGroup(), tmp_path / "x.rpp")
    assert result is False
    assert any("无法生成相对路径" in m for m in fake.messages)


def test_normalize_rpp_suffix_double():
    from app.gui import _normalize_rpp_suffix
    assert _normalize_rpp_suffix("名称.rpp.rpp") == "名称.rpp"


def test_normalize_rpp_suffix_other_extension():
    from app.gui import _normalize_rpp_suffix
    assert _normalize_rpp_suffix("foo.wav") == "foo.wav.rpp"


def test_normalize_rpp_suffix_uppercase():
    from app.gui import _normalize_rpp_suffix
    assert _normalize_rpp_suffix("foo.RPP") == "foo.rpp"


def test_normalize_rpp_suffix_no_extension():
    from app.gui import _normalize_rpp_suffix
    assert _normalize_rpp_suffix("foo") == "foo.rpp"


def test_normalize_rpp_suffix_already_rpp():
    from app.gui import _normalize_rpp_suffix
    assert _normalize_rpp_suffix("foo.rpp") == "foo.rpp"


def test_build_rpp_sample_rate_default_and_override(tmp_path):
    content_default = build_rpp([], rpp_dir=tmp_path)
    assert "SAMPLERATE 44100 0 0" in content_default
    content_48k = build_rpp([], rpp_dir=tmp_path, sample_rate=48000)
    assert "SAMPLERATE 48000 0 0" in content_48k


def test_build_rpp_fades_have_seventh_field(tmp_path):
    content = build_rpp([RppItem(path=tmp_path / "x.wav", length=1.0)], rpp_dir=tmp_path)
    assert "FADEIN 1 0 0 1 0 0 0" in content
    assert "FADEOUT 1 0 0 1 0 0 0" in content


def test_build_rpp_master_section(tmp_path):
    content = build_rpp([], rpp_dir=tmp_path)
    assert "MASTERHWOUT 0 0 1 0 0 0 0 -1" in content
    assert "MASTER_VOLUME 1 0 -1 -1 1" in content
    assert "MASTERMUTESOLO 0" in content


def test_get_sample_rate_wav(tmp_path):
    path = make_wav(tmp_path / "sr.wav", seconds=1.0, rate=44100)
    assert get_sample_rate(path) == 44100


@pytest.mark.parametrize(
    ("filename", "expected_lines"),
    [
        ("song.wav", ["      <SOURCE WAVE", '        FILE "song.wav"']),
        ("song.aiff", ["      <SOURCE WAVE", '        FILE "song.aiff"']),
        ("song.aif", ["      <SOURCE WAVE", '        FILE "song.aif"']),
        ("song.flac", ["      <SOURCE FLAC", '        FILE "song.flac"']),
        ("song.mp3", ["      <SOURCE MP3", '        FILE "song.mp3" 1']),
        ("song.m4a", ["      <SOURCE VIDEO", "        FLIP 0 1", '        FILE "song.m4a"']),
        ("song.m4r", ["      <SOURCE VIDEO", "        FLIP 0 1", '        FILE "song.m4r"']),
        ("song.mp4", ["      <SOURCE VIDEO", "        FLIP 0 1", '        FILE "song.mp4"']),
        ("song.ogg", ["      <SOURCE VORBIS", '        FILE "song.ogg"']),
        ("song.oga", ["      <SOURCE VORBIS", '        FILE "song.oga"']),
        ("song.opus", ["      <SOURCE OPUS", '        FILE "song.opus"']),
        ("song.xyz", ["      <SOURCE WAVE", '        FILE "song.xyz"']),
    ],
)
def test_build_rpp_source_tag_by_suffix(tmp_path, filename, expected_lines):
    content = build_rpp([RppItem(path=tmp_path / filename, length=1.0)], rpp_dir=tmp_path)
    for expected in expected_lines:
        assert expected in content
